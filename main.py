import argparse
import multiprocessing
import os
import time
from typing import Callable

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from src import (
    clean_up,
    find_resnponse_file_path,
    read_response_file,
    save_result,
    split_audio_task,
    summarization_task,
    transcription_task,
    video_to_audio_task,
)
from src.log.my_logger import MyLogger
from src.model import Task

my_logger = MyLogger(__name__)
logger = my_logger.logger


def worker(
    func: Callable,
    task_queue: multiprocessing.Queue,
    result_queue: multiprocessing.Queue,
    final_result_queue: multiprocessing.Queue,
):
    for task in iter(task_queue.get, "STOP"):
        logger.info(
            f"""
            start working!!
            pid: {os.getpid()}
            function: {func.__name__}
            task: {task}
            """
        )
        result: Task = func(task)
        if result.status == "success":
            logger.info(
                f"""
                        working is completed successfully!!
                        pid: {os.getpid()}
                        function: {func.__name__}
                        result: {result}
                        """
            )
            result_queue.put(result)
        else:
            logger.error(
                f"""
                        working is completed with error.
                        pid: {os.getpid()}
                        function: {func.__name__}
                        result: {result}
                        """
            )
            final_result_queue.put(result)


class Watcher:
    def __init__(
        self,
        root_dir: str,
        task_queue: multiprocessing.Queue,
        result_queue: multiprocessing.Queue,
    ):
        self._video_observer = Observer()
        self._root_dir = root_dir
        self._task_queue = task_queue
        self._result_queue = result_queue

    def run(self):
        video_event_handler = Handler(self._task_queue)
        video_dir = os.path.join(self._root_dir, "video")
        self._video_observer.schedule(
            video_event_handler,
            video_dir,
            recursive=True,
        )
        self._video_observer.start()
        logger.info(f"Observer started at {video_dir}")
        try:
            while True:
                time.sleep(5)
                # 結果の収集などの追加のロジックは必要に応じてここに記述
                # 今回は結果を表示するだけ
                if not self._result_queue.empty():
                    logger.info("result_queue created")
                    result = self._result_queue.get()
                    # 結果の保存
                    save_result(result)
                    # 清掃処理
                    clean_up(result)
        except KeyboardInterrupt:
            logger.warning("keyboard interrupt detected")
            logger.warning("Observer Stopped")
            self._video_observer.stop()
            # すべてのプロセスを停止
            for _ in range(args.num_workers):
                self._task_queue.put("STOP")
                self._result_queue.put("STOP")
            self._task_queue.close()
            self._result_queue.close()
        except Exception as e:
            logger.warning("unexpected error detected")
            logger.warning(e)
            logger.warning("Observer Stopped")
            self._video_observer.stop()
            # すべてのプロセスを停止
            for _ in range(args.num_workers):
                self._task_queue.put("STOP")
                self._result_queue.put("STOP")
            self._task_queue.close()
            self._result_queue.close()


class Handler(FileSystemEventHandler):
    def __init__(self, task_queue):
        self.task_queue = task_queue

    def on_created(self, event):
        # 動画ファイルが作成されたら，動画ファイルのパスをキューに追加
        # 正しい動画ファイルが作成されたかどうかは，video_to_audioで判定する
        # なので，ファイルのvalidation等はここでは行わない
        if event.is_directory:
            return

        # 動画ファイルに対応するレスポンスファイルのパスを取得
        root_dir = os.path.dirname(os.path.dirname(event.src_path))
        video_file_name = os.path.basename(event.src_path)
        response_file_path = find_resnponse_file_path(
            root_dir=root_dir,
            video_file_name=video_file_name,
        )
        response = read_response_file(response_file_path)
        self.task_queue.put(
            Task(
                status="success",
                root_dir=root_dir,
                progress="start video_to_audio",
                response_file_path=response_file_path,
                video_file_path=event.src_path,
                response=response,
            )
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="video_to_mom directory observer")
    parser.add_argument(
        "--root_dir",
        type=str,
        help="root directory",
    )
    parser.add_argument(
        "--num_workers",
        type=int,
        default=3,
        help="num of workers for multiprocessing",
    )
    args = parser.parse_args()
    logger.info(
        f"""
        ================================
        video to summary observer start to run.
        root_dir: {args.root_dir}
        num_workers: {args.num_workers}
        ================================
        """
    )
    video_to_audio_queue: multiprocessing.Queue = multiprocessing.Queue()
    audio_split_queue: multiprocessing.Queue = multiprocessing.Queue()
    transcription_queue: multiprocessing.Queue = multiprocessing.Queue()
    summarization_queue: multiprocessing.Queue = multiprocessing.Queue()
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    # video to audio
    for _ in range(args.num_workers):
        worker_ = multiprocessing.Process(
            target=worker,
            args=(
                video_to_audio_task,
                video_to_audio_queue,
                audio_split_queue,
                result_queue,
            ),
        )
        worker_.start()

    # split_audio
    for _ in range(args.num_workers):
        worker_ = multiprocessing.Process(
            target=worker,
            args=(
                split_audio_task,
                audio_split_queue,
                transcription_queue,
                result_queue,
            ),
        )
        worker_.start()

    # transcription
    for _ in range(args.num_workers):
        worker_ = multiprocessing.Process(
            target=worker,
            args=(
                transcription_task,
                transcription_queue,
                summarization_queue,
                result_queue,
            ),
        )
        worker_.start()

    # summarization
    for _ in range(args.num_workers):
        worker_ = multiprocessing.Process(
            target=worker,
            args=(
                summarization_task,
                summarization_queue,
                result_queue,
                result_queue,
            ),
        )
        worker_.start()

    logger.info(f"start watching {args.root_dir}")
    watcher = Watcher(args.root_dir, video_to_audio_queue, result_queue)
    watcher.run()

    # 以下のような結果が表示される
    # {
    #     "status": "success",
    #     "progress": "summarization completed",
    #     "video_file_path": "data/video/1.mp4",
    #     "audio_file_path": "data/audio/1.wav",
    #     "audio_file_size": 0,
    #     "transcription_file_path": "data/transcription/1.txt",
    #     "transcription_file_size": 0,
    #     "summarization_file_path": "data/summarization/1.txt",
    #     "summarization_file_size": 0,
    # }
