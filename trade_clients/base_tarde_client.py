from abc import ABC, abstractmethod 
from commons.custom_logger import CustomLogger

class BaseTradeClient(ABC):
    def __init__(self) -> None:
        self.logger = CustomLogger(name=self.__class__.__name__)
        self.logger.debug(message=f'Initializing {self.__class__.__name__}')

    @abstractmethod
    def fetch_klines(self, symbol, timeframe, timeframe_limit=100):
        pass
    
# EOF
