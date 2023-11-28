import logging
import logging.handlers
import os

# class DebugFilter(logging.Filter):
#     def filter(self, record):
#         return record.levelno == logging.DEBUG


# class MainFilter(logging.Filter):
#     def filter(self, record):
#         return record.levelno != logging.DEBUG


class MyLogger:
    def __init__(self, name):
        log_dir = self._make_log_dir()
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s : %(levelname)s : %(name)s : %(funcName)s  - line:%(lineno)d - %(message)s"
        )
        main_file_path = os.path.join(log_dir, "main.log")
        main_handler = logging.handlers.RotatingFileHandler(
            filename=main_file_path,
            encoding="utf-8",
            maxBytes=10**7,
            backupCount=3,
        )
        main_handler.setLevel(logging.INFO)
        main_handler.setFormatter(formatter)
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
        while os.path.basename(current_dir) != "src":
            current_dir = os.path.dirname(current_dir)
        log_dir = os.path.join(os.path.dirname(current_dir), "log")
        os.makedirs(log_dir, exist_ok=True)
        return log_dir
