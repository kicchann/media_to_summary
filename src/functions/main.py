import os
from typing import List, Union

import ffmpeg  # type: ignore
from src.functions.config import (
    MAX_DURATION_FOR_WHISPER,
    OPENAI_API_35_ENDPOINT,
    OPENAI_API_35_MODEL,
    OPENAI_API_35_VERSION,
    TOKEN_LIMIT,
    TOKEN_SIZE_FOR_SPLIT,
)
from src.functions.model import AudioData, Transcription
from src.functions.utils import (
    AudioSplitter,
    create_chat_completion,
    set_path_for_ffmpeg_bin,
    transcript_by_whisper,
)


class VideoToAudioConverter:
    def __init__(self):
        self._process_time = 0

    def convert(self, video_file_path: str, audio_file_path: str):
        self.__convert(
            video_file_path=video_file_path,
            audio_file_path=audio_file_path,
        )
        # self._process_time = time.time()
        # while True:
        #     if os.path.exists(audio_file_path):
        #         break
        #     if time.time() - self._process_time > 1800:
        #         raise TimeoutError(
        #             "video to audio conversion takes too long time. please check ffmpeg process"
        #         )
        #     time.sleep(1)

    @staticmethod
    def __convert(video_file_path: str, audio_file_path: str):
        # async def __convert(video_file_path: str, audio_file_path: str):
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
        keywords=description,
        speaker=audio_data.speaker,
        duration=audio_data.duration,
        start_time=audio_data.start_time,
    )
    return transcription


def extract_keywords(transcript_text: str):
    system_prompt = f"""  
    # instructions  

    - You are an excellent AI assistant  
    - Show off your brilliant reasoning skills and follow the tasks below in order  

    # tasks  

    - Please output in JAPANESE
    - Interpret the input text abstractly, extract keywords, and output comma-separated keywords
    - number of keywords MUST NOT BE MORE THAN 5
    - sort keywords in descending order of importance
    """
    keywords = create_chat_completion(
        system_prompt,
        transcript_text,
    )
    try:
        keywords = keywords.split(",")[:5]
        return ",".join(keywords)
    except Exception as e:
        return ""


def process_transcription(master_prompt: str, transcript_text: str):
    system_prompt = f"""  
    # instructions  

    - You are an excellent AI assistant  
    - Show off your brilliant reasoning skills and follow the tasks below in order  

    # tasks  

    Interpret the transcripion abstractly, correct misspelled words and grammatical errors, and output the corrected text.
    To correct misspelled words, use the following keywords to indicate what's in your transcription: {master_prompt}.
    Output in JAPANESE.
    """
    keywords = create_chat_completion(
        system_prompt,
        transcript_text,
    )
    return keywords


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
        
        Interpret the prior input text and later input text as a single conversation, remove unnecessary expressions, correct the conversation to be grammatically correct, and compress it not to exceed the specified word count.
        DO NOT EXCEED THE WORD COUNT LIMIT.

        - Please output in JAPANESE
        - WORD COUNT LIMIT: {text_token_limit//2}
        """
    all_script = " ".join([transcription.text for transcription in transcriptions])
    for i in range(len(all_script) // (split_token_length // 2) + 1):
        if i == 0:
            prior = all_script[
                (split_token_length // 2) * i : (split_token_length // 2) * (i + 1)
            ]
            continue
        later = all_script[
            (split_token_length // 2) * i : (split_token_length // 2) * (i + 1)
        ]
        user_prompt = create_user_prompt(prior, later)
        prior = create_chat_completion(
            system_prompt,
            user_prompt,
            max_tokens=text_token_limit,
            openai_api_endpoint=OPENAI_API_35_ENDPOINT,
            openai_api_model=OPENAI_API_35_MODEL,
            openai_api_version=OPENAI_API_35_VERSION,
        )
    return prior


def summarize_transcription(
    transcriptions: List[Transcription],
    add_title: bool,
    add_todo: bool,
):
    system_prompt_1 = f"""  
    # instructions  

    - You are an excellent AI assistant  
    - Show off your brilliant reasoning skills and follow the tasks below in order  

    # tasks  

    - Interpret the transcripion abstractly, summarize it without any loss of information, and output the summary with markdown bullet points
    - Output in JAPANESE
    - It is preferable to refer concrete numbers, expressions, and examples from the transcription as much as possible
    """
    summary_text = "## 要約 \n\n"
    min_unit = MAX_DURATION_FOR_WHISPER / 60
    for i, transcription in enumerate(transcriptions):
        summary = create_chat_completion(
            system_prompt_1,
            transcription.text,
            openai_api_endpoint=OPENAI_API_35_ENDPOINT,
            openai_api_model=OPENAI_API_35_MODEL,
            openai_api_version=OPENAI_API_35_VERSION,
        )
        summary_text += (
            f"### {int(i*min_unit)}分-{int((i+1)*min_unit)}分ごろ \n\n" + summary + "\n\n"
        )
    if add_title:
        system_prompt_2 = f"""  
        # instructions  

        - You are an excellent AI assistant  
        - Show off your brilliant reasoning skills and follow the tasks below in order  

        # tasks  

        - Interpret the summary text abstractly, generate a simlple and easy-to-understand title, and output it
        - Output in JAPANESE
        """
        title = create_chat_completion(
            system_prompt_2,
            summary_text,
            openai_api_endpoint=OPENAI_API_35_ENDPOINT,
            openai_api_model=OPENAI_API_35_MODEL,
            openai_api_version=OPENAI_API_35_VERSION,
        )
        summary_text = "## タイトル \n\n" + title + "\n\n" + summary_text
    if add_todo:
        system_prompt_3 = f"""  
        # instructions  

        - You are an excellent AI assistant  
        - Show off your brilliant reasoning skills and follow the tasks below in order  

        # tasks  

        - Interpret the summary text abstractly, and output the todos with markdown bullet points
        - Output in JAPANESE
        """
        todo = create_chat_completion(
            system_prompt_3,
            summary_text,
            openai_api_endpoint=OPENAI_API_35_ENDPOINT,
            openai_api_model=OPENAI_API_35_MODEL,
            openai_api_version=OPENAI_API_35_VERSION,
        )
        summary_text += "## TODO \n\n" + todo + "\n\n"
    return summary_text


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

    Interpret the transcripion abstractly, summarize it without any loss of information, and output the summary with bullet points.
    TOTAL WORD COUNT RANGE MUST BE WITHIN THE SPECIFIED RANGE AS FOLLOWS.

    - Lower word limit: {int(summary_length*0.7)}
    - Upper word limit: {int(summary_length*1.0)}

    Output in JAPANESE, and use the following template (markdown format) to output the summary.

    # template  

    """
    if add_title:
        system_prompt += "\n\n## タイトル \n\n[please write title]\n\n"
    system_prompt += "## 要約 \n- [please write summary]\n\n"
    if add_todo:
        system_prompt += "## TODO \n- [please write todo]\n\n"
    summary = create_chat_completion(
        system_prompt,
        transcript_text,
        max_tokens=summary_length * 2,
    )
    return summary
