from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from models.run_mode import RunMode
from commons.custom_logger import CustomLogger

@dataclass
class BotRun():
    run_id: Optional[int] = None
    config_id: int = 0
    bot_fullname: Optional[str] = None
    run_mode: RunMode = RunMode.BACKTEST
    start_time: datetime = field(default_factory=datetime.now)
    initial_balance: float = 0.0
    is_closed: Optional[bool] = False

    # set on close
    end_time: Optional[datetime] = field(default_factory=datetime.now)
    duration_minutes: Optional[int] = 0
    total_positions: Optional[int] = 0
    winning_positions: Optional[int] = 0
    losing_positions: Optional[int] = 0
    win_rate: Optional[float] = 0.0
    final_balance: Optional[float] = 0.0
    roi_percent: Optional[float] = 0.0
    daily_roi: Optional[float] = 0.0
    annual_roi: Optional[float] = 0.0
    notes: Optional[str] = None
    created_at: Optional[datetime] = field(default_factory=datetime.now)


    def __post_init__(self):
        self.logger = CustomLogger(name=f'{BotRun.__name__}_{self.bot_fullname or "unknown"}')
        self.logger.debug(f"Initialized BacktestRun: {self}")

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            run_id=data.get("run_id"),
            bot_fullname=data.get("bot_fullname"), # type: ignore
            config_id=data.get("config_id"), # type: ignore
            run_mode=data.get("run_mode"), # type: ignore
            is_closed=data.get("is_closed", False), # type: ignore
            start_time=data.get("start_time"), # type: ignore
            end_time=data.get("end_time", datetime.now()),
            duration_minutes=data.get("duration_minutes", 0),
            total_positions=data.get("total_positions", 0),
            winning_positions=data.get("winning_positions", 0),
            losing_positions=data.get("losing_positions", 0),
            win_rate=float(data.get("win_rate", 0)),
            initial_balance=float(data.get("initial_balance", 0)),
            final_balance=float(data.get("final_balance", 0)),
            roi_percent=float(data.get("roi_percent", 0)),
            daily_roi=float(data.get("daily_roi", 0)),
            annual_roi=float(data.get("annual_roi", 0)),
            notes=data.get("notes", ''),
            created_at=data.get("created_at", datetime.now())
        )

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "config_id": self.config_id,
            "bot_fullname": self.bot_fullname,
            "run_mode": self.run_mode,
            "is_closed": self.is_closed,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_minutes": self.duration_minutes,
            "total_positions": self.total_positions,
            "winning_positions": self.winning_positions,
            "losing_positions": self.losing_positions,
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
