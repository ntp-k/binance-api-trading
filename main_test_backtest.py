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

def main_backtest(symbol, timeframe, leverage, quantity, balance):
    trade_engine = BinanceClient()
    trade_engine.init()
    final_balance = balance

    bot = TestBotMACDHist2ConEMA200(
        mode=RunMode.BACKTEST,
        trade_engine=trade_engine,
        symbol=symbol,
        timeframe=timeframe,
        leverage=leverage,
        quantity=quantity
    )

    full_df = trade_engine.fetch_klines(symbol=symbol, timeframe=timeframe, timeframe_limit=1500)
    # for index, row in full_df.iterrows():
    #     current_time = row['open_time']
    #     current_price = row['open']
    #     print(index, current_time, current_price)

    window_size = 4
    for i in range(window_size+1, len(full_df)+1):
        klines_df = full_df.iloc[i - window_size:i].copy()
        final_balance += bot.run(klines_df=klines_df)
    
    print(final_balance)


if __name__ == "__main__":
    strategy = 'macdhist2con'
    symbol = 'BNBUSDT'
    timeframe = '15m'
    leverage = 10
    quantity = 0.01
    balance = 10

    main_backtest(symbol=symbol, timeframe=timeframe,
         leverage=leverage, quantity=quantity, balance=balance)


# EOF
