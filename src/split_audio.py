import os

from src.config import SPLIT_AUDIO_DIR
from src.functions import split_audio
from src.model import Task


def split_audio_task(task: Task) -> Task:
    """
    音声ファイルを分割する関数

    Args:
        task (Task): 処理対象のタスク
    Returns:
        Task: 処理結果のタスク
    """
    print("split_audio_task called")

    os.makedirs(SPLIT_AUDIO_DIR, exist_ok=True)
    audio_data_list = split_audio(str(task.audio_file_path), SPLIT_AUDIO_DIR)
    # 処理結果情報
    result = task.model_copy(
        deep=True,
        update=dict(
            status="success",
            progress="audio file splitted",
            audio_data_list=audio_data_list,
        ),
    )
    return result
