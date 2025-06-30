from commons.custom_logger import CustomLogger
from models.bot_config import BotConfig
from models.enum.run_mode import RunMode
from trade_clients.get_trade_client import get_trade_client
from models.enum.trade_client import TradeClient
import strategies.get_strategy as get_strategy
from abstracts.base_trade_client import BaseTradeClient

class Bot:
    bot_config: BotConfig
    trade_client: BaseTradeClient

    def __init__(self, bot_config: BotConfig):
        self.logger = CustomLogger(name=f"{self.__class__.__name__}:{bot_config.bot_name.replace(' ', '_')}")
        self.logger.debug(message=f'Initializing {self.__class__.__name__}')

        self.bot_config: BotConfig = bot_config

        self._init_trade_client(run_mode=bot_config.run_mode, trade_client=bot_config.trade_client)
        self._init_entry_strategy(entry_strategy=self.bot_config.entry_strategy, dynamic_config=self.bot_config.dynamic_config)
        self._init_exit_strategy(exit_strategy=self.bot_config.exit_strategy, dynamic_config=self.bot_config.dynamic_config)

    

    def _init_trade_client(self, run_mode: RunMode, trade_client: TradeClient):
        try:
            self.logger.debug(message=f'Initializing trade client')
            self.trade_client: BaseTradeClient = get_trade_client(run_mode=run_mode, trade_client=trade_client) # type: ignore
            self.trade_client.set_running(running=True)
            self.logger.debug(message=f'Initialized trade client {self.trade_client.__class__.__name__}')
            return self.trade_client
        except Exception as e:
            self.logger.error_e(message='Error while initializing trade client', e=e)

    def _init_entry_strategy(self, entry_strategy, dynamic_config):
        try:
            self.logger.debug(message=f'Initializing entry strategy')
            self.entry_strategy = get_strategy.get_entry_strategy(entry_strategy=entry_strategy, dynamic_config=dynamic_config)
            self.logger.debug(message=f'Entry Strategy {self.entry_strategy.__class__.__name__}')
            return self.entry_strategy
        except Exception as e:
            self.logger.error_e(message='Error while initializing entry strategy', e=e)

    def _init_exit_strategy(self, exit_strategy, dynamic_config):
        try:
            self.logger.debug(message=f'Initializing exit strategy')
            self.exit_strategy = get_strategy.get_exit_strategy(exit_strategy=exit_strategy, dynamic_config=dynamic_config)
            self.logger.debug(message=f'Exit Strategy {self.exit_strategy.__class__.__name__}')
            return self.entry_strategy
        except Exception as e:
            self.logger.error_e(message='Error while initializing exit strategy', e=e)


    def execute(self):
        klines_df = self.trade_client.fetch_klines(
            symbol=self.bot_config.symbol,
            timeframe=self.bot_config.timeframe,
            timeframe_limit=self.bot_config.timeframe_limit
        )
        active_position_dict: dict = self.trade_client.fetch_position(symbol=self.bot_config.symbol)
        


        

    def run(self):
        while self.trade_client.running:
            self.logger.critical(self.bot_config.bot_id)
            self.execute()
            self.trade_client.wait()

# EOF
