import os

import ffmpeg  # type: ignore
from src.functions.utils import set_path_for_ffmpeg_bin


class MediaToAudioConverter:
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
        ext = audio_file_path.split(".")[-1]
        stream = ffmpeg.output(stream, audio_file_path, format=ext)
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
