import asyncio
import json
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.asr.stream_session import StreamSession
from app.core.authentication import token_from_subprotocol, validate_stream_token
from app.core.errors import ASRError
from app.core import metrics

router = APIRouter(prefix="/v1/audio")


async def send_error(websocket: WebSocket, code: str, message: str) -> None:
    await websocket.send_json({"type": "error", "error": {"code": code, "message": message}})


@router.websocket("/transcriptions/stream")
async def stream(websocket: WebSocket):
    state = websocket.app.state
    protocols = websocket.headers.get("sec-websocket-protocol", "")
    token = token_from_subprotocol([p.strip() for p in protocols.split(",") if p.strip()])
    try:
        if not state.recognizer_service.ready:
            raise ASRError(503, "model_unavailable", "Model is not ready.")
        if state.active_streams >= state.settings.stream_max_connections:
            raise ASRError(429, "service_busy", "Concurrency limit reached.")
        if not token:
            raise ASRError(401, "invalid_session_token", "Invalid streaming token.")
        validate_stream_token(token, state.settings.asr_stream_token_secret)
    except ASRError as exc:
        await websocket.accept(subprotocol="asr.v1")
        await send_error(websocket, exc.code, exc.message)
        await websocket.close(code=1008)
        metrics.stream_errors.labels(exc.code).inc()
        return

    await websocket.accept(subprotocol="asr.v1")
    state.active_streams += 1
    metrics.stream_connections.inc()
    metrics.stream_connections_total.inc()
    session: StreamSession | None = None
    started_at = time.monotonic()
    try:
        first = await asyncio.wait_for(websocket.receive_text(), timeout=state.settings.stream_idle_timeout_seconds)
        try:
            start_msg = json.loads(first)
        except json.JSONDecodeError as exc:
            raise ASRError(400, "invalid_request", "Invalid request.") from exc
        if start_msg.get("type") != "start":
            raise ASRError(400, "invalid_request", "First message must be start.")
        if start_msg.get("sample_rate") != 16000:
            raise ASRError(400, "unsupported_sample_rate", "Only 16000 Hz audio is supported.")
        if start_msg.get("encoding") != "pcm_s16le":
            raise ASRError(400, "unsupported_encoding", "Only pcm_s16le audio is supported.")
        if start_msg.get("language", "auto") not in {"auto", "zh", "en"}:
            raise ASRError(400, "invalid_request", "Invalid request.")
        session = StreamSession(state.recognizer_service, state.settings)
        await websocket.send_json({"type": "started", "session_id": session.session_id})
        while True:
            if time.monotonic() - started_at > state.settings.stream_max_duration_seconds:
                raise ASRError(400, "stream_duration_exceeded", "Streaming duration exceeded.")
            message = await asyncio.wait_for(websocket.receive(), timeout=state.settings.stream_idle_timeout_seconds)
            if "bytes" in message and message["bytes"] is not None:
                frame = message["bytes"]
                if len(frame) > state.settings.stream_max_message_bytes:
                    raise ASRError(400, "invalid_audio_frame", "Expected mono PCM16 audio at 16000 Hz.")
                text = session.accept_pcm16(frame)
                if text:
                    await websocket.send_json({"type": "partial", "text": text})
                if session.endpoint_detected():
                    await websocket.send_json({"type": "final", "text": session.commit()})
                continue
            if "text" in message and message["text"] is not None:
                data = json.loads(message["text"])
                if data.get("type") == "commit":
                    await websocket.send_json({"type": "final", "text": session.commit()})
                elif data.get("type") == "stop":
                    await websocket.send_json({"type": "completed", "text": session.current_text()})
                    await websocket.close()
                    return
                else:
                    raise ASRError(400, "invalid_request", "Invalid request.")
    except WebSocketDisconnect:
        return
    except asyncio.TimeoutError:
        await send_error(websocket, "stream_idle_timeout", "Streaming connection was idle too long.")
        metrics.stream_errors.labels("stream_idle_timeout").inc()
        await websocket.close(code=1008)
    except ASRError as exc:
        await send_error(websocket, exc.code, exc.message)
        metrics.stream_errors.labels(exc.code).inc()
        await websocket.close(code=1008)
    finally:
        state.active_streams -= 1
        metrics.stream_connections.dec()
