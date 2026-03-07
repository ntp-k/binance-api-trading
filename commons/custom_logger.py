from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import logging
import os
from pythonjsonlogger import jsonlogger

from commons.constants import LOGS_DIR, DEFAULT_LOG_LEVEL, DATETIME_FORMAT_FILE

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

class FileCustomFormatter(logging.Formatter):
    FORMAT_STRING = "%(asctime)s   %(levelname)s  \t[%(name)s]   %(message)s"

    def __init__(self):
        super().__init__(self.FORMAT_STRING)

    def format(self, record):
        return super().format(record)

class CustomLogger:
    """
    Custom logger with file and console output.
    
    Features:
    - Colored console output
    - File logging with rotation support
    - Singleton pattern for shared log file
    - Automatic log directory creation
    """
    
    _log_file_cache = {}  # Cache log filenames by date
    _handlers_cache = {}  # Cache handlers to prevent duplicates
    
    def __init__(
        self,
        name: str = '',
        level: str = os.getenv(key='LOG_LEVELS', default=DEFAULT_LOG_LEVEL),
        log_filename: str = ''
    ) -> None:
        """
        Initialize custom logger.
        
        Args:
            name: Logger name (defaults to 'default')
            level: Log level from environment or default
            log_filename: Optional custom log filename
        """
        self.logger_name = name if name else 'default'
        self.level = level.upper()

        # Ensure log directory exists
        log_dir = os.path.join(os.getcwd(), LOGS_DIR)
        os.makedirs(log_dir, exist_ok=True)
        
        # Determine log filename (shared across loggers for same day)
        if log_filename:
            self.log_filename = os.path.join(log_dir, log_filename)
        else:
            self.log_filename = self._get_daily_log_filename(log_dir)

        # Get or create logger
        self.logger = logging.getLogger(name=self.logger_name)
        self.logger.setLevel(level=logging.DEBUG)

        # Add handlers only if not already present
        if not self.logger.handlers:
            self._setup_handlers()
    
    @classmethod
    def _get_daily_log_filename(cls, log_dir: str) -> str:
        """
        Get log filename for current day (cached).
        
        Args:
            log_dir: Directory for log files
            
        Returns:
            Full path to log file
        """
        today = datetime.now(timezone.utc) + timedelta(hours=7)
        date_key = today.strftime('%Y%m%d')
        
        if date_key not in cls._log_file_cache:
            dt_str = today.strftime(format=DATETIME_FORMAT_FILE)
            cls._log_file_cache[date_key] = os.path.join(log_dir, f'{dt_str}.log')
        
        return cls._log_file_cache[date_key]
    
    def _setup_handlers(self) -> None:
        """Setup file and console handlers for logger."""
        # File handler - always DEBUG level
        file_handler = logging.FileHandler(
            filename=self.log_filename,
            encoding='utf-8'
        )
        file_handler.setLevel(level=logging.DEBUG)
        file_handler.setFormatter(fmt=FileCustomFormatter())
        self.logger.addHandler(hdlr=file_handler)

        # Console handler - uses configured level
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level=self.level)
        console_handler.setFormatter(fmt=ConsoleCustomFormatter())
        self.logger.addHandler(hdlr=console_handler)

    def debug(self, message: str) -> str:
        """Log debug message."""
        self.logger.debug(msg=message)
        return message

    def info(self, message: str) -> str:
        """Log info message."""
        self.logger.info(msg=message)
        return message

    def warning(self, message: str) -> str:
        """Log warning message."""
        self.logger.warning(msg=message)
        return message

    def warning_e(self, message: str, e: Exception) -> str:
        """Log warning with exception details."""
        self.logger.warning(msg=message)
        self.logger.warning(msg=f'{type(e).__name__}: {e}')
        return message

    def error(self, message: str) -> str:
        """Log error message."""
        self.logger.error(msg=message)
        return message

    def error_e(self, message: str, e: Exception) -> str:
        """Log error with exception details."""
        self.logger.error(msg=message)
        self.logger.error(msg=f'{type(e).__name__}: {e}')
        return message

    def critical(self, message: str) -> str:
        """Log critical message."""
        self.logger.critical(msg=message)
        return message

    def critical_e(self, message: str, e: Exception) -> str:
        """Log critical with exception details."""
        self.logger.critical(msg=message)
        self.logger.critical(msg=f'{type(e).__name__}: {e}')
        return message
    
    def close(self) -> None:
        """Close all handlers and cleanup resources."""
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)


if __name__ == '__main__':
    logger = CustomLogger(name=__name__, level='DEBUG')
    logger.debug(message="debug message")
    logger.info(message="info message")
    logger.warning(message="warning message")
    logger.error(message="error message")
    logger.critical(message="critical message")

# EOF
