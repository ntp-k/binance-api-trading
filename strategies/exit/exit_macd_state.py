from abstracts.base_exit_strategy import BaseExitStrategy
from models.enum.position_side import PositionSide
from models.position_signal import PositionSignal
from core.position_handler import PositionHandler
import strategies.data_processor as data_processor

class ExitMacdState(BaseExitStrategy):
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
        self.dynamic_config = dynamic_config
        self.macd_decimal = dynamic_config.get('macd_decimal', 2)
        self.close_price_diff_threshold = dynamic_config.get('close_price_diff_thsd', 0)

    def _process_data(self, klines_df):
        klines_df = data_processor.calculate_macd(df=klines_df, decimal=self.macd_decimal)
        return klines_df

    def should_close(self, klines_df, position_handler: PositionHandler) -> PositionSignal:
        '''
        return
            - position.position_side if no need to close
            - PositionSide.ZERO if need to close
        '''

        position = position_handler.get_position()
        klines_df = self._process_data(klines_df=klines_df)
        new_position_side = position.position_side
        checklist_reasons  = [f'{position.symbol} Exit Signal']

        latest_kline = klines_df.iloc[-1]
        current_price = latest_kline['current_price']
        current_macd = latest_kline['macd']
        current_candle_open_time  = str(object=latest_kline['open_time'])

        # Condition 1: MACD against position
        macd_against_position = (
            (position.position_side == PositionSide.LONG and current_macd < 0) or
            (position.position_side == PositionSide.SHORT and current_macd > 0)
        )
        if macd_against_position:
            checklist_reasons.append(f"MACD {current_macd:.4f} against {position.position_side.name}: ✅")
        else:
            checklist_reasons.append(f"MACD {current_macd:.4f} against {position.position_side.name}: ❌")

        # Condition 2: Different candle
        different_candle = position.open_candle != current_candle_open_time
        if different_candle:
            checklist_reasons.append(f"diff cdl ({position.open_candle[5:-9]}/{current_candle_open_time[5:-9]}): ✅")
        else:
            checklist_reasons.append(f"diff cdl ({position.open_candle[5:-9]}/{current_candle_open_time[5:-9]}): ❌")
        
        # Condition 3: Price difference over threshold
        price_diff_percent = abs(current_price - position.entry_price) / position.entry_price * 100
        price_diff_over_threshold = price_diff_percent > self.close_price_diff_threshold
        if price_diff_over_threshold:
            checklist_reasons.append(
                f"pdiff > thrsd ({price_diff_percent:.2f}% > {self.close_price_diff_threshold:.2f}%): ✅"
            )
        else:
            checklist_reasons.append(
                f"pdiff > thrsd ({price_diff_percent:.2f}% > {self.close_price_diff_threshold:.2f}%): ❌"
            )

        reason_message = " | ".join(checklist_reasons)
        # self.logger.info(reason_message)

         # actual logic
        if macd_against_position and different_candle and price_diff_over_threshold:
            self.logger.debug(f'cur_macd: {current_macd:.4f}, open_c: {position.open_candle}, cur_c: {current_candle_open_time}, cur_p: {current_price}, p_diff: {different_candle:.2f}%')
            new_position_side = PositionSide.ZERO # close position

        return PositionSignal(position_side = new_position_side, reason = reason_message)

# EOF
