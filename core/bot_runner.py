from commons.custom_logger import CustomLogger
from core.bot_config import BotConfig
from core.bot_mode import BotMode
from models.strategies import Strategies
from trade_engine.binance.binance_client import BinanceClient
from models.trading_position import TradingPosition
from data_adapters.base_adapter import BaseAdapter

class BotRunner:
    def __init__(self, bot_config: BotConfig, data_adapter: BaseAdapter, binace_client: BinanceClient):
        self.bot_fullname = f'{bot_config.run_mode.value}|{bot_config.strategy.value}|{bot_config.symbol}|{bot_config.timeframe}'
        self.bot_enging_fullname = f'{BotRunner.__name__}_{self.bot_fullname}'
        self.logger = CustomLogger(name=self.bot_enging_fullname)

        self.logger.debug('Initializing bot runner')

        self.config: BotConfig = bot_config
        self.data_dapter: BaseAdapter = data_adapter
        self.binace_client: BinanceClient = binace_client

        self.strategy_engine = self.init_strategy(self.config.strategy)
        self.logger.debug(f'Loaded strategy: {self.strategy_engine.__class__}')

        self.bot_engine = self.init_bot_engine(self.config.run_mode)
        self.logger.debug(f'Loaded bot engine: {self.bot_engine.__class__}')

        self.trading_position: TradingPosition = TradingPosition.mock(self.config.symbol)

    def init_strategy(self, strategy):
        try:
            self.logger.debug(f'Initializing strategy: {strategy}')
            if strategy == Strategies.MACD_BASIC:
                from strategies.macd.macd_strategy import MACDStrategy
                return MACDStrategy(self)
        except ImportError as e:
            self.logger.error_e(f'Failed to initialize strategy {strategy.value}:', e)
            raise e
        except Exception as e:
            self.logger.error_e(f'Unexpected error initializing strategy {strategy.value}:', e)
            raise e


    def init_bot_engine(self, run_mode):
        try:
            self.logger.debug(f'Initializing bot engine for run mode: {run_mode.value}')
            if run_mode == BotMode.LIVE:
                from core.bot_engine.bot_engine_live import BotEngineLive
                return BotEngineLive()
            elif run_mode == BotMode.FORWARDTEST:
                from core.bot_engine.bot_engine_forwardtest import BotEngineForwardtest
                return BotEngineForwardtest()
            else:
                from core.engines.backtest_engine import BotEngineBacktest
                return BotEngineBacktest(self, self.strategy_engine)
        except ImportError as e:
            self.logger.error_e(f'Failed to initialize bot engine for run mode {run_mode.value}:', e)
            raise e
        except Exception as e:
            self.logger.error_e(f'Unexpected error initializing bot engine for run mode {run_mode.value}:', e)
            raise e

    def run(self):
        try:
            self.logger.info(f'Starting bot runner for {self.bot_fullname}')
            result = self.bot_engine.run() # type: ignore
            result['bot_fullname'] = self.bot_fullname

            self.logger.info(f'Bot runner for {self.bot_fullname} completed successfully')

            return result

        except Exception as e:
            self.logger.error_e(f'Error running bot {self.bot_fullname}:', e)
            raise e


if __name__ == "__main__":
    pass

# EOF
