from commons.custom_logger import CustomLogger
from core.bot_runner import BotRunner
from models.enum.position_side import PositionSide
from models.enum.trade_signal import TradeSignal

class ForwardtestEngine:
    def __init__(self, bot_runner):
        self.name = f'{self.__class__.__name__}_{bot_runner.bot_fullname}'
        self.logger = CustomLogger(name=self.name)
        self.logger.debug(f'Initializing {self.__class__.__name__}')

        self.bot_runner: BotRunner = bot_runner

        self.start_candle = int(self.bot_runner.bot.candle_for_indicator)
        self.initial_balance = float(self.bot_runner.run.initial_balance)
        self.balance = self.initial_balance
        self.pnl = 0.0
        self.winning_positions = 0
        self.positions = []

        self.running: bool = True


    def run(self):
        self.logger.debug(
            f'Starting forwardtest for {self.bot_runner.bot_fullname}')
    
        # Simulate the backtest process
        klines = self.bot_runner.trade_engine.fetch_klines(
            self.bot_runner.bot.symbol,
            self.bot_runner.bot.timeframe,
            self.bot_runner.bot.timeframe_limit
        )
        klines_with_strategy_df = self.bot_runner.strategy_engine.init(klines)
        last_row = klines_with_strategy_df.iloc[-1]

        signal = self.bot_runner.strategy_engine.on_update(last_row)

# EOF
