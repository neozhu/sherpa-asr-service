#!/usr/bin/env python3
from pathlib import Path
from app.core.config import get_settings

settings = get_settings()
missing = [p for p in (settings.model_encoder, settings.model_decoder, settings.model_tokens) if not Path(p).is_file()]
if missing:
    raise SystemExit("Missing model files: " + ", ".join(missing))
print("Model files verified.")
