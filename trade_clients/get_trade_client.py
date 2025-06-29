from models.enum.run_mode import RunMode
from models.enum.trade_client import TradeClient

def get_trade_client(run_mode: RunMode, trade_client: TradeClient):
    if trade_client == TradeClient.OFFLINE:
        if run_mode == RunMode.LIVE:
            from trade_clients.offline.offline_live_client import OfflineLiveTradeClient
            return OfflineLiveTradeClient()
    else: # trade_client == TradeClient.BINANCE
        if run_mode == RunMode.LIVE:
            from trade_clients.binance.binance_live_trade_client import BinanceLiveTradeClient
            _b = BinanceLiveTradeClient()
            _b.init()
            return _b

# EOF
