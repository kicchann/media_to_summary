from src.functions import transcript_audio
from src.log.my_logger import MyLogger
from src.model import Task

my_logger = MyLogger(__name__)
logger = my_logger.logger


def transcription_task(task: Task) -> Task:
    """
    文字起こし処理を行う関数

    Args:
        task (Task): 処理対象のタスク
    Returns:
        Task: 処理結果のタスク
    """
    logger.info("transcription_task called")
    # 処理結果情報
    transcriptions = []
    if not task.audio_data_list:
        return task
    for audio_data in task.audio_data_list:
        try:
            transcriptions += [transcript_audio(audio_data)]
        except Exception as e:
            logger.error("error occurred while transcribing audio file")
            logger.error(f"audio_data: {audio_data}")
            logger.error(e)
            result = task.model_copy(
                deep=True,
                update=dict(
                    status="error",
                    progress="error occurred while transcribing audio file",
                    transcriptions=None,
                ),
            )
            return result
    result = task.model_copy(
        deep=True,
        update=dict(
            status="success",
            progress="transcription completed",
            transcriptions=transcriptions,
        ),
    )
    logger.info("transcription_task finished")
    return result
