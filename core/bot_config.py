from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from commons.custom_logger import CustomLogger

@dataclass
class BotConfig:
    bot_id: str
    symbol: str
    timeframe: str
    timeframe_limit: int
    leverage: int
    quantity: float
    strategy: str
    poll_interval: int
    enabled: bool
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        self.logger = CustomLogger(name=self.__class__.__name__)
        self.logger.debug(f"Loaded BotConfig: {self}")

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

        if self.poll_interval < 1:
            raise ValueError("Poll interval must be at least 1 second.")

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            bot_id=data.get("bot_id"), # type: ignore
            symbol=data.get("symbol"),  # type: ignore
            timeframe=data.get("timeframe"),  # type: ignore
            timeframe_limit=int(data.get("timeframe_limit", 100)), 
            leverage=int(data.get("leverage", 1)),
            quantity=float(data.get("quantity", 0.0)),
            strategy=data.get("strategy"),  # type: ignore
            poll_interval=int(data.get("poll_interval", 10)),
            enabled=bool(data.get("enabled", True)),
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
