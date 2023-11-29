import json
import os
from glob import glob
from typing import Union

from src.config import RESPONSE_KEY
from src.log.my_logger import MyLogger
from src.model import Response, Task, VideoInfo

my_logger = MyLogger(__name__)
logger = my_logger.logger


def find_resnponse_file_path(root_dir, video_file_name: str) -> Union[str, None]:
    """
    動画ファイルに対応するレスポンスファイルのパスを返す関数

    Args:
        root_dir (str): ルートディレクトリ
        video_file_name (str): 動画ファイル名

    Returns:
        str: レスポンスファイルのパス
    """
    logger.info("find_resnponse_file_path called")
    logger.info(f"root_dir: {root_dir}")
    logger.info(f"video_file_name: {video_file_name}")
    logger.info("start searching response file path")
    # "root_dir\response"から，動画ファイルに対応するresponseファイルを探す
    files = glob(os.path.join(root_dir, "response", "*.json"))
    response_file_path = None
    for file_ in files:
        with open(file_, "r", encoding="UTF-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            continue
        if RESPONSE_KEY.VIDEO_INFO.value not in data:
            continue
        video_info = json.loads(data[RESPONSE_KEY.VIDEO_INFO.value])
        if video_info[0]["name"] == video_file_name:
            response_file_path = file_
            logger.info("response file path found successfully")
            logger.info(f"response_file_path: {response_file_path}")
            break
    if response_file_path is None:
        logger.warning("response file path not found")
    logger.info("finish searching response file path")
    return response_file_path


def read_response_file(response_file_path: Union[str, None]) -> Union[Response, None]:
    """
    レスポンスファイルを読み込む関数

    Args:
        response_file_path (str): レスポンスファイルのパス

    Returns:
        dict: レスポンスファイルの内容
    """
    logger.info("read_response_file called")
    logger.info(f"response_file_path: {response_file_path}")
    if response_file_path is None:
        logger.warning("response file path is not found")
        logger.info("finish reading response file")
        return None
    with open(response_file_path, "r", encoding="UTF-8") as f:
        response_dict = json.load(f)
    new_response_dict = {}
    for k, v in response_dict.items():
        k_ = RESPONSE_KEY(k).name.lower()
        if k_ == "video_info":
            video_info_list = json.loads(v)
            v = VideoInfo(**video_info_list[0])
        if "add_" in k_:
            v = True if v == "必要" else False
        new_response_dict[k_] = v
    response = Response(**new_response_dict)
    logger.info("finish reading response file")
    return response


def clean_up(result: Task):
    """
    処理結果情報をクリーンアップする関数

    Args:
        result (Task): 処理結果情報

    Returns:
        None
    """
    # 一時ファイルをディレクトリから削除する
    logger.info("clean_up called")

    if result.audio_file_path:
        try:
            os.remove(result.audio_file_path)
            logger.info(f"remove {result.audio_file_path}")
        except Exception as e:
            logger.warning("failed to remove audio file")
            logger.warning(e)
    if result.audio_data_list:
        for audio_data in result.audio_data_list:
            try:
                os.remove(audio_data.file_path)
                logger.info(f"remove {audio_data.file_path}")
            except Exception as e:
                logger.warning("failed to remove audio file")
                logger.warning(e)
    logger.info("finish cleaning up")
    return


def save_result(result: Task):
    """
    処理結果情報を保存する関数

    Args:
        result (Task): 処理結果情報

    Returns:
        None
    """
    logger.info("save_result called")
    # 処理結果情報を保存する
    if not result.response_file_path:
        logger.warning("response file path is not found")
        logger.info("finish saving result")
        return

    root_dir = os.path.dirname(os.path.dirname(result.response_file_path))
    response_file_name = os.path.basename(result.response_file_path)
    result_dir = os.path.join(root_dir, "result")
    result_file_path = os.path.join(result_dir, response_file_name)

    if not os.path.exists(result_dir):
        os.makedirs(result_dir, exist_ok=True)
    with open(result_file_path, "w", encoding="UTF-8") as f:
        json.dump(result.model_dump(), f, ensure_ascii=False, indent=4)
    logger.info(f"result saved to {result_file_path}")
    logger.info("finish saving result")
    return


# {
#     "status": "success",
#     "progress": "summarization completed",
#     "message": "要約が完了しました",
#     "response_file_path": "",
#     "video_file_path": "",
#     "audio_file_path": "",
#     "split_audio_file_paths": [],
#     "transcriptions": [],
#     "summarization": {
#         "summary": "<h2>## タイトル</h2><p>タイトルのサンプルです</p><h2>## 要約</h2><p>要約のサンプルです</p>",
#         "transcription_file_url": "",
#     },
#     "response": {
#         "responder": "",
#         "submit_date": "",
#         "description": "ステーキ",
#         "summary_length": 1000,
#         "add_title": "必要",
#         "add_todo": "必要",
#         "video_info": "",
#     },
# }
