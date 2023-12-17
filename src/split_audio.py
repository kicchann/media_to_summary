import os

from src.config import SPLIT_AUDIO_DIR
from src.functions import split_audio
from src.log.my_logger import MyLogger
from src.model import Task

my_logger = MyLogger(__name__)
logger = my_logger.logger


def split_audio_task(task: Task) -> Task:
    """
    音声ファイルを分割する関数

    Args:
        task (Task): 処理対象のタスク
    Returns:
        Task: 処理結果のタスク
    """
    logger.info("split_audio_task called")

    os.makedirs(SPLIT_AUDIO_DIR, exist_ok=True)
    try:
        audio_data_list = split_audio(
            audio_file_path=str(task.audio_file_path),
            split_audio_dir=SPLIT_AUDIO_DIR,
            use_last_10_mins_only=task.response.use_last_10_mins_only,
        )
    except Exception as e:
        logger.error("error occurred while splitting audio file")
        logger.error(e)
        result = task.model_copy(
            deep=True,
            update=dict(
                status="error",
                progress="error occurred while splitting audio file",
                message="音声ファイルの加工に失敗しました",
                audio_data_list=None,
            ),
        )
        return result
    if len(audio_data_list) == 0:
        logger.warning("failed to split audio file")
        result = task.model_copy(
            deep=True,
            update=dict(
                status="error",
                progress="audio file is not splitted",
                message="音声ファイルを加工しましたが，ファイルが見つかりません",
                audio_data_list=None,
            ),
        )
        return result
    # 処理結果情報
    result = task.model_copy(
        deep=True,
        update=dict(
            status="success",
            progress="audio file splitted",
            audio_data_list=audio_data_list,
        ),
    )
    logger.info(f"audio is splitted in {len(audio_data_list)} pieces")
    logger.info("split_audio_task finished")
    return result
