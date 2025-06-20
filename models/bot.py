from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

from commons.custom_logger import CustomLogger
from models.enum.strategies import Strategies

@dataclass
class Bot:
    bot_id: Optional[int] = None
    bot_name: str = ""
    strategy: Strategies = Strategies.MACDHIST
    symbol: str = ""
    leverage: int = 1
    quantity: float = 1.0
    timeframe: str = ""
    timeframe_limit: int = 1
    candle_for_indicator: Optional[int] = None
    config: Optional[Dict[str, Any]] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    def __post_init__(self):
        self.logger = CustomLogger(name=f'{Bot.__name__}_{self.bot_id}')
        self.logger.debug(f"Loaded {self}")

    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        if type(data['strategy']) == type('string'):
            data['strategy'] = Strategies(data['strategy'].upper())
        return cls(**data)

# EOF
