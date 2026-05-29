"""
Wick Mean Reversion Entry Strategy

Strategy Logic:
- Only trade when previous candle has strong body movement (> min_body_pct threshold)
- If previous candle is RED (bearish) → LONG (expect bounce/mean reversion)
- If previous candle is GREEN (bullish) → SHORT (expect pullback/mean reversion)

This strategy is based on the observation that strong moves tend to reverse in the next candle.
The body filter ensures we only trade after significant moves, improving win rate.

Best performing configurations from backtests:
- Daily (1d) timeframe with body > 0.7%
- 12h timeframe with body > 0.5-0.7%
- Symbols: BTCUSDC, SOLUSDC, BNBUSDC, ETHUSDC
"""

from abstracts.base_entry_strategy import BaseEntryStrategy
from models.enum.position_side import PositionSide
from models.position_signal import PositionSignal
from core.position_handler import PositionHandler
import pandas as pd


class EntryWickMeanReversion(BaseEntryStrategy):
    """Mean reversion entry strategy based on previous candle body strength."""

    def __init__(self, dynamic_config, logger=None):
        super().__init__(logger=logger)
        self.min_body_pct = dynamic_config.get('min_body_pct', 0.005)  # Default 0.5%
        self.decimal = dynamic_config.get('decimal', 2)
        self.training_candles = dynamic_config.get('training_candles', 300)
        self.upper_wick_25th = None
        self.lower_wick_25th = None
        
        self.logger.info(f"Initialized WickMeanReversion: min_body_pct={self.min_body_pct*100:.2f}%, "
                        f"training_candles={self.training_candles}")

    def _process_data(self, klines_df: pd.DataFrame) -> pd.DataFrame:
        """Process klines data and calculate wick metrics."""
        klines_df['is_green'] = klines_df['close'] > klines_df['open']
        klines_df['is_red'] = klines_df['close'] < klines_df['open']
        klines_df['body_change_pct'] = abs((klines_df['close'] - klines_df['open']) / klines_df['open'])
        
        # Calculate wicks from OPEN price
        klines_df['upper_wick'] = klines_df['high'] - klines_df['open']
        klines_df['upper_wick_pct'] = (klines_df['upper_wick'] / klines_df['open']) * 100
        klines_df['lower_wick'] = klines_df['open'] - klines_df['low']
        klines_df['lower_wick_pct'] = (klines_df['lower_wick'] / klines_df['open']) * 100
        
        # Calculate percentiles from training data
        if len(klines_df) >= self.training_candles:
            training_df = klines_df.iloc[-self.training_candles:]
            self.upper_wick_25th = training_df['upper_wick_pct'].quantile(0.25)
            self.lower_wick_25th = training_df['lower_wick_pct'].quantile(0.25)
            self.logger.debug(f"Calculated percentiles: upper_25th={self.upper_wick_25th:.4f}%, "
                            f"lower_25th={self.lower_wick_25th:.4f}%")
        
        return klines_df

    def should_open(self, klines_df, position_handler: PositionHandler) -> PositionSignal:
        """Determine if position should be opened based on mean reversion logic."""
        symbol = position_handler.bot_config.symbol
        new_position_side = PositionSide.ZERO
        checklist_reasons = [f"{symbol} Wick Mean Reversion Entry"]

        # Need at least 2 candles
        if len(klines_df) < 2:
            checklist_reasons.append("Not enough candles: ❌")
            return PositionSignal(position_side=PositionSide.ZERO, reason=" | ".join(checklist_reasons))

        klines_df = self._process_data(klines_df)

        prev_candle = klines_df.iloc[-2]
        current_candle = klines_df.iloc[-1]
        
        # Check if percentiles are calculated
        if self.upper_wick_25th is None or self.lower_wick_25th is None:
            checklist_reasons.append("Percentiles not calculated yet: ❌")
            return PositionSignal(position_side=PositionSide.ZERO, reason=" | ".join(checklist_reasons))

        # Check if it's a new candle
        current_open_time = str(current_candle['open_time'])
        last_position_open_candle = position_handler.last_position_open_candle
        new_candle = current_open_time != last_position_open_candle

        if not new_candle:
            checklist_reasons.append(f"Not new candle (last: {last_position_open_candle[5:-9]} / cur: {current_open_time[5:-9]}): ❌")
            return PositionSignal(position_side=PositionSide.ZERO, reason=" | ".join(checklist_reasons))

        # Check body change filter
        prev_body_change = prev_candle['body_change_pct']
        body_filter_passed = prev_body_change >= self.min_body_pct
        
        checklist_reasons.append(f"Prev body change: {prev_body_change*100:.3f}% (min: {self.min_body_pct*100:.2f}%): {'✅' if body_filter_passed else '❌'}")
        
        if not body_filter_passed:
            return PositionSignal(position_side=PositionSide.ZERO, reason=" | ".join(checklist_reasons))

        # Mean reversion logic
        if prev_candle['is_red']:
            # Previous RED → LONG (expect bounce)
            new_position_side = PositionSide.LONG
            checklist_reasons.append(f"Prev RED candle → LONG (mean reversion): ✅")
        elif prev_candle['is_green']:
            # Previous GREEN → SHORT (expect pullback)
            new_position_side = PositionSide.SHORT
            checklist_reasons.append(f"Prev GREEN candle → SHORT (mean reversion): ✅")
        else:
            checklist_reasons.append("Prev candle is doji → ZERO: ❌")

        reason_message = " | ".join(checklist_reasons)
        return PositionSignal(position_side=new_position_side, reason=reason_message)

    def calculate_tp_sl(self, klines_df, position_side, entry_price):
        """
        Calculate TP based on 25th percentile wick.
        SL is not set here (returns -1.0) - handled by exit strategy.
        
        TP Logic:
        - LONG: entry + lower_wick_25th% (expect price to rise by typical lower wick amount)
        - SHORT: entry - upper_wick_25th% (expect price to fall by typical upper wick amount)
        """
        if self.upper_wick_25th is None or self.lower_wick_25th is None:
            self.logger.warning("Percentiles not calculated, using default TP")
            return -1.0, -1.0

        if position_side == PositionSide.LONG:
            # For LONG: TP is entry + lower_wick_25th%
            tp_price = round(entry_price * (1 + self.lower_wick_25th / 100), self.decimal)
            self.logger.debug(f"LONG TP = entry + {self.lower_wick_25th:.4f}%: {tp_price}")
        elif position_side == PositionSide.SHORT:
            # For SHORT: TP is entry - upper_wick_25th%
            tp_price = round(entry_price * (1 - self.upper_wick_25th / 100), self.decimal)
            self.logger.debug(f"SHORT TP = entry - {self.upper_wick_25th:.4f}%: {tp_price}")
        else:
            self.logger.warning(f"Unexpected position_side: {position_side}")
            tp_price = -1.0

        # SL is handled by exit strategy
        sl_price = -1.0
        
        return tp_price, sl_price


# EOF

# Made with Bob
