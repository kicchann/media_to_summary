from typing import List, Literal, Union

from pydantic import BaseModel

from src.functions.model import AudioData, Transcription
from src.model import Response, Summarization


class Task(BaseModel):
    status: Literal["success", "error"]
    progress: str
    response_file_path: Union[str, None] = None
    video_file_path: Union[str, None] = None
    audio_file_path: Union[str, None] = None
    audio_data_list: Union[List[AudioData], None] = None
    transcriptions: Union[List[Transcription], None] = None
    summarization: Union[Summarization, None] = None
    response: Union[Response, None] = None
    message: Union[str, None] = None
