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

        position_side = position.position_side
        new_position_side = position_side

        # ----- CANDLE CLOSE CHECK -----
        # This closes at the **end of the candle** (new candle open time)
        is_new_candle = (position.open_candle != cur_open_time)

        if is_new_candle:
            checklist.append(f"New Candle - pos {position.open_candle[5:-9]} / cur {cur_open_time[5:-9]}: ✅")
        else:
            checklist.append(f"New Candle - pos {position.open_candle[5:-9]} / cur {cur_open_time[5:-9]}: ❌")

        # core logic
        if is_new_candle:
            new_position_side = PositionSide.ZERO

        reason_message = " | ".join(checklist)
        return PositionSignal(position_side=new_position_side, reason=reason_message)

# EOF

# Made with Bob
