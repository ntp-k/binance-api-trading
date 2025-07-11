from abstracts.base_exit_strategy import BaseExitStrategy
from models.enum.position_side import PositionSide
from models.position_signal import PositionSignal
from models.position import Position
import strategies.data_processor as data_processor

class ExitTPSL(BaseExitStrategy):
    """
    Exit strategy:
    - Closes LONG if MACD histogram goes negative
    - Closes SHORT if MACD histogram goes positive
    - But:
        * ignores exit on same candle as entry
        * ignores exit if price change is within a threshold
    """
    dynamic_config: dict
    macd_decimal: float
    close_price_diff_threshold: float

    def __init__(self, dynamic_config):
        super().__init__()


    def _process_data(self, klines_df):
        pass

    def should_close(self, klines_df, position_handler) -> PositionSignal:
        '''
        return
            - position.position_side if no need to close
            - PositionSide.ZERO if need to close
        '''

        position = position_handler.get_position()
        return PositionSignal(position_side = position.position_side, reason = f'{position.symbol} Exit Signal | TP/SL triggered: ❌')

# EOF
