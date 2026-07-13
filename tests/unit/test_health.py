from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.health import router


class DummyRecognizer:
    ready = True


class DummySettings:
    model_name = "sherpa-streaming-paraformer-zh-en"


def test_liveness_and_readiness():
    app = FastAPI()
    app.state.recognizer_service = DummyRecognizer()
    app.state.offline_recognizer_service = DummyRecognizer()
    app.state.settings = DummySettings()
    app.state.active_streams = 2
    app.state.active_uploads = 0
    app.include_router(router)
    client = TestClient(app)
    assert client.get("/health/live").json() == {"status": "alive"}
    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["active_streams"] == 2


def test_readiness_requires_offline_recognizer():
    app = FastAPI()
    app.state.recognizer_service = DummyRecognizer()
    app.state.offline_recognizer_service = type("OfflineRecognizer", (), {"ready": False})()
    app.state.settings = DummySettings()
    app.state.active_streams = 0
    app.state.active_uploads = 0
    app.include_router(router)

    response = TestClient(app).get("/health/ready")

    assert response.status_code == 503
