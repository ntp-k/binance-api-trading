from core.bot_runner import BotRunner
from commons.custom_logger import CustomLogger
from commons.common import calculate_roi_metrics
from models.trading_enums import TradeSignal, PositionSide
from models.trading_position import TradingPosition
from models.bot_run import BotRun


class BacktestEngine:
    def __init__(self, bot_runner, strategy_engine):
        self.bot_enging_fullname = f'{BacktestEngine.__name__}_{bot_runner.bot_fullname}'
        self.logger = CustomLogger(name=self.bot_enging_fullname)

        self.logger.debug('Initializing backtest bot engine')

        self.bot_runner: BotRunner = bot_runner
        self.strategy_engine = strategy_engine

        self.start_candle = int(self.bot_runner.config.param_1)
        self.initial_balance = float(self.bot_runner.config.param_2)
        self.balance = self.initial_balance
        self.positions = []

    def close_position(self, current_time, current_price):
        self.bot_runner.trading_position.close(current_price, current_time)
        self.logger.debug(
            f'{current_time}  |  {"Close":<8}  |  {self.bot_runner.trading_position.side.value:<5}  |  {current_price:.2f}')
        return self.bot_runner.trading_position

    def open_position(self, current_time, current_price, signal: TradeSignal):
        side = PositionSide.LONG if signal == TradeSignal.BUY else PositionSide.SHORT
        self.bot_runner.trading_position = TradingPosition.from_dict({
            'run_id': self.bot_runner.bot_run.run_id,
            'is_closed': False,
            'entry_price': current_price,
            'open_time': current_time,
            'symbol': self.bot_runner.config.symbol,
            'amount': self.bot_runner.config.quantity,
            'side': side,
            'mark_price': 0.0,
            'unrealized_profit': 0.0
        })
        self.logger.debug(
            f'{current_time}  |  {"Open":<8}  |  {side.value:<5}  |  {current_price:.2f}')
        self.bot_runner.trading_position

    def log_position_to_db(self, position: TradingPosition):
        try:
            self.logger.debug(f'logged position to database')
            self.bot_runner.data_dapter.insert_trading_position(position) # type: ignore
        except Exception as e:
            self.logger.error_e(f'Error logging position to database for bot run: {self.bot_runner.bot_run.run_id}', e)
            raise e

    def run(self):
        self.logger.info(
            f'Starting backtest for {self.bot_runner.bot_fullname}')
        signal: TradeSignal = TradeSignal.HOLD

        # Simulate the backtest process
        klines = self.bot_runner.binace_client.fetch_klines(
            self.bot_runner.config.symbol,
            self.bot_runner.config.timeframe,
            self.bot_runner.config.timeframe_limit
        )

        klines_with_strategy_df = self.strategy_engine.init(klines)

        # ignore the last positin if any
        for index, row in klines_with_strategy_df.iloc[self.start_candle:].iterrows():
            try:
                signal = self.strategy_engine.on_update(row)
            except Exception as e:
                self.logger.error_e(f'Error processing row {index}', e)
                raise e

            if signal == TradeSignal.HOLD:
                continue

            # TradeSignal.BUY or TradeSignal.SELL
            pnl = 0.0

            # Close existing position if any
            try:
                position = self.close_position(row['open_time'], row['open'])

                if position.side != PositionSide.ZERO:
                    self.log_position_to_db(position=position)
                pnl = position.pnl
                self.balance += pnl  # type: ignore
            except Exception as e:
                self.logger.error_e(f'Error closing position', e)
                self.logger.error(
                    f'Position: {self.bot_runner.trading_position}')
                self.logger.error(
                    f'Position: {self.bot_runner.trading_position.to_dict()}')
                raise e

            # log the position
            self.positions.append(self.bot_runner.trading_position.to_dict())
            self.logger.debug(f'{row["open_time"]}  |  {"Position":<8}  |  {self.bot_runner.trading_position.side.value:<5}  |  {self.bot_runner.trading_position.entry_price:.2f}  ->  {row["open"]:.2f}  |  {"+" if pnl >= 0 else ""}{pnl:.2f}  |  {self.balance:.2f}\n')  # type: ignore

            # Open new position
            try:
                self.open_position(row['open_time'], row['open'], signal)
            except Exception as e:
                self.logger.error_e(f'Error opening position', e)
                self.logger.error(f'Row data: {row.to_dict()}')
                self.logger.error(f'Signal: {signal}')
                raise e

        # Finalize the backtest
        start_time = klines_with_strategy_df['open_time'].iloc[self.start_candle]
        end_time = klines_with_strategy_df['open_time'].iloc[-1]
        duration = end_time - start_time
        total_positions = len(self.positions)
        winning_positions = sum(1 for pos in self.positions if pos.get('pnl', 0) >= 0)
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

        print(start_time, end_time)
        return BotRun.from_dict({
            'run_id': self.bot_runner.bot_run.run_id, # will not be updated
            'config_id': int(self.bot_runner.config.config_id), # will not be updated
            'bot_fullname': self.bot_runner.bot_fullname, # will not be updated
            'run_mode': self.bot_runner.run_mode, # will not be updated
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
            'annual_roi': annual_roi,
            'is_closed': True
        })


# EOF
