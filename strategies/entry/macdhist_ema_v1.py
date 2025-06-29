from models.enum.position_side import PositionSide
from abstracts.base_entry_strategy import BaseEntryStrategy
import strategies.data_processor as data_processor

class MacdHistEMAV1Strategy(BaseEntryStrategy):
    """
    An entry strategy combining MACD histogram crossing zero
    with price being above/below the EMA.
    """

    def __init__(self, dynamic_config):
        super().__init__()
        self.dynamic_config = dynamic_config
        self.ema_period = dynamic_config.get('ema_peroid', 200)

    def _process_data(self, klines_df):
        klines_df = data_processor.calculate_macd(df=klines_df, decimal=self.dynamic_config.get('macd_decimal', 2))
        klines_df = data_processor.calculate_ema(df=klines_df, ema=self.ema_period)
        return klines_df

    def should_open(self, klines_df) -> tuple[bool, PositionSide]:
        """
        Determine whether to open a long or short position based on:
        - MACD histogram crossing zero
        - price crossing EMA
        """
        klines_df = self._process_data(klines_df=klines_df)
        should_open = False
        position_side = PositionSide.ZERO 

        # # looking for opening
        #     if current_candle_time == position.last_action_candle_time:
        #         print(f"{_dt} | skipping open, already took action on this candle | pct: {position.last_action_candle_time} | cct: {current_candle_time}")
        #     else:
        #         _direction = None
        #         if (current_price >= current_ema_200) and prev_prev_hist < 0 and previous_hist > 0 and current_hist > previous_hist:
        #             _direction = 'long'
        #         elif (current_price < current_ema_200) and prev_prev_hist > 0 and previous_hist < 0 and current_hist < previous_hist:
        #             _direction = 'short'
                
        #         if _direction is not None:
        #             print(f"{_dt} | {'OPEN':<5} | pph: {prev_prev_hist} | ph: {previous_hist} | ch: {current_hist} | ema_200: {current_ema_200}")
        #             position.open_position(symbol=symbol, quantity=quantity, direction=_direction)
        #             position.last_action_candle_time = current_candle_time
    
        return should_open, position_side

# EOF
