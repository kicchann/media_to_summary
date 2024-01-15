from pydantic import BaseModel


class AudioData(BaseModel):
    file_path: str
    start: float = 0.0
    end: float = 0.0
