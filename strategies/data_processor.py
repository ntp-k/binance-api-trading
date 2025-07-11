import pandas as pd


def calculate_macd(df, fast=12, slow=26, signal=9, decimal=-1):
    df['ema_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=slow, adjust=False).mean()
    df['macd'] = df['ema_fast'] - df['ema_slow']
    df['signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
    df['histogram'] = df['macd'] - df['signal']
    if decimal != -1:
        df['histogram'] = df['histogram'].round(decimal)
    return df


def calculate_ema(df, ema=200, decimal=-1):
    ema_name = f'ema_{ema}'
    df[ema_name] = df['close'].ewm(span=ema, adjust=False).mean()
    if decimal != -1:
        df[ema_name] = df[ema_name].round(decimal)
    return df


def calculate_rsi(df, period=14, decimal=-1):
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    if decimal != -1:
        df['rsi'] = df['rsi'].round(decimal)
    return df


def calculate_atr(df, period=14, decimal=-1):
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()

    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    # First ATR = SMA of first `period` TRs
    atr = tr.rolling(window=period).mean()
    atr.iloc[period:] = tr.iloc[period:].ewm(alpha=1/period, adjust=False).mean()

    df['atr'] = atr

    if decimal != -1:
        df['atr'] = df['atr'].round(decimal)

    return df

# EOF
