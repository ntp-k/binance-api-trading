import os
from commons.custom_logger import CustomLogger
from core.bot_config import BotConfig
from core.bot_run_mode import BotRunMode

from strategies.strategies import Strategies
from trade_engine.binance.binance_client import BinanceClient
from trading.trading_position import TradingPosition
from trading.future_trading_types import PositionSide


# from strategies import get_strategy
# from modes import run_backtest, run_simulation, run_live


class BotRunner:
    def __init__(self, bot_config: BotConfig):
        self.logger = CustomLogger(name=BotRunner.__name__)
        self.logger.debug('Initializing bot runner')
        self.config: BotConfig = bot_config
        self.bot_fullname = f'{bot_config.run_mode}|{bot_config.strategy}|{bot_config.symbol}|{bot_config.timeframe}'

        self.data_source = BinanceClient()



        # self.trade_engine = None
        # self.init_trade_engine(self.config.run_mode)

        self.strategy_engine = self.init_strategy(self.config.strategy)
        self.logger.debug(f'Loaded strategy: {self.strategy_engine.__class__}')

        self.bot_engine = self.init_bot_engine(self.config.run_mode)
        self.logger.debug(f'Loaded bot engine: {self.bot_engine.__class__}')

        self.trading_position: TradingPosition = TradingPosition.from_dict({
            'symbol': self.config.symbol,
            'position_side': PositionSide.ZERO,
            'entry_price': 0.0,
            'quantity': 0.0,
            'unrealized_profit': 0.0,
            'realized_profit': 0.0,
            'open_time': None,
        })
    
    def init_strategy(self, strategy):
        if strategy == Strategies.MACD_BASIC:
            from strategies.macd.macd_strategy import MACDStrategy
            return MACDStrategy(self)



    def init_bot_engine(self, run_mode):
        if run_mode == BotRunMode.LIVE:
            from core.bot_engine_live import BotEngineLive
            return BotEngineLive()
        elif run_mode == BotRunMode.FORWARDTEST:
            from core.bot_engine_forwardtest import BotEngineForwardtest
            return BotEngineForwardtest()
        else:
            from core.bot_engine_backtest import BotEngineBacktest
            return BotEngineBacktest(self, self.strategy_engine)



    
    # def init_trade_engine(self, run_mode):
    #     if run_mode == BotRunMode.LIVE:
    #         self.trade_engine = self.data_source  # Binance Client
    #     elif run_mode == BotRunMode.SIMULATION:
    #         pass
    #     else:
    #         from trade_engine.backtest_trade_engine import BacktestTradeEngine
    #         self.trade_engine = BacktestTradeEngine()

    #     self.logger.debug(
    #         f'Loaded trade engine: {self.trade_engine.__class__}')



    def run(self):
        self.bot_engine.run(bot_runner=self) # type: ignore
        
        
        # self.logger.debug(f'Current Position: {current_position}')
        # signal = self.strategy_engine.apply_strategy(klines=klines, current_position=current_position)
        

    def run_backtest(self):
        pass

    def run_simulation(self):
        pass

    def run_live(self):
        pass


if __name__ == "__main__":
    pass

# EOF
