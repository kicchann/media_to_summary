import time
from typing import List

from src.functions import extract_keywords, recognite_speakers, transcript_audio
from src.log.my_logger import MyLogger
from src.model import Task, Transcription

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
    transcriptions: List[Transcription] = []
    if not task.audio_data_list:
        return task
    for i, audio_data in enumerate(task.audio_data_list):
        logger.info(
            f"{task.id_} - section={i+1}/{len(task.audio_data_list)}, start={audio_data.start}, end={audio_data.end}"
        )
        prompt_dict = {
            "info_from_user": extract_keywords(task.response.description),
        }
        if i > 0:
            text = " ".join([t.text for t in transcriptions if t.section == i - 1])
            prompt_dict["previous_transcription"] = extract_keywords(text)
        logger.info(f"{task.id_} - prompt_dict = {prompt_dict}")
        try:
            desc = ", ".join(list(prompt_dict.values()))
            logger.info(f"{task.id_} - transcribing audio file")
            transcriptions += transcript_audio(
                audio_data=audio_data, description=desc, section=i
            )
            time.sleep(30)
            # ここで、文字起こしの修正をしようとしたが、うまくいかなかったのでコメントアウト
            # logger.info(f"{task.id_} - correcting transcriptions")
            # for t in transcriptions_base:
            #     logger.info(f"before - {t.text}")
            #     t = t.model_copy(
            #         update=dict(
            #             text=correct_transcription(
            #                 keywords=desc, transcript_text=t.text
            #             )
            #             or ""
            #         )
            #     )
            #     logger.info(f"after - {t.text}")
            #     transcriptions += [t]
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

    # TODO:話者識別
    # 将来話者識別できるように、発言者数を収集しているが、
    # 現時点ではうまくいかないのでコメントアウト
    # if task.response.recognite_speakers:
    #     logger.info(f"{task.id_} - recogniting speakers")
    #     transcriptions = recognite_speakers(
    #         task.audio_data_list,
    #         transcriptions,
    #         task.response.speakers,
    #     )

    # transcriptionsのstart, endを更新
    # 基準になる秒数を計算
    def my_round(number, ndigits=0):
        p = 10**ndigits
        return (number * p * 2 + 1) // 2 / p

    logger.info(f"{task.id_} - updating start/end of transcriptions")
    new_transcriptions = []
    for t in transcriptions:
        audio_data = task.audio_data_list[t.section]
        # audio_dataのstartは小数点第1位で丸める
        start = my_round(audio_data.start, 1)
        update_ = dict(start=t.start + start, end=t.end + start)
        new_transcriptions += [t.model_copy(update=update_)]

    result = task.model_copy(
        deep=True,
        update=dict(
            status="success",
            progress="transcription completed",
            transcriptions=new_transcriptions,
        ),
    )
    logger.info(f"{task.id_} - transcription_task finished")
    return result
