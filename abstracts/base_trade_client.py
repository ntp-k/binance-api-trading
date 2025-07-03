from abc import ABC, abstractmethod
from time import sleep
import pandas as pd
import random

from commons.custom_logger import CustomLogger


class BaseTradeClient(ABC):
    wait_time: int = 0
    running: bool = False

    def __init__(self) -> None:
        self.logger = CustomLogger(name=self.__class__.__name__)
        self.logger.debug(message=f'Initializing {self.__class__.__name__}')

    @abstractmethod
    def set_leverage(self, symbol: str, leverage: int) -> dict:
        """
        Subclass must implement.
        """
        pass
       
    @abstractmethod
    def fetch_position(self, symbol) -> dict:
        """
        Subclass must implement.
        """
        pass

    @abstractmethod
    def fetch_klines(self, symbol, timeframe, timeframe_limit=100) -> pd.DataFrame:
        """
        Subclass must implement.
        """
        pass

    @abstractmethod
    def place_order(self, symbol: str, order_side: str, order_type: str, quantity: float, price: float = 0, reduce_only: bool = False, time_in_force: str = "GTC") -> dict:
        """
        Subclass must implement.
        """
        pass

    def set_wait_time(self, wait_time_sec: int):
        self.wait_time = wait_time_sec

    def set_running(self, running: bool = False):
        self.running = running

    def wait(self):
        _min_wait_time = max(0, self.wait_time - 5)
        _wait_time = random.randint(a=_min_wait_time, b=self.wait_time)
        sleep(_wait_time)

# EOF
