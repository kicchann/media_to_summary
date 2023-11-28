from src.functions import transcript_audio
from src.model import Task


def transcription_task(task: Task) -> Task:
    """
    文字起こし処理を行う関数

    Args:
        task (Task): 処理対象のタスク
    Returns:
        Task: 処理結果のタスク
    """
    print("transcription_task called")
    # 処理結果情報
    transcriptions = []
    if isinstance(task.audio_data_list, list):
        for audio_data in task.audio_data_list:
            transcription = transcript_audio(audio_data)
            transcriptions += [transcription]

    result = task.model_copy(
        deep=True,
        update=dict(
            progress="transcription completed",
            transcriptions=transcriptions,
        ),
    )
    return result
