import json
import os

from commons.custom_logger import CustomLogger
from models.bot_config import BotConfig
from models.enum.position_side import PositionSide
from models.position import Position

POSITION_RECORDS_DIR = "position_records"
POSITION_RECORD_FILENAME_TEMPLATE = "runid_{run_id}_record_{count}.json"
POSITION_STATES_DIR = "position_states"
POSITION_STATES_FILENAME_TEMPLATE = "runid_{run_id}_state.json"

class PositionHandler:
    bot_config: BotConfig
    position: Position | None = None
    position_count: int = 1

    def __init__(self, bot_config: BotConfig):
        self.logger = CustomLogger(name=f"PositionHandler:{bot_config.bot_name}")
        self.bot_config: BotConfig = bot_config
        self.position: Position | None = None

        if not os.path.exists(POSITION_RECORDS_DIR):
            os.mkdir(POSITION_RECORDS_DIR)
        if not os.path.exists(POSITION_STATES_DIR):
            os.mkdir(POSITION_STATES_DIR)
        _position_state_file_name = POSITION_STATES_FILENAME_TEMPLATE.format(run_id=self.bot_config.run_id)
        self.position_state_file_path = os.path.join(POSITION_STATES_DIR, _position_state_file_name)

    def open_position(self, position_side: PositionSide, price: float, candle: str):
        if self.position:
            self.logger.warning('Already had openned position')
            return

        self.position = Position(
            position_side=position_side,
            entry_price=price,
            open_candle=candle
        )
        self.logger.info(f"Opened {position_side.name} position at {price}")

    def close_position(self, reason: str):
        if not self.position:
            self.logger.warning('No position ti close')
            return

        self.logger.info(f"Closing position {self.position.position_side.name} due to {reason}")

        self.position = None

    def set_position(self, position_dict: dict):
        try:
            self.position = Position.from_dict(position_dict)
            self.logger.info(f"Restored position from dict: side={self.position.position_side.name}, "
                            f"entry_price={self.position.entry_price}")
        except Exception as e:
            self.logger.error_e("Error while setting position from dict", e=e)
        
    def is_open(self) -> bool:
        return self.position is not None

    def get_position(self) -> Position | None:
        return self.position

    def _dump_position(self, file_path):
        if not self.position:
            self.logger.warn("No position to dump.")
            return
        with open(file_path, "w") as f:
            json.dump(self.position.to_dict(), f, indent=4)
        self.logger.debug(f"Position dumped to {file_path}")

    def _dump_position_record(self):
        file_name = POSITION_RECORD_FILENAME_TEMPLATE.format(run_id=self.bot_config.run_id, count=self.position_count)
        file_path = os.path.join(POSITION_RECORDS_DIR, file_name)
        self._dump_position(file_path=file_path)
        self.position_count += 1

    def dump_position_state(self):
        self._dump_position(file_path=self.position_state_file_path)
    
    def read_position_state(self):
        if not os.path.exists(self.position_state_file_path):
            self.logger.warning('No position state file')
            return
        with open(self.position_state_file_path, 'r') as f:
            data = json.load(f)
            self.position = Position.from_dict(data=data)
            self.position.run_id = self.bot_config.run_id

# EOF
