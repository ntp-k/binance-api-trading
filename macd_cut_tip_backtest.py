import copy
import macd_history

# --- CONFIG ---
# SYMBOL = 'BTCUSDT'
# INTERVAL = '5m'
# LIMIT = 500
# START_BALANCE = 500_000

def detect_histogram_state_change(prev_hist: float, cur_hist: float) -> str | None:
    """
    Determine if the MACD histogram has crossed from negative to positive or vice versa.

    Returns:
        'positive' if changed from negative to positive,
        'negative' if changed from positive to negative,
        None if no state change.
    """
    if prev_hist < 0 and cur_hist > 0:
        # Histogram crossed from negative to positive
        return 'positive'
    elif prev_hist > 0 and cur_hist < 0:
        # Histogram crossed from positive to negative
        return 'negative'
    else:
        return None

def detect_histogram_trend_change(prev_trend: float, current_trend: float) -> str:
    """
    Determine if the MACD histogram trend is increasing, decreasing, or unchanged.

    Returns:
        'increasing' if current_trend > prev_trend
        'decreasing' if current_trend < prev_trend
        'unchanged' if current_trend == prev_trend
    """
    if current_trend > prev_trend:
        return 'increasing'
    elif current_trend < prev_trend:
        return 'decreasing'
    else:
        return 'unchanged'

def detect_histogram_trend(hist_diff):
    if hist_diff > 0:
        return 1
    elif hist_diff < 0:
        return -1
    else:
        return 0

class Position:
    def __init__(self, position_side):
        self.position_side = position_side # (LONG, SHORT, NONE)
        self.open_time = ''
        self.entry_price = 0
        self.close_time = ''
        self.close_price = 0
        self.pnl = 0
    
    def close_position(self):
        self.position_side = "NONE"
        self.open_time = ''
        self.entry_price = 0
        self.close_time = ''
        self.close_price = 0
        self.pnl = 0

# --- BACKTEST LOGIC ---
def backtest_macd_cut_tip(df, balance):
    position = Position(position_side='NONE')
    entry_price = 0.0
    trades = []

    prev_hist = df['histogram'].iloc[0]
    prev_trend = 0  # 1 = increasing, -1 = decreasing

    for i in range(1, len(df)):
        row = df.iloc[i]
        hist = row['histogram']
        hist_diff = hist - prev_hist

        # Determine trend change
        current_trend = detect_histogram_trend(hist_diff)
        if current_trend == 0: current_trend = prev_trend

        time_str = row['open_time'].strftime('%Y-%m-%d %H:%M:%S')
        price = row['open']

        # Entry conditions
        if position.position_side == 'NONE':
            if detect_histogram_state_change(prev_hist, hist) == 'positive':
                position.position_side = 'LONG'
                position.open_time = time_str
                position.entry_price = price
                # entry_price = price
                # trades.append(f"[{time_str}] OPEN LONG @ {price}")
            elif detect_histogram_state_change(prev_hist, hist) == 'negative':
                position.position_side = 'SHORT'
                position.open_time = time_str
                position.entry_price = price
                # entry_price = price
                # trades.append(f"[{time_str}] OPEN SHORT @ {price}")

        # Exit conditions
        elif position.position_side == 'LONG':
            if detect_histogram_trend_change(prev_trend, current_trend) == 'decreasing':
                position.close_time = time_str
                position.close_price = price
                position.pnl = (price - position.entry_price)
                balance += position.pnl
                trades.append(copy.deepcopy(position))
                position.close_position()

        elif position.position_side == 'SHORT':
            if detect_histogram_trend_change(prev_trend, current_trend) == 'increasing':
                position.close_time = time_str
                position.close_price = price
                position.pnl = (position.entry_price - price)
                balance += position.pnl
                trades.append(copy.deepcopy(position))
                position.close_position()

        prev_hist = hist
        prev_trend = current_trend

    return trades, balance


if __name__ == "__main__":

    symbol = "SOLUSDT"
    interval = "30m"
    limit = 1500
    start_balance = 500

    df = macd_history.get_macd(symbol, interval, limit)
    trades, final_balance = backtest_macd_cut_tip(df, start_balance)

    # --- OUTPUT RESULTS ---
    for t in trades:
        print(f"{str(t.open_time)} → {str(t.close_time)} | {t.position_side:<5} | "
            f"{t.entry_price:.2f} → {t.close_price:.2f} | "
            f"{'+' if t.pnl >= 0 else ''}{t.pnl:.2f} USD")

    # Final balance summary
    overall_pnl = final_balance- start_balance
    print(f"\n📊 {start_balance:,.2f} → {final_balance:,.2f} | {'+' if overall_pnl >= 0 else ''}{overall_pnl:.2f}\n")
