import subprocess
import os
import time

subprocess.run(
    f'PYTHONPATH="{os.path.dirname(os.path.abspath(__file__))}"',
    shell=True
)


import commons.common as common
from commons.custom_logger import CustomLogger
from trade_engine.binance.binance_client import BinanceClient
from strategies.etc import macd
from models.enum.macd_stage import MACDStage
from models.enum.trade_signal import TradeSignal
from models.enum.position_side import PositionSide
from strategies.etc import helper


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
    open_time: str
    close_time: str


class Signal:
    trade_signal: TradeSignal
    reason: str


class PositionHandler():
    def __init__(self, bot_runner, trade_engine) -> None:
        self.bot_runner = bot_runner
        self.trade_engine: BinanceClient = trade_engine
        self.position = None
        self.logger: CustomLogger = None # type: ignore
    
    def open_position(self):
        pass

    def close_position(self, order_side=None):
        self.logger.debug(f'Closing Position')
        _position = self.trade_engine.get_position(symbol=symbol)
        self.logger.debug(_position)

        

        # _order = self.trade_engine.place_order(
        #     symbol=symbol,
        #     order_side=order_side.value, # BUY, SELL
        #     order_type='MARKET', # LIMIT, MARKET, STOP, STOP_MARKET ...
        #     quantity=abs(_position["position_amt"]),
        #     reduce_only=True
        # )



        

        






class Strategy:
    def __init__(self, position_handler) -> None:
        self.strategy = 'macdhist2conema200'
        self.position_handler = position_handler
        self.last_state = MACDStage.ZERO
        self.logger = None



    def should_open(self):
        pass

    def should_close(self, klines_df, position_handler):
        klines_macd_df = macd.calculate_macd_ema(df=klines_df, ema=200, decimal=3)

        last_6_rows = klines_macd_df.iloc[-6:]  # Use last 6 candles
        last_6_hists  = list(last_6_rows['histogram'].values)
    
        last_row = last_6_rows.iloc[-1]
        last_hist = last_row['histogram']
        last_ema200 = last_row['ema_200']

        signal: Signal = Signal()
        signal.trade_signal = TradeSignal.HOLD
        signal.reason = 'MACD Hist Same'

        state = helper.detect_macd_state(value=last_hist)

        # look for close oppty
        if position_handler.position is not None:
            if self.last_state == MACDStage.NEGATIVE and state == MACDStage.POSITIVE:
                signal.trade_signal = TradeSignal.BUY
                signal.reason = 'MACD Hist Neg -> Pos'
            elif self.last_state == MACDStage.POSITIVE and state == MACDStage.NEGATIVE:
                signal.trade_signal = TradeSignal.SELL
                signal.reason = 'MACD Hist Pos -> Neg'
            return signal   # don't close, no need to open new position
    

    




class TestBotMACDHist2ConEMA200:
    def __init__(self, symbol, timeframe, leverage, quantity) -> None:
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

        self.binance_client = BinanceClient()
        self.position_handler = PositionHandler(bot_runner=self.bot_runner, trade_engine=self.binance_client)
        self.strategy_engine = Strategy(position_handler=self.position_handler)
        
        log_name = f'{run.run_id}_{self.strategy_engine.strategy}_{symbol}_{timeframe}.log'
        self.logger = CustomLogger(name=self.__class__.__name__, log_filename=log_name)

        self.position_handler.logger = self.logger  # type: ignore
        self.strategy_engine.logger = self.logger   # type: ignore
        self.binance_client.logger = self.logger    # type: ignore

        self.binance_client.init()

        self.logger.info(f'Starting Bot...')
        self.logger.info(f'Strategy:   { self.strategy_engine.strategy}')
        self.logger.info(f'Symbol:     {symbol}')
        self.logger.info(f'Timeframe:  {timeframe}')

    def run(self):
        # try:

        df = self.binance_client.fetch_klines(symbol=self.bot_runner.bot.symbol, timeframe=self.bot_runner.bot.timeframe, timeframe_limit=1000)
        close_signal: Signal = self.strategy_engine.should_close(df, self.position_handler) # type: ignore
        
        if close_signal.trade_signal == TradeSignal.HOLD:
            return # skip
        
        # close position
        if self.position_handler.position is not None:
            self.position_handler.close_position(order_side=close_signal.trade_signal)
        
        
        # except Exception as e:
        #     self.logger.error_e("Error in run loop", e)




def main(symbol, timeframe, leverage, quantity):
    bot = TestBotMACDHist2ConEMA200(
        symbol=symbol,
        timeframe=timeframe,
        leverage=leverage,
        quantity=quantity
    )

    while True:
        bot.run()
        time.sleep(30)


if __name__ == "__main__":
    strategy = 'macdhist2con'
    symbol = 'BNBUSDT'
    timeframe = '15m'
    leverage = 10
    quantity = 0.01

    main(symbol=symbol, timeframe=timeframe,
         leverage=leverage, quantity=quantity)


# EOF
