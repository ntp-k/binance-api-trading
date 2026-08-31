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
from commons.custom_logger import CustomLogger
from models.enum.position_side import PositionSide


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


def resolve_sl_price(
    entry_price: float,
    position_side: PositionSide,
    quantity: Optional[float],
    decimal: int,
    dynamic_config: dict,
    logger: Optional[CustomLogger] = None
) -> float:
    """
    Resolve the stop loss price from a bot's dynamic_config.

    Two ways to express the stop, in priority order:

    - `sl_target_pct`: distance as a fraction of entry price (e.g. 0.0125 = 1.25%).
      Preferred. The risk it expresses is independent of position size, so it does
      not move when lot-size rounding changes the position's notional.
    - `sl_target_pnl`: a fixed loss in USDC. Kept for backward compatibility. The
      distance it produces is `sl_target_pnl / quantity`, so the risk it actually
      expresses drifts whenever quantity is re-rounded to the exchange step size.
      The resolved percentage is logged so that drift stays visible.

    Args:
        entry_price: Filled entry price of the opened position
        position_side: LONG or SHORT
        quantity: Actual position quantity (signed); required for `sl_target_pnl`
        decimal: Price rounding precision for the SL order
        dynamic_config: Bot's dynamic_config holding the SL setting
        logger: Optional logger for warnings and the resolved-risk line

    Returns:
        Stop loss price, or -1.0 when no stop is configured or it cannot be resolved
    """
    dynamic_config = dynamic_config or {}
    sl_target_pct = dynamic_config.get('sl_target_pct')
    sl_target_pnl = dynamic_config.get('sl_target_pnl', 0)

    if sl_target_pct is not None:
        sl_distance_pct = abs(float(sl_target_pct))
        if sl_distance_pct <= 0:
            if logger:
                logger.warning(
                    f"Skipping SL calculation - sl_target_pct is not positive: {sl_target_pct}"
                )
            return -1.0
    elif sl_target_pnl:
        if sl_target_pnl >= 0:
            if logger:
                logger.warning(
                    f"Skipping SL calculation - sl_target_pnl is non-negative: {sl_target_pnl}"
                )
            return -1.0
        if not quantity:
            if logger:
                logger.warning(
                    "sl_target_pnl is configured but quantity not available from opened position. "
                    "SL price cannot be calculated."
                )
            return -1.0
        notional = abs(quantity) * entry_price
        sl_distance_pct = abs(sl_target_pnl) / notional
        # Fixed-USDC stops hide their real risk: the same sl_target_pnl is a different
        # percentage every time quantity is re-rounded. Surface it on every entry.
        if logger:
            logger.info(
                f"SL from sl_target_pnl={sl_target_pnl}: quantity={quantity}, "
                f"notional={notional:.2f}, effective distance={sl_distance_pct*100:.3f}% "
                f"of entry. Set sl_target_pct={sl_distance_pct:.5f} to pin this risk."
            )
    else:
        return -1.0

    if position_side == PositionSide.LONG:
        sl_price = entry_price * (1 - sl_distance_pct)
    elif position_side == PositionSide.SHORT:
        sl_price = entry_price * (1 + sl_distance_pct)
    else:
        if logger:
            logger.warning(f"Unexpected position_side: {position_side}")
        return -1.0

    return round(sl_price, decimal)

# EOF
