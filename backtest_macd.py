import requests
import pandas as pd
from datetime import datetime
import common

SYMBOL = 'SOLUSDT'
INTERVAL = '1h'
LIMIT = 1500
START_CAPITAL = 200
binance_cred = common.load_binance_cred()

def fetch_klines(symbol, interval, limit=500):
    url = 'https://fapi.binance.com/fapi/v1/klines'
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    headers, signed_params = common.sign_request(params=params, binance_credential=binance_cred)
    response = requests.get(url, headers=headers, params=signed_params)
    response.raise_for_status()
    data = response.json()

    df = pd.DataFrame(data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'num_trades',
        'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
    ])
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    df['open_time'] = df['open_time'].dt.tz_localize('UTC').dt.tz_convert('Asia/Bangkok')
    df['open'] = df['open'].astype(float)
    df['close'] = df['close'].astype(float)
    return df

def calculate_macd(df, fast=12, slow=26, signal=9):
    df['ema_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=slow, adjust=False).mean()
    df['macd'] = df['ema_fast'] - df['ema_slow']
    df['signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
    df['histogram'] = (df['macd'] - df['signal']).round(4)
    return df

def detect_state(value):
    if value > 0:
        return 'positive'
    elif value < 0:
        return 'negative'
    return 'zero'

# Fetch and calculate MACD
df = fetch_klines(SYMBOL, INTERVAL, LIMIT)
df = calculate_macd(df)

# Simulation variables
capital = START_CAPITAL
position = None
entry_price = None
entry_time = None
last_state = None
trade_log = []

for index, row in df.iterrows():
    hist = row['histogram']
    state = detect_state(hist)

    if state in ['positive', 'negative'] and state != last_state:
        current_time = row['open_time']
        current_price = row['open']

        # Close previous position
        if position == 'long':
            pnl = (current_price - entry_price)
            capital += pnl
            trade_log.append({
                'entry_time': entry_time,
                'exit_time': current_time,
                'position': 'LONG',
                'entry_price': entry_price,
                'exit_price': current_price,
                'pnl': pnl
            })
        elif position == 'short':
            pnl = (entry_price - current_price)
            capital += pnl
            trade_log.append({
                'entry_time': entry_time,
                'exit_time': current_time,
                'position': 'SHORT',
                'entry_price': entry_price,
                'exit_price': current_price,
                'pnl': pnl
            })

        # Open new position
        if state == 'positive':
            position = 'long'
        elif state == 'negative':
            position = 'short'
        entry_price = current_price
        entry_time = current_time
        last_state = state

# Final position exit
if position:
    final_price = df.iloc[-1]['close']
    final_time = df.iloc[-1]['open_time']
    if position == 'long':
        pnl = (final_price - entry_price) 
    else:
        pnl = (entry_price - final_price) 
    capital += pnl
    trade_log.append({
        'entry_time': entry_time,
        'exit_time': final_time,
        'position': position.upper(),
        'entry_price': entry_price,
        'exit_price': final_price,
        'pnl': pnl
    })

# Print trade log summary
print(f"\n{'#' * 60}")
print(f"{'TRADE LOG':^60}")
print(f"{'#' * 60}")
for t in trade_log:
    print(f"{t['entry_time']} → {t['exit_time']} | {t['position']:<5} | "
          f"Entry: {t['entry_price']:.2f} → Exit: {t['exit_price']:.2f} | "
          f"PnL: {'+' if t['pnl'] >= 0 else ''}{t['pnl']:.2f} USD")

# Final capital summary
print(f"\n📊 Final Capital: ${capital:,.2f} (Start: ${START_CAPITAL:,.2f})")
