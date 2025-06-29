from commons.custom_logger import CustomLogger
from models.bot_config import BotConfig
from models.position import Position
from models.enum.position_side import PositionSide

class PositionHandler:
    bot_config: BotConfig
    position: Position | None = None

    def __init__(self, bot_config: BotConfig):
        self.logger = CustomLogger(name=f"PositionHandler:{bot_config.bot_name}")
        self.bot_config: BotConfig = bot_config
        self.position: Position | None = None

    def open_position(self, side: PositionSide, price: float, candle: str):
        self.position = Position(
            position_side=side,
            entry_price=price,
            open_candle=candle
        )
        self.logger.info(f"Opened {side.name} position at {price}")

    def close_position(self, reason: str):
        if self.position:
            self.logger.info(f"Closing position {self.position.position_side.name} due to {reason}")
            self.position = None

    def is_open(self) -> bool:
        return self.position is not None

    def get_position(self) -> Position | None:
        return self.position
