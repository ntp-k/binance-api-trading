from datetime import datetime

from commons.custom_logger import CustomLogger
from core.bot_config import BotConfig
from models.run_mode import RunMode
from models.strategies import Strategies
from trade_engine.binance.binance_client import BinanceClient
from models.trading_position import TradingPosition
from data_adapters.base_adapter import BaseAdapter
from models.bot_run import BotRun

class BotRunner:
    def __init__(self, run_mode: RunMode, bot_config: BotConfig, data_adapter: BaseAdapter, binace_client: BinanceClient):
        self.bot_fullname = f'{run_mode.value}|{bot_config.strategy.value}|{bot_config.symbol}|{bot_config.timeframe}'
        self.bot_enging_fullname = f'{BotRunner.__name__}_{self.bot_fullname}'
        self.logger = CustomLogger(name=self.bot_enging_fullname)

        self.logger.debug('Initializing bot runner')

        self.run_mode: RunMode = run_mode
        self.config: BotConfig = bot_config
        self.data_dapter: BaseAdapter = data_adapter
        self.binace_client: BinanceClient = binace_client

        self.bot_run: BotRun = self.create_bot_run()
        self.logger.debug(f'Initialized bot run: {self.bot_run}')

        self.strategy_engine = self.init_strategy(self.config.strategy)
        self.logger.debug(f'Loaded strategy: {self.strategy_engine.__class__}')

        self.bot_engine = self.init_bot_engine(run_mode)
        self.logger.debug(f'Loaded bot engine: {self.bot_engine.__class__}')

        self.trading_position: TradingPosition = TradingPosition.mock(self.config.symbol)


    def create_bot_run(self):
        try:

            bot_run: BotRun = BotRun.from_dict({
                'config_id': int(self.config.config_id),
                'run_mode': self.run_mode,
                'start_time': datetime.now(),
                'initial_balance': float(self.config.param_2), # type: ignore
                'is_closed': False,
            })
            run_id = self.data_dapter.insert_bot_run(bot_run) # type: ignore
            bot_run.run_id = run_id
            return bot_run
        except Exception as e:
            self.logger.error_e(f'Error creating bot run to database', e)
            raise e 

    def update_bot_run(self, bot_run: BotRun):

        self.logger.debug(f'Updating bot run {bot_run.run_id} to database')

        try:
            self.data_dapter.update_bot_run(bot_run) # type: ignore
        except Exception as e:
            self.logger.error_e(f'Error updateing bot run {bot_run.run_id} to database:', e)
            raise e

    def init_strategy(self, strategy):
        try:
            self.logger.debug(f'Initializing strategy: {strategy}')
            if strategy == Strategies.MACDHIST:
                from strategies.macdhist.macdhist import MACDHistStrategy
                return MACDHistStrategy(self)
        except ImportError as e:
            self.logger.error_e(f'Failed to initialize strategy {strategy.value}:', e)
            raise e
        except Exception as e:
            self.logger.error_e(f'Unexpected error initializing strategy {strategy.value}:', e)
            raise e

    def init_bot_engine(self, run_mode):
        try:
            self.logger.debug(f'Initializing bot engine for run mode: {run_mode.value}')
            if run_mode == RunMode.LIVE:
                from core.engines.live_engine import LiveEngine
                return LiveEngine()
            elif run_mode == RunMode.FORWARDTEST:
                from core.engines.forwardtest_engine import ForwardtestEngine
                return ForwardtestEngine()
            else:
                from core.engines.backtest_engine import BacktestEngine
                return BacktestEngine(self, self.strategy_engine)
        except ImportError as e:
            self.logger.error_e(f'Failed to initialize bot engine for run mode {run_mode.value}:', e)
            raise e
        except Exception as e:
            self.logger.error_e(f'Unexpected error initializing bot engine for run mode {run_mode.value}:', e)
            raise e


    def close_position(self, position: TradingPosition):
        pass

    def open_position(self, position: TradingPosition):
        pass


    def run(self):
        try:
            self.logger.info(f'Starting bot runner for {self.bot_fullname}')
            self.bot_run: BotRun = self.bot_engine.run() # type: ignore

            self.update_bot_run(self.bot_run)
            self.logger.info(f'Bot runner for {self.bot_fullname} completed successfully')
    
            return self.bot_run

        except Exception as e:
            self.logger.error_e(f'Error running bot {self.bot_fullname}:', e)
            raise e


if __name__ == "__main__":
    pass

# EOF
