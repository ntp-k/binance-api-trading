from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any

from models.enum.run_mode import RunMode

@dataclass
class BotConfig:
    bot_id: int
    run_id: int
    bot_name: str
    run_mode: RunMode
    entry_strategy: str
    exit_strategy: str
    symbol: str
    leverage: int
    quantity: float
    timeframe: str
    timeframe_limit: int
    strategy_config: Dict[str, Any]
    created_at: datetime

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        if type(data['run_mode']) == type('string'):
            data['run_mode'] = RunMode(value=data['run_mode'].upper())
        return cls(**data)

    def to_dict(self) -> dict:
        return self.__dict__

# EOF
