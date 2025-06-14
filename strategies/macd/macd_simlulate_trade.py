import json
from pathlib import Path
import common.common as common
import macd_history
import google_sheet

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

    def close_position(self, current_price):
        if self.position == 'long':
            pnl = current_price - self.entry_price
        elif self.position == 'short':
            pnl = self.entry_price - current_price
        else:
            return 0.0
        
        position_info: dict = {
            'direction': self.position,
            'open_time': self.open_time,
            'entry_price': self.entry_price,
            'pnl': pnl
        }

        # Reset
        self.position = None
        self.entry_price = None
        self.open_time = None
    
        return position_info

    def open_position(self, direction, current_price, current_time):
        self.position = direction
        self.entry_price = current_price
        self.open_time = current_time


# --- Logging ---
def log_trade(sheet, symbol, leverage, interval, quantity, open_time, close_time, direction, entry_price, close_price, pnl):
    file_exists = Path(TRADE_LOG_FILE).exists()
    with open(TRADE_LOG_FILE, 'a') as f:
        if not file_exists:
            f.write("symbol,leverage,interval,quantity,open_time,close_time,direction,entry_price,close_price,pnl\n")
        f.write(f"{symbol},{leverage},{interval},{quantity},{str(open_time)[:-6]},{str(close_time)[:-6]},{direction},{entry_price:.2f},{close_price:.2f},{pnl:.2f}\n")

    google_sheet.log_trade_to_sheet(
            sheet,
            symbol,
            leverage,
            interval,
            quantity,
            open_time,
            close_time,
            direction,
            entry_price,
            close_price,
            pnl
        )

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
    leverage = 10
    quantity = 1
    limit = 1500

    wallet = Wallet.from_file()
    position = Position.from_file()
    sheet = google_sheet.init_google_sheet()

    df = macd_history.get_macd(symbol, interval, limit)
    last_row = df.iloc[-1]

    current_time = str(last_row['open_time'])
    current_price = last_row['open']
    hist_value = last_row['histogram']
    current_state = detect_state(hist_value)

    if current_state == position.last_state:
        wallet.save()
        position.save()
        return

    print(f"{current_time} | {hist_value:.4f} | {current_state}")
    log_state_change(current_time, hist_value, current_state)

    if current_state in ['positive', 'negative']:
        position_info = position.close_position(current_price)
        if type(position_info) != type(0.0):
            wallet.update_balance(position_info['pnl'])
            # log
            log_trade(
                sheet,
                symbol.upper(),
                leverage,
                interval,
                quantity,
                str(position_info['open_time'])[:-6],
                str(current_time)[:-6],
                position_info['direction'].upper(),
                position_info['entry_price'],
                current_price,
                position_info['pnl']
            )

        new_position = 'long' if current_state == 'positive' else 'short'
        position.open_position(new_position, current_price, current_time)

    position.last_state = current_state

    wallet.save()
    position.save()


if __name__ == "__main__":
    main()

# EOF
