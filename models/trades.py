from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

from commons.custom_logger import CustomLogger

@dataclass
class Trade:
    trade_id: Optional[int] = None
    run_id: int = 0
    trade_side: str = ""
    trade_type: Optional[str] = None
    price: float = 0.0
    reduce_only: Optional[bool] = None
    trade_time: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        self.logger = CustomLogger(name=f'{Trade.__name__}_{self.run_id}')
        self.logger.debug(f"Loaded {self}")

    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(**data)

# EOF
