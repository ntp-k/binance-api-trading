from abc import ABC, abstractmethod

class BaseStrategyEngine(ABC):
    @abstractmethod
    def on_price_update(self, kline):
        pass
