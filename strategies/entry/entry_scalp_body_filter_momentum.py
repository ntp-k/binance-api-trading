"""
Entry strategy based on candle body percentage filter with momentum.

Strategy Logic:
- Triggers on new candle open
- Checks previous candle body percentage
- If body_pct >= threshold, allows trade
- Enter LONG if previous candle is green (bullish)
- Enter SHORT if previous candle is red (bearish)
- Uses very small TP percentage for scalping
"""
from abstracts.base_entry_strategy import BaseEntryStrategy
from models.enum.position_side import PositionSide
from models.position_signal import PositionSignal
from core.position_handler import PositionHandler


class EntryScalpBodyFilterMomentum(BaseEntryStrategy):
    """
    Entry strategy that filters trades based on candle body percentage.
    
    Configuration (dynamic_config):
    - min_body_pct: Minimum body percentage to allow trade (e.g., 0.003 = 0.3%)
    - tp_pct: Take profit percentage (e.g., 0.001 = 0.1%)
    - decimal: Price decimal places for rounding (default: 2)
    """

    def __init__(self, dynamic_config, logger=None):
        super().__init__(logger=logger)
        self.min_body_pct = dynamic_config.get('min_body_pct', 0.003)  # 0.3% default
        self.tp_pct = dynamic_config.get('tp_pct', 0.001)  # 0.1% default
        self.decimal = dynamic_config.get('decimal', 2)
        self.min_holding_seconds = dynamic_config.get('min_holding_seconds', 60)  # 60 seconds default
        
        self.logger.info(
            f"Initialized with min_body_pct={self.min_body_pct}, tp_pct={self.tp_pct}, "
            f"min_holding_seconds={self.min_holding_seconds}"
        )

    def _process_data(self, klines_df):
        """
        Calculate body percentage for each candle.
        Body percentage = abs(close - open) / open
        """
        klines_df['body_pct'] = abs(klines_df['close'] - klines_df['open']) / klines_df['open']
        return klines_df

    def should_open(self, klines_df, position_handler: PositionHandler) -> PositionSignal:
        """
        Determine if position should be opened based on:
        1. New candle check OR last position held < min_holding_seconds (quick exit allows re-entry)
        2. Previous candle body percentage >= threshold
        3. Previous candle direction (green = LONG, red = SHORT)
        """
        symbol = position_handler.bot_config.symbol
        new_position_side = PositionSide.ZERO
        checklist_reasons = [f"{symbol} Entry Signal"]

        # Process data to get body_pct
        klines_df = self._process_data(klines_df)

        # Get previous and current candle
        prev_candle = klines_df.iloc[-2]
        current_candle = klines_df.iloc[-1]
        
        # Check if it's a new candle
        current_open_time = str(current_candle['open_time'])
        last_position_open_candle = position_handler.last_position_open_candle
        new_candle = current_open_time != last_position_open_candle
        
        # Check if last position was held for less than min_holding_seconds (quick exit)
        last_holding_seconds = position_handler.last_position_holding_seconds
        quick_exit = last_holding_seconds > 0 and last_holding_seconds < self.min_holding_seconds
        
        # Allow entry if: new candle OR quick exit on same candle
        can_enter = new_candle or quick_exit

        if not can_enter:
            checklist_reasons.append(
                f"Not a new candle (last: {last_position_open_candle[5:-9]} / cur: {current_open_time[5:-9]}) "
                f"AND not quick exit (holding: {last_holding_seconds:.1f}s >= {self.min_holding_seconds}s): ❌"
            )
            reason_message = " | ".join(checklist_reasons)
            return PositionSignal(position_side=new_position_side, reason=reason_message)
        
        if quick_exit:
            checklist_reasons.append(
                f"Quick exit detected (holding: {last_holding_seconds:.1f}s < {self.min_holding_seconds}s) "
                f"-> Allow re-entry on same candle: ✅"
            )

        # Calculate previous candle metrics
        prev_body_pct = prev_candle['body_pct']
        prev_candle_green = prev_candle['close'] > prev_candle['open']
        prev_candle_red = prev_candle['close'] < prev_candle['open']
        
        # Check body percentage filter
        body_filter_passed = prev_body_pct >= self.min_body_pct
        
        checklist_reasons.append(
            f"Prev candle body_pct {prev_body_pct:.4f} >= {self.min_body_pct:.4f}: "
            f"{'✅' if body_filter_passed else '❌'}"
        )

        if not body_filter_passed:
            reason_message = " | ".join(checklist_reasons)
            return PositionSignal(position_side=new_position_side, reason=reason_message)

        # Determine direction
        if prev_candle_green:
            new_position_side = PositionSide.LONG
            checklist_reasons.append(f"Prev candle GREEN -> LONG: ✅")
        elif prev_candle_red:
            new_position_side = PositionSide.SHORT
            checklist_reasons.append(f"Prev candle RED -> SHORT: ✅")
        else:
            checklist_reasons.append(f"Prev candle DOJI (no direction): ❌")

        reason_message = " | ".join(checklist_reasons)
        return PositionSignal(position_side=new_position_side, reason=reason_message)

    def calculate_tp_sl(self, klines_df, position_side, entry_price):
        """
        Calculate TP based on configured percentage.
        SL is not set here (will be handled by exit strategy).
        
        Returns:
            Tuple of (tp_price, sl_price)
            - tp_price: Entry price +/- tp_pct
            - sl_price: -1.0 (not used, handled by exit strategy)
        """
        if position_side == PositionSide.LONG:
            tp_price = round(entry_price * (1 + self.tp_pct), self.decimal)
            self.logger.debug(f"LONG TP = entry {entry_price} + {self.tp_pct*100}% = {tp_price}")
        elif position_side == PositionSide.SHORT:
            tp_price = round(entry_price * (1 - self.tp_pct), self.decimal)
            self.logger.debug(f"SHORT TP = entry {entry_price} - {self.tp_pct*100}% = {tp_price}")
        else:
            self.logger.warning(f"Unexpected position_side: {position_side}")
            tp_price = -1.0

        # SL is handled by exit strategy
        sl_price = -1.0
        
        return tp_price, sl_price

# EOF

# Made with Bob
