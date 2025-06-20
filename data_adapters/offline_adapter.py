from datetime import datetime

from commons.custom_logger import CustomLogger
from models.position import Position
from models.run import Run

class OfflineAdapter:
    def __init__(self):
        self.logger = CustomLogger(name=self.__class__.__name__)

    def fetch_activate_bots(self) -> list:
        activate_bots = [{
            'activate_id': -1,
            'bot_id': -1,
            'mode': 'backtest',
            'initial_balance': 100,
            'created_at': datetime.now()
        }]
        self.logger.debug(
            f"Retrieved {len(activate_bots)} bot(s).")
        self.logger.debug(activate_bots)
        return activate_bots

    def fetch_bot(self, bot_id) -> dict:
        mock_bot_data = {
            "bot_id": bot_id,
            "bot_name": "Mock Bot",
            "strategy": "MACDHIST",
            "symbol": "BTCUSDT",
            "leverage": 10,
            "quantity": 1,
            "timeframe": "15m",
            "timeframe_limit": 1500,
            "candle_for_indicator": 200,
            "config": {
            },
            "created_at": "2025-06-20T15:00:00"
        }
        self.logger.debug(
            f"Retrieved bot [{bot_id}] 's data")
        self.logger.debug(mock_bot_data)
        return mock_bot_data

    def create_run(self, bot_id: int, mode: str, init_balance: float, s_time) -> int:
        self.logger.debug('Inserting Run')
        run_id = -1
        self.logger.debug(f'Created Run [{run_id}]')
        return run_id

    def update_run(self, run: Run):
        pass

    def insert_trading_position(self, position: Position):
        pass


# EOF
