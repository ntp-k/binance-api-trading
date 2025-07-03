from models.enum.position_side import PositionSide
from abstracts.base_entry_strategy import BaseEntryStrategy
import strategies.data_processor as data_processor
from models.position_signal import PositionSignal

class EntryMacdHistState(BaseEntryStrategy):
    """
    An entry strategy combining MACD histogram crossing zero
    with price being above/below the EMA.
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
        prev_prev_hist, prev_hist, current_hist = klines_df.iloc[-3:]['histogram'].values

        current_hist_positive = current_hist > 0
        prev_hist_positive = prev_hist > 0
        prev_prev_hist_positive = prev_prev_hist > 0
        current_hist_more_than_prev_hist = current_hist > prev_hist

        if current_hist_positive:
            # looking for Long position (-,+,++)
            checklist_reasons.append('Looking for LONG')
            if not prev_prev_hist_positive:
                checklist_reasons.append(f"pph neg ({prev_prev_hist:.4f}): ✅")
            else:
                checklist_reasons.append(f"pph neg ({prev_prev_hist:.4f}): ❌")
            
            if prev_hist_positive:
                checklist_reasons.append(f"ph pos ({prev_hist:.4f}): ✅")
            else:
                checklist_reasons.append(f"ph pos ({prev_hist:.4f}): ❌")     

            if current_hist_more_than_prev_hist:
                checklist_reasons.append(f"ch > ph ({current_hist:.4f} > {prev_hist:.4f}): ✅")
            else:
                checklist_reasons.append(f"ch > ph ({current_hist:.4f} > {prev_hist:.4f}): ❌")

        else: # current_hist < 0:
            # looking for short (+,-,--)
            checklist_reasons.append('Looking for SHORT')
            if prev_prev_hist_positive:
                checklist_reasons.append(f"pph hist pos ({prev_prev_hist:.4f}): ✅")
            else:
                checklist_reasons.append(f"pph hist pos ({prev_prev_hist:.4f}): ❌")
            
            if not prev_hist_positive:
                checklist_reasons.append(f"ph neg ({prev_hist:.4f}): ✅")
            else:
                checklist_reasons.append(f"pht neg ({prev_hist:.4f}): ❌")     

            if not current_hist_more_than_prev_hist:
                checklist_reasons.append(f"ch < ph ({current_hist:.4f} < {prev_hist:.4f}): ✅")
            else:
                checklist_reasons.append(f"ch < ph ({current_hist:.4f} < {prev_hist:.4f}): ❌")  

        reason_message = " | ".join(checklist_reasons)
        # self.logger.info(reason_message)

        # actual logic
        if not prev_hist_positive and prev_hist_positive and current_hist_more_than_prev_hist:
            new_position_side = PositionSide.LONG
            self.logger.debug(f'pph: {prev_prev_hist}, ph: {prev_hist}, ch: {current_hist}')
        elif prev_prev_hist_positive and not prev_hist_positive and not current_hist_more_than_prev_hist:
            new_position_side = PositionSide.SHORT
            self.logger.debug(f'pph: {prev_prev_hist}, ph: {prev_hist}, ch: {current_hist}')
        
        return PositionSignal(position_side = new_position_side, reason = reason_message)

# EOF
