
def get_trade_engine(is_offline):
    if is_offline:
        from trade_engine.offline_trade_engine import OfflineTradeEngine
        return OfflineTradeEngine()
    else:
        from trade_engine.binance.binance_client import BinanceClient
        return BinanceClient()

# EOF
