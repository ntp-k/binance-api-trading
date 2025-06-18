from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

from commons.custom_logger import CustomLogger
from models.enum.run_mode import RunMode

@dataclass
class Run:
    run_id: Optional[int] = None
    bot_id: int = 0
    mode: RunMode = RunMode.BACKTEST
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_trades: Optional[int] = None
    total_positions: Optional[int] = None
    winning_positions: Optional[int] = None
    initial_balance: float = 0.0
    final_balance: Optional[float] = None
    note: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        self.logger = CustomLogger(name=f'{Run.__name__}_{self.run_id}')
        self.logger.debug(f"Loaded {self}")

    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(**data)

# EOF
