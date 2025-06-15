import os
from commons.custom_logger import CustomLogger
from core.bot_config import BotConfig
from core.bot_run_mode import BotRunMode

from strategies.strategies import Strategies
from trade_engine.binance.binance_client import BinanceClient

# from strategies import get_strategy
# from modes import run_backtest, run_simulation, run_live

class BotRunner:
    def __init__(self, bot_config: BotConfig):
        self.logger = CustomLogger(name=BotRunner.__name__)
        self.logger.debug('Initializing bot runner')
        self.config = bot_config

        self.strategy = self.config.strategy
        self.run_mode = self.config.run_mode
        self.symbol = self.config.symbol
        self.timeframe = self.config.timeframe
        self.data_source = BinanceClient()

        self.trade_engine = None
        self.init_trade_engine(self.run_mode)
        
        self.strategy_engine = None
        self.init_strategy(self.strategy)


    def init_trade_engine(self, run_mode):
        if run_mode == BotRunMode.LIVE:
            self.trade_engine = self.data_source # Binance Client
        elif run_mode == BotRunMode.SIMULATION:
            pass
        else:
            from trade_engine.backtest_trade_engine import BacktestTradeEngine
            self.trade_engine =  BacktestTradeEngine()

        self.logger.debug(f'Loaded trade engine: {self.trade_engine.__class__}')

    def init_strategy(self, strategy):
        if strategy == Strategies.MACD_BASIC:
            from strategies.macd.macd import MACDStrategy
            self.strategy_engine = MACDStrategy()

        self.logger.debug(f'Loaded strategy: {self.strategy_engine.__class__}')


    def run(self):
        if self.run_mode == BotRunMode.LIVE:
            self.run_live()
        elif self.run_mode == BotRunMode.SIMULATION:
            self.run_simulation()
        else:
            self.run_backtest()

    def run_backtest(self):
        pass

    def run_simulation(self):
        pass

    def run_live(self):
        pass


if __name__ == "__main__":
    pass

# EOF
