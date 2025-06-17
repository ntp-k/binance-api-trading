from enum import Enum

from strategies.base_strategy import BaseStrategy
from commons.custom_logger import CustomLogger
from models.trading_enums import TradeSignal
from core.bot_runner import BotRunner

class MACDStage(Enum):
    NEGATIVE = 'negative'
    POSITIVE = 'positive'
    ZERO = 'zero'

DECIMAL = 4

class MACDHistStrategy(BaseStrategy):
    def __init__(self, but_runner):
        self.bot_runner: BotRunner = but_runner
        self.name = f'{MACDHistStrategy.__name__}_{self.bot_runner.bot_fullname}'
        self.logger = CustomLogger(name=self.name)
        self.last_state = MACDStage.ZERO

    def calculate_macd(self, df, fast=12, slow=26, signal=9):
        df['ema_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=slow, adjust=False).mean()
        df['macd'] = df['ema_fast'] - df['ema_slow']
        df['signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
        df['histogram'] = df['macd'] - df['signal']
        df['histogram'] = df['histogram'].round(DECIMAL)
        return df

    def init(self, klines):
        self.macd_df = self.calculate_macd(klines)
        return self.macd_df

    def detect_state(self, value):
        if value > 0:
            return MACDStage.POSITIVE
        elif value < 0:
            return MACDStage.NEGATIVE
        return MACDStage.ZERO

    def on_update(self, row):
        try:
            state = self.detect_state(row['histogram'])

            if state == MACDStage.ZERO or state == self.last_state:
                return TradeSignal.HOLD

            # state change detected
            # self.logger.info(f'State change: {self.last_state.value} -> {state.value}')
            self.last_state = state

            if state == MACDStage.POSITIVE:
                return TradeSignal.BUY
            elif state == MACDStage.NEGATIVE:
                return TradeSignal.SELL
            else:
                self.logger.warning(f'Unexpected state: {state}')
                return TradeSignal.HOLD
        except Exception as e:
            self.logger.error_e(f'Error processing row:', e)
            raise e

    def on_price_update(self, kline):
        return super().on_price_update(kline)
