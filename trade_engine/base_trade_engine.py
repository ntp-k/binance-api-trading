from abc import ABC, abstractmethod

class BaseTradeEngine(ABC):
    @abstractmethod
    def place_order(self) -> list:
        pass

# EOF
