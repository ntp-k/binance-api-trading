import common
import requests
import pandas as pd


binance_cred = common.load_binance_cred()

# Constants
SYMBOL = 'SOLUSDT'
INTERVAL = '5m'  # You can change this (1m, 15m, 1d, etc.)
LIMIT = 300  # Number of candles
DECIMAL = 4

# Step 1: Get Kline (candlestick) data
def fetch_klines(symbol, interval, limit=100):
    url = 'https://fapi.binance.com/fapi/v1/klines'
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': limit
    }
    (headers, signed_params) = common.sign_request(params=params, binance_credential=binance_cred)
    response = requests.get(url, headers= headers, params=signed_params)
    data = response.json()
    df = pd.DataFrame(data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'num_trades',
        'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
    ])
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Bangkok')
    df['close'] = df['close'].astype(float)
    df['open'] = df['open'].astype(float)
    return df

# Step 2: Calculate MACD
def calculate_macd(df, fast=12, slow=26, signal=9):
    df['ema_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=slow, adjust=False).mean()
    df['macd'] = df['ema_fast'] - df['ema_slow']
    df['signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
    df['histogram'] = df['macd'] - df['signal']
    df['histogram'] = df['histogram'].round(DECIMAL)
    return df

def get_macd(symbol, interval, limit):
    df = fetch_klines(symbol, interval, limit)
    df = calculate_macd(df)
    # print(df.tail(10))
    return df


if __name__ == "__main__":
    get_macd(SYMBOL, INTERVAL, LIMIT)

# EOF
