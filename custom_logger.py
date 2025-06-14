from dotenv import load_dotenv
import logging
import os
from datetime import datetime

import common.common as common

load_dotenv()

class ConsoleCustomFormatter(logging.Formatter):
    purpul = "\x1b[35m"
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s   %(levelname)s  \t[%(name)s:%(lineno)d]   %(message)s"

    FORMATS = {
        logging.DEBUG: purpul + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class FileCustomFormatter(logging.Formatter):
    format = "%(asctime)s   %(levelname)s  \t[%(name)s:%(lineno)d]   %(message)s"
    FORMATS = {
        logging.DEBUG: format,
        logging.INFO: format,
        logging.WARNING: format,
        logging.ERROR: format,
        logging.CRITICAL: format
    }
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

class CustomLogger:
    def __init__(self, name='', log_dir='', level='INFO') -> None:
        self.logger_name = name if name == '' else 'default'
        self.log_dir = log_dir
        _d = common.get_datetime_now_string_gmt_plus_7()[:-9]
        self.log_filepath = os.path.join(self.log_dir, f'{_d}.log')

        print(
            f'[INFO] [{os.path.basename(__file__)}] Innitializing logger for {name} : level={level}')
        self.logger = logging.getLogger(self.logger_name)
        self.logger.setLevel(level)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(ConsoleCustomFormatter())
        self.logger.addHandler(console_handler)

        file_handler = logging.FileHandler(self.log_filepath)
        file_handler.setLevel(level)
        file_handler.setFormatter(FileCustomFormatter())
        self.logger.addHandler(file_handler)

    def debug(self, message):
        self.logger.debug(message)
        return message

    def info(self, message):
        self.logger.info(message)
        return message

    def warning(self, message):
        self.logger.warning(message)
        return message

    def warning_e(self, message, e):
        self.logger.warning(message)
        self.logger.warning(f'{type(e)}: {e}')
        return message

    def error(self, message):
        self.logger.error(message)
        return message

    def error_e(self, message, e):
        self.logger.error(message)
        self.logger.error(f'{type(e)}: {e}')
        return message

    def critical(self, message):
        self.logger.critical(message)
        return message

    def critical_e(self, message, e):
        self.logger.critical(message)
        self.logger.critical(f'{type(e)}: {e}')
        return message


if __name__ == '__main__':
    logger = CustomLogger(__name__)
    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")
    logger.critical("critical message")

# EOF
