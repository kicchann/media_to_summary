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
    logger.info("transcription_task called")
    # 処理結果情報
    transcriptions = []
    if not task.audio_data_list:
        return task
    for i, audio_data in enumerate(task.audio_data_list):
        logger.info(f"transcription_task: {i+1}/{len(task.audio_data_list)}")
        logger.info(f"start: {audio_data.start}")
        logger.info(f"end: {audio_data.end}")
        prompt_dict = {
            "info_from_user": extract_keywords(task.response.description),
        }
        if i > 0:
            text = " ".join([t.text for t in transcriptions if t.section == i - 1])
            prompt_dict["previous_transcription"] = extract_keywords(text)
        logger.info(f"prompt_dict: {prompt_dict}")
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
            logger.error("error occurred while transcribing audio file")
            logger.error(f"audio_data: {audio_data}")
            logger.error(e)
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
    # 話者識別
    if task.response.recognite_speakers:
        logger.info("recogniting speakers")
        transcriptions = recognite_speakers(transcriptions, task.response.speakers)
    result = task.model_copy(
        deep=True,
        update=dict(
            status="success",
            progress="transcription completed",
            transcriptions=transcriptions,
        ),
    )
    logger.info("transcription_task finished")
    return result
