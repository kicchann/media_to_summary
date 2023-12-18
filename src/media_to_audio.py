import os
import uuid

from src.config import AUDIO_DIR
from src.functions import MediaToAudioConverter
from src.log.my_logger import MyLogger
from src.model import Task

my_logger = MyLogger(__name__)
logger = my_logger.logger


def media_to_audio_task(task: Task) -> Task:
    """
    動画ファイルを音声ファイルに変換する関数

    Args:
        task (Task): 処理対象のタスク
    Returns:
        Task: 処理結果のタスク
    """
    logger.info(f"{task.id_} - media_to_audio_task called")

    if not task.media_file_path or not os.path.exists(str(task.media_file_path)):
        logger.warning(f"{task.id_} - {task.media_file_path} does not exist")
        result = task.model_copy(
            deep=True,
            update=dict(
                status="error",
                progress="media file does not exist",
                message="メディアファイルが見つかりません",
                audio_file_path=None,
            ),
        )
        return result

    os.makedirs(AUDIO_DIR, exist_ok=True)
    audio_file_path = os.path.join(AUDIO_DIR, f"{uuid.uuid4()}.mp3")
    # 動画ファイルを音声ファイルに変換
    try:
        logger.info(f"{task.id_} - start converting media to audio")
        converter = MediaToAudioConverter()
        audio_file_path = converter.convert(
            media_file_path=task.media_file_path,
            audio_file_path=audio_file_path,
        )
        logger.info(f"{task.id_} - finish converting media to audio")
    except Exception as e:
        logger.warning(
            f"{task.id_} - error occurred while converting to audio. error may occur when ffmpeg takes too long time"
        )
        logger.warning(f"{task.id_} - {e}")
        result = task.model_copy(
            deep=True,
            update=dict(
                status="error",
                progress="error occurred while converting to audio",
                message="音声を抽出する際にエラーが発生しました",
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
    logger.info(f"{task.id_} - media_to_audio_task finished")
    return result
