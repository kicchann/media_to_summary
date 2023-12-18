from src.functions import compress_text, summarize_text, summarize_transcription
from src.log.my_logger import MyLogger
from src.model import Summarization, Task

my_logger = MyLogger(__name__)
logger = my_logger.logger


def summarization_task(task: Task) -> Task:
    """
    要約処理を行う関数

    Args:
        task (Task): 処理対象のタスク
    Returns:
        Task: 処理結果のタスク
    """
    logger.info(f"{task.id_} - summarization_task called")

    if not task.transcriptions or not task.response:
        return task
    try:
        logger.info(f"{task.id_} - summarizing text")
        summary = summarize_transcription(
            transcriptions=task.transcriptions,
            add_title=task.response.add_title,
            add_todo=task.response.add_todo,
        )
        # logger.info("compressing text")
        # compressed_text = compress_text(task.transcriptions)
        # logger.info("summarizing text")
        # summary = summarize_text(
        #     transcript_text=compressed_text,
        #     summary_length=task.response.summary_length,
        #     add_title=task.response.add_title,
        #     add_todo=task.response.add_todo,
        # )
        summarization = Summarization(summary=summary)
    except Exception as e:
        logger.error(f"{task.id_} - error occurred while summarizing text")
        logger.error(f"{task.id_} - {e}")
        result = task.model_copy(
            deep=True,
            update=dict(
                status="error",
                progress="error occurred while summarizing text",
                message="要約中にエラーが発生しました",
                summarization=None,
            ),
        )
        return result
    result = task.model_copy(
        deep=True,
        update=dict(
            status="success",
            progress="summarization completed",
            message="要約が完了しました",
            summarization=summarization,
        ),
    )
    logger.info(f"{task.id_} - summarization_task finished")
    return result
