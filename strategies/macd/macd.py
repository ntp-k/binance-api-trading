from strategies.base_strategy import BaseStrategy
from commons.custom_logger import CustomLogger
from services.binance.binance_client import BinanceClient

DECIMAL = 4

class MACDStrategy(BaseStrategy):
    def __init__(self):
        self.logger = CustomLogger(name=MACDStrategy.__name__)
    


    def calculate_macd(self, df, fast=12, slow=26, signal=9):
        df['ema_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=slow, adjust=False).mean()
        df['macd'] = df['ema_fast'] - df['ema_slow']
        df['signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
        df['histogram'] = df['macd'] - df['signal']
        df['histogram'] = df['histogram'].round(DECIMAL)
        return df

    def run_backtest(self):
        pass


    def on_price_update(self, kline):
        return super().on_price_update(kline)
    

    