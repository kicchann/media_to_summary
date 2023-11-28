from pydantic import BaseModel


class Response(BaseModel):
    responder: str
    submit_date: str
    video_info: str  # json.dumps(video_info)可能
    description: str
    summary_length: int
    add_title: bool
    add_todo: bool
