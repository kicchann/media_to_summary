from enum import Enum

AUDIO_DIR = r"C:\Windows\Temp\audio"
SPLIT_AUDIO_DIR = r"C:\Windows\Temp\split_audio"


########
# Power Automate
########
class RESPONSE_KEY(Enum):
    """
    Power Automateからのレスポンス情報のkeyを定義するEnum
    """

    RESPONDER = "responder"
    SUBMIT_DATE = "submitDate"
    MEDIA_INFO = "r194b77b73c3e4a1bb2bf8e1474c5723d"
    DESCRIPTION = "r1eac063e4e4c4fc2b1e8ac38513178db"
    ADD_TITLE = "r39f644b99ee1496286adc477c019f3c1"
    ADD_TODO = "r1bcd572e3cc34bd5b72d265a83219997"
    USE_LAST_10_MINS_ONLY = "r43ca32a4736c4277ae9732688fe56f54"
    SPEAKERS = "r32ccc023bbf6417688907292ed35049c"
    IGNORE_KEY = "r9ed8248e05a7451497c3dcd88b459c96"
    # SUMMARY_LENGTH = "rd7f5a61df13c4128937960df65119963" # 今は無効


class VIDEO_INFO_KEY(Enum):
    """
    Power Automateからのレスポンス情報のkeyを定義するEnum
    """

    NAME = "name"
    LINK = "link"
    ID = "id"
    TYPE = "type"
    REFERENCE_ID = "referenceId"
    DRIVE_ID = "driveId"
    STATUS = "status"
    UPLOAD_SESSION_URL = "uploadSessionUrl"
