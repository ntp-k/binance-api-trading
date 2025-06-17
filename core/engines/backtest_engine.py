from commons.custom_logger import CustomLogger
from models.trading_enums import TradeSignal, PositionSide
from models.trading_position import TradingPosition
from core.bot_runner import BotRunner
from commons.common import calculate_roi_metrics

class EngineBacktest:
    def __init__(self, bot_runner, strategy_engine):
        self.bot_enging_fullname = f'{EngineBacktest.__name__}_{bot_runner.bot_fullname}'
        self.logger = CustomLogger(name=self.bot_enging_fullname)

        self.logger.debug('Initializing backtest bot engine')
        
        self.bot_runner: BotRunner = bot_runner
        self.strategy_engine = strategy_engine

        self.start_candle = int(self.bot_runner.config.param_1)
        self.initial_balance = float(self.bot_runner.config.param_2)
        self.banalce = self.initial_balance
        self.positions = []

    def close_position(self, current_time, current_price):
        pnl = 0.0
        if self.bot_runner.trading_position.side == PositionSide.LONG:
            pnl = (current_price - self.bot_runner.trading_position.entry_price) * self.bot_runner.trading_position.amount

        else: # PositionSide.SHORT
            pnl = (self.bot_runner.trading_position.entry_price - current_price) * self.bot_runner.trading_position.amount

        self.bot_runner.trading_position.close(current_price, current_time)
        self.bot_runner.trading_position.unrealized_profit = pnl

        self.logger.debug(f'{current_time}  |  {"Close":<8}  |  {self.bot_runner.trading_position.side.value:<5}  |  {current_price:.2f}')
        

      
        return pnl

    def open_position(self, current_time, current_price, signal: TradeSignal):
        side = PositionSide.LONG if signal == TradeSignal.BUY else PositionSide.SHORT

        self.bot_runner.trading_position = TradingPosition.from_dict({
            'symbol': self.bot_runner.config.symbol,
            'amount': self.bot_runner.config.quantity,
            'side': side,
            'entry_price': current_price,
            'mark_price': current_price,
            'unrealized_profit': 0.0,
            'open_time': current_time
        })

        self.logger.debug(f'{current_time}  |  {"Open":<8}  |  {side.value:<5}  |  {current_price:.2f}')

    def run(self):
        self.logger.info(f'Starting backtest for {self.bot_runner.bot_fullname}')
        signal : TradeSignal = TradeSignal.HOLD
        
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
                self.logger.error(f'Error processing row {index}: {e}')
                raise e

            if signal == TradeSignal.HOLD:
                continue

            # TradeSignal.BUY or TradeSignal.SELL

            # Close existing position if any
            try:
                pnl = self.close_position(row['open_time'], row['open'])
                self.banalce += pnl
            except Exception as e:
                self.logger.error(f'Error closing position: {e}')
                self.logger.error(f'Position: {self.bot_runner.trading_position}')
                self.logger.error(f'Position: {self.bot_runner.trading_position.to_dict()}')
                raise e

            # log the position
            self.positions.append(self.bot_runner.trading_position.to_dict())
            self.logger.debug(f'{row["open_time"]}  |  {"Position":<8}  |  {self.bot_runner.trading_position.side.value:<5}  |  {self.bot_runner.trading_position.entry_price:.2f}  ->  {row["open"]:.2f}  |  {"+" if pnl >= 0 else ""}{pnl:.2f}  |  {self.banalce:.2f}\n')

            # Open new position
            try:
                self.open_position(row['open_time'], row['open'], signal)
            except Exception as e:
                self.logger.error(f'Error opening position: {e}')
                self.logger.error(f'Row data: {row.to_dict()}')
                self.logger.error(f'Signal: {signal}')
                raise e

        # Finalize the backtest
        duration = klines_with_strategy_df['open_time'].iloc[-1] - klines_with_strategy_df['open_time'].iloc[self.start_candle]
        total_trades = len(self.positions)
        win_rate = sum(1 for pos in self.positions if pos.get('unrealized_profit') >= 0) / total_trades * 100 if total_trades > 0 else 0
        roi = (self.banalce - self.initial_balance) / self.initial_balance * 100 if self.initial_balance > 0 else 0
        daily_roi, annual_roi = calculate_roi_metrics(self.initial_balance, self.banalce, duration)
        
        self.logger.debug('Backtest completed successfully')
        self.logger.info(f'Duration: {duration}')
        self.logger.info(f'Total Trades: {total_trades}')
        self.logger.info(f'Win Rate: {win_rate:.2f}%')
        self.logger.info(f'Balance: {self.initial_balance:.2f}  ->  {self.banalce:.2f}  |  ROI: {roi:.2f}%  |  Daily ROI: {daily_roi:.2f}%  |  Annual ROI: {annual_roi:.2f}%') # type: ignore
        return {
            'duration': duration,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'roi': roi,
            'daily_roi': daily_roi,
            'annual_roi': annual_roi,
            'initial_balance': self.initial_balance,
            'final_balance': self.banalce,
        }

# EOF
