import os
import uuid

from src.config import AUDIO_DIR
from src.functions import convert_video_to_audio
from src.log.my_logger import MyLogger
from src.model import Task

my_logger = MyLogger(__name__)
logger = my_logger.logger


def video_to_audio_task(task: Task) -> Task:
    """
    動画ファイルを音声ファイルに変換する関数

    Args:
        task (Task): 処理対象のタスク
    Returns:
        Task: 処理結果のタスク
    """
    logger.info("video_to_audio_task called")

    if not task.video_file_path or not os.path.exists(str(task.video_file_path)):
        logger.warning("{task.video_file_path} does not exist")
        result = task.model_copy(
            deep=True,
            update=dict(
                status="error",
                progress="video file does not exist",
                message="動画ファイルが見つかりません",
                audio_file_path=None,
            ),
        )
        return result

    os.makedirs(AUDIO_DIR, exist_ok=True)
    audio_file_path = os.path.join(AUDIO_DIR, f"{uuid.uuid4()}.mp3")
    # 動画ファイルを音声ファイルに変換
    # ただし，1時間以上かかる場合は，エラーとする
    try:
        logger.info("start converting video to audio")
        convert_video_to_audio(
            video_file_path=task.video_file_path,
            audio_file_path=audio_file_path,
        )
        logger.info("finish converting video to audio")
    except Exception as e:
        logger.warning(
            "error occurred while converting video to audio. error may occur when ffmpeg takes too long time"
        )
        logger.warning(e)
        result = task.model_copy(
            deep=True,
            update=dict(
                status="error",
                progress="ffmpeg takes too long time",
                message="動画から音声を抽出する際にエラーが発生しました",
                audio_file_path=None,
            ),
        )
        return result
    # 処理結果情報
    result = task.model_copy(
        deep=True,
        update=dict(
            status="success",
            progress="audio file created",
            audio_file_path=audio_file_path,
        ),
    )
    logger.info("video_to_audio_task finished")
    return result
