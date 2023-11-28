import logging
import logging.handlers
import os


class DebugFilter(logging.Filter):
    def filter(self, record):
        return record.levelno == logging.DEBUG


class MainFilter(logging.Filter):
    def filter(self, record):
        return record.levelno != logging.DEBUG


class MyLogger:
    def __init__(self, name):
        log_dir = self._make_log_dir()
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s : %(levelname)s : %(name)s : %(funcName)s  - line:%(lineno)d - %(message)s"
        )

        debug_file_path = os.path.join(log_dir, "debug.log")
        debug_handler = logging.handlers.RotatingFileHandler(
            filename=debug_file_path, encoding="utf-8", maxBytes=10**7, backupCount=3
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(formatter)
        debug_filter = DebugFilter()
        debug_handler.addFilter(debug_filter)
        self.logger.addHandler(debug_handler)

        main_file_path = os.path.join(log_dir, "main.log")
        main_handler = logging.handlers.RotatingFileHandler(
            filename=main_file_path, encoding="utf-8", maxBytes=100, backupCount=5
        )
        main_handler.setLevel(logging.INFO)
        main_handler.setFormatter(formatter)
        main_filter = MainFilter()
        main_handler.addFilter(main_filter)
        self.logger.addHandler(main_handler)

        # /**コンソール出力設定例
        # import sys
        # console_handler = logging.StreamHandler(sys.stdout)
        # console_handler.setLevel(logging.INFO)
        # console_handler.setFormatter(formatter)
        # info_filter = InfoFilter()
        # console_handler.addFilter(info_filter)
        # self.logger.addHandler(console_handler)

        # error_handler = logging.StreamHandler(sys.stderr)
        # error_handler.setLevel(logging.WARNING)
        # error_handler.setFormatter(formatter)
        # self.logger.addHandler(error_handler)
        # **/

    def _make_log_dir(self) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        for _ in range(2):
            log_dir = os.path.dirname(current_dir)

        if not os.path.exists(log_dir):
            # ディレクトリが存在しない場合、ディレクトリを作成する
            os.makedirs(log_dir)
        return log_dir
