from pydantic import BaseModel

# from src.model import MediaInfo


class Response(BaseModel):
    responder: str
    submit_date: str
    # media_info: MediaInfo #いらない
    description: str
    # summary_length: int # この値は使わない
    add_title: bool
    add_todo: bool
    use_last_10_mins_only: bool = False
