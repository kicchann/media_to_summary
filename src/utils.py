import json
import os
from glob import glob

from src.config import RESPONSE_KEY


def find_resnponse_file_path(root_dir, video_file_name: str):
    """
    動画ファイルに対応するレスポンスファイルのパスを返す関数

    Args:
        root_dir (str): ルートディレクトリ
        video_file_name (str): 動画ファイル名

    Returns:
        str: レスポンスファイルのパス
    """
    # "root_dir\response"から，動画ファイルに対応するresponseファイルを探す
    files = glob(os.path.join(root_dir, "response", "*.json"))
    response_file_path = None
    for file_ in files:
        with open(file_, "r", encoding="UTF-8") as f:
            data = json.load(f)
        # r46dc0e4de2e948cf9370d88e7beb0071は動画ファイル情報のkey
        if not isinstance(data, dict):
            continue
        if "r46dc0e4de2e948cf9370d88e7beb0071" not in data:
            continue
        video_info = json.loads(data["r46dc0e4de2e948cf9370d88e7beb0071"])
        if video_info[0]["name"] == video_file_name:
            response_file_path = file_
            break
    return response_file_path


def clean_up(result: dict):
    """
    処理結果情報をクリーンアップする関数

    Args:
        result (dict): 処理結果情報
        {
            "status": str,
            "progress": str,
            "response_file_path": str,
            "video_file_path": str,
            "audio_file_path": str,
            "split_audio_file_paths": list[str],
            "transcriptions": list[dict],
            "summarization": dict,
        }

    Returns:
        None
    """
    # ファイルがあればディレクトリから削除する
    # if os.path.exists(result["video_file_path"]):
    #     os.remove(result["video_file_path"])
    # if os.path.exists(result["audio_file_path"]):
    #     os.remove(result["audio_file_path"])
    # for file_path in result["split_audio_file_paths"]:
    #     if os.path.exists(file_path):
    #         os.remove(file_path)
    return


def save_result(result: dict):
    """
    処理結果情報を保存する関数

    Args:
        result (dict): 処理結果情報
        {
            "status": str,
            "progress": str,
            "response_file_path": str,
            "video_file_path": str,
            "audio_file_path": str,
            "split_audio_file_paths": list[str],
            "transcriptions": list[dict],
            "summarization": dict,
        }

    Returns:
        None
    """
    # 処理結果情報を保存する
    root_dir = os.path.dirname(os.path.dirname(result["response_file_path"]))
    response_file_name = os.path.basename(result["response_file_path"])
    result_dir = os.path.join(root_dir, "result")
    result_file_path = os.path.join(result_dir, response_file_name)

    # レスポンスファイルを読み込む
    response = {}
    if result["response_file_path"] != "":
        with open(result["response_file_path"], "r", encoding="UTF-8") as f:
            response = json.load(f)
        result["response"] = {}
        for k, v in response.items():
            k_ = RESPONSE_KEY(k).name
            if k_ == "ignore_key":
                continue
            result["response"][k_] = v
    if result["status"] == "error":
        result["message"] = "エラーが発生しました"
    else:
        result["message"] = "要約が完了しました"

    if not os.path.exists(result_dir):
        os.makedirs(result_dir, exist_ok=True)
    with open(result_file_path, "w", encoding="UTF-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
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
