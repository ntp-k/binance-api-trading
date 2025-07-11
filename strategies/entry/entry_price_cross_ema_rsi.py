from abstracts.base_entry_strategy import BaseEntryStrategy
from models.enum.position_side import PositionSide
from models.position_signal import PositionSignal
import strategies.data_processor as data_processor
import pandas as pd

class EntryPriceCrossEMARSI(BaseEntryStrategy):
    """
    Entry when:
    - EMA9 crosses EMA21 in direction of trend
    - Price above both EMAs (for LONG), below both (for SHORT)
    - RSI confirms momentum
    """
    def __init__(self, dynamic_config):
        super().__init__()
        self.decimal = dynamic_config.get('macd_decimal', 2)
        self.ema_fast = dynamic_config.get('ema_fast', 9)
        self.ema_slow = dynamic_config.get('ema_slow', 21)
        self.rsi_period = dynamic_config.get('rsi_period', 14)
        self.rsi_long_min = dynamic_config.get('rsi_long_min', 55)
        self.rsi_short_max = dynamic_config.get('rsi_short_max', 45)

        # for tp/sl
        self.atr_period = dynamic_config.get('atr_period', 14)
        self.tp_multiplier = dynamic_config.get('take_profit_atr', 2.0)
        self.sl_multiplier   = dynamic_config.get('stop_loss_atr', 1.0)

    def _process_data(self, klines_df):
        klines_df = data_processor.calculate_ema(df=klines_df, ema=self.ema_fast, decimal=self.decimal)
        klines_df = data_processor.calculate_ema(df=klines_df, ema=self.ema_slow, decimal=self.decimal)
        klines_df = data_processor.calculate_rsi(df=klines_df, period=self.rsi_period, decimal=2)
        return klines_df

    def should_open(self, klines_df, position_handler) -> PositionSignal:
        symbol = position_handler.bot_config.symbol
        new_position_side = PositionSide.ZERO
        checklist_reasons = [f"{symbol} Entry Signal"]

        klines_df = self._process_data(klines_df)
        last = klines_df.iloc[-1]
        prev = klines_df.iloc[-2]
        rsi = last['rsi']

        # EMA crossover detection
        ema_fast = f'ema_{self.ema_fast}'
        ema_slow = f'ema_{self.ema_slow}'
        long_cross = prev[ema_fast] < prev[ema_slow] and last[ema_fast] > last[ema_slow]
        short_cross = prev[ema_fast] > prev[ema_slow] and last[ema_fast] < last[ema_slow]
        
        # Price confirmation
        price_above = last['close'] > last[ema_fast] and last['close'] > last[ema_slow]
        price_below = last['close'] < last[ema_fast] and last['close'] < last[ema_slow]

        # rsi confirm
        rsi_bullish = rsi > self.rsi_long_min
        rsi_bearish = rsi < self.rsi_short_max

        if price_above:
            checklist_reasons.append('Looking for LONG')
            if long_cross:
                checklist_reasons.append('ema long cross: ✅')
            else:
                checklist_reasons.append('ema long cross: ❌')
            
            if rsi_bullish:
                checklist_reasons.append('rsi bullish: ✅')
            else:
                checklist_reasons.append('rsi bullish: ❌')


        elif price_below:
            checklist_reasons.append('Looking for SHORT')
            if long_cross:
                checklist_reasons.append('ema short cross: ✅')
            else:
                checklist_reasons.append('ema short cross: ❌')
            
            if rsi_bearish:
                checklist_reasons.append('rsi bearish: ✅')
            else:
                checklist_reasons.append('rsi bearish: ❌')

        # core logic
        if long_cross and price_above and rsi_bullish:
            new_position_side = PositionSide.LONG
        elif short_cross and price_below and rsi_bearish:
            new_position_side = PositionSide.SHORT
        
        self.logger.debug(message=f"price: {last['close']}, ema9: {prev[ema_fast]}, ema21: {last[ema_slow]}, rsi: {last['rsi']}")
        reason_message = " | ".join(checklist_reasons)

        return PositionSignal(position_side=new_position_side, reason=reason_message)

    def calculate_tp_sl(self, klines_df, position_side, entry_price):
        klines_df = data_processor.calculate_atr(df=klines_df)
        atr = klines_df.iloc[-1]['atr']

        tp_price = 0
        sl_price = 0

        if position_side == PositionSide.LONG:
            sl_price = entry_price - (self.sl_multiplier * atr)
            tp_price = entry_price + (self.tp_multiplier * atr)
        elif position_side == PositionSide.SHORT:
            sl_price = entry_price + (self.sl_multiplier * atr)
            tp_price = entry_price - (self.tp_multiplier * atr)
        else:
            raise(f'Erorr calculating TP/SL when PositionSide is {position_side}')
        
        return round(tp_price, self.decimal4), round(sl_price, self.decimal4)

# EOF
