from abstracts.base_exit_strategy import BaseExitStrategy
from models.enum.position_side import PositionSide
from models.position_signal import PositionSignal
from core.position_handler import PositionHandler

class ExitCandleClose(BaseExitStrategy):

    def __init__(self, dynamic_config):
        super().__init__()
        self.dynamic_config = dynamic_config

    def _process_data(self, klines_df):
        return klines_df

    def should_close(self, klines_df, position_handler: PositionHandler) -> PositionSignal:

        position = position_handler.get_position()
        checklist = [f"{position.symbol} Exit Signal"]

        cur_candle = klines_df.iloc[-1]
        cur_open_time = str(cur_candle["open_time"])
        cur_price = cur_candle["current_price"]
        sl_price = position_handler.sl_price

        position_side = position.position_side
        new_position_side = position_side

        # ----- SL HIT CHECK -----
        long_sl_hit  = (position_side == PositionSide.LONG  and cur_price <= sl_price)
        short_sl_hit = (position_side == PositionSide.SHORT and cur_price >= sl_price)

        if position_side == PositionSide.LONG:
            checklist.append(f"LONG | price {cur_price} <= SL {sl_price}: {'✅' if long_sl_hit else '❌'}")
        else:
            checklist.append(f"SHORT | price {cur_price} >= SL {sl_price}: {'✅' if short_sl_hit else '❌'}")

        # ----- CANDLE CLOSE CHECK -----
        # This closes at the **end of the candle** (new candle open time)
        is_new_candle = (position.open_candle != cur_open_time)

        if is_new_candle:
            checklist.append(f"New Candle - pos {position.open_candle} / cur {cur_open_time}: ✅")
        else:
            checklist.append(f"New Candle - pos {position.open_candle} / cur {cur_open_time}: ❌")

        # core logic
        if long_sl_hit or short_sl_hit or is_new_candle:
            new_position_side = PositionSide.ZERO

        reason_message = " | ".join(checklist)
        return PositionSignal(position_side=new_position_side, reason=reason_message)

# EOF
