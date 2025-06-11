import json
from pathlib import Path
import common
import macd_history

# File paths
WALLET_FILE = '_private_macd_wallet_state.json'
POSITION_FILE = '_private_macd_position_state.json'
TRADE_LOG_FILE = '_private_macd_trade_log.csv'
STATE_CHANGE_LOG = '_private_macd_state_change.log'

binance_cred = common.load_binance_cred()

# --- Wallet ---
class Wallet:
    def __init__(self, balance=500.0):
        self.balance = balance

    def update_balance(self, pnl):
        self.balance += pnl

    def to_dict(self):
        return {'balance': self.balance}

    @classmethod
    def from_file(cls):
        if Path(WALLET_FILE).exists():
            with open(WALLET_FILE, 'r') as f:
                data = json.load(f)
                return cls(balance=data.get('balance', 500.0))
        return cls()

    def save(self):
        with open(WALLET_FILE, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


# --- Position ---
class Position:
    def __init__(self):
        self.position = None
        self.entry_price = None
        self.open_time = None
        self.last_state = None

    def to_dict(self):
        return {
            'position': self.position,
            'entry_price': self.entry_price,
            'open_time': self.open_time,
            'last_state': self.last_state,
        }

    @classmethod
    def from_file(cls):
        if Path(POSITION_FILE).exists():
            with open(POSITION_FILE, 'r') as f:
                data = json.load(f)
                p = cls()
                p.position = data.get('position')
                p.entry_price = data.get('entry_price')
                p.open_time = data.get('open_time')
                p.last_state = data.get('last_state')
                return p
        return cls()

    def save(self):
        with open(POSITION_FILE, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    def close_position(self, current_price, current_time):
        if self.position == 'long':
            pnl = current_price - self.entry_price
        elif self.position == 'short':
            pnl = self.entry_price - current_price
        else:
            return 0.0

        log_trade(self.open_time, current_time, self.position.upper(), self.entry_price, current_price, pnl)

        # Reset
        self.position = None
        self.entry_price = None
        self.open_time = None
        return pnl

    def open_position(self, direction, current_price, current_time):
        self.position = direction
        self.entry_price = current_price
        self.open_time = current_time


# --- Logging ---
def log_trade(direction, entry_time, exit_time, entry_price, exit_price, pnl):
    file_exists = Path(TRADE_LOG_FILE).exists()
    with open(TRADE_LOG_FILE, 'a') as f:
        if not file_exists:
            f.write("entry_time,exit_time,direction,entry_price,exit_price,pnl\n")
        f.write(f"{str(entry_time)[:-6]},{str(exit_time)[:-6]},{direction},{entry_price:.2f},{exit_price:.2f},{pnl:.2f}\n")

def log_state_change(timestamp, hist_value, state):
    with open(STATE_CHANGE_LOG, 'a') as f:
        f.write(f"{timestamp} | {hist_value:.4f} | {state}\n")


# --- Utility ---
def detect_state(value):
    if value > 0:
        return 'positive'
    elif value < 0:
        return 'negative'
    return 'zero'


# --- MAIN (One-time execution) ---
def main():
    symbol = "SOLUSDT"
    interval = "15m"
    limit = 1500

    wallet = Wallet.from_file()
    position = Position.from_file()

    df = macd_history.get_macd(symbol, interval, limit)
    last_row = df.iloc[-1]

    current_time = str(last_row['open_time'])
    current_price = last_row['open']
    hist_value = last_row['histogram']
    current_state = detect_state(hist_value)

    print(f"{current_time} | {hist_value:.4f} | {current_state}")
    log_state_change(current_time, hist_value, current_state)

    if current_state in ['positive', 'negative'] and current_state != position.last_state:
        pnl = position.close_position(current_price, current_time)
        wallet.update_balance(pnl)

        new_position = 'long' if current_state == 'positive' else 'short'
        position.open_position(new_position, current_price, current_time)

    position.last_state = current_state

    wallet.save()
    position.save()


if __name__ == "__main__":
    main()

# EOF
