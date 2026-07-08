"""
Exit strategy with countdown timer and max loss protection.

Strategy Logic:
- If TP is hit, position closes automatically (handled by TP_SL system)
- If countdown_minutes expires, force close position
- If current price reaches sl_price (max loss), force close position
- Uses position open_time to calculate elapsed time
"""
from abstracts.base_exit_strategy import BaseExitStrategy
from models.bot_config import BotConfig
from models.enum.position_side import PositionSide
from models.position_signal import PositionSignal
from core.position_handler import PositionHandler
from commons.common import get_datetime_now_gmt_plus_7
from datetime import datetime
import pandas as pd


class ExitCountdownWithMaxLoss(BaseExitStrategy):
    """
    Exit strategy that closes position based on:
    1. Countdown timer expiration
    2. Price reaching SL level (max loss protection)
    
    Configuration (dynamic_config):
    - countdown_minutes: Minutes to wait before force close (e.g., 60 = 1 hour)
    - cooldown_after_countdown_seconds: Cooldown after countdown expiry (optional, in seconds)
    - cooldown_after_max_loss_seconds: Cooldown after max loss hit (optional, in seconds)
    """

    def __init__(self, bot_config: BotConfig, logger=None):
        super().__init__(logger=logger)
        self.bot_config: BotConfig = bot_config
        self.dynamic_config = bot_config.dynamic_config
        self.countdown_minutes = self.dynamic_config.get('countdown_minutes', 60)  # 60 min default
        self.cooldown_after_countdown_seconds = self.dynamic_config.get('cooldown_after_countdown_seconds', 0)
        self.cooldown_after_max_loss_seconds = self.dynamic_config.get('cooldown_after_max_loss_seconds', 0)
        
        self.logger.info(
            f"Initialized with countdown_minutes={self.countdown_minutes}, "
            f"cooldown_after_countdown_seconds={self.cooldown_after_countdown_seconds}, "
            f"cooldown_after_max_loss_seconds={self.cooldown_after_max_loss_seconds}"
        )
    
    def get_cooldown_seconds(self, close_reason: str = '', pnl: float = 0.0) -> float:
        """
        Get cooldown duration after position close based on which condition triggered.
        For countdown exits, only apply cooldown if position closed with loss.
        
        Args:
            close_reason: Simple reason string like "SL Hit - 1734.22 (1796.29)" or "Countdown 230min (230min)"
            pnl: The profit/loss of the closed position
        
        Returns:
            Cooldown duration in seconds based on close reason
        """
        # Check which condition triggered
        if close_reason.startswith('SL Hit'):
            return self.cooldown_after_max_loss_seconds
        elif close_reason.startswith('Countdown'):
            # Apply cooldown only if position closed with loss
            if pnl < 0:
                return self.cooldown_after_countdown_seconds
            else:
                return 0.0  # No cooldown for profitable countdown exits
        
        # Default: no cooldown
        return 0.0

    def _calculate_elapsed_minutes(self, position_open_time: str) -> float:
        """
        Calculate elapsed minutes since position opened using open_time.
        
        Args:
            position_open_time: Position open time string (format: 'YYYY-MM-DD HH:MM:SS' in GMT+7)
            
        Returns:
            Number of minutes elapsed
        """
        try:
            # Parse position open time (stored in GMT+7)
            open_dt = datetime.strptime(position_open_time, '%Y-%m-%d %H:%M:%S')
            
            # Get current time in GMT+7 (to match position open_time timezone)
            current_dt = get_datetime_now_gmt_plus_7()
            # Remove timezone info for comparison
            current_dt = current_dt.replace(tzinfo=None)
            
            # Calculate elapsed time
            elapsed = current_dt - open_dt
            elapsed_minutes = elapsed.total_seconds() / 60.0
            
            return elapsed_minutes
        except Exception as e:
            self.logger.error(f"Error calculating elapsed time: {e}")
            # Return large number to trigger force close on error
            return 999999.0

    def _process_data(self, klines_df):
        """
        Process klines data. No additional indicators needed.
        
        Args:
            klines_df: DataFrame containing klines data
            
        Returns:
            Unmodified klines DataFrame
        """
        return klines_df

    def should_close(self, klines_df, position_handler: PositionHandler) -> PositionSignal:
        """
        Determine if position should be closed based on:
        1. Countdown timer expiration
        2. Current price reaching SL level
        
        Args:
            klines_df: DataFrame containing klines data
            position_handler: Position handler with current position
            
        Returns:
            PositionSignal with ZERO to close position, or current position_side to hold
        """
        position = position_handler.get_position()
        
        # Safety check: if no position exists, return ZERO
        if position is None:
            return PositionSignal(
                position_side=PositionSide.ZERO,
                reason="No position to close"
            )
        
        klines_df = self._process_data(klines_df=klines_df)
        
        position_side = position.position_side
        new_position_side = position_side
        
        # Get current price from latest candle
        current_candle = klines_df.iloc[-1]
        current_price = float(current_candle['close'])
        
        # Get SL price from position handler
        sl_price = position_handler.sl_price
        
        # ----- MAX LOSS CHECK (SL Price) -----
        sl_hit = False
        if sl_price > 0:  # Only check if SL is set
            if position_side == PositionSide.LONG:
                # For LONG: close if current price <= SL price
                sl_hit = current_price <= sl_price
            elif position_side == PositionSide.SHORT:
                # For SHORT: close if current price >= SL price
                sl_hit = current_price >= sl_price
        
        # ----- COUNTDOWN TIMER CHECK -----
        elapsed_minutes = self._calculate_elapsed_minutes(position.open_time)
        countdown_expired = elapsed_minutes >= self.countdown_minutes
        
        # ----- CORE LOGIC: Close position if countdown expired OR SL hit -----
        # Priority: SL hit takes precedence over countdown
        if sl_hit:
            new_position_side = PositionSide.ZERO
            reason_message = f"SL Hit - {current_price} ({sl_price})"
            self.logger.info(
                f"Max loss reached for {position.symbol} at price {current_price} "
                f"(SL: {sl_price}, position: {position_side.name})"
            )
        elif countdown_expired:
            new_position_side = PositionSide.ZERO
            reason_message = f"Countdown {elapsed_minutes:.0f}min ({self.countdown_minutes}min)"
            self.logger.info(
                f"Countdown expired for {position.symbol} after {elapsed_minutes:.1f} minutes "
                f"(threshold: {self.countdown_minutes} min, open_time: {position.open_time})"
            )
        else:
            reason_message = f"Holding - SL: {current_price} {sl_price}, Elapsed: {elapsed_minutes:.1f}min ({self.countdown_minutes}min)"
        
        return PositionSignal(position_side=new_position_side, reason=reason_message)

# EOF

# Made with Bob