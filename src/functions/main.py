from typing import List, Union

import numpy as np
from src.functions.config import (
    OPENAI_API_35_ENDPOINT,
    OPENAI_API_35_MODEL,
    OPENAI_API_35_VERSION,
    OPENAI_API_ENDPOINT,
    OPENAI_API_MODEL,
    OPENAI_API_VERSION,
    TOKEN_LIMIT,
    TOKEN_SIZE_FOR_SPLIT,
)
from src.functions.model import AudioData, Speaker, Transcription
from src.functions.utils import (
    AudioSplitter,
    create_chat_completion,
    get_features_of_voice,
    get_n_cluster_by_x_means,
    get_speakers_by_k_means,
    transcript_by_whisper,
)


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
    section: int = 0,
    speaker_recognition: bool = True,
) -> List[Transcription]:
    prompt = description
    print("transcripting...")
    transcript_list = transcript_by_whisper(audio_data.file_path, prompt)
    print("getting features...")
    features = []
    if speaker_recognition:
        features = get_features_of_voice(audio_data.file_path, transcript_list)
    transcriptions = []
    print("returning transcriptions...")
    for i, t in enumerate(transcript_list):
        f = features[i] if len(features) > 0 else []
        # 雑音を文字起こしして同じ文字列が何度も続くことがある
        # それを除外するために、2回以上続く場合は直前のtranscriptionを除外する
        if i > 1 and t["text"] == transcriptions[-1].text:
            transcriptions = transcriptions[:-1]
        transcriptions.append(
            Transcription(
                text=t["text"],
                keywords=description,
                features=f,
                start=t["start"],
                end=t["end"],
                section=section,
            )
        )
    return transcriptions


def recognite_speakers(
    transcriptions: List[Transcription],
    speakers: Union[int, tuple[int], None] = None,
) -> List[Transcription]:
    """
    話者識別の結果を反映する
    transcriptionsにあるfeaturesとkMeans++を用いて実装
    speakersがNoneと、tupleの場合はx_meansを使って話者数を推定
    speakersがintの場合は、その数の話者を想定してクラスタリング
    """
    try:
        features = np.array([t.features for t in transcriptions])
        if not isinstance(speakers, int):
            speakers = get_n_cluster_by_x_means(features, speakers)
        speakers = get_speakers_by_k_means(features, speakers)
        # Transcriptionにspeaker情報を追加
        for i, t in enumerate(transcriptions):
            transcriptions[i] = t.model_copy(
                update=dict(speaker=Speaker(name=speakers[i]))
            )
        return transcriptions
    except Exception as e:
        return transcriptions


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
    You are a highly skilled AI. 
    Your task is to analyze the transcripion abstractly, correct misspelled words and grammatical errors, and output the corrected text.
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
    summary_header = "## 要約 \n\n"
    summaries = []
    unique_sections = sorted(list(set([t.section for t in transcriptions])))
    base_time = 0.0
    for section in unique_sections:
        target_transcriptions = [t for t in transcriptions if t.section == section]
        if len(unique_sections) == 1:
            summary = create_chat_completion(
                system_prompt_1,
                " ".join([t.text for t in target_transcriptions]),
                openai_api_endpoint=OPENAI_API_35_ENDPOINT,
                openai_api_version=OPENAI_API_35_VERSION,
                openai_api_model=OPENAI_API_35_MODEL,
            )
        else:
            summary = create_chat_completion(
                system_prompt_1,
                " ".join([t.text for t in target_transcriptions]),
            )
        start = min([t.start for t in target_transcriptions]) + base_time
        end_time = max([t.end for t in target_transcriptions]) + base_time
        base_time = end_time
        start_str = f"{str(int(start//60)).zfill(2)}:{str(int(start%60)).zfill(2)}"
        end_str = f"{str(int(end_time//60)).zfill(2)}:{str(int(end_time%60)).zfill(2)}"
        summaries.append(
            {
                "start": start_str,
                "end": end_str,
                "summary": summary,
            }
        )
    summary_text = summary_header + "\n\n".join(
        [
            f"### {summary['start']} - {summary['end']}\n\n{summary['summary']}"
            # f"### {i+1} / {len(summaries)}\n\n{summary['summary']}"
            for i, summary in enumerate(summaries)
        ]
    )
    if add_title:
        title_header = "## タイトル \n\n"
        system_prompt_2 = f"""
        You are a highly skilled AI. Your task is to analyze the following Japanese summary, then generate a simple and easy-to-understand title in Japanese. Output title text only. Here is the summary:
        """
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
