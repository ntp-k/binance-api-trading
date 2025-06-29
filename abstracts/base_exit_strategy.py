from abc import ABC, abstractmethod

from commons.custom_logger import CustomLogger

class BaseExitStrategy(ABC):
    def __init__(self) -> None:
        self.logger = CustomLogger(name=self.__class__.__name__)
    
    @abstractmethod
    def process_data(self, klines_df) :
        pass

    @abstractmethod
    def should_close(klines_df) -> bool:
        pass

# EOF

