from dotenv import load_dotenv
import logging
import os
from pythonjsonlogger import jsonlogger

import commons.common as common

load_dotenv()

class JsonCustomFormatter(jsonlogger.JsonFormatter): # type: ignore
    def __init__(self):
        super().__init__(
            '%(asctime)s %(levelname)s %(name)s %(message)s',
            json_ensure_ascii=False
        )

class ConsoleCustomFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\x1b[35m",          # Purple
        logging.INFO: "\033[96m",           # Bright Cyan
        logging.WARNING: "\x1b[33;20m",     # Yellow
        logging.ERROR: "\x1b[31;20m",       # Red
        logging.CRITICAL: "\x1b[31;1m",     # Bold Red
    }
    RESET = "\x1b[0m"
    FORMAT_STRING = "%(asctime)s   %(levelname)s  \t[%(name)s]   %(message)s"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        formatter = logging.Formatter(f"{color}{self.FORMAT_STRING}{self.RESET}")
        return formatter.format(record)

# class FileCustomFormatter(logging.Formatter):
#     FORMAT_STRING = "%(asctime)s   %(levelname)s  \t[%(name)s:%(lineno)d]   %(message)s"

#     def __init__(self):
#         super().__init__(self.FORMAT_STRING)

#     def format(self, record):
#         return super().format(record)

class CustomLogger:
    def __init__(self, name='', level=os.getenv('LOG_LEVELS', 'INFO'), log_filename: str = '') -> None:
        self.logger_name = name if name != '' else 'default'
        self.level = level.upper()

        log_dir = os.path.join(os.getcwd(), 'logs')
        if not os.path.exists(log_dir):
            os.mkdir(log_dir)
        
        if log_filename == '':
            _d = common.get_datetime_now_string_gmt_plus_7(format='%Y%m%d_%H%M%S')
            self.log_filename = os.path.join(log_dir, f'{_d}.log')
        else:
            self.log_filename = os.path.join(log_dir, log_filename)

        # print(f'{_d}\t  INFO\t\t[{os.path.basename(__file__)[:-3]}]   Initializing logger for {name} : level={self.level}')
        self.logger = logging.getLogger(self.logger_name)
        self.logger.setLevel(self.level)

        json_handler = logging.FileHandler( self.log_filename)
        json_handler.setFormatter(JsonCustomFormatter())
        self.logger.addHandler(json_handler)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.level)
        console_handler.setFormatter(ConsoleCustomFormatter())
        self.logger.addHandler(console_handler)

        # file_handler = logging.FileHandler(self.log_filepath)
        # file_handler.setLevel(self.level)
        # file_handler.setFormatter(FileCustomFormatter())
        # self.logger.addHandler(file_handler)

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
    logger = CustomLogger(__name__, 'DEBUG')
    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")
    logger.critical("critical message")

# EOF
