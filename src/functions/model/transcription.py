from pydantic import BaseModel

from functions.model import User


class Transcription(BaseModel):
    text: str
    speaker: User = User()
    duration: float = 0.0
    start_time: float = 0.0
