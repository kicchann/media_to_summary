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
) -> List[Transcription]:
    transcript_list = transcript_by_whisper(audio_data.file_path, description)
    transcriptions: List[Transcription] = []
    if transcript_list is None:
        return transcriptions
    for i, t in enumerate(transcript_list):
        # 雑音を文字起こしして同じ文字列が何度も続くことがある
        # それを除外するために、2回以上続く場合はそのtranscriptionを除外する
        if i > 1 and t["text"] == transcriptions[-1].text:
            continue
        transcriptions.append(
            Transcription(
                text=t["text"],
                keywords=description,
                features=[],
                start=t["start"],
                end=t["end"],
                section=section,
            )
        )
    return transcriptions

  
def recognite_speakers(
    audio_data_list: List[AudioData],
    transcriptions: List[Transcription],
    speakers: Union[int, tuple[int]],
) -> List[Transcription]:
    """
    話者識別の結果を反映する
    transcriptionsにあるfeaturesとkMeans++を用いて実装
    speakersがNoneと、tupleの場合はx_meansを使って話者数を推定
    speakersがintの場合は、その数の話者を想定してクラスタリング
    """
    try:
        features = []
        # 特徴量を取得
        for i, audio_data in enumerate(audio_data_list):
            target_transcriptions = [t for t in transcriptions if t.section == i]
            features += get_features_of_voice(
                audio_data.file_path,
                [[t.start, t.end] for t in target_transcriptions],
            )
        # クラスタリング
        if not isinstance(speakers, int):
            speakers = get_n_cluster_by_x_means(features, speakers)
        speakers = get_speakers_by_k_means(features, speakers)
        # Transcriptionにspeaker情報を追加
        new_transcriptions = []
        for i, t in enumerate(transcriptions):
            update_ = dict(
                features=features[i],
                speaker=Speaker(name=speakers[i]),
            )
            new_transcriptions += [t.model_copy(deep=True, update=update_)]
        # ソートしてから返す
        new_transcriptions = sorted(new_transcriptions)
        return new_transcriptions
    except Exception as e:
        return transcriptions


def get_keywords_from_document(
    file_path: str,
) -> str:
    from pypdf import PdfReader

    # 今はPDFのみ対応
    if not file_path.endswith(".pdf"):
        return ""
    # PDFの読み込み
    reader = PdfReader(file_path)
    text = "\n".join([page.extract_text() for page in reader.pages])
    # 6000文字に限定してテキスト抽出
    if len(text) > 6000:
        text = text[:3000] + "(中略)" + text[-3000:]
    return extract_keywords(text, max(len(text) // 500, 5))


def extract_keywords(transcript_text: str, num_of_keywords: int = 5) -> str:
    if len(transcript_text) < 25:
        return transcript_text
    system_prompt = f"""
    You are highly skilled AI trained to extract important keywords or abstract words from a given text.
    """
    q_1 = "人工知能は私たちの生活をより便利にし、効率的にするための強力なツールです。それは、データ分析、画像認識、自然言語処理など、多くの異なるタスクで使用することができます。"
    a_1 = ",".join(
        [
            "人工知能",
            "機械学習",
            "データ分析",
            "自然言語処理",
            "画像認識",
            "効率的",
            "便利",
            "生活",
            "強力",
            "ツール",
            "タスク",
        ][:num_of_keywords]
    )
    q_2 = "廃棄物発電、再生可能エネルギー（バイオマス、地熱、風力等）、コージェネレーション、石油・天然ガス開発といった各種施設・プラントのEPC・O&Mを通じて、持続可能な環境調和型社会の構築に貢献します。"
    a_2 = ",".join(
        [
            "プラント施設",
            "EPC",
            "O&M",
            "持続可能",
            "環境調和型社会",
            "配管工事",
            "エンジニアリング",
            "廃棄物発電",
            "再生可能エネルギー",
            "汚泥資源化",
            "コージェネレーション",
            "石油・天然ガス開発",
            "パイプライン",
        ][:num_of_keywords]
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": q_1},
        {"role": "assistant", "content": a_1},
        {"role": "user", "content": q_2},
        {"role": "assistant", "content": a_2},
        {"role": "user", "content": transcript_text},
    ]
    keywords = create_chat_completion(messages)
    try:
        keywords = keywords.split(",")[:num_of_keywords]
        return ", ".join(keywords)
    except Exception as e:
        return transcript_text[:50]


def correct_transcription(keywords: str, transcript_text: str):
    system_prompt = f"""  
    You are a highly skilled AI trained to analyze the following transcription, correct misspelled words and grammatical errors, and output the corrected transcription.
    For correstion, you can take into account the following keywords of the transcription.
    keywords: {keywords}
    Output in JAPANESE.
    here is the transcription:
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": transcript_text},
    ]
    keywords = create_chat_completion(messages)
    return keywords


def summarize_transcription(
    transcriptions: List[Transcription],
    add_title: bool,
    add_todo: bool,
):
    summary_header = "## 要約 \n\n"
    summaries = []
    # sectionごとに要約を行う
    unique_sections = sorted(list(set([t.section for t in transcriptions])))
    for section in unique_sections:
        target_transcriptions = [t for t in transcriptions if t.section == section]
        # sectionが1つの場合は、GPT-4を使って要約を行う
        if len(unique_sections) == 1:
            summary = __summarize_text(target_transcriptions, use_gpt_4=True)
        else:
            summary = __summarize_text(target_transcriptions)
        # 開始時間と終了時間を取得
        start = min([t.start for t in target_transcriptions])
        end_time = max([t.end for t in target_transcriptions])
        start_str = f"{str(int(start//60)).zfill(2)}:{str(int(start%60)).zfill(2)}"
        end_str = f"{str(int(end_time//60)).zfill(2)}:{str(int(end_time%60)).zfill(2)}"
        # 要約結果を追加
        summaries.append({"start": start_str, "end": end_str, "summary": summary})
    summary_text = summary_header + "\n\n".join(
        [
            f"### {summary['start']} - {summary['end']}\n\n{summary['summary']}"
            # f"### {i+1} / {len(summaries)}\n\n{summary['summary']}"
            for i, summary in enumerate(summaries)
        ]
    )
    if add_title:
        title_header = "## タイトル \n\n"
        title = __create_title("\n".join([summary["summary"] for summary in summaries]))
        summary_text = title_header + title + "\n\n" + summary_text
    if add_todo:
        todo_header = "\n\n## TODO \n\n"
        todo = __create_todos("\n".join([summary["summary"] for summary in summaries]))
        summary_text += todo_header + todo
    return summary_text


def __create_title(text: str):
    system_prompt = f"""
    I'm highly skilled AI tranined to generate a simple and easy-to-understand title from given summary in Japanese.
    """
    q_1 = "人工知能は私たちの生活をより便利にし、効率的にするための強力なツールです。それは、データ分析、画像認識、自然言語処理など、多くの異なるタスクで使用することができます。"
    a_1 = "生活を便利にする強力なツールとしての人工知能"
    q_2 = (
        "- 病気の予防と健康維持に、健康的な食事と適度な運動が不可欠であることを認識共有した。\n - その上で、今後の活動の進め方や目標・方針について議論した。"
    )
    a_2 = "病気の予防と健康維持に向けた活動の進め方や目標・方針について"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": q_1},
        {"role": "assistant", "content": a_1},
        {"role": "user", "content": q_2},
        {"role": "assistant", "content": a_2},
        {"role": "user", "content": text},
    ]
    return create_chat_completion(messages)


def __create_todos(text: str):
    system_prompt = f"""
    You are a highly skilled AI trained to analyze the summary and generate a list of tasks from it.
    Output only important tasks that require concrete action for simplicity and efficiency.
    Output only tasks in markdown bullet points in Japanese.
    """
    q_1 = "カレーを作るためには、まずじゃがいも、人参、玉ねぎを切ります。次に、鍋に油を熱し、肉を炒めます。肉が白くなったら、切った野菜を加えて炒め続けます。野菜が柔らかくなったら、水500mlとカレールーを加えてよく混ぜます。カレーが煮込まれている間、ご飯を炊きます。カレーが十分に煮込まれたら、火から下ろし、炊きたてのご飯と一緒に盛り付けます。"
    a_1 = "- 野菜をカットする\n- 肉・野菜を加熱する\n- 500mlの水とカレールーを加えてよく混ぜる\n- ご飯を炊く\n- カレーとご飯を盛り付ける"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": q_1},
        {"role": "assistant", "content": a_1},
        {"role": "user", "content": text},
    ]
    return create_chat_completion(messages)


def __summarize_text(
    transcriptions: List[Transcription],
    use_gpt_4: bool = False,
):
    openai_api_endpoint = OPENAI_API_35_ENDPOINT if use_gpt_4 else None
    openai_api_version = OPENAI_API_35_VERSION if use_gpt_4 else None
    openai_api_model = OPENAI_API_35_MODEL if use_gpt_4 else None
    # 先に文字起こしの修正を行う
    system_prompt_1 = f"""  
    You are a highly skilled AI. 
    Your task is to analyze the following transcription, correct misspelled words and grammatical errors, and output the corrected transcription.
    For correstion, take into account the following keywords, which is extracted from the transcription.
    keywords: {transcriptions[0].keywords}
    Output in JAPANESE.
    here is the transcription:
    """
    messages = [
        {"role": "system", "content": system_prompt_1},
        {"role": "user", "content": " ".join([t.text for t in transcriptions])},
    ]
    corrected_text = create_chat_completion(
        messages,
        openai_api_endpoint=openai_api_endpoint,
        openai_api_version=openai_api_version,
        openai_api_model=openai_api_model,
    )
    # そのあとに要約を行う
    system_prompt_2 = f"""
    You are a highly skilled AI. Your task is to analyze the following transcription, summarize it without losing any important information, and present the summary in markdown bullet points in Japanese. When possible, include specific numbers, expressions, and examples from the transcription in your summary. Here is the transcription:
    """
    messages = [
        {"role": "system", "content": system_prompt_2},
        {"role": "user", "content": corrected_text},
    ]
    summary = create_chat_completion(
        messages,
        openai_api_endpoint=openai_api_endpoint,
        openai_api_version=openai_api_version,
        openai_api_model=openai_api_model,
    )
    return summary


# 今は使っていない
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
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": create_user_prompt(prior, later)},
        ]

        prior = create_chat_completion(
            messages,
            max_tokens=text_token_limit,
        )
    return prior
