from pydantic import BaseModel

from functions.model import User


class AudioData(BaseModel):
    file_path: str
    speaker: User = User()
    duration: float = 0.0
    start_time: float = 0.0
