import os
import uuid

from src.config import AUDIO_DIR
from src.functions import convert_video_to_audio
from src.model import Task


def video_to_audio_task(task: Task) -> Task:
    """
    動画ファイルを音声ファイルに変換する関数

    Args:
        task (Task): 処理対象のタスク
    Returns:
        Task: 処理結果のタスク
    """
    print("video_to_audio_task called")

    if not os.path.exists(str(task.video_file_path)):
        print("video_file_path does not exist")
        result = task.model_copy(
            deep=True,
            update=dict(
                status="error",
                progress="video file does not exist",
            ),
        )
        return result

    os.makedirs(AUDIO_DIR, exist_ok=True)
    audio_file_path = os.path.join(AUDIO_DIR, f"{uuid.uuid4()}.mp3")
    # 動画ファイルを音声ファイルに変換
    # ただし，1時間以上かかる場合は，エラーとする
    try:
        convert_video_to_audio(
            video_file_path=task.video_file_path,
            audio_file_path=audio_file_path,
        )
    except Exception as e:
        print(e)
        result = task.model_copy(
            deep=True,
            update=dict(
                status="error",
                progress="ffmpeg takes too long time",
                message="動画ファイルを音声ファイルに変換する際にエラーが発生しました",
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
    return result
