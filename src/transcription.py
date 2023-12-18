import json

from src.functions import (
    extract_keywords,
    process_transcription,
    recognite_speakers,
    transcript_audio,
)
from src.log.my_logger import MyLogger
from src.model import Task

my_logger = MyLogger(__name__)
logger = my_logger.logger


def transcription_task(task: Task) -> Task:
    """
    文字起こし処理を行う関数

    Args:
        task (Task): 処理対象のタスク
    Returns:
        Task: 処理結果のタスク
    """
    logger.info(f"{task.id_} - transcription_task called")
    # 処理結果情報
    transcriptions = []
    if not task.audio_data_list:
        return task
    for i, audio_data in enumerate(task.audio_data_list):
        logger.info(
            f"{task.id_}: transcription_task = {i+1}/{len(task.audio_data_list)}"
        )
        logger.info(f"{task.id_} - start = {audio_data.start}")
        logger.info(f"{task.id_} - end = {audio_data.end}")
        prompt_dict = {
            "info_from_user": extract_keywords(task.response.description),
        }
        if i > 0:
            text = " ".join([t.text for t in transcriptions if t.section == i - 1])
            prompt_dict["previous_transcription"] = extract_keywords(text)
        logger.info(f"{task.id_} - prompt_dict = {prompt_dict}")
        try:
            transcriptions += transcript_audio(
                audio_data=audio_data,
                description=",".join(list(prompt_dict.values())),
                section=i,
            )
            # TODO: 文法の修正はコストの観点から一旦保留
            # for t in transcriptions_base:
            #     transcriptions += [t.model_copy(
            #         update=dict(
            #             text=process_transcription(
            #                 master_prompt=t.keywords,
            #                 transcript_text=t.text,
            #             ),
            #         )
            #     )]
        except Exception as e:
            logger.error(f"{task.id_} - error occurred while transcribing audio file")
            logger.error(f"{task.id_} - audio_data = {audio_data}")
            logger.error(f"{task.id_} - {e}")
            result = task.model_copy(
                deep=True,
                update=dict(
                    status="error",
                    progress="error occurred while transcribing audio file",
                    message="文字起こし中にエラーが発生しました",
                    transcriptions=None,
                ),
            )
            return result
    # transcriptionsのstart, endを更新
    # 基準になる秒数を計算
    logger.info(f"{task.id_} - updating start, end of transcriptions")
    unique_sections = sorted(list(set([t.section for t in transcriptions])))
    base_times = []
    for section in unique_sections:
        target_transcriptions = [t for t in transcriptions if t.section == section]
        base_time = base_times[-1] if len(base_times) > 0 else 0.0
        end_time = max([t.end for t in target_transcriptions]) + base_time
        base_times += [end_time]
    # start, endを更新
    for i in range(len(transcriptions)):
        base_time = base_times[transcriptions[i].section]
        start = transcriptions[i].start + base_time
        end = transcriptions[i].end + base_time
        transcriptions[i] = transcriptions[i].model_copy(
            update=dict(start=start, end=end)
        )

    # 話者識別
    if task.response.recognite_speakers:
        logger.info(f"{task.id_} - recogniting speakers")
        transcriptions = recognite_speakers(transcriptions, task.response.speakers)
    result = task.model_copy(
        deep=True,
        update=dict(
            status="success",
            progress="transcription completed",
            transcriptions=transcriptions,
        ),
    )
    logger.info(f"{task.id_} - transcription_task finished")
    return result
