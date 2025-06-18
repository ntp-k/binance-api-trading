from enum import Enum
from strategies.base_strategy import BaseStrategy
from commons.custom_logger import CustomLogger
from models.trading_enums import TradeSignal
from core.bot_runner import BotRunner
import pandas as pd

DECIMAL = 4

class MACDStage(Enum):
    NEGATIVE = 'negative'
    POSITIVE = 'positive'
    ZERO = 'zero'

class MACD_MACDHIST_EMA200_Strategy(BaseStrategy):
    def __init__(self, bot_runner: BotRunner):
        self.bot_runner = bot_runner
        self.logger = CustomLogger(name=self.__class__.__name__)
        self.current_position = None  # can be "LONG", "SHORT", or None
        self.histogram_history = []
        self.ema_period = 200
        self.entry_confirm_bars = 2
        self.exit_confirm_bars = 5
        self.last_histogram_state = MACDStage.ZERO

    def calculate_indicators(self, df):
        df['ema_200'] = df['close'].ewm(span=self.ema_period, adjust=False).mean()
        df['ema_fast'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_fast'] - df['ema_slow']
        df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['histogram'] = (df['macd'] - df['signal']).round(DECIMAL)
        return df

    def init(self, klines: pd.DataFrame):
        self.df = self.calculate_indicators(klines)
        return self.df

    def detect_histogram_state(self, hist_value):
        if hist_value > 0:
            return MACDStage.POSITIVE
        elif hist_value < 0:
            return MACDStage.NEGATIVE
        return MACDStage.ZERO

    def on_update(self, row):
        try:
            current_hist = row['histogram']
            current_macd = row['macd']
            current_price = row['close']
            current_ema200 = row['ema_200']

            self.histogram_history.append(current_hist)

            # Maintain histogram history length
            max_bars = max(self.entry_confirm_bars, self.exit_confirm_bars) + 1
            if len(self.histogram_history) > max_bars:
                self.histogram_history.pop(0)

            # Check if we currently have an open position
            if self.current_position is None:
                # Check LONG entry conditions
                if (current_hist < 0 and current_macd > 0 and current_price > current_ema200 and
                    self.check_consecutive_increase(self.entry_confirm_bars)):
                    self.current_position = "LONG"
                    self.last_histogram_state = MACDStage.NEGATIVE
                    self.logger.info("Opening LONG position")
                    return TradeSignal.BUY

                # Check SHORT entry conditions
                if (current_hist > 0 and current_macd < 0 and current_price < current_ema200 and
                    self.check_consecutive_decrease(self.entry_confirm_bars)):
                    self.current_position = "SHORT"
                    self.last_histogram_state = MACDStage.POSITIVE
                    self.logger.info("Opening SHORT position")
                    return TradeSignal.SELL

            else:
                # Check exit conditions
                if (self.detect_histogram_state(current_hist) != self.last_histogram_state or
                    self.check_opposite_histogram(self.exit_confirm_bars)):
                    self.logger.info(f"Closing {self.current_position} position")
                    self.current_position = None
                    return TradeSignal.CLOSE

            return TradeSignal.HOLD

        except Exception as e:
            self.logger.error_e('Error during on_update:', e)
            raise e

    def check_consecutive_increase(self, bars):
        if len(self.histogram_history) < bars + 1:
            return False
        return all(self.histogram_history[i] > self.histogram_history[i - 1]
                   for i in range(-bars, 0))

    def check_consecutive_decrease(self, bars):
        if len(self.histogram_history) < bars + 1:
            return False
        return all(self.histogram_history[i] < self.histogram_history[i - 1]
                   for i in range(-bars, 0))

    def check_opposite_histogram(self, bars):
        if len(self.histogram_history) < bars:
            return False

        if self.current_position == 'LONG':
            return all(h <= 0 for h in self.histogram_history[-bars:])
        if self.current_position == 'SHORT':
            return all(h >= 0 for h in self.histogram_history[-bars:])

        return False

# EOF
