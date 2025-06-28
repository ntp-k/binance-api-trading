from commons.custom_logger import CustomLogger
from models.bot_config import BotConfig
from models.enum.run_mode import RunMode
from trade_clients.get_trade_client import get_trade_client
import strategies.get_strategy as get_strategy

class Bot:
    # client: BaseClient
    # strategy: BaseStrategy

    def __init__(self, offline: False, bot_config: BotConfig):
        self.logger = CustomLogger(name=f'{self.__class__.__name__}:{bot_config.bot_name.replace(' ', '_')}')
        self.logger.debug(message=f'Initializing {self.__class__.__name__}')

        self.bot_config: BotConfig = bot_config

        self._init_trade_client(run_mode=bot_config.run_mode)
        self._init_entry_strategy(entry_strategy=self.bot_config.entry_strategy, dynamic_config=self.bot_config.dynamic_config)

    

    def _init_trade_client(self, run_mode: RunMode):
        try:
            self.logger.debug(message=f'Initializing trade client')
            self.trade_client = get_trade_client(run_mode=run_mode)
            klines_df = self.trade_client.fetch_klines(
                symbol=self.bot_config.symbol,
                timeframe=self.bot_config.timeframe,
                timeframe_limit=self.bot_config.timeframe_limit
            )
            print(klines_df)

            self.logger.debug(message=f'Initialized trade client {self.trade_client.__class__.__name__}')
            return self.trade_client
        except Exception as e:
            self.logger.error_e(message='Error while initializing trade client', e=e)

    def _init_entry_strategy(self, entry_strategy, dynamic_config):
        try:
            self.logger.debug(message=f'Initializing entry strategy')
            self.entry_strategy = get_strategy.get_entry(entry_strategy=entry_strategy, dynamic_config=dynamic_config)
            self.logger.debug(message=f'Initialized entry strategy {self.entry_strategy.__class__.__name__}')
            return self.entry_strategy
        except Exception as e:
            self.logger.error_e(message='Error while initializing trade client', e=e)

    # def _init_exit_strategy(self, exit_strategy, strategy_config):
    #     try:
    #         self.exit_strategy = get_trade_client(run_mode=run_mode)
    #         return self.exit_strategy
    #     except Exception as e:
    #         self.logger.error_e(message='Error while initializing trade client', e=e)




    def execute(self):
        pass
        # market_data = self.client.fetch_market()
        # position_data = self.client.fetch_position()
        # processed_data = self.strategy.process(market_data)

        # if self.strategy.should_open(processed_data, position_data):
        #     self.client.trade_buy()
        # elif self.strategy.should_close(processed_data, position_data):
        #     self.client.trade_sell()
        
        # self.client.wait()

    def run(self):
        pass
        # count = 0
        # while True:
        #     try:
        #         print(count)
        #         self.execute()
        #         count += 1
        #     except:
        #         print('Error')
        #         break

# EOF
