from commons.custom_logger import CustomLogger
from commons.common import calculate_roi_metrics
from core.bot_runner import BotRunner
from models.enum.positino_side import PositionSide
from models.enum.trade_signal import TradeSignal


class BacktestEngine:
    def __init__(self, bot_runner: BotRunner):
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


    def _log_position_to_datastore(self, position):
        try:
            # self.logger.debug(f'logging position to datastore')
            self.bot_runner.data_adapter.insert_trading_position(position) # type: ignore
        except Exception as e:
            self.logger.error_e(f'Error logging position to datastore', e)
            raise e


    def run(self):
        self.logger.debug(
            f'Starting backtest for {self.bot_runner.bot_fullname}')
        signal: TradeSignal = TradeSignal.HOLD

        # Simulate the backtest process
        klines = self.bot_runner.trade_engine.fetch_klines(
            self.bot_runner.bot.symbol,
            self.bot_runner.bot.timeframe,
            self.bot_runner.bot.timeframe_limit
        )

        klines_with_strategy_df = self.bot_runner.strategy_engine.init(klines)

        # ignore the last positin if any
        for index, row in klines_with_strategy_df.iloc[self.start_candle:].iterrows():
            try:
                signal = self.bot_runner.strategy_engine.on_update(row)
            except Exception as e:
                self.logger.error_e(f'Error processing row {index}', e)
                raise e

            if signal == TradeSignal.HOLD:
                continue

            # TradeSignal.BUY or TradeSignal.SELL
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

        # Finalize the backtest
        start_time = klines_with_strategy_df['open_time'].iloc[self.start_candle]
        end_time = klines_with_strategy_df['open_time'].iloc[-1]
        duration = end_time - start_time
        total_positions = len(self.positions)
        winning_positions = self.winning_positions
        losing_positions = total_positions - winning_positions
        win_rate = winning_positions / total_positions * 100 if total_positions > 0 else 0
        roi = (self.balance - self.initial_balance) / \
            self.initial_balance * 100 if self.initial_balance > 0 else 0
        daily_roi, annual_roi = calculate_roi_metrics(
            self.initial_balance, self.balance, duration)

        self.logger.debug('Backtest completed successfully')
        self.logger.info(f'Duration: {duration}')
        self.logger.info(f'Total Position: {total_positions}')
        self.logger.info(f'Win Rate: {win_rate:.2f}%')
        self.logger.info(
            # type: ignore
            f'Balance: {self.initial_balance:.2f}  ->  {self.balance:.2f}  |  ROI: {roi:.2f}%  |  Daily ROI: {daily_roi:.2f}%  |  Annual ROI: {annual_roi:.2f}%')

        return {
            'bot_id': int(self.bot_runner.bot.bot_id), # will not be updated
            'run_id': int(self.bot_runner.run.run_id), # will not be updated
            'bot_fullname': self.bot_runner.bot_fullname, # will not be updated
            'run_mode': self.bot_runner.run.mode, # will not be updated
            'start_time': start_time, # will not be updated
            'end_time': end_time,
            'duration_minutes': int(duration.total_seconds() / 60),
            'total_positions': total_positions,
            'winning_positions': winning_positions,
            'losing_positions': losing_positions,
            'win_rate': win_rate,
            'initial_balance': self.initial_balance, # will not be updated
            'final_balance': self.balance,
            'roi_percent': roi,
            'daily_roi': daily_roi,
            'annual_roi': annual_roi
        }


# EOF
