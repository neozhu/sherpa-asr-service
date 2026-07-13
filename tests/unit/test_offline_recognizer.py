import sys
from types import SimpleNamespace

import numpy as np


def test_offline_recognizer_transcribes_with_paraformer(monkeypatch, tmp_path):
    from app.asr.recognizer import OfflineRecognizerService

    model = tmp_path / "model.onnx"
    tokens = tmp_path / "tokens.txt"
    model.touch()
    tokens.touch()

    class FakeStream:
        result = SimpleNamespace(text="recognized text")

        def accept_waveform(self, sample_rate, samples):
            self.sample_rate = sample_rate
            self.samples = samples

    class FakeRecognizer:
        def create_stream(self):
            return FakeStream()

        def decode_stream(self, stream):
            pass

    def from_paraformer(**kwargs):
        fake_module.arguments = kwargs
        return FakeRecognizer()

    fake_module = SimpleNamespace(
        OfflineRecognizer=SimpleNamespace(from_paraformer=from_paraformer)
    )
    monkeypatch.setitem(sys.modules, "sherpa_onnx", fake_module)
    settings = SimpleNamespace(
        offline_model=str(model),
        offline_model_tokens=str(tokens),
        sherpa_num_threads=4,
        sherpa_provider="cpu",
    )

    service = OfflineRecognizerService(settings)
    service.start()

    assert service.ready is True
    assert service.transcribe(np.zeros(16000, dtype=np.float32)) == "recognized text"
    assert fake_module.arguments["paraformer"] == str(model)
    assert fake_module.arguments["tokens"] == str(tokens)
