from abstracts.base_exit_strategy import BaseExitStrategy
from models.enum.position_side import PositionSide
from models.position_signal import PositionSignal
from models.position import Position
import strategies.data_processor as data_processor

class ExitMacdHistState(BaseExitStrategy):
    """
    Exit strategy that closes the position when the MACD histogram
    changes sign (crosses from positive to negative or vice versa).
    """

    def __init__(self, dynamic_config):
        super().__init__()
        self.dynamic_config = dynamic_config
        self.macd_decimal = dynamic_config.get('macd_decimal', 2)
        self.close_price_diff_thsd = dynamic_config.get('close_price_diff_thsd', 0)

    def _process_data(self, klines_df):
        klines_df = data_processor.calculate_macd(df=klines_df, decimal=self.macd_decimal)
        return klines_df

    def should_close(self, klines_df, position: Position) -> PositionSignal:
        klines_df = self._process_data(klines_df=klines_df)
        position_signal: PositionSignal = PositionSignal(
            position_side=position.position_side,
            reason='Hold position'
        )

        current_price = klines_df.iloc[-1]['current_price']
        current_hist = klines_df.iloc[-1]['histogram']
        current_candle = str(object=klines_df.iloc[-1]['open_time'])

        long_position_but_negative_hist = position.position_side == PositionSide.LONG and current_hist < 0
        short_position_but_positive_hist = position.position_side == PositionSide.SHORT and current_hist > 0
       
        if long_position_but_negative_hist:
            position_signal.position_side = PositionSide.ZERO # should close position
            position_signal.reason = f'LONG position with negative histogram'
        elif short_position_but_positive_hist:
            position_signal.position_side = PositionSide.ZERO # should close position
            position_signal.reason = f'SHORT position with positive histogram'
        
        if position_signal.position_side == PositionSide.ZERO:
            price_diff_percent = abs(current_price - position.entry_price) / position.entry_price * 100
            # just openned on this candle which can still constantly switch between positive and negative 
            if position.open_candle == current_candle:
                position_signal.position_side = position.position_side
                position_signal.reason = f'Skipping close: cannot close on open candle'
            # price does not move much, prevent sideways market
            elif price_diff_percent < self.close_price_diff_thsd:
                position_signal.position_side = position.position_side
                position_signal.reason = f'Skipping close: price difference within threshold {price_diff_percent:.2f} % / {self.close_price_diff_thsd:.2f} %'  

        return position_signal

# EOF
