from abstracts.base_exit_strategy import BaseExitStrategy
from models.enum.position_side import PositionSide
from models.position_signal import PositionSignal
from core.position_handler import PositionHandler

class ExitCandleClose(BaseExitStrategy):
    """
    Exit strategy:
    - Closes position at the close of the previous candle
    """
    dynamic_config: dict

    def __init__(self, dynamic_config):
        super().__init__()
        self.dynamic_config = dynamic_config

    def _process_data(self, klines_df):
        return klines_df

    def should_close(self, klines_df, position_handler: PositionHandler) -> PositionSignal:
        '''
        return
            - position.position_side if no need to close
            - PositionSide.ZERO if need to close
        '''
        position = position_handler.get_position()
        new_position_side = position.position_side
        checklist_reasons  = [f'{position.symbol} Exit Signal']

        cur_candle = klines_df.iloc[-1]
        cur_candle_open_time  = str(object=cur_candle['open_time'])
    
        different_candle = position.open_candle != cur_candle_open_time
        if different_candle:
            new_position_side = PositionSide.ZERO # close position
            checklist_reasons.append(f"diff cdl (pos {position.open_candle[5:-9]} / cr {cur_candle_open_time[5:-9]}): ✅")
        else:
            # same candle, do not close
            checklist_reasons.append(f"diff cdl (pos {position.open_candle[5:-9]} / cr {cur_candle_open_time[5:-9]}): ❌")

        reason_message = " | ".join(checklist_reasons)
        return PositionSignal(position_side = new_position_side, reason = reason_message) 

# EOF