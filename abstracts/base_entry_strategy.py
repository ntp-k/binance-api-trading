from abc import ABC, abstractmethod

from commons.custom_logger import CustomLogger
from models.position_signal import PositionSignal
from core.position_handler import PositionHandler

class BaseEntryStrategy(ABC):
    def __init__(self) -> None:
        self.logger = CustomLogger(name=self.__class__.__name__)
        self.logger.debug(f'Initializing {self.__class__.__name__}')
    
    @abstractmethod
    def _process_data(self, klines_df) :
        """
        Subclass must implement.
        """
        pass

    @abstractmethod
    def should_open(self, klines_df, position_handler: PositionHandler) -> PositionSignal:
        """
        Subclass must implement.
        """
        pass

    @abstractmethod
    def calculate_tp_sl(self, klines_df, position_side, entry_price):
        """
        Subclass must implement.
        """
        pass


# EOF

