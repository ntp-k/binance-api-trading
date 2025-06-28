
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
    df['ema_200'] = df['close'].ewm(span=ema, adjust=False).mean()
    if decimal != -1:
        df['histogram'] = df['histogram'].round(decimal)
    return df

# EOF
