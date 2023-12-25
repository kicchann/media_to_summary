import asyncio
import os
import tempfile
import time
from typing import Dict, List, Union

import librosa
import numpy as np
import openai
import requests
from pydub import AudioSegment
from scipy.stats import multivariate_normal
from sklearn.cluster import KMeans
from src.functions.config import (
    DEFAULT_LANGUAGE,
    IGNORE_DURATION_MILISECONDS,
    OPENAI_API_35_ENDPOINT,
    OPENAI_API_35_MODEL,
    OPENAI_API_35_VERSION,
    OPENAI_API_WHISPER_DEPLOYMENT,
    OPENAI_API_WHISPER_ENDPOINT,
    OPENAI_API_WHISPER_VERSION,
    OPENAI_CHAT_TEMPERATURE,
    OPENAI_USE_AZURE,
    RETRY_COUNT,
    USE_FASTER_WHISPER,
)


def set_path_for_ffmpeg_bin(base_dir: str):
    # set PATH for ffmpeg
    ffmpeg_path = os.path.join(base_dir, "ffmpeg_bin", "bin")
    os.environ["PATH"] = ffmpeg_path + os.pathsep + os.environ["PATH"]


def create_chat_completion(
    messages: List[Dict[str, str]],
    max_tokens: Union[int, None] = None,
    temperature: Union[float, None] = None,
    openai_use_azure: Union[bool, None] = None,
    openai_api_endpoint: Union[str, None] = None,
    openai_api_version: Union[str, None] = None,
    openai_api_model: Union[str, None] = None,
    retry_count: Union[int, None] = None,
) -> Union[str, None]:
    openai_use_azure = openai_use_azure or OPENAI_USE_AZURE
    openai_api_endpoint = openai_api_endpoint or OPENAI_API_35_ENDPOINT  # GPT3.5を使う
    openai_api_version = openai_api_version or OPENAI_API_35_VERSION  # GPT3.5を使う
    openai_api_model = openai_api_model or OPENAI_API_35_MODEL  # GPT3.5を使う
    temperature = temperature or OPENAI_CHAT_TEMPERATURE
    retry_count = retry_count or RETRY_COUNT

    retry = 0
    while retry < retry_count:
        try:
            if retry > 0:
                print("retry: {}".format(retry))
            return _create_chat_completion(
                messages,
                max_tokens,
                temperature,
                openai_use_azure,
                openai_api_endpoint,
                openai_api_version,
                openai_api_model,
            )
        except Exception as e:
            print("An error occurred:", str(e))
            retry += 1
            time.sleep(5 * retry)
            continue
    return None


def _create_chat_completion(
    messages: List[Dict[str, str]],
    max_tokens: Union[int, None],
    temperature: float,
    openai_use_azure: bool,
    openai_api_endpoint: str,
    openai_api_version: str,
    openai_api_model: str,
) -> str:
    openai.api_type = "azure" if openai_use_azure else "openai"

    # azureの場合
    openai.api_version = openai_api_version
    openai.azure_endpoint = openai_api_endpoint
    if "gpt-4" in openai_api_model:
        openai.api_key = os.environ["OPENAI_API_KEY"]
    else:
        openai.api_key = os.environ["OPENAI_API_35_KEY"]
    os.environ["http_proxy"] = "http://egvs00395:3128"
    os.environ["https_proxy"] = "http://egvs00395:3128"
    need_continue: bool = False
    contents: List[str] = []
    response = openai.chat.completions.create(
        model=openai_api_model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=60,
    )
    content = response.choices[0].message.content
    contents.append(content)
    if response.choices[0].finish_reason == "length":
        need_continue = True
    while need_continue:
        message = {
            "role": "assistant",
            "content": content,
        }
        response = openai.chat.completions.create(
            model=openai_api_model,
            messages=messages + [message],
            temperature=temperature,
            timeout=60,
        )
        content = response.choices[0].message.content
        contents.append(content)
        if response.choices[0].finish_reason != "length":
            need_continue = False
    return "".join(contents)


def transcript_by_whisper(
    file_path: str,
    prompt: str,
    language: Union[str, None] = None,
    use_faster_whisper: bool = None,
    openai_api_whisper_endpoint: Union[str, None] = None,
    openai_api_whisper_deployment: Union[str, None] = None,
    openai_api_whisper_api_version: Union[str, None] = None,
    retry_count: Union[int, None] = None,
) -> Union[str, None]:
    language = language or DEFAULT_LANGUAGE
    use_faster_whisper = use_faster_whisper or USE_FASTER_WHISPER
    openai_api_whisper_endpoint = (
        openai_api_whisper_endpoint or OPENAI_API_WHISPER_ENDPOINT
    )
    openai_api_whisper_deployment = (
        openai_api_whisper_deployment or OPENAI_API_WHISPER_DEPLOYMENT
    )
    openai_api_whisper_api_version = (
        openai_api_whisper_api_version or OPENAI_API_WHISPER_VERSION
    )
    retry_count = retry_count or RETRY_COUNT

    if use_faster_whisper:
        return _transcript_by_faster_whisper(
            file_path,
            prompt,
            language,
        )
    else:
        retry = 0
        while retry < retry_count:
            try:
                if retry > 0:
                    print("retry: {}".format(retry))
                return _transcript_by_azure_whisper(
                    file_path,
                    prompt,
                    language,
                    openai_api_whisper_endpoint,
                    openai_api_whisper_deployment,
                    openai_api_whisper_api_version,
                )
            except Exception as e:
                print("An error occurred on whisper:", str(e))
                retry += 1
                time.sleep(5 * retry)
                continue
    return None


def _transcript_by_azure_whisper(
    file_path: str,
    prompt: str,
    language: str,
    openai_api_whisper_endpoint: str,
    openai_api_whisper_deployment: str,
    openai_api_whisper_api_version: str,
) -> Union[list, None]:
    # azureの場合
    # url = "https://ek53-azureopenai-ncus.openai.azure.com/openai/deployments/whisper-1/audio/transcriptions?api-version=2023-09-01-preview"
    url = "{}openai/deployments/{}/audio/transcriptions?api-version={}".format(
        openai_api_whisper_endpoint,
        openai_api_whisper_deployment,
        openai_api_whisper_api_version,
    )
    headers = {
        "content_type": "multipart/form-data",  # "multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW",
        "api-key": os.getenv("OPENAI_API_WHISPER_KEY"),
    }
    # data = {"prompt": prompt, "response_format": "verbose_json"}
    data = {"prompt": prompt, "language": language, "response_format": "verbose_json"}
    try:
        with open(file_path, "rb") as f:
            transcript = requests.post(
                url, headers=headers, data=data, files=[("file", f)]
            ).json()
        # 0.3秒以下の音声は無視する
        return [
            {"start": s["start"], "end": s["end"], "text": s["text"]}
            for s in transcript.get("segments")
            if float(s["end"]) - float(s["start"]) > IGNORE_DURATION_MILISECONDS / 1000
        ]
    except:
        return None


def _transcript_by_faster_whisper(
    file_path: str,
    prompt: str,
    language: str,
) -> Union[list, None]:
    from faster_whisper import WhisperModel

    model_size = "large-v2"
    # user_profile = os.environ["USERPROFILE"]
    # model_size = os.path.join(
    #     user_profile,
    #     r"Documents\models--Systran--faster-whisper-large-v2\snapshots\f0fe81560cb8b68660e564f55dd99207059c092e",  # float32用？
    # )
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(
        file_path,
        language=language,
        initial_prompt=prompt,
        without_timestamps=True,
    )
    return [
        {
            "start": s.start,
            "end": s.end,
            "text": s.text,
        }
        for s in segments
    ]


def get_features_of_voice(file_path: str, start_and_ends: List[List[float]]) -> list:
    # 音声ファイルから特徴量を抽出する
    # file_pathから音声ファイルを取得して、transcript_listのstartとendの間の音声を抽出する
    # 抽出した音声を一時ファイルに保存する
    # 抽出した音声から特徴量を抽出する
    format = file_path.split(".")[-1]
    sound = AudioSegment.from_file(file_path, format=format)
    features = []
    with tempfile.TemporaryDirectory() as dname:
        for start_and_end in start_and_ends:
            # librosa.feature.mfccで特徴量を抽出する
            # 失敗した場合は、np.zeros(40)を返す
            # TODO: タイムアウトエラーの実装
            try:
                start = min(start_and_end)
                end = max(start_and_end)
                audio_segment = sound[start * 1000 : end * 1000]
                fpath = os.path.join(dname, "tmp.mp3")
                audio_segment.export(fpath, format="mp3")
                mp3, sr = librosa.load(fpath, sr=None)
                mfcc = librosa.feature.mfcc(y=mp3, sr=sr, n_mfcc=40)
                mean_mfcc = np.mean(mfcc, axis=1)
                norm_array = mean_mfcc / np.linalg.norm(mean_mfcc)
            except:
                norm_array = np.zeros(40)
            features.append(norm_array.tolist())
    return features


def get_n_cluster_by_x_means(features: np.ndarray, n_clusters: list[int]) -> int:
    # 特徴量からクラスタリングを行う
    # 先にnp.zeros(40)を除外する
    features = features[~np.all(features == 0, axis=1)]

    # そもそも特徴量のcosine類似度が高い場合は、クラスタリングを行わない
    # その場合は、n_clusters=1を返す
    # 基準となる特徴量を取得
    base_feature = features[0]
    for i, f in enumerate(features):
        if np.dot(base_feature, f) < 0.98:
            break
        if i == len(features) - 1:
            return 1

    # クラスタリングとBICの計算
    bic_dict = {}
    for n_cluster in n_clusters:
        bic = 0
        km = KMeans(n_clusters=n_cluster, init="k-means++", n_init=10, random_state=0)
        km.fit(features)
        centers = km.cluster_centers_
        for vec in features:
            p_sum = 0
            for i in range(n_cluster):
                center = centers[i]
                cov = np.cov(features[km.labels_ == i].T)
                p_sum += multivariate_normal.pdf(
                    vec, mean=center, cov=cov, allow_singular=True
                )
            bic -= np.log((p_sum + 1e-8) / n_cluster)
        bic += n_cluster * features.shape[1] * np.log(features.shape[0]) / 2
        bic_dict[n_cluster] = bic

    # BICが最小のクラスタ数を取得
    n_cluster = min(bic_dict, key=bic_dict.get)
    return n_cluster


def get_speakers_by_k_means(features: np.ndarray, n_clusters: int) -> List[str]:
    # 特徴量からクラスタリングを行う
    # クラスタリング時は、np.zeros(40)を除外
    ex_features = features[~np.all(features == 0, axis=1)]
    km = KMeans(n_clusters=n_clusters, init="k-means++", n_init=10, random_state=0)
    km.fit(ex_features)
    labels = km.labels_.tolist()
    # 0,1,2...をA,B,C...に変換する
    speakers = [chr(65 + label) for label in labels]

    # np.zeros(40)を除外した分、speakersの長さが短くなっているので、
    # "-"を追加してspeakersの長さを元に戻す
    for i, feature in enumerate(features):
        if np.all(feature == 0):
            speakers.insert(i, "-")
    return speakers
