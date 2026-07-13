# Sherpa ASR Service Specification

Version 1 implements a lightweight FastAPI speech-to-text service backed by one CPU sherpa-onnx `OnlineRecognizer` model. The service exposes upload transcription, real-time PCM16 WebSocket streaming, liveness/readiness health checks, optional Prometheus metrics, API-key authentication, short-lived streaming tokens, bounded upload/stream limits, Docker deployment, and no batch/background infrastructure.
