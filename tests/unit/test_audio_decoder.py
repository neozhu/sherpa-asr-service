import numpy as np
import pytest
from app.asr.audio_decoder import pcm16le_to_float32, validate_supported_filename
from app.core.errors import ASRError


def test_pcm16le_to_float32():
    data = np.array([-32768, 0, 32767], dtype="<i2").tobytes()
    out = pcm16le_to_float32(data)
    assert out.dtype == np.float32
    assert out[0] == -1.0
    assert out[1] == 0.0
    assert out[2] > 0.99


def test_pcm16_requires_even_byte_count():
    with pytest.raises(ASRError) as exc:
        pcm16le_to_float32(b"x")
    assert exc.value.code == "invalid_audio_frame"


def test_unsupported_extension_rejected():
    with pytest.raises(ASRError) as exc:
        validate_supported_filename("audio.exe")
    assert exc.value.code == "unsupported_audio_format"
