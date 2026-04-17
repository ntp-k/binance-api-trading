from typing import Optional
from abstracts.base_trade_client import BaseTradeClient
from commons.custom_logger import CustomLogger

class BaseLiveTradeClient(BaseTradeClient):
    def __init__(self, logger: Optional[CustomLogger] = None) -> None:
        super().__init__(logger=logger)

# EOF
