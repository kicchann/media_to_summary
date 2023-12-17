import argparse
import multiprocessing
import os
import time
from typing import Callable

from src import (
    clean_up,
    find_resnponse_file_path,
    media_to_audio_task,
    read_response_file,
    save_result,
    split_audio_task,
    summarization_task,
    transcription_task,
)
from src.log.my_logger import MyLogger
from src.model import Task
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

my_logger = MyLogger(__name__)
logger = my_logger.logger


def worker(
    func: Callable,
    task_queue: multiprocessing.Queue,
    result_queue: multiprocessing.Queue,
    final_result_queue: multiprocessing.Queue,
):
    for task in iter(task_queue.get, "STOP"):
        if task.status == "error":
            logger.info(
                f"""
                received error task.
                pid: {os.getpid()}
                function: {func.__name__}
                task: {task}
                """
            )
            final_result_queue.put(task)
            continue
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
        self._media_observer = Observer()
        self._root_dir = root_dir
        self._task_queue = task_queue
        self._result_queue = result_queue

    def run(self):
        media_event_handler = Handler(self._task_queue)
        media_dir = os.path.join(self._root_dir, "media")
        self._media_observer.schedule(
            media_event_handler,
            media_dir,
            recursive=True,
        )
        self._media_observer.start()
        logger.info(f"Observer started at {media_dir}")
        try:
            while True:
                time.sleep(5)
                # 結果の収集などの追加のロジックは必要に応じてここに記述
                # 今回は結果を表示するだけ
                if self._result_queue.qsize() != 0:
                    logger.info("result_queue created")
                    result = self._result_queue.get()
                    # 結果の保存
                    save_result(result)
                    # 清掃処理
                    clean_up(result)
        except KeyboardInterrupt:
            logger.warning("keyboard interrupt detected")
            logger.warning("Observer Stopped")
            self._media_observer.stop()
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
            self._media_observer.stop()
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
        # 正しい動画ファイルが作成されたかどうかは，media_to_audioで判定する
        # なので，ファイルのvalidation等はここでは行わない
        if event.is_directory:
            return

        # 動画ファイルに対応するレスポンスファイルのパスを取得
        root_dir = os.path.dirname(os.path.dirname(event.src_path))
        media_file_name = os.path.basename(event.src_path)

        # 動画ファイルとresponseファイルにアクセスができるようになるまで待機
        # 15分経ってもアクセスできない場合は，エラーとして処理を中断
        current_time = time.time()
        while True:
            try:
                response_file_path = find_resnponse_file_path(
                    root_dir=root_dir,
                    media_file_name=media_file_name,
                )
                if not response_file_path:
                    raise Exception()
                response = read_response_file(response_file_path)
                with open(event.src_path, "rb"):
                    break
            except Exception as e:
                if time.time() - current_time <= 15 * 60:
                    time.sleep(60)
                    continue
                logger.error(
                    f"""
                    cannot access to {event.src_path} for 15 minutes.
                    please check the file.
                    """
                )
                self.task_queue.put(
                    Task(
                        status="error",
                        progress="cannot access to response file or media file",
                        response_file_path=response_file_path,
                        media_file_path=event.src_path,
                        media_file_name=os.path.basename(event.src_path),
                        response=None,
                        message="回答ファイルまたは動画ファイルへのアクセスに失敗しました",
                    )
                )
                return

        self.task_queue.put(
            Task(
                status="success",
                progress="start media_to_audio",
                response_file_path=response_file_path,
                media_file_path=event.src_path,
                media_file_name=os.path.basename(event.src_path),
                response=response,
            )
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="media_to_mom directory observer")
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
        media to summary observer start to run.
        root_dir: {args.root_dir}
        num_workers: {args.num_workers}
        ================================
        """
    )
    media_to_audio_queue: multiprocessing.Queue = multiprocessing.Queue()
    audio_split_queue: multiprocessing.Queue = multiprocessing.Queue()
    transcription_queue: multiprocessing.Queue = multiprocessing.Queue()
    summarization_queue: multiprocessing.Queue = multiprocessing.Queue()
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    # media to audio
    for _ in range(args.num_workers):
        worker_ = multiprocessing.Process(
            target=worker,
            args=(
                media_to_audio_task,
                media_to_audio_queue,
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
    # whisperの制限により，同時に3つまでしか処理できない
    for _ in range(3):  # args.num_workers
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
    watcher = Watcher(args.root_dir, media_to_audio_queue, result_queue)
    watcher.run()

    # 以下のような結果が表示される
    # {
    #     "status": "success",
    #     "progress": "summarization completed",
    #     "media_file_path": "data/media/1.mp4",
    #     "audio_file_path": "data/audio/1.wav",
    #     "audio_file_size": 0,
    #     "transcription_file_path": "data/transcription/1.txt",
    #     "transcription_file_size": 0,
    #     "summarization_file_path": "data/summarization/1.txt",
    #     "summarization_file_size": 0,
    # }
