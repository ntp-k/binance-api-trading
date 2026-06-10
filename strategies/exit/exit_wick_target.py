"""
Wick Target Exit Strategy

Exit Logic:
- Exit when TP target is hit (handled by bot's TP/SL system)
- If target not hit by candle close, exit at candle close
- No stop loss (SL disabled) - rely on candle close exit

This exit strategy is designed to work with the wick mean reversion entry strategy.
Based on backtests, exiting at candle close (if target not hit) works better than
using a wide stop loss.
"""

from abstracts.base_exit_strategy import BaseExitStrategy
from models.bot_config import BotConfig
from models.enum.position_side import PositionSide
from models.position_signal import PositionSignal
from core.position_handler import PositionHandler
import pandas as pd


class ExitWickTarget(BaseExitStrategy):
    """
    Exit strategy that closes position at candle close if TP not hit.
    
    This is essentially a "candle close" exit strategy, but named to match
    the wick mean reversion entry strategy for clarity.
    """

    def __init__(self, bot_config: BotConfig, logger=None):
        super().__init__(logger=logger)
        self.bot_config: BotConfig = bot_config
        self.dynamic_config = bot_config.dynamic_config

    def _process_data(self, klines_df: pd.DataFrame) -> pd.DataFrame:
        """
        No additional processing needed for this exit strategy.
        
        Args:
            klines_df: DataFrame with OHLC data
            
        Returns:
            Unchanged DataFrame
        """
        return klines_df

    def should_close(self, klines_df: pd.DataFrame, position_handler: PositionHandler) -> PositionSignal:
        """
        Determine if position should be closed.
        
        Exit Logic:
        1. Check if TP target is hit → Close immediately
        2. If TP not hit, check if new candle opened → Close at candle close
        3. Otherwise hold position
        
        Args:
            klines_df: DataFrame with OHLC data
            position_handler: Handler with current position state
            
        Returns:
            PositionSignal indicating whether to close (ZERO) or hold position
        """
        position = position_handler.get_position()
        
        # Safety check: if no position exists, return ZERO
        if position is None:
            return PositionSignal(
                position_side=PositionSide.ZERO,
                reason="No position to close"
            )
        
        checklist = [f"{position.symbol} Wick Target Exit"]

        current_candle = klines_df.iloc[-1]
        current_open_time = str(current_candle["open_time"])
        current_price = current_candle['current_price']

        position_side = position.position_side
        new_position_side = position_side

        # Get TP price from position handler
        tp_price = position_handler.tp_price
        
        # ----- CHECK 1: TP HIT -----
        tp_hit = False
        if tp_price > 0.0:
            if position_side == PositionSide.LONG:
                tp_hit = (current_price >= tp_price)
                checklist.append(f"LONG TP | price {current_price} >= TP {tp_price}: {'✅' if tp_hit else '❌'}")
            elif position_side == PositionSide.SHORT:
                tp_hit = (current_price <= tp_price)
                checklist.append(f"SHORT TP | price {current_price} <= TP {tp_price}: {'✅' if tp_hit else '❌'}")
        else:
            checklist.append("TP not set: ❌")

        if tp_hit:
            checklist.append("Exit at TP: ✅")
            new_position_side = PositionSide.ZERO
            reason_message = " | ".join(checklist)
            return PositionSignal(position_side=new_position_side, reason=reason_message)

        # ----- CHECK 2: CANDLE CLOSE -----
        # Check if it's a new candle (meaning the entry candle has closed)
        is_new_candle = (position.open_candle != current_open_time)

        if is_new_candle:
            checklist.append(f"New candle - Entry: {position.open_candle[5:-9]} / Current: {current_open_time[5:-9]}: ✅")
            checklist.append("Exit at candle close: ✅")
            new_position_side = PositionSide.ZERO
        else:
            checklist.append(f"Same candle - Entry: {position.open_candle[5:-9]} / Current: {current_open_time[5:-9]}: ❌")
            checklist.append("Hold position: ✅")

        reason_message = " | ".join(checklist)
        return PositionSignal(position_side=new_position_side, reason=reason_message)


# EOF

# Made with Bob
