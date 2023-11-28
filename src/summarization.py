from src.functions import compress_text, summarize_text
from src.model import Summarization, Task


def summarization_task(task: Task) -> Task:
    """
    要約処理を行う関数

    Args:
        task (Task): 処理対象のタスク
    Returns:
        Task: 処理結果のタスク
    """
    print("summarization_task called")

    if isinstance(task.transcriptions, list):
        compressed_text = compress_text(task.transcriptions)
    if task.response is not None:
        summary = summarize_text(
            transcript_text=compressed_text,
            summary_length=task.response.summary_length,
            add_title=task.response.add_title,
            add_todo=task.response.add_todo,
        )
    summarization = Summarization(summary=summary)
    result = task.model_copy(
        deep=True,
        update=dict(
            progress="summarization completed",
            summarization=summarization,
        ),
    )
    return result
