import json
import os

from commons.custom_logger import CustomLogger
from models.bot_config import BotConfig
from models.position import Position
from commons.common import get_datetime_now_string_gmt_plus_7

POSITION_RECORDS_DIR = "position_records"
POSITION_RECORD_FILENAME_TEMPLATE = "runid_{run_id}_record_{dt}.json"
POSITION_STATES_DIR = "position_states"
POSITION_STATES_FILENAME_TEMPLATE = "runid_{run_id}_state.json"


class PositionHandler:
    bot_config: BotConfig
    position: Position | None = None
    entry_price: float
    tp_order_id: str
    tp_price: float
    sl_order_id: str
    sl_price: float
    last_position_close_candle_open_time: str

    def __init__(self, bot_config: BotConfig):
        self.logger = CustomLogger(
            name=f"PositionHandler:{bot_config.bot_name}")
        self.bot_config: BotConfig = bot_config
        self.position: Position | None = None
        self.entry_price = 0.0
        self.tp_order_id = ''
        self.tp_price = 0.0
        self.sl_order_id = ''
        self.sl_price = 0.0
        self.last_position_close_candle_open_time = ''

        if not os.path.exists(POSITION_RECORDS_DIR):
            os.mkdir(POSITION_RECORDS_DIR)
        if not os.path.exists(POSITION_STATES_DIR):
            os.mkdir(POSITION_STATES_DIR)
        _position_state_file_name = POSITION_STATES_FILENAME_TEMPLATE.format(
            run_id=self.bot_config.run_id)
        self.position_state_file_path = os.path.join(
            POSITION_STATES_DIR, _position_state_file_name)
    
        self.read_position_state()
    
    def set_tp_order_id(self, id):
        self.tp_order_id = id
    
    def set_tp_price(self, price):
        self.tp_price = price
    
    def get_tp_order_id(self):
        return self.tp_order_id
    
    def set_sl_order_id(self, id):
        self.sl_order_id = id
    
    def set_sl_price(self, price):
        self.sl_price = price
    
    def get_sl_order_id(self):
        return self.sl_order_id

    def clear_tp_sl_orders(self):
        self.entry_price = 0.0
        self.tp_order_id = ''
        self.tp_price = 0.0
        self.sl_order_id = ''
        self.sl_price = 0.0

    def open_position(self, position_dict: dict):
        try:
            self.entry_price = position_dict.get('entry_price')
            self.position = Position.from_dict(position_dict)
        except Exception as e:
            self.logger.error_e(
                message="Error while setting position from dict", e=e)

    def close_position(self, position_dict: dict):
        self.position.close_reason = position_dict['close_reason']
        self.position.close_fee = position_dict['close_fee']
        self.position.close_price = position_dict['close_price']
        self.position.close_time = get_datetime_now_string_gmt_plus_7(
            format='%Y-%m-%d %H:%M:%S')
        self.position.pnl = position_dict['pnl']
        self.last_position_close_candle_open_time = position_dict['close_candle_open_time']

        self._dump_position_record()
        self.position = None
        if os.path.exists(self.position_state_file_path):
            os.remove(self.position_state_file_path)

    def update_pnl(self, pnl: float):
        self.position.max_pnl = max(pnl, self.position.max_pnl)
        self.position.min_pnl = min(pnl, self.position.min_pnl)
        self.position.pnl = pnl

    def is_open(self) -> bool:
        return self.position is not None

    def clear_position(self):
        self.position = None
        if os.path.exists(self.position_state_file_path):
            os.remove(self.position_state_file_path)

    def get_position(self) -> Position | None:
        return self.position

    def _dump_position(self, file_path):
        if not self.position:
            self.logger.warning("No position to dump.")
            return
        with open(file=file_path, mode="w", encoding="utf-8") as f:
            json.dump(obj=self.position.to_dict(), fp=f, indent=4)
        # self.logger.debug(message=f"Position dumped to {file_path}")

    def _dump_position_record(self):
        _dt = get_datetime_now_string_gmt_plus_7(format='%Y%m%d_%H%M%S')
        file_name = POSITION_RECORD_FILENAME_TEMPLATE.format(
            run_id=self.bot_config.run_id, dt=_dt)
        file_path = os.path.join(POSITION_RECORDS_DIR, file_name)
        self._dump_position(file_path=file_path)

    def dump_position_state(self):
        self._dump_position(file_path=self.position_state_file_path)

    def read_position_state(self):
        try:
            if os.path.exists(self.position_state_file_path):
                with open(file=self.position_state_file_path, mode='r', encoding="utf-8") as f:
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
