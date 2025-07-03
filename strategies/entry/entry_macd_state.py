from models.enum.position_side import PositionSide
from abstracts.base_entry_strategy import BaseEntryStrategy
import strategies.data_processor as data_processor
from models.position_signal import PositionSignal

class EntryMacdState(BaseEntryStrategy):
    """
    An entry strategy combining MACD crossing zero
    """

    dynamic_config: dict
    ema_period: float

    def __init__(self, dynamic_config):
        super().__init__()
        self.dynamic_config = dynamic_config
        self.ema_period = dynamic_config.get('ema_peroid', 200)

    def _process_data(self, klines_df):
        klines_df = data_processor.calculate_macd(df=klines_df, decimal=self.dynamic_config.get('macd_decimal', 2))
        return klines_df

    def should_open(self, klines_df, position_handler) -> PositionSignal:
        symbol = position_handler.bot_config.symbol
        new_position_side = PositionSide.ZERO # don't open position
        checklist_reasons  = [f'{symbol} Entry Signal']

        klines_df = self._process_data(klines_df=klines_df)
        prev_macd, cur_macd = klines_df.iloc[-2:]['macd'].values

        cur_macd_positive = cur_macd > 0

        if cur_macd_positive:
            new_position_side = PositionSide.LONG
            checklist_reasons.append('Looking for LONG')
            checklist_reasons.append(f"cmcad pos ({cur_macd:.4f}): ✅")
        else: # cur macd negative
            new_position_side = PositionSide.SHORT
            checklist_reasons.append('Looking for SHORT')
            checklist_reasons.append(f"cmcad neg ({cur_macd:.4f}): ✅")
        self.logger.debug(f'pmacd: {prev_macd:.4f}, cmcad: {cur_macd:.4f}')
        reason_message = " | ".join(checklist_reasons)

        return PositionSignal(position_side = new_position_side, reason = reason_message)

# EOF
