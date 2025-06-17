from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from commons.custom_logger import CustomLogger
from models.strategies import Strategies

'''
Params Mapping from BotConfig

BACKTEST
    BotConfig.params_1 = ignore this x start candle (use to calculate signal) (ex. 120 = start from the 120th candle)
    BotConfig.params_2 = Initial Balance in USD (ex. 100.0)
    BotConfig.params_3 = Trading Interval in minutes (ex. 86400 = backtest for 1 day (yesterday)
    BotConfig.params_4 = None
    BotConfig.params_5 = None

FORWARDTEST
    BotConfig.params_1 = ignore this x start candle (use to calculate signal) (ex. 120 = start from the 120th candle)
    BotConfig.params_2 = Initial Balance in USD (ex. 100.0)
    BotConfig.params_3 = None
    BotConfig.params_4 = None
    BotConfig.params_5 = None

LIVE
    BotConfig.params_1 = ignore this x start candle (use to calculate signal) (ex. 120 = start from the 120th candle)
    BotConfig.params_2 = Initial Balance in USD (ex. 100.0)
    BotConfig.params_3 = None
    BotConfig.params_4 = None
    BotConfig.params_5 = None
'''

@dataclass
class BotConfig:
    config_id: str
    enabled: bool
    strategy: Strategies
    symbol: str
    leverage: int
    quantity: float
    timeframe: str
    timeframe_limit: int
    param_1: Optional[str] = None
    param_2: Optional[str] = None
    param_3: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        self.logger = CustomLogger(name=f'{BotConfig.__name__}_{self.config_id}')
        self.logger.debug(f"Loaded {self}")

        self.validate()

    def validate(self):
        required_fields = ["config_id", "symbol", "timeframe", "strategy"]
        for field in required_fields:
            if not getattr(self, field):
                raise ValueError(f"Missing required field: {field}")

        if self.leverage <= 0 or self.quantity <= 0:
            raise ValueError("Leverage and quantity must be positive numbers.")

        if self.timeframe_limit <= 0 and self.timeframe_limit > 1500:
            raise ValueError("Timeframe limit must be a positive integer.")


    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            config_id=str(data['config_id']),
            enabled=bool(data.get("enabled", True)),
            strategy=Strategies(data['strategy'].upper()),
            symbol=data.get("symbol"),  # type: ignore
            leverage=int(data.get("leverage", 1)),
            quantity=float(data.get("quantity", 0.0)),
            timeframe=data.get("timeframe"),  # type: ignore
            timeframe_limit=int(data.get("timeframe_limit", 100)), 
            param_1=data.get("param_1"), # type: ignore
            param_2=data.get("param_2"), # type: ignore
            param_3=data.get("param_3"), # type: ignore
            notes=data.get("notes"),
            created_at=cls.parse_datetime(data.get("created_at")),
            updated_at=cls.parse_datetime(data.get("updated_at"))
        )
    
    def to_dict(self) -> dict:
        return {
            "config_id": self.config_id,
            "enabled": self.enabled,
            "strategy": self.strategy.value,
            "symbol": self.symbol,
            "leverage": self.leverage,
            "quantity": self.quantity,
            "timeframe": self.timeframe,
            "timeframe_limit": self.timeframe_limit,
            "param_1": self.param_1,
            "param_2": self.param_2,
            "param_3": self.param_3,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


    @staticmethod
    def parse_datetime(value):
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None

# EOF
