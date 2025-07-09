from commons.common import get_datetime_now_string_gmt_plus_7
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from models.enum.position_side import PositionSide
from datetime import datetime
from commons.common import get_datetime_now_string_gmt_plus_7

@dataclass
class Position:
    position_id: Optional[int] = None
    run_id: int = 0
    symbol: str = ''
    position_side: PositionSide = PositionSide.LONG
    entry_price: float = 0.0
    open_candle: str = ''
    open_reason: str = ''
    open_time: datetime = get_datetime_now_string_gmt_plus_7()
    open_fee: Optional[float] = 0.0
    close_time: Optional[datetime] = None
    close_price: Optional[float] = 0.0
    pnl: Optional[float] = 0.0
    close_reason: Optional[str] = ''
    close_fee: Optional[float] = 0.0
    max_pnl: Optional[float] = 0.0
    min_pnl: Optional[float] = 0.0
    created_at: Optional[datetime] = get_datetime_now_string_gmt_plus_7()
    
    def to_dict(self):
        return {
            "run_id": self.run_id,
            "symbol": self.symbol,
            "position_side": self.position_side.name,  # <-- note this
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
            "min_pnl": self.min_pnl
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            run_id=data["run_id"],
            symbol=data["symbol"],
            position_side=PositionSide[data["position_side"]] if type(data["position_side"]) == type('a') else data["position_side"],
            entry_price=data["entry_price"],
            open_candle=data["open_candle"],
            open_reason=data.get("open_reason", ""),
            open_time=data.get("open_time", get_datetime_now_string_gmt_plus_7(format='%Y-%m-%d %H:%M:%S')),
            open_fee=data.get("open_fee", 0.0),
            close_time=data.get("close_time", 0.0),
            close_price=data.get("close_price", 0.0),
            pnl=data.get('pnl', 0.0),
            close_reason=data.get("close_reason", ""),
            close_fee=data.get("close_fee", 0.0),
            max_pnl=data.get("max_pnl", 0),
            min_pnl=data.get("min_pnl", 0.0)
        )


if __name__ == "__main__":
    pass

# EOF
