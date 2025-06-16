from commons.custom_logger import CustomLogger
from trading.future_trading_types import TradeSignal, PositionSide
from core.bot_runner import BotRunner

class BotEngineBacktest:
    def __init__(self, bot_runner, strategy_engine):
        self.bot_enging_fullname = f'{BotEngineBacktest.__name__}_{bot_runner.bot_fullname}'
        self.logger = CustomLogger(name=self.bot_enging_fullname)
        self.logger.debug('Initializing backtest bot engine')
        
        self.bot_runner: BotRunner: = bot_runner
        self.strategy_engine = strategy_engine

        self.trade_interval = self.bot_runner.config.param_1
        self.initial_banalce = self.bot_runner.config.param_2
        self.positions = []

    def close_position(self, current_time, current_price):
        pnl = 0.0
        if self.bot_runner.trading_position.side == PositionSide.LONG:
            pnl = (current_price - self.bot_runner.trading_position.entry_price) * self.bot_runner.trading_position.amount
            self.bot_runner.trading_position.close(current_price, current_time)
            self.bot_runner.trading_position.unrealized_profit = pnl

        elif self.bot_runner.trading_position.side == PositionSide.SHORT:
            pnl = (self.bot_runner.trading_position.entry_price - current_price) * self.bot_runner.trading_position.amount
            self.bot_runner.trading_position.close(current_price, current_time)
            self.bot_runner.trading_position.unrealized_profit = pnl

        else:
            self.logger.warning('No position to close.')
        
        self.logger.info(f'Closed {self.bot_runner.trading_position.side} position  |  pnl:   {'+' if pnl >= 0 else ''}{pnl:.2f}')
        return pnl

    def open_position(self, current_time, current_price, signal: TradeSignal):
        if signal == TradeSignal.BUY:
            self.bot_runner.trading_position = self.bot_runner.trade_engine.open_position(
                symbol=self.bot_runner.config.symbol,
                side=PositionSide.LONG,
                amount=self.bot_runner.config.quantity,
                entry_price=current_price,
                mark_price=current_price,
                unrealized_profit=0.0,
                open_time=current_time
            )
            self.logger.info(f'Opened LONG position at {current_price:.2f}')

        elif signal == TradeSignal.SELL:
            self.bot_runner.trading_position = self.bot_runner.trade_engine.open_position(
                symbol=self.bot_runner.config.symbol,
                side=PositionSide.SHORT,
                amount=self.bot_runner.config.quantity,
                entry_price=current_price,
                mark_price=current_price,
                unrealized_profit=0.0,
                open_time=current_time
            )
            self.logger.info(f'Opened SHORT position at {current_price:.2f}')
        
        else:
            self.logger.error('Invalid signal to open position.')

    def run(self):
        self.logger.info(f'Starting backtest for {self.bot_runner.bot_fullname}')
        signal : TradeSignal = TradeSignal.HOLD
        
        # Simulate the backtest process
        klines = self.bot_runner.data_source.fetch_klines(
            self.bot_runner.config.symbol,
            self.bot_runner.config.timeframe,
            self.bot_runner.config.timeframe_limit
        )

        klines_with_strategy_df = self.strategy_engine.init(klines)

        for index, row in klines_with_strategy_df.iterrows():

            signal = self.strategy_engine.on_update(index, row)

            if signal == TradeSignal.HOLD:
                continue

            pnl = self.close_position(row['open_time'], row['open'])
            
            self.open_position(row['open_time'], row['open'], signal)



        self.logger.info('Backtest completed successfully')

# EOF
