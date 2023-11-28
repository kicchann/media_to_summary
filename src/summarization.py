from src.functions import compress_text, summarize_text
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
    logger.info("summarization_task called")

    if not task.transcriptions or not task.response:
        return task
    try:
        compressed_text = compress_text(task.transcriptions)
        summary = summarize_text(
            transcript_text=compressed_text,
            summary_length=task.response.summary_length,
            add_title=task.response.add_title,
            add_todo=task.response.add_todo,
        )
    except Exception as e:
        logger.error("error occurred while summarizing text")
        logger.error(e)
        result = task.model_copy(
            deep=True,
            update=dict(
                status="error",
                progress="error occurred while summarizing text",
                summarization=None,
            ),
        )
        return result
    summarization = Summarization(summary=summary)
    result = task.model_copy(
        deep=True,
        update=dict(
            status="success",
            progress="summarization completed",
            summarization=summarization,
        ),
    )
    logger.info("summarization_task finished")
    return result
