from typing import Union

from pydantic import BaseModel


class Summarization(BaseModel):
    summary: str
    Transcription_file_url: Union[str, None] = None
