from dataclasses import dataclass
from uuid import uuid4
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


@dataclass(frozen=True)
class ErrorInfo:
    status_code: int
    code: str
    message: str


class ASRError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def request_id() -> str:
    return f"req_{uuid4().hex[:12]}"


def error_response(status_code: int, code: str, message: str, rid: str | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "request_id": rid or request_id()}},
    )


async def asr_error_handler(_: Request, exc: ASRError) -> JSONResponse:
    return error_response(exc.status_code, exc.code, exc.message)


async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
    code = "invalid_request" if exc.status_code < 500 else "transcription_failed"
    if exc.status_code == 401:
        code = "authentication_failed"
    return error_response(exc.status_code, code, str(exc.detail))
