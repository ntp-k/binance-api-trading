#!/usr/bin/env python3
"""
Manual Position Closer for Binance Futures

This script allows you to manually close an open position on Binance Futures.
It fetches the current position for a specified symbol and places a market order
to close it completely (flatten the position).

Usage:
    python3 standalone_services/binance_manual_close_position.py BTCUSDC
"""

import argparse
import os
import sys
from typing import Optional

# Add the repository root to the path to allow direct execution of this script.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from trade_clients.binance.binance_live_trade_client import BinanceLiveTradeClient
from commons.custom_logger import CustomLogger
from models.enum.position_side import PositionSide
from models.enum.order_side import OrderSide


def close_position(symbol: str, logger: Optional[CustomLogger] = None) -> bool:
    """
    Close an open position for the specified symbol.
    
    Args:
        symbol: Trading pair symbol (e.g., "BTCUSDT")
        logger: Optional custom logger instance
    
    Returns:
        True if position was closed successfully, False otherwise
    """
    if logger is None:
        logger = CustomLogger(name="ManualClosePosition")
    
    # Initialize Binance client
    logger.info(message="=" * 60)
    logger.info(message=f"Manual Position Closer - {symbol}")
    logger.info(message="=" * 60)
    
    client = BinanceLiveTradeClient(logger=logger)
    client.init()
    
    # Fetch current position
    logger.info(message=f"Fetching current position for {symbol}...")
    position = client.fetch_position(symbol=symbol)
    
    if not position:
        logger.warning(message=f"No active position found for {symbol}")
        logger.info(message="Nothing to close. Exiting.")
        return False
    
    # Extract position details
    position_side = position['position_side']
    quantity = abs(position['quantity'])
    entry_price = position['entry_price']
    pnl = position['pnl']
    mark_price = position['mark_price']
    
    logger.info(message="-" * 60)
    logger.info(message="Current Position Details:")
    logger.info(message=f"  Symbol:       {symbol}")
    logger.info(message=f"  Side:         {position_side.value}")
    logger.info(message=f"  Quantity:     {quantity}")
    logger.info(message=f"  Entry Price:  {entry_price}")
    logger.info(message=f"  Mark Price:   {mark_price}")
    logger.info(message=f"  Unrealized PnL: {'+' if pnl >= 0 else ''}{pnl:.2f} USDT")
    logger.info(message="-" * 60)
    
    # Determine the order side to close the position
    # If LONG position, we need to SELL to close
    # If SHORT position, we need to BUY to close
    if position_side == PositionSide.LONG:
        order_side = OrderSide.SELL.value
        logger.info(message="Position is LONG → Placing SELL order to close")
    elif position_side == PositionSide.SHORT:
        order_side = OrderSide.BUY.value
        logger.info(message="Position is SHORT → Placing BUY order to close")
    else:
        logger.error(message=f"Unknown position side: {position_side}")
        return False
    
    # Confirm before closing
    logger.warning(message=f"\n⚠️  About to close {position_side.value} position of {quantity} {symbol}")
    logger.warning(message=f"⚠️  Current PnL: {'+' if pnl >= 0 else ''}{pnl:.2f} USDT\n")
    
    try:
        user_input = input("Do you want to proceed? (yes/no): ").strip().lower()
        if user_input not in ['yes', 'y']:
            logger.info(message="Operation cancelled by user.")
            return False
    except (KeyboardInterrupt, EOFError):
        logger.info(message="\nOperation cancelled by user.")
        return False
    
    # Place market order to close position
    logger.info(message=f"Placing MARKET {order_side} order for {quantity} {symbol}...")
    
    try:
        order_result = client.place_order(
            symbol=symbol,
            order_side=order_side,
            order_type="MARKET",
            quantity=quantity,
            reduce_only=True  # Ensure we only close, not open new position
        )
        
        if not order_result:
            logger.error(message="Failed to place close order")
            return False
        
        logger.info(message="=" * 60)
        logger.info(message="✅ Position Close Order Placed Successfully!")
        logger.info(message=f"  Order ID:     {order_result.get('orderId', 'N/A')}")
        logger.info(message=f"  Status:       {order_result.get('status', 'N/A')}")
        logger.info(message=f"  Side:         {order_result.get('side', 'N/A')}")
        logger.info(message=f"  Quantity:     {order_result.get('executedQty', 'N/A')}")
        logger.info(message=f"  Avg Price:    {order_result.get('avgPrice', 'N/A')}")
        logger.info(message="=" * 60)
        
        # Verify position is closed
        logger.info(message="Verifying position closure...")
        new_position = client.fetch_position(symbol=symbol)
        
        if not new_position:
            logger.info(message="✅ Position successfully closed and flattened!")
            return True
        else:
            logger.warning(message="⚠️  Position still exists after close order")
            logger.warning(message=f"Remaining quantity: {new_position.get('quantity', 0)}")
            return False
            
    except Exception as e:
        logger.error_e(message="Error closing position", e=e)
        return False


def main():
    """Main entry point for the script."""
    logger = CustomLogger(name="ManualClosePosition")
    parser = argparse.ArgumentParser(
        description="Close one Binance Futures position after confirmation."
    )
    parser.add_argument("symbol", help="Trading pair to close, e.g. BTCUSDC")
    args = parser.parse_args()
    
    try:
        success = close_position(symbol=args.symbol.upper(), logger=logger)
        
        if success:
            logger.info(message="\n✅ Script completed successfully")
            sys.exit(0)
        else:
            logger.warning(message="\n⚠️  Script completed with warnings")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info(message="\n\n⚠️  Script interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error_e(message="Unexpected error in main", e=e)
        sys.exit(1)


if __name__ == "__main__":
    main()

# EOF

# Made with Bob
