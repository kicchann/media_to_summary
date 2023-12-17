import os
import random
import string
import time
from typing import List, Union

import openai
import requests
from src.functions.config import (
    DEFAULT_LANGUAGE,
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
    system_prompt: str,
    user_prompt: str,
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
                system_prompt,
                user_prompt,
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
    system_prompt: str,
    user_prompt: str,
    max_tokens: Union[int, None],
    temperature: float,
    openai_use_azure: bool,
    openai_api_endpoint: str,
    openai_api_version: str,
    openai_api_model: str,
) -> str:
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
    openai.api_key = (
        os.environ["OPENAI_API_KEY"]
        if "gpt-4" in openai_api_model
        else os.environ["OPENAI_API_35_KEY"]
    )
    need_continue: bool = False
    contents: List[str] = []
    response = openai.chat.completions.create(
        model=openai_api_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    content = response.choices[0].message.content
    contents.append(content)
    if response.choices[0].finish_reason == "length":
        need_continue = True
    while need_continue:
        response = openai.chat.completions.create(
            model=openai_api_model,
            messages=[
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": contents[-1]},
            ],
            temperature=temperature,
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
                print("An error occurred:", str(e))
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
) -> Union[str, None]:
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
    data = {"prompt": prompt, "language": language, "response_format": "verbose_json"}
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
    #     r"Documents\models--Systran--faster-whisper-large-v2\snapshots\f0fe81560cb8b68660e564f55dd99207059c092e",  # float32用？
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
