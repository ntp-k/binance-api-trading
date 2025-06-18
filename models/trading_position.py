from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from models.enum.positino_side import PositionSide


@dataclass
class TradingPosition:
    position_id: Optional[int]
    run_id: Optional[int]
    symbol: str
    amount: float
    side: PositionSide
    entry_price: float
    mark_price: float
    unrealized_profit: float
    open_time: datetime
    is_closed: bool = False

    # set on close
    close_price: Optional[float] = None
    close_time: Optional[datetime] = None
    pnl: Optional[float] = 0.0

    def is_open(self) -> bool:
        return self.close_time is None

    def close(self, price: float, time: datetime):
        """Close the position with given price and optional time"""
        self.close_price = price
        self.close_time = time
        self.is_closed = True
        self.pnl = ((self.close_price - self.entry_price) if self.side == PositionSide.LONG else (self.entry_price - self.close_price)) * self.amount

    def to_dict(self) -> dict:
        """Convert the position to a dictionary representation"""
        return {
            "position_id": self.position_id,
            "run_id": self.run_id,
            "symbol": self.symbol,
            "amount": self.amount,
            "side": self.side.value if isinstance(self.side, PositionSide) else str(self.side),
            "entry_price": self.entry_price,
            "mark_price": self.mark_price,
            "unrealized_profit": self.unrealized_profit,
            "open_time": self.open_time.isoformat() if self.open_time else None,
            "close_price": self.close_price,
            "close_time": self.close_time.isoformat() if self.close_time else None,
            "pnl": self.pnl
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TradingPosition":
        """Create a TradingPosition from a dictionary"""
        return cls(
            position_id=int(data.get('position_id', 0)),
            run_id=data["run_id"],
            symbol=data["symbol"],
            amount=float(data["amount"]),
            side=PositionSide(data["side"]) if not isinstance(
                data["side"], PositionSide) else data["side"],
            entry_price=float(data["entry_price"]),
            mark_price=float(data["mark_price"]),
            unrealized_profit=float(data["unrealized_profit"]),
            open_time=data["open_time"],
            close_price=float(data["close_price"]) if data.get(
                "close_price") else None,
            close_time=datetime.fromisoformat(
                data["close_time"]) if data.get("close_time") else None,
            pnl=float(data["pnl"]) if data.get("pnl") else 0.0
        )

    @classmethod
    def mock(cls, symbol: str) -> "TradingPosition":
        """Return a mock instance for testing or dev use."""
        now = datetime.now()
        return cls(
            position_id=0,
            run_id=0,
            symbol=symbol,
            side=PositionSide.ZERO,
            amount=0.0,
            entry_price=0.0,
            mark_price=0.0,
            unrealized_profit=0.0,
            open_time=now,
            close_price=None,
            close_time=None,
            pnl=0.0,
            is_closed=False
        )


# EOF
