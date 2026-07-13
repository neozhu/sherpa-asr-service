from fastapi import APIRouter, Request
from app.core.errors import error_response

router = APIRouter()


@router.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/health/ready")
async def ready(request: Request):
    state = request.app.state
    if not getattr(state.recognizer_service, "ready", False):
        return error_response(503, "model_unavailable", "Model is not ready.")
    return {
        "status": "ready",
        "model": state.settings.model_name,
        "active_streams": state.active_streams,
        "active_uploads": state.active_uploads,
    }
