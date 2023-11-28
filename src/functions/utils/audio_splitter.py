import os
import shutil
from typing import Dict, List, Union

from pydub import AudioSegment
from pydub.silence import split_on_silence

from src.functions.config import (
    KEEP_SILENCE,
    MAX_FILE_SIZE_FOR_WHISPER,
    MIN_SILENCE_LEN,
    SILENCE_THRESH,
)
from src.functions.model import AudioData


class AudioSplitter:
    def __init__(
        self,
        max_file_size_for_whisper: Union[float, None] = None,
        min_silence_len: Union[int, None] = None,
        silence_thresh: Union[int, None] = None,
        keep_silence: Union[int, None] = None,
    ):
        self._max_file_size_for_whisper = (
            max_file_size_for_whisper or MAX_FILE_SIZE_FOR_WHISPER
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

        # 25MBを超える場合は分割する
        # 超えない場合はそのままaudiosフォルダに移動
        file_size = os.path.getsize(audio_file_path)
        if file_size <= self._max_file_size_for_whisper:
            audio_data_id = str(1).zfill(3)
            split_audio_file_path = os.path.join(
                split_audio_dir, f"out_{audio_data_id}.{format}"
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

        # ファイルの最大再生時間を計算
        total_length = len(sound)
        max_length = total_length * (self._max_file_size_for_whisper / file_size)

        # 無音部分をカットして分割
        chunks = split_on_silence(
            sound,
            min_silence_len=self._min_silence_len,
            silence_thresh=self._silence_thresh,
            keep_silence=self._keep_silence,
        )

        # chunkがmax_lengthを超えない最大の長さになるように，chunkを結合する
        # 結合したchunkをoutput_mp3に渡して，mp3ファイルを出力する
        new_chunks = []
        for i, chunk in enumerate(chunks):
            if i == 0:
                new_chunks.append(chunk)
                continue
            if len(new_chunks[-1] + chunk) > max_length:
                new_chunks.append(chunk)
            new_chunks[-1] += chunk

        # chunkをmp3ファイルに出力する
        audio_data_list: List[AudioData] = []
        for i, chunk in enumerate(new_chunks):
            start_time = sum([len(c) for c in new_chunks[:i]])
            audio_data_id = str(i + 1).zfill(3)
            split_audio_file_path = os.path.join(
                split_audio_dir, f"out_{audio_data_id}.{format}"
            )
            chunk.export(split_audio_file_path, format=format)
            audio_data_list += [
                AudioData(
                    file_path=split_audio_file_path,
                    start_time=start_time,
                    duration=len(sound),
                )
            ]
        return audio_data_list
