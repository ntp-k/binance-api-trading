import os
import json
import requests
import pandas as pd
from datetime import datetime
import commons.common as common

# ---- Configuration ----
SYMBOL = 'SOLUSDT'
INTERVAL = '5m'
LIMIT = 5
STATE_FILE = '_private_last_hist_state.json'
LOG_FILE = 'hist_states.log'
LINE_NOTIFY_TOKEN = os.getenv("LINE_NOTIFY_TOKEN")
binance_cred = common.load_binance_cred()

# ---- Fetch and Calculate MACD ----
def fetch_klines(symbol, interval, limit=100):
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
    df['close'] = df['close'].astype(float)
    return df

def calculate_macd(df, fast=12, slow=26, signal=9):
    df['ema_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=slow, adjust=False).mean()
    df['macd'] = df['ema_fast'] - df['ema_slow']
    df['signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
    df['histogram'] = (df['macd'] - df['signal']).round(2)
    return df

# ---- Notification & Logging ----
'''
def send_line_notify(message):
    url = 'https://notify-api.line.me/api/notify'
    headers = {"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}
    data = {"message": message}
    requests.post(url, headers=headers, data=data)
'''

def log_state(state, value):
    with open(LOG_FILE, 'a') as log:
        log.write(f"{datetime.now().isoformat()} | {value} | {state.upper()}\n")

def load_last_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f).get("state")
    return None

def save_last_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump({"state": state}, f)

# ---- Main Execution ----
try:
    df = fetch_klines(SYMBOL, INTERVAL, LIMIT)
    df = calculate_macd(df)
    latest_hist = df['histogram'].iloc[-1]

    current_state = (
        "positive" if latest_hist > 0 else
        "negative" if latest_hist < 0 else
        "zero"
    )

    previous_state = load_last_state()
    log_state(current_state, latest_hist)

    if previous_state and current_state != previous_state and current_state in ["positive", "negative"]:
        message = f"📊 MACD histogram crossed from {previous_state.upper()} to {current_state.upper()}.\nCurrent value: {latest_hist}"
        # send_line_notify(message)

    save_last_state(current_state)

except Exception as e:
    with open(LOG_FILE, 'a') as log:
        log.write(f"{datetime.now().isoformat()} | ERROR | {str(e)}\n")
