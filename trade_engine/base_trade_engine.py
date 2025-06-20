from commons.custom_logger import CustomLogger
from abc import ABC, abstractmethod

class BaseTradeEngine(ABC):
    def __init__(self):
        self.logger = CustomLogger(name=BaseTradeEngine.__name__)
    
    def init(self):
        pass

    def set_leverage(self, symbol: str, leverage: int) -> dict:
        pass

    def place_order(self, symbol: str, order_side: str, order_type: str, quantity: float,
                    price: float = 0, reduce_only: bool = False, time_in_force: str = "GTC") -> dict:
        pass

    def get_position(self, symbol):
        pass

    def fetch_klines(self, symbol, timeframe, timeframe_limit=100):
        pass

# EOF
