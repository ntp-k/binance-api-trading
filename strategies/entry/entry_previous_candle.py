from abstracts.base_entry_strategy import BaseEntryStrategy
from models.enum.position_side import PositionSide
from models.position_signal import PositionSignal

class EntryPreviousCandle(BaseEntryStrategy):
    """
    Entry at the beginning of the candle:
    - Long if previous candle is positive
    - Short if previous candle is negative

    TP: at candle close
    SL: previous day open price
    """

    def __init__(self, dynamic_config):
        super().__init__()
        self.decimal = dynamic_config.get('decimal', 2)

    def _process_data(self, klines_df):
        return klines_df

    def should_open(self, klines_df, position_handler) -> PositionSignal:
        symbol = position_handler.bot_config.symbol
        new_position_side = PositionSide.ZERO
        checklist_reasons = [f"{symbol} Entry Signal"]

        prev_candle = klines_df.iloc[-2]

        prev_candle_positive = prev_candle['close'] > prev_candle['open']
        prev_candle_negative = prev_candle['close'] < prev_candle['open']
        
        sl_price = prev_candle['open']
        current_price = klines_df.iloc[-1]['current_price']

        if prev_candle_positive:
            if sl_price < current_price:
                checklist_reasons.append(f"Previous candle positive -> LONG: ✅, sl price {sl_price} < current price {current_price}: ✅")
            else:
                checklist_reasons.append(f"Previous candle positive -> LONG: ✅, sl price {sl_price} < current price {current_price}: ❌")
        elif prev_candle_negative:
            if sl_price > current_price:
                checklist_reasons.append(f"Previous candle negative -> SHORT: ✅, sl price {sl_price} > current price {current_price}: ✅")
            else:
                checklist_reasons.append(f"Previous candle negative -> SHORT: ✅, sl price {sl_price} > current price {current_price}: ❌")
        else:
            checklist_reasons.append("No previous candle direction -> ZERO ❌")

        # core logic
        if prev_candle_positive and sl_price < current_price:
            new_position_side = PositionSide.LONG
        elif prev_candle_negative and sl_price > current_price:
            new_position_side = PositionSide.SHORT

        reason_message = " | ".join(checklist_reasons)
        return PositionSignal(position_side=new_position_side, reason=reason_message)

    def calculate_tp_sl(self, klines_df, position_side, entry_price):
        """
        SL: previous day open price (previous candle)
        """
        prev_candle = klines_df.iloc[-2]
        sl_price = round(prev_candle['open'], self.decimal)

        self.logger.debug(f"SL = previous candle open: {sl_price}")
        return -1.0, sl_price

# EOF
