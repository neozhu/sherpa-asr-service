from dataclasses import dataclass, field
from uuid import uuid4
import numpy as np
from app.asr.audio_decoder import pcm16le_to_float32
from app.asr.recognizer import SAMPLE_RATE, RecognizerService
from app.core.config import Settings
from app.core.errors import ASRError


@dataclass
class StreamSession:
    recognizer_service: RecognizerService
    settings: Settings
    session_id: str = field(default_factory=lambda: f"asrs_{uuid4().hex[:12]}")

    def __post_init__(self) -> None:
        self.stream = self.recognizer_service.create_stream()
        self.buffered_samples = 0
        self.total_samples = 0
        self.last_text = ""

    @property
    def max_buffer_samples(self) -> int:
        return self.settings.stream_buffer_seconds * SAMPLE_RATE

    def accept_pcm16(self, frame: bytes) -> str:
        samples = pcm16le_to_float32(frame)
        self.buffered_samples += len(samples)
        self.total_samples += len(samples)
        if self.buffered_samples > self.max_buffer_samples:
            raise ASRError(400, "audio_buffer_overflow", "Audio is being sent faster than it can be processed.")
        self.stream.accept_waveform(SAMPLE_RATE, samples)
        self._decode_ready()
        self.buffered_samples = 0
        text = self.current_text()
        if text != self.last_text:
            self.last_text = text
        return text

    def _decode_ready(self) -> None:
        recognizer = self.recognizer_service.recognizer
        while recognizer.is_ready(self.stream):
            recognizer.decode_stream(self.stream)

    def current_text(self) -> str:
        result = self.recognizer_service.recognizer.get_result(self.stream)
        return getattr(result, "text", str(result)).strip()

    def commit(self) -> str:
        self.stream.input_finished()
        self._decode_ready()
        text = self.current_text()
        self.stream = self.recognizer_service.create_stream()
        self.last_text = ""
        self.buffered_samples = 0
        return text

    def endpoint_detected(self) -> bool:
        return bool(self.recognizer_service.recognizer.is_endpoint(self.stream))
