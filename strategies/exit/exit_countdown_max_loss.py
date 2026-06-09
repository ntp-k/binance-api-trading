"""
Exit strategy with countdown timer and max loss protection.

Strategy Logic:
- If TP is hit, position closes automatically (handled by TP_SL system)
- If TP not hit within countdown_minutes, force close position
- If max_loss_pnl is reached, force close position immediately
- Uses position open_time to calculate elapsed time
"""
from abstracts.base_exit_strategy import BaseExitStrategy
from models.enum.position_side import PositionSide
from models.position_signal import PositionSignal
from core.position_handler import PositionHandler
from commons.common import get_datetime_now_gmt_plus_7
from datetime import datetime
import pandas as pd


class ExitCountdownMaxLoss(BaseExitStrategy):
    """
    Exit strategy that closes position based on:
    1. Countdown timer - force close after X minutes if TP not hit
    2. Max loss threshold - force close if PnL drops below threshold
    
    Configuration (dynamic_config):
    - countdown_minutes: Minutes to wait before force close (e.g., 60 = 1 hour)
    - max_loss_pnl: Maximum loss in quote currency before force close (e.g., -5.0 = -5 USDC)
    """

    def __init__(self, dynamic_config, logger=None):
        super().__init__(logger=logger)
        self.countdown_minutes = dynamic_config.get('countdown_minutes', 60)  # 60 min default
        self.max_loss_pnl = dynamic_config.get('max_loss_pnl', -10.0)  # -10 USDC default
        
        self.logger.info(
            f"Initialized with countdown_minutes={self.countdown_minutes}, "
            f"max_loss_pnl={self.max_loss_pnl}"
        )

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
        2. Max loss threshold reached
        
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
        
        checklist = [f"{position.symbol} Exit Signal"]
        
        position_side = position.position_side
        new_position_side = position_side
        
        # ----- COUNTDOWN TIMER CHECK -----
        elapsed_minutes = self._calculate_elapsed_minutes(position.open_time)
        countdown_expired = elapsed_minutes >= self.countdown_minutes
        
        checklist.append(
            f"Countdown | elapsed {elapsed_minutes:.1f}min >= {self.countdown_minutes}min: "
            f"{'✅ FORCE CLOSE' if countdown_expired else '❌'}"
        )
        
        # ----- MAX LOSS CHECK -----
        current_pnl = position.pnl
        max_loss_hit = current_pnl <= self.max_loss_pnl
        
        checklist.append(
            f"Max Loss | PnL {current_pnl:.2f} <= {self.max_loss_pnl:.2f}: "
            f"{'✅ FORCE CLOSE' if max_loss_hit else '❌'}"
        )
        
        # ----- CORE LOGIC: Close position if countdown expired or max loss hit -----
        if countdown_expired:
            new_position_side = PositionSide.ZERO
            self.logger.info(
                f"Countdown expired for {position.symbol} after {elapsed_minutes:.1f} minutes "
                f"(threshold: {self.countdown_minutes} min, open_time: {position.open_time})"
            )
        
        if max_loss_hit:
            new_position_side = PositionSide.ZERO
            self.logger.info(
                f"Max loss hit for {position.symbol} at PnL {current_pnl:.2f} "
                f"(threshold: {self.max_loss_pnl:.2f})"
            )
        
        reason_message = " | ".join(checklist)
        return PositionSignal(position_side=new_position_side, reason=reason_message)

# EOF

# Made with Bob
