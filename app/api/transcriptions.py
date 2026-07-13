import time
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import PlainTextResponse
from app.asr.audio_decoder import decode_audio_file_async, write_upload_to_temp
from app.asr.recognizer import SAMPLE_RATE
from app.core.authentication import require_api_key
from app.core.errors import ASRError
from app.core import metrics

router = APIRouter(prefix="/v1/audio", dependencies=[Depends(require_api_key)])


@router.post("/transcriptions")
async def transcribe(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form("auto"),
    response_format: str = Form("json"),
):
    if language not in {"auto", "zh", "en"} or response_format not in {"json", "text"}:
        raise ASRError(400, "invalid_request", "Invalid request.")
    state = request.app.state
    if not state.recognizer_service.ready:
        raise ASRError(503, "model_unavailable", "Model is not ready.")
    if state.upload_semaphore.locked():
        raise ASRError(429, "service_busy", "Concurrency limit reached.")
    path: Path | None = None
    start = time.perf_counter()
    await state.upload_semaphore.acquire()
    state.active_uploads += 1
    metrics.upload_requests.inc()
    try:
        path = await write_upload_to_temp(file.file, file.filename, state.settings)
        samples = await decode_audio_file_async(path, min(30, state.settings.upload_timeout_seconds))
        duration = len(samples) / SAMPLE_RATE
        if duration > state.settings.max_audio_duration_seconds:
            raise ASRError(413, "audio_too_long", "Audio exceeds duration limit.")
        text = await request.app.state.loop.run_in_executor(None, state.recognizer_service.transcribe, samples)
        processing_time = time.perf_counter() - start
        metrics.upload_duration.observe(processing_time)
        if response_format == "text":
            return PlainTextResponse(text)
        return {"text": text, "duration": round(duration, 3), "processing_time": round(processing_time, 3)}
    except ASRError as exc:
        metrics.upload_errors.labels(exc.code).inc()
        raise
    except Exception as exc:
        metrics.upload_errors.labels("transcription_failed").inc()
        raise ASRError(500, "transcription_failed", "Transcription failed.") from exc
    finally:
        state.active_uploads -= 1
        state.upload_semaphore.release()
        if path:
            path.unlink(missing_ok=True)
