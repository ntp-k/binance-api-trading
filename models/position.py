from dataclasses import dataclass, field
from typing import Optional, Union
from models.enum.position_side import PositionSide
from commons.common import get_datetime_now_string_gmt_plus_7


@dataclass
class Position:
    """
    Represents a trading position with entry/exit details and PnL tracking.
    
    Attributes:
        position_id: Unique identifier for the position
        run_id: Bot run identifier
        symbol: Trading pair symbol
        position_side: LONG or SHORT
        entry_price: Price at which position was opened
        open_candle: Candle timestamp when position opened
        open_reason: Strategy reason for opening
        open_time: Timestamp when position opened
        open_fee: Fee paid to open position
        close_time: Timestamp when position closed
        close_price: Price at which position was closed
        pnl: Profit/loss in quote currency
        close_reason: Reason for closing position
        close_fee: Fee paid to close position
        max_pnl: Maximum PnL reached during position lifetime
        min_pnl: Minimum PnL reached during position lifetime
        created_at: Position creation timestamp
        tp_price: Take profit price (for persistence across restarts)
        sl_price: Stop loss price (for persistence across restarts)
        tp_order_id: Take profit order ID (for persistence across restarts)
        sl_order_id: Stop loss order ID (for persistence across restarts)
    """
    position_id: Optional[int] = None
    run_id: int = 0
    symbol: str = ''
    position_side: PositionSide = PositionSide.LONG
    entry_price: float = 0.0
    open_candle: str = ''
    open_reason: str = ''
    open_time: str = field(default_factory=lambda: get_datetime_now_string_gmt_plus_7())
    open_fee: float = 0.0
    close_time: Optional[str] = None
    close_price: float = 0.0
    pnl: float = 0.0
    close_reason: str = ''
    close_fee: float = 0.0
    max_pnl: float = 0.0
    min_pnl: float = 0.0
    created_at: str = field(default_factory=lambda: get_datetime_now_string_gmt_plus_7())
    tp_price: float = 0.0
    sl_price: float = 0.0
    tp_order_id: str = ''
    sl_order_id: str = ''
    
    def to_dict(self) -> dict:
        """Convert position to dictionary for serialization."""
        return {
            "run_id": self.run_id,
            "symbol": self.symbol,
            "position_side": self.position_side.name,
            "entry_price": self.entry_price,
            "open_candle": self.open_candle,
            "open_reason": self.open_reason,
            "open_time": self.open_time,
            "open_fee": self.open_fee,
            "close_time": self.close_time,
            "close_price": self.close_price,
            "pnl": self.pnl,
            "close_reason": self.close_reason,
            "close_fee": self.close_fee,
            "max_pnl": self.max_pnl,
            "min_pnl": self.min_pnl,
            "tp_price": self.tp_price,
            "sl_price": self.sl_price,
            "tp_order_id": self.tp_order_id,
            "sl_order_id": self.sl_order_id
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Position':
        """
        Create Position instance from dictionary.
        
        Args:
            data: Dictionary containing position data
            
        Returns:
            Position instance
        """
        # Parse position_side
        position_side = data["position_side"]
        if isinstance(position_side, str):
            position_side = PositionSide[position_side]
        
        return cls(
            run_id=data.get("run_id", 0),
            symbol=data.get("symbol", ""),
            position_side=position_side,
            entry_price=data.get("entry_price", 0.0),
            open_candle=data.get("open_candle", ""),
            open_reason=data.get("open_reason", ""),
            open_time=data.get("open_time", get_datetime_now_string_gmt_plus_7(format='%Y-%m-%d %H:%M:%S')),
            open_fee=data.get("open_fee", 0.0),
            close_time=data.get("close_time"),
            close_price=data.get("close_price", 0.0),
            pnl=data.get('pnl', 0.0),
            close_reason=data.get("close_reason", ""),
            close_fee=data.get("close_fee", 0.0),
            max_pnl=data.get("max_pnl", 0.0),
            min_pnl=data.get("min_pnl", 0.0),
            tp_price=data.get("tp_price", 0.0),
            sl_price=data.get("sl_price", 0.0),
            tp_order_id=data.get("tp_order_id", ""),
            sl_order_id=data.get("sl_order_id", "")
        )


if __name__ == "__main__":
    pass

# EOF
