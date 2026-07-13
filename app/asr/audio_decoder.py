import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import BinaryIO
import numpy as np
from app.core.config import Settings
from app.core.errors import ASRError

SUPPORTED_EXTENSIONS = {".wav", ".webm", ".mp3", ".m4a", ".aac", ".ogg", ".flac"}


def validate_supported_filename(filename: str | None) -> None:
    suffix = Path(filename or "").suffix.lower()
    if suffix and suffix not in SUPPORTED_EXTENSIONS:
        raise ASRError(415, "unsupported_audio_format", "Unsupported audio format.")


async def write_upload_to_temp(file: BinaryIO, filename: str | None, settings: Settings) -> Path:
    validate_supported_filename(filename)
    total = 0
    suffix = Path(filename or "upload").suffix[:16]
    tmp = tempfile.NamedTemporaryFile(prefix="asr_upload_", suffix=suffix, delete=False)
    path = Path(tmp.name)
    try:
        while chunk := file.read(1024 * 1024):
            total += len(chunk)
            if total > settings.max_upload_size_bytes:
                raise ASRError(413, "file_too_large", "Upload exceeds size limit.")
            tmp.write(chunk)
    finally:
        tmp.close()
    return path


def decode_audio_file(path: Path, timeout_seconds: int) -> np.ndarray:
    command = [
        "ffmpeg",
        "-nostdin",
        "-v",
        "error",
        "-i",
        str(path),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "f32le",
        "pipe:1",
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        raise ASRError(504, "transcription_timeout", "Speech recognition timed out.") from exc
    except subprocess.CalledProcessError as exc:
        raise ASRError(400, "invalid_audio", "The uploaded audio could not be decoded.") from exc
    if not result.stdout:
        raise ASRError(400, "invalid_audio", "The uploaded audio could not be decoded.")
    return np.frombuffer(result.stdout, dtype=np.float32).copy()


def pcm16le_to_float32(frame: bytes) -> np.ndarray:
    if len(frame) % 2:
        raise ASRError(400, "invalid_audio_frame", "Expected mono PCM16 audio at 16000 Hz.")
    return (np.frombuffer(frame, dtype="<i2").astype(np.float32) / 32768.0).copy()


async def decode_audio_file_async(path: Path, timeout_seconds: int) -> np.ndarray:
    return await asyncio.to_thread(decode_audio_file, path, timeout_seconds)
