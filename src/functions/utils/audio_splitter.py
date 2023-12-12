import os
import shutil
import uuid
from typing import Dict, List, Union

from pydub import AudioSegment
from pydub.silence import split_on_silence
from src.functions.config import (
    KEEP_SILENCE,
    MAX_DURATION_FOR_WHISPER,
    MAX_FILE_SIZE_FOR_WHISPER,
    MIN_SILENCE_LEN,
    SILENCE_THRESH,
)
from src.functions.model import AudioData


class AudioSplitter:
    def __init__(
        self,
        max_file_size_for_whisper: Union[float, None] = None,
        max_duration_for_whisper: Union[float, None] = None,
        min_silence_len: Union[int, None] = None,
        silence_thresh: Union[int, None] = None,
        keep_silence: Union[int, None] = None,
    ):
        self._max_file_size_for_whisper = (
            max_file_size_for_whisper or MAX_FILE_SIZE_FOR_WHISPER
        )
        self._max_duration_for_whisper = (
            max_duration_for_whisper or MAX_DURATION_FOR_WHISPER
        )
        self._min_silence_len = min_silence_len or MIN_SILENCE_LEN
        self._silence_thresh = silence_thresh or SILENCE_THRESH
        self._keep_silence = keep_silence or KEEP_SILENCE

    # https://agusblog.net/colab-file-split/?reloadTimes=2
    def split(
        self,
        audio_file_path: str,
        split_audio_dir: str,
    ) -> List[AudioData]:
        # audio_file_pathから拡張子を取得してformatに指定する
        _, ext = os.path.splitext(audio_file_path)
        format = ext.lstrip(".")
        sound = AudioSegment.from_file(audio_file_path, format=format)
        file_size = os.path.getsize(audio_file_path)
        total_duration = sound.duration_seconds

        # 10分を超える場合、25MBを超える場合は分割する
        # 超えない場合はそのままaudiosフォルダに移動
        if (
            total_duration <= self._max_duration_for_whisper
            and file_size <= self._max_file_size_for_whisper
        ):
            audio_data_id = str(uuid.uuid4())  # str(1).zfill(3)
            split_audio_file_path = os.path.join(
                split_audio_dir, f"{audio_data_id}.{format}"
            )
            # ファイルをコピーしてaudiosフォルダに移動
            shutil.copyfile(audio_file_path, split_audio_file_path)
            return [
                AudioData(
                    file_path=split_audio_file_path,
                    start_time=0,
                    duration=len(sound),
                )
            ]

        # durationのthreshholdをファイルサイズとdurationから計算する
        max_duration_from_size = total_duration * (
            self._max_file_size_for_whisper / file_size
        )
        max_duration = min(max_duration_from_size, self._max_duration_for_whisper)

        # 無音部分をカットして分割
        chunks = split_on_silence(
            sound,
            min_silence_len=self._min_silence_len,
            silence_thresh=self._silence_thresh,
            keep_silence=self._keep_silence,
        )

        # chunkがmax_lengthを超えない最大の長さになるように，chunkを結合する
        # 結合したchunkを，mp3ファイルを出力する
        new_chunk = None
        start_time = 0.0
        audio_data_list: List[AudioData] = []
        for chunk in chunks:
            # 0.3s以下のchunkは無視する
            if chunk.duration_seconds <= 0.3:
                continue
            if new_chunk is None:
                new_chunk = chunk
                continue
            if new_chunk.duration_seconds + chunk.duration_seconds > max_duration:
                audio_data_id = str(uuid.uuid4())
                split_audio_file_path = os.path.join(
                    split_audio_dir, f"{audio_data_id}.{format}"
                )
                new_chunk.export(split_audio_file_path, format=format)
                audio_data_list += [
                    AudioData(
                        file_path=split_audio_file_path,
                        start_time=start_time,
                        duration=new_chunk.duration_seconds,
                    )
                ]
                start_time += new_chunk.duration_seconds
                new_chunk = chunk
            else:
                new_chunk += chunk
        if new_chunk is not None:
            audio_data_id = str(uuid.uuid4())
            split_audio_file_path = os.path.join(
                split_audio_dir, f"{audio_data_id}.{format}"
            )
            new_chunk.export(split_audio_file_path, format=format)
            audio_data_list += [
                AudioData(
                    file_path=split_audio_file_path,
                    start_time=start_time,
                    duration=new_chunk.duration_seconds,
                )
            ]
        return audio_data_list
