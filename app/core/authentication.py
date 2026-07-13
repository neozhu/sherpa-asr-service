import base64
import hashlib
import hmac
import json
import time
from secrets import compare_digest
from typing import Any
from fastapi import Header
from .config import Settings, get_settings
from .errors import ASRError


def validate_api_key(value: str | None, settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    if not value:
        return False
    expected = settings.api_keys
    return any(compare_digest(value, key) for key in expected)


async def require_api_key(
    authorization: str | None = Header(default=None),
    settings: Settings = get_settings(),
) -> None:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ASRError(401, "authentication_failed", "Invalid API key.")
    if not validate_api_key(authorization[7:].strip(), settings):
        raise ASRError(401, "authentication_failed", "Invalid API key.")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def create_stream_token(secret: str, scope: str = "asr:stream", ttl_seconds: int = 60, nonce: str | None = None) -> str:
    payload = {"scope": scope, "exp": int(time.time()) + ttl_seconds, "nonce": nonce or hashlib.sha256(str(time.time_ns()).encode()).hexdigest()[:16]}
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64url(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def validate_stream_token(token: str, secret: str) -> dict[str, Any]:
    try:
        body, sig = token.split(".", 1)
        expected = _b64url(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
        if not compare_digest(sig, expected):
            raise ValueError
        payload = json.loads(_b64url_decode(body))
    except Exception as exc:
        raise ASRError(401, "invalid_session_token", "Invalid streaming token.") from exc
    if payload.get("scope") != "asr:stream":
        raise ASRError(401, "invalid_session_token", "Invalid streaming token.")
    if int(payload.get("exp", 0)) < int(time.time()):
        raise ASRError(401, "session_expired", "Streaming token has expired.")
    return payload


def token_from_subprotocol(protocols: list[str] | None) -> str | None:
    for protocol in protocols or []:
        if protocol.startswith("bearer."):
            return protocol[7:]
    return None
