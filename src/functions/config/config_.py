from enum import Enum


class TASK_STATUS(Enum):
    PENDING = "pending"
    START = "start"
    UPLOAD_DATA = "upload data"
    SPLIT_AUDIO = "split audio"
    TRANSCRIPT_AUDIO = "transcript audio"
    SUMMARIZE_TEXT = "summarize text"
    COMPLETE = "complete"
    FAILED = "failed"
    INTERRUPT = "interrupt"


####################
# 音声ファイル取り出し関連
####################


####################
# 文字起こし関連
####################

USE_FASTER_WHISPER = False
OPENAI_API_WHISPER_ENDPOINT = "https://ed01-openai-ncus2.openai.azure.com/"
OPENAI_API_WHISPER_DEPLOYMENT = "whisper-1"
OPENAI_API_WHISPER_VERSION = "2023-09-01-preview"
OPENAI_USE_AZURE = True
DEFAULT_LANGUAGE = "ja"

# whisperは25MBまでしか受け付けない
MAX_FILE_SIZE_FOR_WHISPER: float = 25 * 1000 * 1000 * 0.9

# whisperに投げるときは10分までにする
MAX_DURATION_FOR_WHISPER: float = 10 * 60

# pydubで分割する際の設定
# 最小の無音長
MIN_SILENCE_LEN: int = 100
# 無音とみなすdBFS
SILENCE_THRESH: int = -40
# 分割後に前後に追加する無音長
# KEEP_SILENCE: int = 500
# 前後に追加しないので、以下を利用
KEEP_SILENCE: int = 0
# ごく短い音声を無視する
IGNORE_DURATION_MILISECONDS: int = 300

####################
# GPT関連
####################

OPENAI_API_ENDPOINT = "https://ed01-openai-cae.openai.azure.com/"
OPENAI_API_MODEL = "gpt-4-32k"
OPENAI_API_VERSION = "2023-07-01-preview"

OPENAI_API_35_ENDPOINT = "https://ed01-openai-ncus2.openai.azure.com/"
OPENAI_API_35_MODEL = "gpt-35-turbo-16k"
OPENAI_API_35_VERSION = "2023-07-01-preview"
OPENAI_CHAT_TEMPERATURE = 0.0

RETRY_COUNT = 5

# # GPT4で文章圧縮する際の設定
# TOKEN_SIZE_FOR_SPLIT: int = 14000
# TOKEN_LIMIT: int = 20000

# GPT3.5で文章圧縮する際の設定
TOKEN_SIZE_FOR_SPLIT: int = 2000
TOKEN_LIMIT: int = 8000
