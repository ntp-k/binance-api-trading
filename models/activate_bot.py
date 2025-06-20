from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

from commons.custom_logger import CustomLogger
from models.enum.run_mode import RunMode

@dataclass
class ActivateBot:
    activate_id: Optional[int] = None
    bot_id: int = 0
    mode: RunMode = RunMode.BACKTEST
    initial_balance: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        self.logger = CustomLogger(name=f'{ActivateBot.__name__}_{self.activate_id}')
        self.logger.debug(f"Loaded {self}")

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActivateBot":
        if type(data['mode']) == type('string'):
            data['mode'] = RunMode(data['mode'].upper())
        return cls(**data)

# EOF
