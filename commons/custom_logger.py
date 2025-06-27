from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import logging
import os
from pythonjsonlogger import jsonlogger

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

class CustomLogger:
    def __init__(self, name='', level=os.getenv(key='LOG_LEVELS', default='INFO'), log_filename: str = '') -> None:
        self.logger_name = name if name != '' else 'default'
        self.level = level.upper()

        log_dir = os.path.join(os.getcwd(), 'logs')
        if not os.path.exists(path=log_dir):
            os.mkdir(path=log_dir)
        
        if log_filename == '':
            _dt = datetime.now(timezone.utc) + timedelta(hours=7)
            _dt_str = _dt.strftime(format='%Y%m%d_%H%M%S')
            self.log_filename = os.path.join(log_dir, f'{_dt_str}.log')
        else:
            self.log_filename = os.path.join(log_dir, log_filename)

        self.logger = logging.getLogger(name=self.logger_name)
        self.logger.setLevel(level=self.level)

        json_handler = logging.FileHandler(filename=self.log_filename)
        json_handler.setFormatter(fmt=JsonCustomFormatter())
        self.logger.addHandler(hdlr=json_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(fmt=ConsoleCustomFormatter())
        self.logger.addHandler(hdlr=console_handler)

    def debug(self, message):
        self.logger.debug(msg=message)
        return message

    def info(self, message):
        self.logger.info(msg=message)
        return message

    def warning(self, message):
        self.logger.warning(msg=message)
        return message

    def warning_e(self, message, e):
        self.logger.warning(msg=message)
        self.logger.warning(msg=f'{type(e)}: {e}')
        return message

    def error(self, message):
        self.logger.error(msg=message)
        return message

    def error_e(self, message, e):
        self.logger.error(msg=message)
        self.logger.error(msg=f'{type(e)}: {e}')
        return message

    def critical(self, message):
        self.logger.critical(msg=message)
        return message

    def critical_e(self, message, e):
        self.logger.critical(msg=message)
        self.logger.critical(msg=f'{type(e)}: {e}')
        return message


if __name__ == '__main__':
    logger = CustomLogger(name=__name__, level='DEBUG')
    logger.debug(message="debug message")
    logger.info(message="info message")
    logger.warning(message="warning message")
    logger.error(message="error message")
    logger.critical(message="critical message")

# EOF
