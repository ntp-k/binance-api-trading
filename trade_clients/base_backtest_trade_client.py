from trade_clients.base_tarde_client import BaseTradeClient

class BaseBacktestTradeClient(BaseTradeClient):
    def __init__(self) -> None:
        super().__init__()


# EOF
