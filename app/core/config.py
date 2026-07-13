from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "production"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    asr_api_keys: str = ""
    asr_stream_token_secret: str = "replace-with-a-long-random-secret"

    model_name: str = "sherpa-streaming-paraformer-zh-en"
    model_encoder: str = "/models/streaming-paraformer-zh-en/encoder.int8.onnx"
    model_decoder: str = "/models/streaming-paraformer-zh-en/decoder.int8.onnx"
    model_tokens: str = "/models/streaming-paraformer-zh-en/tokens.txt"
    offline_model: str = "/models/sherpa-onnx-paraformer-trilingual-zh-cantonese-en/model.onnx"
    offline_model_tokens: str = "/models/sherpa-onnx-paraformer-trilingual-zh-cantonese-en/tokens.txt"

    sherpa_provider: str = "cpu"
    sherpa_num_threads: int = 4
    sherpa_decoding_method: str = "greedy_search"

    max_upload_size_mb: int = 25
    max_audio_duration_seconds: int = 300
    max_concurrent_uploads: int = 2
    upload_timeout_seconds: int = 90

    stream_max_connections: int = 20
    stream_max_batch_size: int = 8
    stream_max_wait_ms: int = 8
    stream_buffer_seconds: int = 5
    stream_idle_timeout_seconds: int = 30
    stream_max_duration_seconds: int = 3600
    stream_max_message_bytes: int = 1048576

    endpoint_rule1_min_trailing_silence: float = 2.4
    endpoint_rule2_min_trailing_silence: float = 1.2
    endpoint_rule3_min_utterance_length: float = 20.0

    enable_metrics: bool = True
    enable_api_docs: bool = False
    log_transcription_text: bool = False
    shutdown_grace_seconds: int = 30

    @property
    def api_keys(self) -> list[str]:
        return [k.strip() for k in self.asr_api_keys.split(",") if k.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
