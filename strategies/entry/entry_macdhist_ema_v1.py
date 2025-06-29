from models.enum.position_side import PositionSide
from abstracts.base_entry_strategy import BaseEntryStrategy
import strategies.data_processor as data_processor
from models.position_signal import PositionSignal

class EntryMacdHistEMAV1(BaseEntryStrategy):
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

    def should_open(self, klines_df) -> PositionSignal:
        klines_df = self._process_data(klines_df=klines_df)
        position_signal = PositionSignal(
            position_side=PositionSide.ZERO,
            reason='No entry signal'
        )

        prev_prev_hist, prev_hist, current_hist = klines_df.iloc[-3:]['histogram'].values
        current_price = klines_df.iloc[-1]['current_price']
        current_ema_200 = klines_df['ema_200'].values[-1]
        # current_candle = str(object=klines_df.iloc[-1]['open_time'])

        price_above_ema = current_price > current_ema_200
        price_below_ema = current_price < current_ema_200
        negetive_then_2_increasing_position = prev_prev_hist < 0 and prev_hist > 0 and current_hist > prev_hist
        positive_then_2_decreasing_negative = prev_prev_hist > 0 and prev_hist < 0 and current_hist < prev_hist

        if price_above_ema and negetive_then_2_increasing_position:
            position_signal.position_side = PositionSide.LONG
            position_signal.reason = 'Price above ema, histogram negative followed by 2 increasing positive'
        elif price_below_ema and positive_then_2_decreasing_negative:
            position_signal.position_side = PositionSide.SHORT
            position_signal.reason = 'Price below ema, histogram positive followed by 2 decreasing negative'       
    
        return position_signal

# EOF
