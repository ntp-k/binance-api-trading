"""
Fee calculator for trading operations.
Calculates fees based on order type and Binance fee structure.
"""
from typing import Dict

# Binance futures fee structure (as of 2024)
BINANCE_FEES = {
    'MAKER': 0.0000,   # 0.02% - for limit orders that add liquidity
    'TAKER': 0.0002,   # 0.04% - for market orders that take liquidity
}


def calculate_open_fee(
    order_type: str,
    entry_price: float,
    quantity: float,
    leverage: int = 1
) -> float:
    """
    Calculate fee for opening a position.
    
    Args:
        order_type: Order type ('MAKER_ONLY', 'MARKET', 'LIMIT')
        entry_price: Entry price of the position
        quantity: Position quantity
        leverage: Position leverage (default 1)
    
    Returns:
        Fee amount in quote currency
    
    Examples:
        >>> calculate_open_fee('MAKER_ONLY', 100.0, 10, 10)
        0.0
        >>> calculate_open_fee('MARKET', 100.0, 10, 10)
        0.4
        >>> calculate_open_fee('LIMIT', 100.0, 10, 10)
        0.2
    """
    position_value = entry_price * quantity
    
    if order_type == 'MAKER_ONLY':
        return 0.0  # Emitted fee for maker-only orders
    elif order_type == 'MARKET':
        return position_value * BINANCE_FEES['TAKER']
    else:  # LIMIT
        return position_value * BINANCE_FEES['MAKER']


def calculate_close_fee(
    order_type: str,
    close_price: float,
    quantity: float,
    leverage: int = 1
) -> float:
    """
    Calculate fee for closing a position.
    
    Args:
        order_type: Order type ('MAKER_ONLY', 'MARKET', 'LIMIT')
        close_price: Close price of the position
        quantity: Position quantity
        leverage: Position leverage (default 1)
    
    Returns:
        Fee amount in quote currency
    
    Examples:
        >>> calculate_close_fee('MAKER_ONLY', 105.0, 10, 10)
        0.0
        >>> calculate_close_fee('MARKET', 105.0, 10, 10)
        0.42
    """
    position_value = close_price * quantity
    
    if order_type == 'MAKER_ONLY':
        return 0.0  # Emitted fee for maker-only orders
    elif order_type == 'MARKET':
        return position_value * BINANCE_FEES['TAKER']
    else:  # LIMIT
        return position_value * BINANCE_FEES['MAKER']


def calculate_total_fees(
    order_type: str,
    entry_price: float,
    close_price: float,
    quantity: float,
    leverage: int = 1
) -> Dict[str, float]:
    """
    Calculate total fees for a complete trade (open + close).
    
    Args:
        order_type: Order type ('MAKER_ONLY', 'MARKET', 'LIMIT')
        entry_price: Entry price of the position
        close_price: Close price of the position
        quantity: Position quantity
        leverage: Position leverage (default 1)
    
    Returns:
        Dictionary with 'open_fee', 'close_fee', and 'total_fee'
    
    Examples:
        >>> fees = calculate_total_fees('MAKER_ONLY', 100.0, 105.0, 10, 10)
        >>> fees['total_fee']
        0.0
        >>> fees = calculate_total_fees('MARKET', 100.0, 105.0, 10, 10)
        >>> fees['total_fee']
        0.82
    """
    open_fee = calculate_open_fee(order_type, entry_price, quantity, leverage)
    close_fee = calculate_close_fee(order_type, close_price, quantity, leverage)
    
    return {
        'open_fee': open_fee,
        'close_fee': close_fee,
        'total_fee': open_fee + close_fee
    }


def calculate_pnl_with_fees(
    position_side: str,
    entry_price: float,
    close_price: float,
    quantity: float,
    leverage: int,
    order_type: str
) -> Dict[str, float]:
    """
    Calculate PnL including fees for a complete trade.
    
    Args:
        position_side: 'LONG' or 'SHORT'
        entry_price: Entry price of the position
        close_price: Close price of the position
        quantity: Position quantity
        leverage: Position leverage
        order_type: Order type ('MAKER_ONLY', 'MARKET', 'LIMIT')
    
    Returns:
        Dictionary with 'gross_pnl', 'open_fee', 'close_fee', 'net_pnl'
    
    Examples:
        >>> pnl = calculate_pnl_with_fees('LONG', 100.0, 105.0, 10, 10, 'MAKER_ONLY')
        >>> pnl['gross_pnl']
        500.0
        >>> pnl['net_pnl']
        500.0
    """
    # Calculate gross PnL (without fees)
    if position_side == 'LONG':
        price_diff = close_price - entry_price
    else:  # SHORT
        price_diff = entry_price - close_price
    
    gross_pnl = price_diff * quantity * leverage
    
    # Calculate fees
    fees = calculate_total_fees(order_type, entry_price, close_price, quantity, leverage)
    
    # Calculate net PnL (after fees)
    net_pnl = gross_pnl - fees['total_fee']
    
    return {
        'gross_pnl': gross_pnl,
        'open_fee': fees['open_fee'],
        'close_fee': fees['close_fee'],
        'total_fee': fees['total_fee'],
        'net_pnl': net_pnl
    }


# EOF

# Made with Bob
