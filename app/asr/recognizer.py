from pathlib import Path
import numpy as np
from app.core.config import Settings

SAMPLE_RATE = 16000


class RecognizerService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.recognizer = None
        self.ready = False
        self.error: str | None = None

    def validate_model_files(self) -> None:
        for path in (self.settings.model_encoder, self.settings.model_decoder, self.settings.model_tokens):
            if not Path(path).is_file():
                raise FileNotFoundError(path)

    def start(self) -> None:
        try:
            self.validate_model_files()
            import sherpa_onnx
            self.recognizer = sherpa_onnx.OnlineRecognizer.from_paraformer(
                tokens=self.settings.model_tokens,
                encoder=self.settings.model_encoder,
                decoder=self.settings.model_decoder,
                num_threads=self.settings.sherpa_num_threads,
                provider=self.settings.sherpa_provider,
                decoding_method=self.settings.sherpa_decoding_method,
                enable_endpoint_detection=True,
                rule1_min_trailing_silence=self.settings.endpoint_rule1_min_trailing_silence,
                rule2_min_trailing_silence=self.settings.endpoint_rule2_min_trailing_silence,
                rule3_min_utterance_length=self.settings.endpoint_rule3_min_utterance_length,
            )
            stream = self.create_stream()
            stream.accept_waveform(SAMPLE_RATE, np.zeros(SAMPLE_RATE // 10, dtype=np.float32))
            while self.recognizer.is_ready(stream):
                self.recognizer.decode_stream(stream)
            self.ready = True
            self.error = None
        except Exception as exc:
            self.ready = False
            self.error = exc.__class__.__name__

    def stop(self) -> None:
        self.ready = False
        self.recognizer = None

    def create_stream(self):
        if not self.recognizer:
            raise RuntimeError("Recognizer is not initialized")
        return self.recognizer.create_stream()

    def transcribe(self, samples: np.ndarray) -> str:
        stream = self.create_stream()
        chunk = SAMPLE_RATE // 2
        for start in range(0, len(samples), chunk):
            stream.accept_waveform(SAMPLE_RATE, samples[start : start + chunk])
            while self.recognizer.is_ready(stream):
                self.recognizer.decode_stream(stream)
        stream.input_finished()
        while self.recognizer.is_ready(stream):
            self.recognizer.decode_stream(stream)
        result = self.recognizer.get_result(stream)
        return getattr(result, "text", str(result)).strip()


class OfflineRecognizerService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.recognizer = None
        self.ready = False
        self.error: str | None = None

    def validate_model_files(self) -> None:
        for path in (self.settings.offline_model, self.settings.offline_model_tokens):
            if not Path(path).is_file():
                raise FileNotFoundError(path)

    def start(self) -> None:
        try:
            self.validate_model_files()
            import sherpa_onnx

            self.recognizer = sherpa_onnx.OfflineRecognizer.from_paraformer(
                paraformer=self.settings.offline_model,
                tokens=self.settings.offline_model_tokens,
                num_threads=self.settings.sherpa_num_threads,
                provider=self.settings.sherpa_provider,
            )
            self.ready = True
            self.error = None
        except Exception as exc:
            self.ready = False
            self.error = exc.__class__.__name__

    def stop(self) -> None:
        self.ready = False
        self.recognizer = None

    def transcribe(self, samples: np.ndarray) -> str:
        if not self.recognizer:
            raise RuntimeError("Recognizer is not initialized")
        stream = self.recognizer.create_stream()
        stream.accept_waveform(SAMPLE_RATE, samples)
        self.recognizer.decode_stream(stream)
        return stream.result.text.strip()
