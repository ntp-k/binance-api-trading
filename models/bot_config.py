from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any

from models.enum.run_mode import RunMode
from models.enum.entry_strategy import EntryStrategy
from models.enum.exit_strategy import ExitStrategy

@dataclass
class BotConfig:
    bot_id: int
    run_id: int
    bot_name: str
    run_mode: RunMode
    entry_strategy: EntryStrategy
    exit_strategy: ExitStrategy
    symbol: str
    leverage: int
    quantity: float
    timeframe: str
    timeframe_limit: int
    dynamic_config: Dict[str, Any]
    created_at: datetime

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        if type(data['run_mode']) == type('string'):
            data['run_mode'] = RunMode(value=data['run_mode'].upper())
        if type(data['entry_strategy']) == type('string'):
            data['entry_strategy'] = EntryStrategy(value=data['entry_strategy'].upper())
        if type(data['exit_strategy']) == type('string'):
            data['exit_strategy'] = ExitStrategy(value=data['exit_strategy'].upper())
        return cls(**data)

    def to_dict(self) -> dict:
        return self.__dict__

# EOF
