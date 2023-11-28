from pydantic import BaseModel

from src.functions.model import Speaker


class Transcription(BaseModel):
    text: str
    speaker: Speaker = Speaker()
    duration: float = 0.0
    start_time: float = 0.0
