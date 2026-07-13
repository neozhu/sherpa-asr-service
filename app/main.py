import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.streaming import router as streaming_router
from app.api.transcriptions import router as transcriptions_router
from app.asr.recognizer import OfflineRecognizerService, RecognizerService
from app.asr.scheduler import StreamingScheduler
from app.core.config import get_settings
from app.core.errors import ASRError, asr_error_handler, http_error_handler
from app.core.logging import configure_logging
from app.core.metrics import metrics_response, model_ready
from fastapi import HTTPException


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    app.state.settings = settings
    app.state.loop = asyncio.get_running_loop()
    app.state.active_streams = 0
    app.state.active_uploads = 0
    app.state.upload_semaphore = asyncio.Semaphore(settings.max_concurrent_uploads)
    app.state.recognizer_service = RecognizerService(settings)
    app.state.offline_recognizer_service = OfflineRecognizerService(settings)
    await app.state.loop.run_in_executor(None, app.state.recognizer_service.start)
    await app.state.loop.run_in_executor(None, app.state.offline_recognizer_service.start)
    model_ready.set(
        1 if app.state.recognizer_service.ready and app.state.offline_recognizer_service.ready else 0
    )
    app.state.scheduler = StreamingScheduler(settings)
    await app.state.scheduler.start()
    yield
    app.state.recognizer_service.stop()
    app.state.offline_recognizer_service.stop()
    model_ready.set(0)
    await app.state.scheduler.stop()


settings = get_settings()
app = FastAPI(
    title="Sherpa ASR Service",
    docs_url="/docs" if settings.enable_api_docs else None,
    redoc_url="/redoc" if settings.enable_api_docs else None,
    openapi_url="/openapi.json" if settings.enable_api_docs else None,
    lifespan=lifespan,
)
app.add_exception_handler(ASRError, asr_error_handler)
app.add_exception_handler(HTTPException, http_error_handler)
app.include_router(health_router)
app.include_router(transcriptions_router)
app.include_router(streaming_router)

if settings.enable_metrics:
    app.get("/metrics")(metrics_response)
