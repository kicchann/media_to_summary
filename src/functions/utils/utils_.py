import os
import random
import string
import time
from typing import Union

import openai
import requests

from src.functions.config import (
    DEFAULT_LANGUAGE,
    OPENAI_API_ENDPOINT,
    OPENAI_API_MODEL,
    OPENAI_API_VERSION,
    OPENAI_API_WHISPER_DEPLOYMENT,
    OPENAI_API_WHISPER_ENDPOINT,
    OPENAI_API_WHISPER_VERSION,
    OPENAI_CHAT_TEMPERATURE,
    OPENAI_USE_AZURE,
    RETRY_COUNT,
)


def create_id(length: int = 8) -> str:
    # 大文字、小文字のアルファベットと数字を含む文字列を作成
    characters = string.ascii_letters + string.digits
    # この文字列からランダムに8文字選び、新しい文字列を作成
    random_string = "".join(random.choice(characters) for _ in range(length))
    return random_string


def set_path_for_ffmpeg_bin(base_dir: str):
    # set PATH for ffmpeg
    ffmpeg_path = os.path.join(base_dir, "ffmpeg_bin", "bin")
    os.environ["PATH"] = ffmpeg_path + os.pathsep + os.environ["PATH"]


def create_chat_completion(
    system_prompt: str,
    user_prompt: str,
    temperature: Union[float, None] = None,
    openai_use_azure: Union[bool, None] = None,
    openai_api_endpoint: Union[str, None] = None,
    openai_api_version: Union[str, None] = None,
    openai_api_model: Union[str, None] = None,
    retry_count: Union[int, None] = None,
):
    openai_use_azure = openai_use_azure or OPENAI_USE_AZURE
    openai_api_endpoint = openai_api_endpoint or OPENAI_API_ENDPOINT
    openai_api_version = openai_api_version or OPENAI_API_VERSION
    openai_api_model = openai_api_model or OPENAI_API_MODEL
    temperature = temperature or OPENAI_CHAT_TEMPERATURE
    retry_count = retry_count or RETRY_COUNT

    retry = 0
    while retry < retry_count:
        try:
            if retry > 0:
                print("retry: {}".format(retry))
            return _create_chat_completion(
                system_prompt,
                user_prompt,
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
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    openai_use_azure: bool,
    openai_api_endpoint: str,
    openai_api_version: str,
    openai_api_model: str,
):
    # # openaiの場合
    # openai.api_key = os.environ["OPENAI_API_KEY"]
    # response = openai.chat.completions.create(
    #     model="gpt-4-32k-0613",
    #     temperature=0.0,
    #     messages=[
    #         {"role": "system", "content": system_prompt},
    #         {"role": "user", "content": user_prompt},
    #     ],
    # )
    # return response.choices[0].message.content

    # azureの場合
    openai.api_type = "azure" if openai_use_azure else "openai"
    openai.api_version = openai_api_version
    openai.azure_endpoint = openai_api_endpoint
    openai.api_key = os.environ["OPENAI_API_KEY"]
    response = openai.chat.completions.create(
        model=openai_api_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content


def transcript_by_whisper(
    file_path: str,
    prompt: str,
    language: Union[str, None] = None,
    openai_api_whisper_endpoint: Union[str, None] = None,
    openai_api_whisper_deployment: Union[str, None] = None,
    openai_api_whisper_api_version: Union[str, None] = None,
    retry_count: Union[int, None] = None,
) -> Union[str, None]:
    language = language or DEFAULT_LANGUAGE
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

    retry = 0
    while retry < retry_count:
        try:
            if retry > 0:
                print("retry: {}".format(retry))
            # return _transcript_by_faster_whisper(
            #     file_path,
            #     prompt,
            #     language,
            # )
            return _transcript_by_whisper(
                file_path,
                prompt,
                language,
                openai_api_whisper_endpoint,
                openai_api_whisper_deployment,
                openai_api_whisper_api_version,
            )
        except Exception as e:
            print("An error occurred:", str(e))
            retry += 1
            time.sleep(5 * retry)
            continue
    return None


def _transcript_by_whisper(
    file_path: str,
    prompt: str,
    language: str,
    openai_api_whisper_endpoint: str,
    openai_api_whisper_deployment: str,
    openai_api_whisper_api_version: str,
) -> Union[str, None]:
    # # openaiの場合
    # with open(file_path, "rb") as f:
    #     transcript = openai.audio.transcriptions.create(
    #         file=f,
    #         model="whisper-1",
    #         prompt=prompt,
    #         language=language,
    #     )

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
    data = {"prompt": prompt, "language": language}
    with open(file_path, "rb") as f:
        transcript = requests.post(
            url, headers=headers, data=data, files=[("file", f)]
        ).json()
    try:
        return transcript["text"]
    except:
        return None


def _transcript_by_faster_whisper(
    file_path: str,
    prompt: str,
    language: str,
):
    from faster_whisper import WhisperModel

    model_size = "large-v2"
    # user_profile = os.environ["USERPROFILE"]
    # model_size = os.path.join(
    #     user_profile,
    #     r"Downloads\video_to_mom_streamlit\src\huggingface\hub\models--guillaumekln--faster-whisper-large-v2\snapshots\f541c54c566e32dc1fbce16f98df699208837e8b",
    # )
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(
        file_path,
        language=language,
        initial_prompt=prompt,
        without_timestamps=True,
    )
    text = ""
    for segment in segments:
        text = text + "\n" + segment.text
    return text
