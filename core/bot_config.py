from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from commons.custom_logger import CustomLogger

@dataclass
class BotConfig:
    bot_id: str
    enabled: bool
    strategy: str
    run_mode: str
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
        self.logger = CustomLogger(name=self.__class__.__name__)
        self.logger.debug(f"Loaded {self}")

        self.validate()

    def validate(self):
        required_fields = ["bot_id", "symbol", "timeframe", "strategy"]
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
            bot_id=data.get("bot_id"), # type: ignore
            enabled=bool(data.get("enabled", True)),
            strategy=data.get("strategy"),  # type: ignore
            run_mode=data.get("run_mode"), # type: ignore
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
