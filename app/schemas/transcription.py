from pydantic import BaseModel


class TranscriptionResponse(BaseModel):
    text: str
    duration: float | None = None
    processing_time: float
