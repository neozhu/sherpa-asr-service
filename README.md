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

## Configuration

The service reads configuration from environment variables. The most important values are:

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `ASR_API_KEYS` | Yes | empty | Comma-separated API keys accepted by `Authorization: Bearer ...` for upload transcription. |
| `ASR_STREAM_TOKEN_SECRET` | Yes | `replace-with-a-long-random-secret` | Shared secret used to validate short-lived WebSocket stream tokens. Use a long random value in production. |
| `MODEL_ENCODER` | No | `/models/streaming-paraformer-zh-en/encoder.int8.onnx` | Encoder model path inside the container or host. |
| `MODEL_DECODER` | No | `/models/streaming-paraformer-zh-en/decoder.int8.onnx` | Decoder model path inside the container or host. |
| `MODEL_TOKENS` | No | `/models/streaming-paraformer-zh-en/tokens.txt` | Token file path inside the container or host. |
| `SHERPA_NUM_THREADS` | No | `4` | CPU threads used by sherpa-onnx. |
| `MAX_CONCURRENT_UPLOADS` | No | `2` | Maximum concurrent upload transcription requests. |
| `STREAM_MAX_CONNECTIONS` | No | `20` | Maximum concurrent WebSocket streams. |

## Local development and debugging

Use Python 3.12 or newer. The default local model paths point to `/models/...`, so for a source checkout you should either set the model path environment variables or create an equivalent `/models` mount/symlink.

### 1. Create a virtual environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If you also need to run the test suite, install the project with its test extras instead:

```bash
python -m pip install -e '.[test]'
```

### 2. Prepare local environment variables

```bash
export ASR_API_KEYS=current-key
export ASR_STREAM_TOKEN_SECRET=replace-with-a-long-random-secret
export MODEL_ENCODER="$PWD/models/streaming-paraformer-zh-en/encoder.int8.onnx"
export MODEL_DECODER="$PWD/models/streaming-paraformer-zh-en/decoder.int8.onnx"
export MODEL_TOKENS="$PWD/models/streaming-paraformer-zh-en/tokens.txt"
```

### 3. Start the service in debug/reload mode

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --reload
```

Verify the local process from another terminal:

```bash
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready
```

For production-like local execution without auto-reload, remove `--reload` and keep a single worker:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```


## GitHub Actions CI/CD

The repository separates CI checks and Docker image publishing into two workflows:

- `.github/workflows/quality-gate.yml` runs Python compile checks and the unit test suite on pull requests, pushes to `main`, and manual runs.
- `.github/workflows/container-publish.yml` builds the Docker image with Buildx for pull requests without publishing it, then logs in to GitHub Container Registry (GHCR) and pushes images on pushes to `main`, semantic version tags such as `v1.2.3`, and manual workflow runs.

The CI workflow uses the repository secrets `ASR_API_KEYS` and `ASR_STREAM_TOKEN_SECRET` as test-time environment variables. The container publishing workflow uses the built-in `GITHUB_TOKEN` with `packages: write` permission to log in to GHCR, so no separate package token secret is required for publishing from this repository. Keep runtime secrets out of the Docker image; pass them when running the container, for example through `.env`, Docker Compose, or your deployment platform.

Published images are tagged as:

- `ghcr.io/<owner>/<repo>:latest` for the default branch.
- `ghcr.io/<owner>/<repo>:main` for pushes to `main`.
- `ghcr.io/<owner>/<repo>:sha-<short-sha>` for traceable builds.
- `ghcr.io/<owner>/<repo>:<semver>` and `<major>.<minor>` for `v*.*.*` tags.

## Local Docker Compose deployment

The `docker-compose.yaml` file builds the service locally, publishes it on port `48732`, and mounts `./models` read-only.

Before starting, install Docker Engine or Docker Desktop with the Compose plugin and confirm it is available:

```bash
docker compose version
```

### 1. Prepare model files

On Ubuntu, download the required model files with the included script:

```bash
bash scripts/download-models.sh
```

The script creates the following layout:

```text
./models/streaming-paraformer-zh-en/encoder.int8.onnx
./models/streaming-paraformer-zh-en/decoder.int8.onnx
./models/streaming-paraformer-zh-en/tokens.txt
```

If the model directory already exists, the script stops without overwriting it. You can also place the three required files in this directory manually.

### 2. Create local environment variables

Create a `.env` file next to `docker-compose.yaml`:

```bash
cat > .env <<EOF_ENV
ASR_API_KEYS=current-key,another-key
ASR_STREAM_TOKEN_SECRET=$(openssl rand -hex 32)
EOF_ENV
```

Use a value you can retain for `ASR_API_KEYS`; clients must send it in the `Authorization: Bearer ...` header.

### 3. Build and start the service

```bash
docker compose up --build -d
```

Check container status and logs:

```bash
docker compose ps
docker compose logs -f sherpa-asr
```

### 4. Verify readiness

```bash
curl http://127.0.0.1:48732/health/live
curl http://127.0.0.1:48732/health/ready
```

The service is ready when `/health/ready` returns `ready: true`.

### 5. Stop or upgrade

```bash
# Stop the service
docker compose down

# Pull code changes, rebuild, and restart
git pull
docker compose up --build -d
```

## Client integration

### Upload transcription by cURL

Use `multipart/form-data` with the audio file field named `file`. Supported file formats depend on `ffmpeg`; common formats such as WAV, MP3, M4A, and FLAC are accepted.

```bash
curl -X POST http://127.0.0.1:48732/v1/audio/transcriptions \
  -H 'Authorization: Bearer current-key' \
  -F 'file=@sample.wav' \
  -F 'language=auto' \
  -F 'response_format=json'
```

Use `response_format=text` for a plain text response:

```bash
curl -X POST http://127.0.0.1:48732/v1/audio/transcriptions \
  -H 'Authorization: Bearer current-key' \
  -F 'file=@sample.wav' \
  -F 'response_format=text'
```

### Upload transcription by Python

```python
import requests

base_url = "http://127.0.0.1:48732"
api_key = "current-key"

with open("sample.wav", "rb") as audio:
    response = requests.post(
        f"{base_url}/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {api_key}"},
        files={"file": ("sample.wav", audio, "audio/wav")},
        data={"language": "auto", "response_format": "json"},
        timeout=120,
    )

response.raise_for_status()
print(response.json())
```

### Upload transcription by JavaScript/TypeScript

Node.js 18+ includes `fetch`, `FormData`, and `Blob` APIs.

```ts
import { readFile } from "node:fs/promises";

const baseUrl = "http://127.0.0.1:48732";
const apiKey = "current-key";
const audio = await readFile("sample.wav");

const form = new FormData();
form.append("file", new Blob([audio], { type: "audio/wav" }), "sample.wav");
form.append("language", "auto");
form.append("response_format", "json");

const response = await fetch(`${baseUrl}/v1/audio/transcriptions`, {
  method: "POST",
  headers: { Authorization: `Bearer ${apiKey}` },
  body: form,
});

if (!response.ok) {
  throw new Error(`ASR request failed: ${response.status} ${await response.text()}`);
}

console.log(await response.json());
```

### Streaming transcription protocol

The WebSocket endpoint accepts raw binary frames containing mono PCM16 little-endian audio at 16 kHz. Authentication uses the WebSocket subprotocol list:

```text
asr.v1, bearer.<stream-token>
```

A stream token is `base64url(payload).base64url(hmac_sha256(secret, base64url(payload)))`, where the JSON payload contains:

```json
{"scope":"asr:stream","exp":1893456000,"nonce":"random-nonce"}
```

After connecting:

1. Send a JSON start message: `{"type":"start","sample_rate":16000,"encoding":"pcm_s16le","language":"auto"}`.
2. Send binary PCM16 frames. A typical frame size is 20-100 ms, for example 3200 bytes for 100 ms at 16 kHz mono PCM16.
3. Receive JSON messages: `started`, `partial`, `final`, `completed`, or `error`.
4. Send `{"type":"commit"}` to force a final segment, or `{"type":"stop"}` to finish the stream.

### Streaming token helper in Python

```python
import base64
import hashlib
import hmac
import json
import time
import uuid


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def create_stream_token(secret: str, ttl_seconds: int = 60) -> str:
    payload = {
        "scope": "asr:stream",
        "exp": int(time.time()) + ttl_seconds,
        "nonce": uuid.uuid4().hex,
    }
    body = b64url(json.dumps(payload, separators=(",", ":")).encode())
    signature = b64url(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}"
```

### Streaming transcription by Python

This example converts an audio file to the required PCM16 stream with `ffmpeg`, sends it to the service, and prints server events.

```python
import asyncio
import json
import subprocess
import websockets

# Reuse create_stream_token from the previous example.

base_url = "ws://127.0.0.1:48732"
secret = "replace-with-a-long-random-secret-at-least-32-bytes"
token = create_stream_token(secret)


async def stream_file(path: str) -> None:
    ffmpeg = subprocess.Popen(
        [
            "ffmpeg",
            "-i", path,
            "-f", "s16le",
            "-acodec", "pcm_s16le",
            "-ac", "1",
            "-ar", "16000",
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    async with websockets.connect(
        f"{base_url}/v1/audio/transcriptions/stream",
        subprotocols=["asr.v1", f"bearer.{token}"],
    ) as websocket:
        await websocket.send(json.dumps({
            "type": "start",
            "sample_rate": 16000,
            "encoding": "pcm_s16le",
            "language": "auto",
        }))

        async def receive_events() -> None:
            async for message in websocket:
                print(message)

        receiver = asyncio.create_task(receive_events())
        assert ffmpeg.stdout is not None
        while chunk := ffmpeg.stdout.read(3200):
            await websocket.send(chunk)
            await asyncio.sleep(0.1)

        await websocket.send(json.dumps({"type": "stop"}))
        await receiver


asyncio.run(stream_file("sample.wav"))
```

## Error response format

HTTP and WebSocket errors use this shape:

```json
{
  "error": {
    "code": "authentication_failed",
    "message": "Invalid API key."
  }
}
```
