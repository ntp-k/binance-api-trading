from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class BacktestRun:
    run_id: Optional[int] = None
    bot_config_id: int = 0
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime = field(default_factory=datetime.utcnow)
    duration_minutes: int = 0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    initial_balance: float = 0.0
    final_balance: float = 0.0
    roi_percent: float = 0.0
    daily_roi: float = 0.0
    annual_roi: float = 0.0
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            run_id=data.get("run_id"),
            bot_config_id=data.get("bot_config_id", 0),
            start_time=data.get("start_time", datetime.utcnow()),
            end_time=data.get("end_time", datetime.utcnow()),
            duration_minutes=data.get("duration_minutes", 0),
            total_trades=data.get("total_trades", 0),
            winning_trades=data.get("winning_trades", 0),
            losing_trades=data.get("losing_trades", 0),
            win_rate=float(data.get("win_rate", 0)),
            initial_balance=float(data.get("initial_balance", 0)),
            final_balance=float(data.get("final_balance", 0)),
            roi_percent=float(data.get("roi_percent", 0)),
            daily_roi=float(data.get("daily_roi", 0)),
            annual_roi=float(data.get("annual_roi", 0)),
            notes=data.get("notes"),
            created_at=data.get("created_at", datetime.utcnow())
        )

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "bot_config_id": self.bot_config_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_minutes": self.duration_minutes,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "initial_balance": self.initial_balance,
            "final_balance": self.final_balance,
            "roi_percent": self.roi_percent,
            "daily_roi": self.daily_roi,
            "annual_roi": self.annual_roi,
            "notes": self.notes,
            "created_at": self.created_at
        }

# EOF
