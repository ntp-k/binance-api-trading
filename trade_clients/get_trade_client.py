from models.enum.run_mode import RunMode

def get_trade_client(run_mode, offline=False):
    if offline:
        if run_mode == RunMode.LIVE:
            from trade_clients.offline.offline_live_client import OfflineLiveTradeClient
            return OfflineLiveTradeClient()
    else:
        if run_mode == RunMode.LIVE:
            from trade_clients.binance.binance_live_trade_client import BinanceLiveTradeClient
            _b = BinanceLiveTradeClient()
            _b.init()
            return _b

# EOF
