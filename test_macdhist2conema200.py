import subprocess
import os
import time

subprocess.run(
    f'PYTHONPATH="{os.path.dirname(os.path.abspath(__file__))}"',
    shell=True
)


import commons.common as common
from commons.custom_logger import CustomLogger
from strategies.etc import macd
from models.enum.macd_stage import MACDStage
from models.enum.trade_signal import TradeSignal
from models.enum.position_side import PositionSide
from strategies.etc import helper
from copy import deepcopy
from models.enum.run_mode import RunMode

class Bot:
    symbol: str = ''
    timeframe: int = 1500
    leverage: int = 1
    quantity: float = 0


class Run:
    run_id: str = ''


class BotRunner:
    bot_fullname: str = ''
    bot: Bot = None  # type: ignore
    run: Run = None  # type: ignore


class Position:
    side: PositionSide
    entry_price: float
    close_price: float
    open_time = None
    close_time = None


class TradeSignalReason:
    trade_signal: TradeSignal
    reason: str


class PositionHandler():
    def __init__(self, bot_runner, trade_engine) -> None:
        self.bot_runner = bot_runner
        self.trade_engine = trade_engine
        self.position: Position = None # type: ignore
        self.logger: CustomLogger = None # type: ignore
    
    def open_position(self, mode, signal_reason, current_price, current_time):
        self.logger.debug(f'{current_time}  Opening with signal: {signal_reason.trade_signal}, {signal_reason.reason}')
        _direction = PositionSide.LONG if signal_reason == TradeSignal.BUY else PositionSide.SHORT
        self.logger.debug(f'{current_time}  Opening {_direction.value} Position')

        self.position = Position()
        self.position.side = _direction

        if mode == RunMode.LIVE:
            _order = self.trade_engine.place_order(
                symbol=self.bot_runner.bot.symbol,
                order_side=signal_reason.value,
                order_type='MARKET',
                quantity=self.bot_runner.bot.quantity,
                reduce_only=False
            )
            _dt = common.get_datetime_now_gmt_plus_7()
            time.sleep(2) # wait for biance to process order

            _position = self.trade_engine.get_position(symbol=self.bot_runner.bot.symbol)
            self.position.entry_price = _position['entry_price']
            self.position.open_time = _dt # type: ignore
        elif mode == RunMode.BACKTEST:
            self.position.entry_price = current_price
            self.position.open_time = current_time
            

    def close_position(self, mode, signal_reason, current_price, current_time):
        self.logger.debug(f'{current_time}  Closing with signal: {signal_reason.trade_signal}, {signal_reason.reason}')
        _direction = PositionSide.LONG if signal_reason == TradeSignal.BUY else PositionSide.SHORT
        self.logger.debug(f'{current_time}  Closing {_direction.value} Position')

        pnl = 0

        if mode == RunMode.LIVE:
            _position = self.trade_engine.get_position(symbol=self.bot_runner.bot.symbol)
            _order = self.trade_engine.place_order(
                symbol=self.bot_runner.bot.symbol,
                order_side=signal_reason.value, # BUY, SELL
                order_type='MARKET', # LIMIT, MARKET, STOP, STOP_MARKET ...
                quantity=abs(_position["quantity"]),
                reduce_only=True
            )

            self.position.close_time = common.get_datetime_now_gmt_plus_7() # type: ignore
            self.position.close_price = _position['mark_price']
            pnl = _position['unrealized_profit']
            self.logger.debug(_position)
        elif mode == RunMode.BACKTEST:
            self.position.close_price = current_price 
            self.position.close_time = current_time
            if self.position.side == PositionSide.LONG:
                pnl = current_price - self.position.entry_price
            elif self.position == PositionSide.SHORT:
                pnl = self.position.entry_price - current_price

        self.logger.info(f'Position  {_direction.value}  |  {self.position.entry_price} -> {self.position.close_price}  |  {"+" if pnl >= 0 else ""}{pnl:.2f}')
        self.position = None # type: ignore
        return pnl


class Strategy:
    '''
    open criteria
        Long
            1. increasing positive macd histogram for 2 consecutive candles (open on 2nd candle)
            2. price above ema200
            ### 2. has 5 consecutive increasing negative candles (open on 5th candle)
        Short
            1. decreasing negative macd histogram for 2 consecutive candles (open on 2nd candle)
            2. price below ema200
            ### 2. has 5 consecutive decreasing position candles (open on 5th candle)

    close criteria
        Long
            1. macd histogram change from positive to negative
        Short
            1. macd histogram change from negative to positive
    '''

    def __init__(self, position_handler) -> None:
        self.strategy = 'macdhist2conema200'
        self.position_handler = position_handler
        self.last_state = MACDStage.ZERO
        self.logger = None


    def should_open(self, klines_df, position_handler):
        signal = TradeSignal.HOLD
        reason = 'No open condition met'

        if position_handler.position is not None:
            return

        df = macd.calculate_macd_ema(df=klines_df, ema=200, decimal=3)
        if len(df) < 3:
            return None  # Not enough data

        last_two = df.iloc[-2:]
        hist1, hist2 = last_two['histogram'].values
        price = last_two['open'].values[-1]
        ema_200 = last_two['ema_200'].values[-1]

        if hist1 > 0 and hist2 > hist1 and price > ema_200:
            signal = TradeSignal.BUY
            reason = 'Positive MACD histogram, increasing 2 candles, price > EMA200'
        elif hist1 < 0 and hist2 < hist1 and price < ema_200:
            signal = TradeSignal.SELL
            reason = 'Negative MACD histogram, decreasing 2 candles, price < EMA200'

        signal_reason: TradeSignalReason = TradeSignalReason()
        signal_reason.trade_signal = signal
        signal_reason.reason = reason
        return signal_reason
    

    def should_close(self, klines_df, position_handler):
        klines_macd_df = macd.calculate_macd_ema(df=klines_df, ema=200, decimal=3)

        # last_6_rows = klines_macd_df.iloc[-6:]  # Use last 6 candles
        # last_6_hists  = list(last_6_rows['histogram'].values)
        last_row = klines_macd_df.iloc[-1]
        last_hist = last_row['histogram']
        # last_ema200 = last_row['ema_200']

        signal_reason: TradeSignalReason = TradeSignalReason()
        signal_reason.trade_signal = TradeSignal.HOLD
        signal_reason.reason = 'MACD histogram not change'

        state = helper.detect_macd_state(value=last_hist)

        # look for close oppty
        if position_handler.position is None:
            signal_reason.reason = 'No openned position'
            return signal_reason

        if self.last_state == MACDStage.NEGATIVE and state == MACDStage.POSITIVE:
            signal_reason.trade_signal = TradeSignal.BUY
            signal_reason.reason = 'MACD histogram state change Neg -> Pos'
        elif self.last_state == MACDStage.POSITIVE and state == MACDStage.NEGATIVE:
            signal_reason.trade_signal = TradeSignal.SELL
            signal_reason.reason = 'MACD histogram state change Pos -> Neg'

        return signal_reason   # don't close, no need to open new position


class TestBotMACDHist2ConEMA200:
    def __init__(self, mode, trade_engine, symbol, timeframe, leverage, quantity) -> None:
        self.mode = mode
        self.trade_engine = trade_engine

        bot = Bot()
        bot.symbol = symbol
        bot.timeframe = timeframe
        bot.leverage = leverage
        bot.quantity = quantity

        run = Run()
        run.run_id = common.get_datetime_now_string_gmt_plus_7('%Y%m%d_%H%M%S')

        bot_runner = BotRunner()
        bot_runner.bot = bot  # type: ignore
        bot_runner.run = run  # type: ignore
        self.bot_runner = bot_runner

        self.position_handler = PositionHandler(bot_runner=self.bot_runner, trade_engine=self.trade_engine)
        self.strategy_engine = Strategy(position_handler=self.position_handler)
        
        log_name = f'{run.run_id}_{self.strategy_engine.strategy}_{symbol}_{timeframe}.log'
        self.logger = CustomLogger(name=self.__class__.__name__, log_filename=log_name)

        self.position_handler.logger = self.logger  # type: ignore
        self.strategy_engine.logger = self.logger   # type: ignore
        self.trade_engine.logger = self.logger    # type: ignore


        self.logger.info(f'Starting Bot...')
        self.logger.info(f'Strategy:   { self.strategy_engine.strategy}')
        self.logger.info(f'Symbol:     {symbol}')
        self.logger.info(f'Timeframe:  {timeframe}')

    def run(self, klines_df):
        # try:

        pnl = 0
        last_row = klines_df.iloc[-1]
        current_price = last_row['open']
        current_time = last_row['open_time']

        # looking for closing
        if self.position_handler.position is not None:
            close_signal_reason: TradeSignalReason = self.strategy_engine.should_close(klines_df=klines_df, position_handler=self.position_handler) # type: ignore
            if close_signal_reason.trade_signal != TradeSignal.HOLD:
                pnl = self.position_handler.close_position(mode=self.mode, signal_reason=close_signal_reason, current_price=current_price, current_time=current_time) # type: ignore

        # logking for opening
        if self.position_handler.position is None:
            open_signal_reason: TradeSignalReason = self.strategy_engine.should_open(klines_df, self.position_handler) # type: ignore
            if open_signal_reason.trade_signal != TradeSignal.HOLD:
                self.position_handler.open_position(mode=self.mode, signal_reason=open_signal_reason, current_price=current_price, current_time=current_time) # type: ignore
        
        return pnl
        # except Exception as e:
        #     self.logger.error_e("Error in run loop", e)


'''
macd start candle need to be 200
ema200 require 500 candles

'''




# EOF
