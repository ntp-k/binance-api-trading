from abstracts.base_exit_strategy import BaseExitStrategy
from models.enum.position_side import PositionSide
from models.position_signal import PositionSignal
from core.position_handler import PositionHandler

class ExitTPSL(BaseExitStrategy):
    """
    Exit strategy based on Take Profit (TP) and Stop Loss (SL) levels.
    
    Monitors current price against TP/SL levels and signals position closure when:
    - LONG position: price >= TP or price <= SL
    - SHORT position: price <= TP or price >= SL
    """

    def __init__(self, dynamic_config):
        """
        Initialize TP/SL exit strategy.
        
        Args:
            dynamic_config: Dynamic configuration dictionary (not used but kept for consistency)
        """
        super().__init__()
        self.dynamic_config = dynamic_config

    def _process_data(self, klines_df):
        """
        Process klines data. No additional indicators needed for TP/SL strategy.
        
        Args:
            klines_df: DataFrame containing klines data
            
        Returns:
            Unmodified klines DataFrame
        """
        return klines_df

    def should_close(self, klines_df, position_handler: PositionHandler) -> PositionSignal:
        """
        Determine if position should be closed based on TP/SL levels.
        
        Args:
            klines_df: DataFrame containing klines data with current_price
            position_handler: Position handler with current position and TP/SL prices
            
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
        
        # Get current price from latest candle
        latest_kline = klines_df.iloc[-1]
        current_price = latest_kline['current_price']
        
        # Get TP/SL prices from position handler
        tp_price = position_handler.tp_price
        sl_price = position_handler.sl_price
        
        position_side = position.position_side
        new_position_side = position_side
        
        # ----- TAKE PROFIT CHECK -----
        long_tp_hit = False
        short_tp_hit = False
        
        if tp_price > 0.0:
            if position_side == PositionSide.LONG:
                long_tp_hit = (current_price >= tp_price)
                checklist.append(f"LONG TP | price {current_price} >= TP {tp_price}: {'✅' if long_tp_hit else '❌'}")
            elif position_side == PositionSide.SHORT:
                short_tp_hit = (current_price <= tp_price)
                checklist.append(f"SHORT TP | price {current_price} <= TP {tp_price}: {'✅' if short_tp_hit else '❌'}")
        else:
            checklist.append(f"TP not set: N/A")
        
        # ----- STOP LOSS CHECK -----
        long_sl_hit = False
        short_sl_hit = False
        
        if sl_price > 0.0:
            if position_side == PositionSide.LONG:
                long_sl_hit = (current_price <= sl_price)
                checklist.append(f"LONG SL | price {current_price} <= SL {sl_price}: {'✅' if long_sl_hit else '❌'}")
            elif position_side == PositionSide.SHORT:
                short_sl_hit = (current_price >= sl_price)
                checklist.append(f"SHORT SL | price {current_price} >= SL {sl_price}: {'✅' if short_sl_hit else '❌'}")
        else:
            checklist.append(f"SL not set: N/A")
        
        # ----- CORE LOGIC: Close position if TP or SL is hit -----
        if long_tp_hit or short_tp_hit or long_sl_hit or short_sl_hit:
            new_position_side = PositionSide.ZERO
            if long_tp_hit or short_tp_hit:
                self.logger.info(f"Take Profit hit for {position.symbol} at price {current_price}")
            if long_sl_hit or short_sl_hit:
                self.logger.info(f"Stop Loss hit for {position.symbol} at price {current_price}")
        
        reason_message = " | ".join(checklist)
        return PositionSignal(position_side=new_position_side, reason=reason_message)

# EOF
