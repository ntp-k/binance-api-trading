"""
Technical indicator calculation functions for trading strategies.
"""
import pandas as pd
from typing import Optional

from commons.constants import (
    MACD_12,
    MACD_26,
    MACD_9,
    EMA_200,
    RSI_14,
    ATR_14
)


def calculate_macd(
    df: pd.DataFrame,
    fast: int = MACD_12,
    slow: int = MACD_26,
    signal: int = MACD_9,
    decimal: int = -1
) -> pd.DataFrame:
    """
    Calculate MACD (Moving Average Convergence Divergence) indicator.
    
    Args:
        df: DataFrame with 'close' column
        fast: Fast EMA period
        slow: Slow EMA period
        signal: Signal line period
        decimal: Decimal places for rounding (-1 for no rounding)
    
    Returns:
        DataFrame with added MACD columns
    """
    df['ema_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=slow, adjust=False).mean()
    df['macd'] = df['ema_fast'] - df['ema_slow']
    df['signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
    df['histogram'] = df['macd'] - df['signal']
    
    if decimal != -1:
        df['histogram'] = df['histogram'].round(decimal)
    
    return df


def calculate_ema(
    df: pd.DataFrame,
    ema: int = EMA_200,
    decimal: int = -1
) -> pd.DataFrame:
    """
    Calculate Exponential Moving Average (EMA).
    
    Args:
        df: DataFrame with 'close' column
        ema: EMA period
        decimal: Decimal places for rounding (-1 for no rounding)
    
    Returns:
        DataFrame with added EMA column
    """
    ema_name = f'ema_{ema}'
    df[ema_name] = df['close'].ewm(span=ema, adjust=False).mean()
    
    if decimal != -1:
        df[ema_name] = df[ema_name].round(decimal)
    
    return df


def calculate_rsi(
    df: pd.DataFrame,
    period: int = RSI_14,
    decimal: int = -1
) -> pd.DataFrame:
    """
    Calculate Relative Strength Index (RSI).
    
    Args:
        df: DataFrame with 'close' column
        period: RSI period
        decimal: Decimal places for rounding (-1 for no rounding)
    
    Returns:
        DataFrame with added RSI column
    """
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


def calculate_atr(
    df: pd.DataFrame,
    period: int = ATR_14,
    decimal: int = -1
) -> pd.DataFrame:
    """
    Calculate Average True Range (ATR) - volatility indicator.
    
    Args:
        df: DataFrame with 'high', 'low', 'close' columns
        period: ATR period
        decimal: Decimal places for rounding (-1 for no rounding)
    
    Returns:
        DataFrame with added ATR column
    """
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
