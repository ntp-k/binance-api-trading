from abstracts.base_entry_strategy import BaseEntryStrategy
from models.enum.position_side import PositionSide
from models.position_signal import PositionSignal
from core.position_handler import PositionHandler

class EntryPreviousCandle(BaseEntryStrategy):
    """
    Entry at the beginning of the candle:
    - Long if previous candle is positive (green)
    - Short if previous candle is negative (red)

    TP: at candle close
    SL:
    - LONG: previous candle's LOW price
    - SHORT: previous candle's HIGH price
    """

    def __init__(self, dynamic_config):
        super().__init__()
        self.decimal = dynamic_config.get('decimal', 2)

    def _process_data(self, klines_df):
        return klines_df

    def should_open(self, klines_df, position_handler: PositionHandler) -> PositionSignal:
        symbol = position_handler.bot_config.symbol
        new_position_side = PositionSide.ZERO
        checklist_reasons = [f"{symbol} Entry Signal"]

        prev_candle = klines_df.iloc[-2]
        prev_candle_positive = prev_candle['close'] > prev_candle['open']
        prev_candle_negative = prev_candle['close'] < prev_candle['open']
        
        # For LONG: use low as SL, for SHORT: use high as SL
        sl_price_long = prev_candle['low']
        sl_price_short = prev_candle['high']
        current_price = klines_df.iloc[-1]['current_price']

        current_open_time = str(klines_df.iloc[-1]['open_time'])
        last_position_open_candle = position_handler.last_position_open_candle
        new_candle = current_open_time != last_position_open_candle

        if new_candle:
            if prev_candle_positive:
                if sl_price_long < current_price:
                    checklist_reasons.append(f"Previous candle positive -> LONG: ✅, sl price {sl_price_long} < current price {current_price}: ✅")
                else:
                    checklist_reasons.append(f"Previous candle positive -> LONG: ✅, sl price {sl_price_long} < current price {current_price}: ❌")
            elif prev_candle_negative:
                if sl_price_short > current_price:
                    checklist_reasons.append(f"Previous candle negative -> SHORT: ✅, sl price {sl_price_short} > current price {current_price}: ✅")
                else:
                    checklist_reasons.append(f"Previous candle negative -> SHORT: ✅, sl price {sl_price_short} > current price {current_price}: ❌")
            else:
                checklist_reasons.append("No previous candle direction -> ZERO: ❌")
        else:
            checklist_reasons.append(f"new candle for position  (las_pos {last_position_open_candle[5:-9]} / cur {current_open_time[5:-9]}) -> ZERO: ❌")
    
        # core logic
        if new_candle:
            if prev_candle_positive and sl_price_long < current_price:
                new_position_side = PositionSide.LONG
            elif prev_candle_negative and sl_price_short > current_price:
                new_position_side = PositionSide.SHORT

        reason_message = " | ".join(checklist_reasons)
        return PositionSignal(position_side=new_position_side, reason=reason_message)

    def calculate_tp_sl(self, klines_df, position_side, entry_price):
        """
        SL:
        - LONG: previous candle's LOW price
        - SHORT: previous candle's HIGH price
        """
        prev_candle = klines_df.iloc[-2]
        
        if position_side == PositionSide.LONG:
            sl_price = round(prev_candle['low'], self.decimal)
            self.logger.debug(f"LONG SL = previous candle low: {sl_price}")
        elif position_side == PositionSide.SHORT:
            sl_price = round(prev_candle['high'], self.decimal)
            self.logger.debug(f"SHORT SL = previous candle high: {sl_price}")
        else:
            # Handle ZERO or unexpected position_side
            self.logger.warning(f"Unexpected position_side: {position_side}, returning default SL")
            sl_price = round(prev_candle['open'], self.decimal)  # Fallback to open price

        return -1.0, sl_price

# EOF
