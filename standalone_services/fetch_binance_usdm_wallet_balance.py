#!/usr/bin/env python3
"""Display the Binance USDⓈ-M Futures wallet balance.

Usage:
    python3 standalone_services/fetch_binance_usdm_wallet_balance.py

The script makes a read-only authenticated request. It does not inspect
positions, submit orders, or start the bot manager.
"""

import os
import sys
from typing import Any, Dict, List, Optional


# Add the repository root to the path to allow direct execution of this script.
REPOSITORY_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPOSITORY_ROOT)

from commons.custom_logger import CustomLogger
from trade_clients.binance.binance_live_trade_client import BinanceLiveTradeClient


def fetch_wallet_balance(
    logger: Optional[CustomLogger] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Fetch and log all USDⓈ-M Futures wallet balances."""
    if logger is None:
        logger = CustomLogger(name="FetchBinanceUsdmWalletBalance")

    logger.info(message="=" * 60)
    logger.info(message="Binance USDⓈ-M Futures Wallet Balance")
    logger.info(message="This is a read-only account request; no orders will be placed.")
    logger.info(message="=" * 60)

    client = BinanceLiveTradeClient(logger=logger)
    client.init()
    balances = client.fetch_wallet_balance()

    if not balances:
        logger.error(message="Binance returned no wallet balances.")
        return None

    logger.info(message="Asset       Wallet Balance     Available Balance  Cross Wallet       Unrealized PnL")
    logger.info(message="-" * 90)
    for balance in balances:
        logger.info(
            message=(
                f"{balance.get('asset', 'N/A'):<12}"
                f"{balance.get('balance', 'N/A'):>18}"
                f"{balance.get('availableBalance', 'N/A'):>20}"
                f"{balance.get('crossWalletBalance', 'N/A'):>18}"
                f"{balance.get('crossUnPnl', 'N/A'):>18}"
            )
        )

    return balances


def main() -> int:
    """Main entry point for the script."""
    logger = CustomLogger(name="FetchBinanceUsdmWalletBalance")
    try:
        return 0 if fetch_wallet_balance(logger=logger) else 1
    except KeyboardInterrupt:
        logger.info(message="\nScript interrupted by user")
        return 130
    except Exception as error:
        logger.error_e(message="Unable to fetch USDⓈ-M wallet balance", e=error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
