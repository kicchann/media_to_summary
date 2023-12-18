import json
import os
from datetime import datetime as dt
from glob import glob
from typing import Union

from src.config import RESPONSE_KEY
from src.log.my_logger import MyLogger
from src.model import MediaInfo, Response, Task

my_logger = MyLogger(__name__)
logger = my_logger.logger


def find_resnponse_file_path(root_dir, media_file_name: str) -> Union[str, None]:
    """
    メディアファイルに対応するレスポンスファイルのパスを返す関数

    Args:
        root_dir (str): ルートディレクトリ
        media_file_name (str): メディアファイル名

    Returns:
        str: レスポンスファイルのパス
    """
    logger.info("find_resnponse_file_path called")
    logger.info(f"root_dir: {root_dir}")
    logger.info(f"media_file_name: {media_file_name}")
    logger.info("start searching response file path")
    # "root_dir\response"から，動画ファイルに対応するresponseファイルを探す
    files = glob(os.path.join(root_dir, "response", "*.json"))
    response_file_path = None
    for file_ in files:
        with open(file_, "r", encoding="UTF-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            continue
        if RESPONSE_KEY.MEDIA_INFO.value not in data:
            continue
        media_info = json.loads(data[RESPONSE_KEY.MEDIA_INFO.value])
        if media_info[0]["name"] == media_file_name:
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
        if "add_" in k_:
            v = True if v in ["必要", "はい"] else False
        if k_ == "use_last_10_mins_only":
            v = True if v in ["必要", "はい"] else False
        if k_ in ["ignore_key", "media_info"]:
            continue
        if k_ == "speakers":
            if v == "話者判別しない":
                new_response_dict["recognite_speakers"] = False
                v = None
            elif v == "1人":
                new_response_dict["recognite_speakers"] = True
                v = 1
            elif v == "2人":
                new_response_dict["recognite_speakers"] = True
                v = 2
            elif v == "3人":
                new_response_dict["recognite_speakers"] = True
                v = 3
            elif v == "4人":
                new_response_dict["recognite_speakers"] = True
                v = 4
            elif v == "2人~5人":
                new_response_dict["recognite_speakers"] = True
                v = list(range(2, 6))
            elif v == "5人~10人":
                new_response_dict["recognite_speakers"] = True
                v = list(range(5, 11))
            else:
                new_response_dict["recognite_speakers"] = True
                v = list(range(2, 11))
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
    logger.info(f"{result.id_} - clean_up called")

    if result.audio_file_path:
        try:
            os.remove(result.audio_file_path)
            logger.info(f"{result.id_} - remove {result.audio_file_path}")
        except Exception as e:
            logger.warning(f"{result.id_} - failed to remove audio file")
            logger.warning(f"{result.id_} - {e}")
    if result.audio_data_list:
        for audio_data in result.audio_data_list:
            try:
                os.remove(audio_data.file_path)
                logger.info(f"{result.id_} - remove {audio_data.file_path}")
            except Exception as e:
                logger.warning(f"{result.id_} - failed to remove audio file")
                logger.warning(f"{result.id_} - {e}")
    logger.info(f"{result.id_} - finish cleaning up")
    return


def save_result(result: Task):
    """
    処理結果情報を保存する関数

    Args:
        result (Task): 処理結果情報

    Returns:
        None
    """
    logger.info(f"{result.id_} - save_result called")
    # 処理結果情報を保存する
    root_dir = os.path.dirname(os.path.dirname(result.response_file_path))
    result_dir = os.path.join(root_dir, "result")

    if not result.response_file_path:
        logger.warning(f"{result.id_} - response file path is not found")
        logger.info(f"{result.id_} - finish saving result")
        time_str = dt.now().strftime("%Y%m%d%H%M%S")
        result_file_path = os.path.join(result_dir, f"error_{time_str}.json")
        # result_file_path = os.path.join(result_dir, f"error_clone.json")
        return

    response_file_name = os.path.basename(result.response_file_path)
    result_file_path = os.path.join(result_dir, response_file_name)
    # result_file_path = os.path.join(result_dir, "clone.json")

    if not os.path.exists(result_dir):
        os.makedirs(result_dir, exist_ok=True)
    with open(result_file_path, "w", encoding="UTF-8") as f:
        json.dump(result.model_dump(), f, ensure_ascii=False, indent=4)
    logger.info(f"{result.id_} - result saved to {result_file_path}")
    logger.info(f"{result.id_} - finish saving result")
    return
