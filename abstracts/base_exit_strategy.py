from abc import ABC, abstractmethod

from commons.custom_logger import CustomLogger
from models.position_signal import PositionSignal

class BaseExitStrategy(ABC):
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
    def should_close(self, klines_df, position) -> PositionSignal:
        """
        Subclass must implement.
        """
        pass

# EOF

