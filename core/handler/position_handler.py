from datetime import datetime

from commons.custom_logger import CustomLogger
from models.enum.position_side import PositionSide
from models.position import Position

class PositionHandler:
    def __init__(self, bot_runner):
        self.logger = CustomLogger(name=f'{self.__class__.__name__}_{bot_runner.bot_fullname}')
        self.logger.debug(f'Initializing {self.__class__.__name__}')
        self.bot_runner = bot_runner

        self.position = self.open_position(
            PositionSide.ZERO,
            0.0,
            datetime.now()
        )

    def open_position(self, position_side, entry_price, open_time):
        self.position = Position.from_dict({
            'run_id': self.bot_runner.run.run_id,
            'position_side': position_side,
            'entry_price': entry_price,
            'open_time': open_time
        })
        self.logger.debug(
            f'{open_time}  |  {"Open":<8}  |  {position_side.value:<5}  |  {entry_price:.2f}')
        return self.position

    def close_position(self, close_price, close_time):
        self.position.close_price = close_price
        self.position.close_time = close_time

        pnl = ((close_price - self.position.entry_price) if self.position.position_side == PositionSide.LONG else (self.position.entry_price - close_price)) * self.bot_runner.bot.quantity
        self.logger.debug(
            f'{close_time}  |  {"Close":<8}  |  {self.position.position_side.value:<5}  |  {close_price:.2f}')

        return self.position, pnl

    def get_current_position(self):
        ...

# EOF
