import pandas as pd

from trade_clients.base_live_trade_client import BaseLiveTradeClient

MOCK_KLINES_PATH = 'resources/mock_klines.json'

class OfflineLiveTradeClient(BaseLiveTradeClient):
    def __init__(self):
        super().__init__()
    
    def fetch_klines(self, symbol, timeframe, timeframe_limit=100):
        return pd.read_json(MOCK_KLINES_PATH, orient='records', lines=True)
        
