import json
import os

from commons.custom_logger import CustomLogger
from models.bot_config import BotConfig
from models.enum.position_side import PositionSide
from models.position import Position
from commons.common import get_datetime_now_string_gmt_plus_7

POSITION_RECORDS_DIR = "position_records"
POSITION_RECORD_FILENAME_TEMPLATE = "runid_{run_id}_record_{count}.json"
POSITION_STATES_DIR = "position_states"
POSITION_STATES_FILENAME_TEMPLATE = "runid_{run_id}_state.json"


class PositionHandler:
    bot_config: BotConfig
    position: Position | None = None
    position_count: int = 1

    def __init__(self, bot_config: BotConfig):
        self.logger = CustomLogger(
            name=f"PositionHandler:{bot_config.bot_name}")
        self.bot_config: BotConfig = bot_config
        self.position: Position | None = None

        if not os.path.exists(POSITION_RECORDS_DIR):
            os.mkdir(POSITION_RECORDS_DIR)
        if not os.path.exists(POSITION_STATES_DIR):
            os.mkdir(POSITION_STATES_DIR)
        _position_state_file_name = POSITION_STATES_FILENAME_TEMPLATE.format(
            run_id=self.bot_config.run_id)
        self.position_state_file_path = os.path.join(
            POSITION_STATES_DIR, _position_state_file_name)

    def open_position(self, position_dict: dict):
        try:
            self.position = Position.from_dict(position_dict)
        except Exception as e:
            self.logger.error_e(
                message="Error while setting position from dict", e=e)

    def close_position(self, position_dict: dict):
        self.position.close_reason = position_dict['close_reason']
        self.position.close_price = position_dict['mark_price']
        self.position.close_time = get_datetime_now_string_gmt_plus_7(
            format='%Y-%m-%d %H:%M:%S')
        self.position.pnl = position_dict['pnl']

        self._dump_position_record()
        self.position = None

    def update_pnl(self, pnl: float):
        self.position.pnl = pnl

    def is_open(self) -> bool:
        return self.position is not None

    def clear_position(self):
        self.position = None
        self.dump_position_state()

    def get_position(self) -> Position | None:
        return self.position

    def _dump_position(self, file_path):
        if not self.position:
            self.logger.warning("No position to dump.")
            return
        with open(file=file_path, mode="w") as f:
            json.dump(obj=self.position.to_dict(), fp=f, indent=4)
        self.logger.debug(message=f"Position dumped to {file_path}")

    def _dump_position_record(self):
        file_name = POSITION_RECORD_FILENAME_TEMPLATE.format(
            run_id=self.bot_config.run_id, count=self.position_count)
        file_path = os.path.join(POSITION_RECORDS_DIR, file_name)
        self._dump_position(file_path=file_path)
        self.position_count += 1

    def dump_position_state(self):
        self._dump_position(file_path=self.position_state_file_path)

    def read_position_state(self):
        try:
            with open(file=self.position_state_file_path, mode='r') as f:
                data = json.load(fp=f)
                self.position = Position.from_dict(data=data)
                self.position.run_id = self.bot_config.run_id
        except Exception as e:
            self.logger.error_e(
                message="Could not restore position state", e=e)
            self.position = None


if __name__ == "__main__":
    pass

# EOF
