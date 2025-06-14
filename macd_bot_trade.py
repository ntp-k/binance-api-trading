import json
from pathlib import Path
import common
import macd_history
import google_sheet
import future_trade

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
        self.last_state = 'zero'

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

    def close_position(self, symbol) -> dict:
        dt_now_str = common.get_datetime_now_string_gmt_plus_7()

        if self.position not in ['long', 'short']:
            return {}

        order_side = 'BUY'
        if self.position == 'long':
            order_side = 'SELL'

        _position = future_trade.query_position(symbol=symbol)
        _order = future_trade.place_order(
            symbol=symbol,
            order_side=order_side, # BUY, SELL
            order_type='MARKET', # LIMIT, MARKET, STOP, STOP_MARKET ...
            quantity=_position["position_amt"],
            reduce_only=True
        )

        pnl = _position["unrealized_profit"]
        print(f"{dt_now_str} | {'CLOSE':<5} | {self.position.upper():<5} | {_position["symbol"]} | {_position["position_amt"]} | {_position["entry_price"]} | {'+' if pnl >= 0 else ''}{pnl:.2f}")

        _position['direction'] = self.position
        _position['open_time'] = self.open_time
        _position['close_time'] = dt_now_str
        _position['pnl'] = pnl

        # Reset
        self.position = None
        self.entry_price = None
        self.open_time = None
    
        return _position

    def open_position(self, symbol, quantity, direction):
        dt_now_str = common.get_datetime_now_string_gmt_plus_7()
    
        order_side = 'BUY'
        if direction == 'short':
            order_side = "SELL"

        _order = future_trade.place_order(
            symbol=symbol,
            order_side=order_side, # BUY, SELL
            order_type='MARKET', # LIMIT, MARKET, STOP, STOP_MARKET ...
            quantity=quantity,
            reduce_only=False
        )

        _position = future_trade.query_position(symbol=symbol)
        print(f"{dt_now_str} | {'OPEN':<5} | {direction.upper():<5} | {_position["symbol"]} | {_position["position_amt"]} | {_position["entry_price"]}")

        self.position = direction
        self.entry_price = _position['entry_price']
        self.open_time = dt_now_str



# --- Logging ---
def log_trade(sheet, symbol, leverage, interval, quantity, open_time, close_time, direction, entry_price, close_price, pnl):
    file_exists = Path(TRADE_LOG_FILE).exists()
    with open(TRADE_LOG_FILE, 'a') as f:
        if not file_exists:
            f.write("symbol,leverage,interval,quantity,open_time,close_time,direction,entry_price,close_price,pnl\n")
        f.write(f"{symbol},{leverage},{interval},{quantity},{str(open_time)},{str(close_time)[:-6]},{direction},{entry_price:.2f},{close_price:.2f},{pnl:.2f}\n")

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

    print(f"{str(current_time)[:-6]} | {hist_value:.4f} | {current_state}")
    log_state_change(current_time, hist_value, current_state)

    if current_state in ['positive', 'negative']:
        position_info = position.close_position(symbol)
        if position_info is None:
            wallet.update_balance(position_info['pnl'])
            # log
            log_trade(
                sheet,
                symbol.upper(),
                leverage,
                interval,
                quantity,
                str(position_info['open_time']),
                str(position_info['close_time']),
                position_info['direction'].upper(),
                position_info['entry_price'],
                position_info['mark_price'],
                position_info['pnl']
            )

        direction = 'long' if current_state == 'positive' else 'short'
        position.open_position(symbol, quantity, direction)

    position.last_state = current_state

    wallet.save()
    position.save()


if __name__ == "__main__":
    main()

# EOF
