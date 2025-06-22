from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

from commons.custom_logger import CustomLogger
from models.enum.position_side import PositionSide

@dataclass
class Position:
    position_id: Optional[int] = None
    run_id: int = 0
    position_side: PositionSide = PositionSide.ZERO
    entry_price: float = 0.0
    open_time: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)

    # set on close
    close_time: Optional[datetime] = None
    close_price: Optional[float] = None

    def close(self, close_price: float, close_time: datetime):
        self.close_price = close_price
        self.close_time = close_time

    def __post_init__(self):
        self.logger = CustomLogger(name=f'{Position.__name__}_{self.run_id}')
        self.logger.debug(f"Loaded {self}")

    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(**data)

# EOF
