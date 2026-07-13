from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from fastapi import Response

upload_requests = Counter("asr_upload_requests_total", "Upload transcription requests")
upload_errors = Counter("asr_upload_errors_total", "Upload transcription errors", ["code"])
upload_duration = Histogram("asr_upload_duration_seconds", "Upload request duration")
stream_connections = Gauge("asr_stream_connections", "Active stream connections")
stream_connections_total = Counter("asr_stream_connections_total", "Total stream connections")
stream_errors = Counter("asr_stream_errors_total", "Stream errors", ["code"])
model_ready = Gauge("asr_model_ready", "Model readiness")


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
