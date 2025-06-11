import os
import json
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
import common
import time

# Constants
SYMBOL = 'SOLUSDT'
INTERVAL = '5m'
LIMIT = 300
START_CAPITAL = 500
STATE_FILE = 'live_state.json'
LOG_FILE = 'live_trades.log'

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

def load_state():
    if Path(STATE_FILE).exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {
        'last_open_time': None,  # Add this line
        'last_state': None,
        'position': None,
        'entry_price': None,
        'entry_time': None,
        'capital': START_CAPITAL
    }

def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, default=str)

def log_trade(entry_time, exit_time, position, entry_price, exit_price, pnl):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{entry_time} → {exit_time} | {position:<5} | Entry: {entry_price:.2f} → "
                f"Exit: {exit_price:.2f} | PnL: {'+' if pnl >= 0 else ''}{pnl:.2f} USD\n")
        print(f"{entry_time} → {exit_time} | {position:<5} | Entry: {entry_price:.2f} → "
                f"Exit: {exit_price:.2f} | PnL: {'+' if pnl >= 0 else ''}{pnl:.2f} USD\n")
        
# --- MAIN ---

while True:
    time.sleep(10)


    state = load_state()
    
    df = fetch_klines(SYMBOL, INTERVAL, LIMIT)

    current_open_time = str(df.iloc[-1]['open_time'])
    # Skip processing if same candle
    if current_open_time == state.get('last_open_time'):
        continue  # Nothing new to process

    df = calculate_macd(df)
    last_row = df.iloc[-1]
    

    current_time = str(last_row['open_time'])
    current_price = last_row['open']
    hist_value = last_row['histogram']
    current_state = detect_state(hist_value)
    print(f"{last_row['open_time']} | {hist_value} | {current_state}")

    if current_state in ['positive', 'negative'] and current_state != state['last_state']:
        # Close previous trade if any
        if state['position'] == 'long':
            pnl = (current_price - float(state['entry_price']))
            state['capital'] += pnl
            log_trade(state['entry_time'], current_time, 'LONG', float(state['entry_price']), current_price, pnl)
        elif state['position'] == 'short':
            pnl = (float(state['entry_price']) - current_price) 
            state['capital'] += pnl
            log_trade(state['entry_time'], current_time, 'SHORT', float(state['entry_price']), current_price, pnl)

        # Open new simulated position
        new_position = 'long' if current_state == 'positive' else 'short'
        state.update({
            'position': new_position,
            'entry_price': current_price,
            'entry_time': current_time,
            'last_state': current_state
        })
    else:
        # No state change
        state['last_state'] = current_state

    # Save updated state
    state['last_open_time'] = current_open_time
    save_state(state)