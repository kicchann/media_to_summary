from pydantic import BaseModel
from src.model import VideoInfo


class Response(BaseModel):
    responder: str
    submit_date: str
    video_info: VideoInfo
    description: str
    # summary_length: int # この値は使わない
    add_title: bool
    add_todo: bool
