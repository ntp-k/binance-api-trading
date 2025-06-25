import subprocess
import os
import time

subprocess.run(
    f'PYTHONPATH="{os.path.dirname(os.path.abspath(__file__))}"',
    shell=True
)

from test_macdhist2conema200 import TestBotMACDHist2ConEMA200
from trade_engine.binance.binance_client import BinanceClient
from models.enum.run_mode import RunMode

def main_live(symbol, timeframe, leverage, quantity):
    trade_engine = BinanceClient()
    trade_engine.init()

    bot = TestBotMACDHist2ConEMA200(
        mode=RunMode.LIVE,
        trade_engine=trade_engine,
        symbol=symbol,
        timeframe=timeframe,
        leverage=leverage,
        quantity=quantity
    )

    while True:

        klines_df = trade_engine.fetch_klines(symbol=symbol, timeframe=timeframe, timeframe_limit=1000)
        bot.run(klines_df=klines_df)

        time.sleep(30)


if __name__ == "__main__":
    strategy = 'macdhist2con'
    symbol = 'BNBUSDT'
    timeframe = '15m'
    leverage = 10
    quantity = 0.01

    main_live(symbol=symbol, timeframe=timeframe,
         leverage=leverage, quantity=quantity)


# EOF
