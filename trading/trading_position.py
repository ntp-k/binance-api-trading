from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timezone, timedelta

from trading.future_trading_types import PositionSide

@dataclass
class TradingPosition:
    symbol: str
    amount: float
    side: PositionSide
    entry_price: float
    mark_price: float
    unrealized_profit: float
    open_time: Optional[datetime] = None

    # Set on close
    close_price: Optional[float] = None
    close_time: Optional[datetime] = None

    def __init__(self, 
                 symbol: str, 
                 amount: float, 
                 side: PositionSide, 
                 entry_price: float, 
                 mark_price: float, 
                 unrealized_profit: float, 
                 open_time: Optional[datetime] = None):
        self.symbol = symbol
        self.amount = amount
        self.side = side
        self.entry_price = entry_price
        self.mark_price = mark_price
        self.unrealized_profit = unrealized_profit
        self.open_time = open_time or datetime.utcnow()
        self.close_price = None
        self.close_time = None


    def is_open(self) -> bool:
        return self.close_time is None

    def close(self, price: float, time: datetime):
        """Close the position with given price and optional time"""
        self.close_price = price
        self.close_time = time


    def to_dict(self) -> dict:
        """Serialize the position (e.g., for logging or DB)"""
        return {
            "symbol": self.symbol,
            "amount": self.amount,
            "side": self.side.value,
            "entry_price": self.entry_price,
            "mark_price": self.mark_price,
            "unrealized_profit": self.unrealized_profit,
            "close_price": self.close_price,
            "open_time": self.open_time.isoformat() if self.open_time else None,
            "close_time": self.close_time.isoformat() if self.close_time else None
        }

    @classmethod
    def from_dict(cls, pos: dict) -> "TradingPosition":
        """Create a Position object from Binance position data"""
        amount = float(pos["positionAmt"])
        update_time = int(pos.get("updateTime", 0))  # milliseconds

        gmt7 = timezone(timedelta(hours=7))
        open_time = None
        if update_time > 0:
            open_time = datetime.fromtimestamp(update_time / 1000, tz=gmt7)
        return cls(
            symbol=pos["symbol"],
            amount=amount,
            side=PositionSide.LONG if amount >= 0 else PositionSide.SHORT,
            entry_price=float(pos["entryPrice"]),
            mark_price=float(pos["markPrice"]),
            unrealized_profit=float(pos["unRealizedProfit"]),
            open_time=open_time
        )

# EOF
