from models.enum.run_mode import RunMode

def get_trade_client(run_mode):
    if run_mode == RunMode.LIVE:
        from trade_clients.binance_live_trade_client import BinanceLiveTradeClient
        _b = BinanceLiveTradeClient()
        _b.init()
        return _b

# EOF
