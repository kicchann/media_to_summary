from pydantic import BaseModel
from src.functions.model import Speaker


class Transcription(BaseModel):
    text: str
    keywords: str = ""
    speaker: Speaker = Speaker()
    features: list = []
    start: float = 0.0
    end: float = 0.0
    section: int = 0

    # sortできるようにする
    def __lt__(self, other):
        if self.section == other.section:
            return self.start < other.start
        else:
            return self.section < other.section

    def __eq__(self, other):
        if self.section != other.section:
            return False
        else:
            return self.start == other.start and self.end == other.end


# 'segments': [{'id': 0,
#    'seek': 0,
#    'start': 0.0,
#    'end': 4.0,
#    'text': '...',
#    'tokens': [...],
#    'temperature': 0.0,
#    'avg_logprob': -0.1294921487569809,
#    'compression_ratio': 1.3574661016464233,
#    'no_speech_prob': 0.02398032322525978},
