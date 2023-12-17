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
    DESCRIPTION = "r7b43495adc0e4c33ad007e5f4d46e633"
    IGNORE_KEY = "r05810abde1e84d0da0e0ee40d83a32f6"
    ADD_TITLE = "r8907a1f996a74a2e96295775ee53b94c"
    ADD_TODO = "r520f4a06e68249b4bc81e8a4fd75d151"
    MEDIA_INFO = "r46dc0e4de2e948cf9370d88e7beb0071"
    USE_LAST_10_MINS_ONLY = "r9f01249d2ddc4d008433f962c172469f"
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
