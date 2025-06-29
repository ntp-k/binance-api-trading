from abc import ABC, abstractmethod
from time import sleep
import pandas as pd

from commons.custom_logger import CustomLogger

class BaseTradeClient(ABC):
    wait_time: int = 0
    running: bool = False

    def __init__(self) -> None:
        self.logger = CustomLogger(name=self.__class__.__name__)
        self.logger.debug(message=f'Initializing {self.__class__.__name__}')

    @abstractmethod
    def fetch_klines(self, symbol, timeframe, timeframe_limit=100) -> pd.DataFrame:
        """
        Subclass must implement.
        """
        pass

    def set_wait_time(self, wait_time_sec: int):
        self.wait_time = wait_time_sec

    def set_running(self, running: bool = False):
        self.running = running

    def wait(self):
        sleep(self.wait_time)
    
# EOF
