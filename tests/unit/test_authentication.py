import time
import pytest
from app.core.authentication import create_stream_token, validate_api_key, validate_stream_token
from app.core.config import Settings
from app.core.errors import ASRError


def test_validate_api_key_supports_rotation():
    settings = Settings(asr_api_keys="current, previous")
    assert validate_api_key("current", settings)
    assert validate_api_key("previous", settings)
    assert not validate_api_key("wrong", settings)


def test_stream_token_round_trip():
    token = create_stream_token("secret", ttl_seconds=60, nonce="n")
    payload = validate_stream_token(token, "secret")
    assert payload["scope"] == "asr:stream"
    assert payload["nonce"] == "n"


def test_expired_stream_token_rejected():
    token = create_stream_token("secret", ttl_seconds=-1)
    with pytest.raises(ASRError) as exc:
        validate_stream_token(token, "secret")
    assert exc.value.code == "session_expired"
