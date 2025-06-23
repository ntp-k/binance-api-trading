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

        try:
            signal = self.bot_runner.strategy_engine.on_update(last_row)
        except Exception as e:
            self.logger.error_e(f'Error processing row {last_row}', e)
            raise e

        if signal == TradeSignal.HOLD:
            return

        pnl = 0.0

        # Close existing position if any
        try:
            position, pnl = self.bot_runner.position_handler.close_position(
                close_price=row['open'],
                close_time=row['open_time']
            )

            if pnl >= 0:
                self.winning_positions += 1

            self.balance += pnl  # type: ignore
    
            self.logger.debug(f' {position.close_time}  |  {"Position":<8}  |  {position.position_side.value:<5}  |  {position.entry_price:.2f}  ->  {position.close_price:.2f}  |  {"+" if pnl >= 0 else ""}{pnl:.2f}  |  {self.balance:.2f}\n')  # type: ignore
            self.positions.append(position.to_dict())
            self._log_position_to_datastore(position)
            
        except Exception as e:
            self.logger.error_e(f'Error closing position', e)
            self.logger.error(
                f'Position: {self.bot_runner.position_handler.position.to_dict()}')
            raise e

        # Open new position
        try:
            side = PositionSide.LONG if signal == TradeSignal.BUY else PositionSide.SHORT
            position = self.bot_runner.position_handler.open_position(side, row['open'], row['open_time'])
        except Exception as e:
            self.logger.error_e(f'Error opening position', e)
            self.logger.error(f'Position: {row.to_dict()}')
            self.logger.error(f'Signal: {signal}')
            raise e
# EOF
