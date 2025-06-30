from commons.common import get_datetime_now_string_gmt_plus_7
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from models.enum.position_side import PositionSide
from datetime import datetime

@dataclass
class Position:
    position_id: Optional[int] = None
    run_id: int = 0
    position_side: PositionSide = PositionSide.LONG
    entry_price: float = 0.0
    open_time: datetime = get_datetime_now_string_gmt_plus_7()
    open_candle: str = ''
    close_time: Optional[datetime] = None
    close_price: Optional[float] = 0.0
    open_signal: Optional[str] = ''
    close_signal: Optional[str] = ''
    created_at: Optional[datetime] = get_datetime_now_string_gmt_plus_7()

    def to_dict(self):
        return {
            "run_id": self.run_id,
            "position_side": self.position_side.name,  # <-- note this
            "entry_price": self.entry_price,
            "open_time": self.open_time,
            "open_candle": self.open_candle,
            "close_time": self.close_time,
            "close_price": self.close_price,
            "open_signal": self.open_signal,
            "close_signal": self.close_signal
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            run_id=data["run_id"],
            position_side=PositionSide[data["position_side"]],  # convert back from name
            entry_price=data["entry_price"],
            open_time=data["open_time"],
            open_candle=data["open_candle"],
            close_time=data["close_time"],
            close_price=data.get("close_price", 0.0),
            open_signal=data.get("open_signal", ""),
            close_signal=data.get("close_signal", "")
        )


if __name__ == "__main__":
    pass

# EOF
