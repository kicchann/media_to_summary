import os
import time
from typing import Dict, List, Union

import ffmpeg  # type: ignore
import timeout_decorator  # type: ignore

from src.functions.config import TOKEN_LIMIT, TOKEN_SIZE_FOR_SPLIT
from src.functions.model import AudioData, Transcription
from src.functions.utils import (
    AudioSplitter,
    create_chat_completion,
    set_path_for_ffmpeg_bin,
    transcript_by_whisper,
)


# 1時間以上かかる場合は，エラーとする
# @timeout_decorator.timeout(3600, use_signals=False)
def convert_video_to_audio(video_file_path: str, audio_file_path: str):
    base_dir = os.path.dirname(os.path.dirname(__file__))
    set_path_for_ffmpeg_bin(base_dir)
    # ffmpeg.bin = os.path.join(os.path.dirname(os.path.dirname(__file__)), r'ffmpeg_bin\bin')
    stream = ffmpeg.input(video_file_path)
    stream = ffmpeg.output(stream, audio_file_path, format="mp3")
    ffmpeg.run(stream, overwrite_output=True)
    return


def split_audio(
    audio_file_path: str,
    split_audio_dir: str,
    **kwargs,
) -> List[AudioData]:
    # 音声ファイルを分割する
    audio_splitter = AudioSplitter(
        max_file_size_for_whisper=kwargs.get("max_file_size_for_whisper"),
        min_silence_len=kwargs.get("min_silence_len"),
        silence_thresh=kwargs.get("silence_thresh"),
        keep_silence=kwargs.get("keep_silence"),
    )
    return audio_splitter.split(audio_file_path, split_audio_dir)


def transcript_audio(
    audio_data: AudioData,
    description: str = "",
) -> Transcription:
    prompt = description
    text = transcript_by_whisper(audio_data.file_path, prompt)

    transcription = Transcription(
        text="" if text is None else text,
        speaker=audio_data.speaker,
        duration=audio_data.duration,
        start_time=audio_data.start_time,
    )
    return transcription


def compress_text(
    transcriptions: List[Transcription],
    text_token_limit: Union[int, None] = None,
    split_token_length: Union[int, None] = None,
):
    def create_user_prompt(prior, later):
        return f"""
        prior input text: "{prior}"
        later input text: "{later}"
        """

    text_token_limit = text_token_limit or TOKEN_LIMIT
    split_token_length = split_token_length or TOKEN_SIZE_FOR_SPLIT
    prior = ""
    system_prompt = f"""
        # instructions

        - You are an excellent AI assistant
        - Show off your brilliant reasoning skills and follow the tasks below in order

        # tasks

        - Interpret the prior input text and later input text as a single conversation
        - Please correct the conversation to be grammatically correct
        - if total length of conversation is less than {text_token_limit} tokens, just output the conversation
        - if total length of conversation is greater than {text_token_limit} tokens, interpret the conversation as a single document and summarize it with a max token length of {text_token_limit}
        - Please output in JAPANESE

        """
    all_script = "".join(
        [
            f"{transcription.text}: {transcription.speaker}"
            for transcription in transcriptions
        ]
    )
    for i in range(len(all_script) // split_token_length + 1):
        later = all_script[split_token_length * i : split_token_length * (i + 1)]
        user_prompt = create_user_prompt(prior, later)
        prior = create_chat_completion(system_prompt, user_prompt) if i > 0 else later
    return prior


def summarize_text(
    transcript_text: str,
    summary_length: int,
    add_title: bool,
    add_todo: bool,
):
    system_prompt = f"""  
    # instructions  

    - You are an excellent AI assistant  
    - Show off your brilliant reasoning skills and follow the tasks below in order  

    # tasks  

    - Interpret the input text abstractly, summarizes it without losing important context, and generate a title of no more than 50 characters  
    - Interpret the input text abstractly, summarize it without losing important context, and generate bulleted summaries of no more than {summary_length} characters in total 
    - In summaries, it is preferable to include the concrete numbers and facts that are important in the input text  
    - Please output in JAPANESE  
    - Please output in a markdown style structured text format  

    # template  

    """
    if add_title:
        system_prompt += "\n\n## タイトル \n\n[please write title]\n\n"
    system_prompt += "## 要約 \n- [please write summary]\n\n"
    if add_todo:
        system_prompt += "## TODO \n- [please write todo]\n\n"
    summary = create_chat_completion(system_prompt, transcript_text)
    return summary
