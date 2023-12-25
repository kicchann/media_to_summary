import os
import uuid
from typing import List, Union

from pydub import AudioSegment
from pydub.silence import split_on_silence
from src.functions.config import (
    IGNORE_DURATION_MILISECONDS,
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

    def __get_max_duration(self, audio_file_path: str, total_duration: float) -> float:
        """
        ファイルサイズとdurationから、durationのthreshholdを計算する
        """
        file_size = os.path.getsize(audio_file_path)
        # durationのthreshholdをファイルサイズとdurationから計算する
        max_duration_from_size = total_duration * (
            self._max_file_size_for_whisper / file_size
        )
        return min(max_duration_from_size, self._max_duration_for_whisper)

    def __split_to_chunks(self, sound):
        """
        音声ファイルのchunkを無音部分でカットするとともに、
        0.3s以下のchunkを無音にして、
        指定された長さになるようにchunkを結合する
        """
        # 無音部分をカットして分割
        chunks = split_on_silence(
            sound,
            min_silence_len=self._min_silence_len,
            silence_thresh=self._silence_thresh,
            keep_silence=True,  # self._keep_silence,
        )
        new_chunks = []
        # 会議後の無音部分を無視するため、index_for_trimを記録する
        index_for_trim = None
        for chunk in chunks:
            # 無音部分を無視する
            if chunk.dBFS < self._silence_thresh:
                continue
            new_chunks.append(chunk)
        return new_chunks[:index_for_trim]

    @staticmethod
    def __create_audio_data(
        chunk,
        start: float,
        split_audio_dir: str,
        format: str,
    ) -> AudioData:
        """
        chunkをmp3形式で出力する
        """
        audio_data_id = str(uuid.uuid4())  # str(1).zfill(3)
        split_audio_file_path = os.path.join(
            split_audio_dir, f"{audio_data_id}.{format}"
        )
        chunk.export(split_audio_file_path, format=format)
        return AudioData(
            file_path=split_audio_file_path,
            start=start,
            end=start + chunk.duration_seconds,
        )

    # https://agusblog.net/colab-file-split/?reloadTimes=2
    def split(
        self,
        audio_file_path: str,
        split_audio_dir: str,
        use_last_10_mins_only: Union[bool, None] = None,
    ) -> List[AudioData]:
        use_last_10_mins_only = use_last_10_mins_only or False
        # audio_file_pathから拡張子を取得してformatに指定する
        format = audio_file_path.split(".")[-1]
        sound = AudioSegment.from_file(audio_file_path, format=format)
        total_duration = sound.duration_seconds
        max_duration = self.__get_max_duration(audio_file_path, total_duration)

        # チャンクに分割
        chunks = self.__split_to_chunks(sound)
        tmp_duration = 0.0
        for chunk in chunks:
            tmp_duration += chunk.duration_seconds

        total_duration = sum([chunk.duration_seconds for chunk in chunks])

        # max_durationを超えない場合はそのままaudiosフォルダに移動
        if total_duration <= max_duration:
            audio_data = self.__create_audio_data(
                sum(chunks),
                0.0,
                split_audio_dir,
                format,
            )
            return [audio_data]

        # use_last_10_mins_onlyがTrueの場合は、最後の10分だけを抽出する
        new_chunk = None
        start = 0.0
        duration_seconds = 0.0
        if use_last_10_mins_only:
            start = total_duration
            for chunk in chunks[::-1]:
                if new_chunk is None:
                    new_chunk = chunk
                    duration_seconds += chunk.duration_seconds
                    continue
                if new_chunk.duration_seconds + chunk.duration_seconds <= 600:
                    new_chunk = chunk + new_chunk
                    duration_seconds += chunk.duration_seconds
                else:
                    start -= new_chunk.duration_seconds
                    audio_data = self.__create_audio_data(
                        new_chunk,
                        start,
                        split_audio_dir,
                        format,
                    )
                    return [audio_data]

        # use_last_10_mins_onlyがFalseの場合は、最大の長さになるようにchunkを結合する
        new_chunk = None
        start = 0.0
        duration_seconds = 0.0
        audio_data_list: List[AudioData] = []
        for chunk in chunks:
            if new_chunk is None:
                new_chunk = chunk
                duration_seconds += chunk.duration_seconds
                continue
            if new_chunk.duration_seconds + chunk.duration_seconds <= max_duration:
                new_chunk += chunk
                duration_seconds += chunk.duration_seconds
            else:
                audio_data = self.__create_audio_data(
                    new_chunk,
                    start,
                    split_audio_dir,
                    format,
                )
                audio_data_list += [audio_data]
                start += duration_seconds
                new_chunk = chunk
                duration_seconds = chunk.duration_seconds
        if new_chunk is not None:
            audio_data = self.__create_audio_data(
                new_chunk,
                start,
                split_audio_dir,
                format,
            )
            audio_data_list += [audio_data]
        return audio_data_list
