# sherpa-asr-service

A lightweight, CPU-based Speech-to-Text service using `k2-fsa/sherpa-onnx` for uploaded audio and live microphone transcription.

## Endpoints

- `POST /v1/audio/transcriptions` — multipart upload transcription; requires `Authorization: Bearer <api-key>`.
- `WebSocket /v1/audio/transcriptions/stream` — raw PCM16, 16 kHz, mono streaming transcription with short-lived HMAC tokens.
- `GET /health/live` — liveness.
- `GET /health/ready` — model readiness and active load.
- `GET /metrics` — optional Prometheus metrics when enabled.

## Runtime

The service is designed for one Uvicorn worker, one loaded `sherpa_onnx.OnlineRecognizer`, bounded upload concurrency, and bounded WebSocket stream buffers.

## Model files

Place the INT8 streaming paraformer zh/en model files at:

```text
models/streaming-paraformer-zh-en/
├── encoder.int8.onnx
├── decoder.int8.onnx
└── tokens.txt
```

or override `MODEL_ENCODER`, `MODEL_DECODER`, and `MODEL_TOKENS`.

## Local run

```bash
pip install -e '.[test]'
export ASR_API_KEYS=current-key
export ASR_STREAM_TOKEN_SECRET=replace-with-a-long-random-secret
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

## Docker

```bash
docker compose up --build
```

The compose file publishes the service on `127.0.0.1:48732` and mounts `./models` read-only.
