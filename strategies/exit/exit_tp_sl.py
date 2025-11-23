from abstracts.base_exit_strategy import BaseExitStrategy
from models.position_signal import PositionSignal
from core.position_handler import PositionHandler

class ExitTPSL(BaseExitStrategy):
    """
    Exit strategy:
    - Temp placeholder for TP/SL exit handling by TradeClient and bot core
    """
    dynamic_config: dict

    def __init__(self, dynamic_config):
        super().__init__()


    def _process_data(self, klines_df):
        pass

    def should_close(self, klines_df, position_handler: PositionHandler) -> PositionSignal:
        '''
        return
            - position.position_side if no need to close
            - PositionSide.ZERO if need to close
        '''
        position = position_handler.get_position()
        return PositionSignal(position_side = position.position_side, reason = f'{position.symbol} Exit Signal | TP/SL triggered: ❌')

# EOF
