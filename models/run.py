from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from commons.custom_logger import CustomLogger
from models.enum.run_mode import RunMode

@dataclass
class Run:
    run_id: Optional[int] = None
    bot_id: int = 0
    mode: RunMode = RunMode.BACKTEST
    initial_balance: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)

    # update at the end
    end_time: Optional[datetime] = None
    total_positions: Optional[int] = None
    winning_positions: Optional[int] = None
    final_balance: Optional[float] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = field(default_factory=datetime.now)

    def __post_init__(self):
        self.logger = CustomLogger(name=f'{Run.__name__}_{self.run_id}')
        # self._set_mode()
        self.logger.debug(f"Loaded {self}")
    
    def _set_mode(self):
        self.mode = RunMode(self.mode)

    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        if type(data['mode']) == type('string'):
            data['mode'] = RunMode(data['mode'].upper())
        return cls(**data)
        
# EOF
