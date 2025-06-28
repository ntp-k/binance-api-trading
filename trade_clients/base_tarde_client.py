from abc import ABC
from commons.custom_logger import CustomLogger

class BaseTradeClient(ABC):
    def __init__(self) -> None:
        self.logger = CustomLogger(name=self.__class__.__name__)
        self.logger.debug(message=f'Initializing {self.__class__.__name__}')

# EOF
