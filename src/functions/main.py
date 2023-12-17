import os
import shutil
from typing import List, Union

import ffmpeg  # type: ignore
from src.functions.config import (
    MAX_DURATION_FOR_WHISPER,
    OPENAI_API_35_ENDPOINT,
    OPENAI_API_35_MODEL,
    OPENAI_API_35_VERSION,
    OPENAI_API_ENDPOINT,
    OPENAI_API_MODEL,
    OPENAI_API_VERSION,
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


class MediaToAudioConverter:
    def __init__(self):
        self._process_time = 0

    def convert(self, media_file_path: str, audio_file_path: str):
        # 動画ファイルが入力された場合は，音声ファイルに変換する
        # 音声ファイルが入力された場合は，そのまま返す
        # 条件分岐が必要かと思いきや、ffmpegは動画ファイルを入力すると音声ファイルに変換してくれるし、
        # 音声ファイルを入力するとそのまま音声ファイルを返してくれる
        # 拡張子が.mp3だからか？
        self.__convert(
            media_file_path=media_file_path,
            audio_file_path=audio_file_path,
        )
        return audio_file_path

    @staticmethod
    def __convert(media_file_path: str, audio_file_path: str):
        # async def __convert(media_file_path: str, audio_file_path: str):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        set_path_for_ffmpeg_bin(base_dir)
        # ffmpeg.bin = os.path.join(os.path.dirname(os.path.dirname(__file__)), r'ffmpeg_bin\bin')
        stream = ffmpeg.input(media_file_path)
        # TODO: 音量正規化
        # stream = ffmpeg.filter(stream, "loudnorm")
        stream = ffmpeg.output(stream, audio_file_path, format="mp3")
        ffmpeg.run(stream, overwrite_output=True)
        return

    @staticmethod
    def __media_or_audio(file_path):
        try:
            probe = ffmpeg.probe(file_path)
            video_streams = [
                stream for stream in probe["streams"] if stream["codec_type"] == "video"
            ]
            audio_streams = [
                stream for stream in probe["streams"] if stream["codec_type"] == "audio"
            ]
            if video_streams:
                return "video"
            elif audio_streams:
                return "audio"
            else:
                raise Exception("file is not video or audio")
        except ffmpeg.Error as e:
            raise e


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
    return audio_splitter.split(
        audio_file_path,
        split_audio_dir,
        use_last_10_mins_only=kwargs.get("use_last_10_mins_only"),
    )


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
    You are a highly skilled AI. 
    Your task is to analyze the following text, extract up to 5 important Japanese keywords, and list them in order of importance. 
    Output only comma-separated keywords. here is the text:
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
        )
    return prior


def summarize_transcription(
    transcriptions: List[Transcription],
    add_title: bool,
    add_todo: bool,
):
    system_prompt_1 = f"""
    You are a highly skilled AI. Your task is to analyze the following transcription, summarize it without losing any important information, and present the summary in markdown bullet points in Japanese. When possible, include specific numbers, expressions, and examples from the transcription in your summary. Here is the transcription:
    """
    # system_prompt_1 = f"""
    # # instructions

    # - You are an excellent AI assistant
    # - Show off your brilliant reasoning skills and follow the tasks below in order

    # # tasks

    # - Interpret the transcripion abstractly, summarize it without any loss of information, and output the summary with markdown bullet points
    # - Output in JAPANESE
    # - It is preferable to refer concrete numbers, expressions, and examples from the transcription as much as possible
    # """
    summary_header = "## 要約 \n\n"
    summaries = []
    for transcription in transcriptions:
        if len(transcriptions) == 1:
            summary = create_chat_completion(
                system_prompt_1,
                transcription.text,
                openai_api_endpoint=OPENAI_API_35_ENDPOINT,
                openai_api_version=OPENAI_API_35_VERSION,
                openai_api_model=OPENAI_API_35_MODEL,
            )
        else:
            summary = create_chat_completion(
                system_prompt_1,
                transcription.text,
            )
        start_time = transcription.start_time
        end_time = transcription.start_time + transcription.duration
        start_min = (
            f"{str(int(start_time//60)).zfill(2)}:{str(int(start_time%60)).zfill(2)}"
        )
        end_min = f"{str(int(end_time//60)).zfill(2)}:{str(int(end_time%60)).zfill(2)}"
        summaries.append(
            {
                "start_min": start_min,
                "end_min": end_min,
                "summary": summary,
            }
        )
        summary_text = summary_header + "\n\n".join(
            [
                f"### {i+1} / {len(summaries)}\n\n{summary['summary']}"
                for i, summary in enumerate(summaries)
            ]
        )
    if add_title:
        title_header = "## タイトル \n\n"
        system_prompt_2 = f"""
        You are a highly skilled AI. Your task is to analyze the following Japanese summary, then generate a simple and easy-to-understand title in Japanese. Output title text only. Here is the summary:
        """
        # system_prompt_2 = f"""
        # # instructions

        # - You are an excellent AI assistant
        # - Show off your brilliant reasoning skills and follow the tasks below in order

        # # tasks

        # - Interpret the summary text abstractly, generate a simlple and easy-to-understand title, and output it
        # - Output in JAPANESE
        # """
        title = create_chat_completion(
            system_prompt_2,
            "\n".join([summary["summary"] for summary in summaries]),
        )
        summary_text = title_header + title + "\n\n" + summary_text
    if add_todo:
        todo_header = "\n\n## TODO \n\n"
        system_prompt_3 = f"""
        You are a highly skilled AI. Your task is to analyze the following summary and generate a list of tasks from it. Output only important tasks that require concrete action for simplicity and efficiency. Output only tasks in markdown bullet points in Japanese. Here is the summary:
        """
        # system_prompt_3 = f"""
        # # instructions

        # - You are an excellent AI assistant
        # - Show off your brilliant reasoning skills and follow the tasks below in order

        # # tasks

        # - Interpret the summary text abstractly, and output the todos with markdown bullet points
        # - Just output bullet points, do not output the heading
        # - Output in JAPANESE
        # """
        todo = create_chat_completion(
            system_prompt_3,
            summary_text,
        )
        summary_text += todo_header + todo
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
