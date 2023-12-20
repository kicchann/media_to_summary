from pydantic import BaseModel
from src.functions.model import Speaker


class AudioData(BaseModel):
    file_path: str
    speaker: Speaker = Speaker()
    duration: float = 0.0
    start: float = 0.0
