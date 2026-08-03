#!/usr/bin/env python3
"""Fetch and save Binance Futures klines without starting a trading bot.

Usage:
    python3 standalone_services/fetch_binance_klines.py BTCUSDC 4h 1500

The script only requests market data.  It does not inspect positions, submit
orders, or start the bot manager.  The resulting CSV is saved under
``resources/klines/``.
"""

import argparse
import os
import sys
from typing import Optional


# Allow execution directly from the repository root or any other directory.
REPOSITORY_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPOSITORY_ROOT)

from commons.custom_logger import CustomLogger
from trade_clients.binance.binance_live_trade_client import BinanceLiveTradeClient


MAX_KLINE_LIMIT = 1500
KLINE_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_asset_volume",
    "num_trades",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
    "ignore",
]


def fetch_and_save_klines(
    symbol: str,
    timeframe: str,
    limit: int,
    logger: Optional[CustomLogger] = None,
) -> Optional[str]:
    """Fetch recent Futures klines and save their OHLCV fields to a CSV file."""
    if logger is None:
        logger = CustomLogger(name="FetchBinanceKlines")

    symbol = symbol.upper()
    if not 1 <= limit <= MAX_KLINE_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_KLINE_LIMIT}; received {limit}")

    logger.info(message="=" * 60)
    logger.info(message=f"Binance Futures Kline Export: {symbol} {timeframe} x {limit}")
    logger.info(message="This is a read-only market-data request; no orders will be placed.")
    logger.info(message="=" * 60)

    client = BinanceLiveTradeClient(logger=logger)
    client.init()
    klines_df = client.fetch_klines(
        symbol=symbol,
        timeframe=timeframe,
        timeframe_limit=limit,
    )

    if klines_df is None or klines_df.empty:
        logger.error(message="Binance returned no klines; no file was created.")
        return None

    output_dir = os.path.join(REPOSITORY_ROOT, "resources", "klines")
    os.makedirs(output_dir, exist_ok=True)
    start_time = klines_df.iloc[0]["open_time"].strftime("%Y%m%dT%H%M%S%z")
    end_time = klines_df.iloc[-1]["close_time"].strftime("%Y%m%dT%H%M%S%z")
    filename = f"{symbol}_{timeframe}_{len(klines_df)}_{start_time}_{end_time}.csv"
    output_path = os.path.join(output_dir, filename)

    # Exclude ``current_price``: it is a live ticker value, not candle data.
    klines_df.loc[:, KLINE_COLUMNS].to_csv(output_path, index=False)

    logger.info(message=f"Saved {len(klines_df)} klines to: {output_path}")
    logger.info(message=f"Period: {klines_df.iloc[0]['open_time']} to {klines_df.iloc[-1]['close_time']}")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch and save recent Binance Futures klines (read-only)."
    )
    parser.add_argument("symbol", help="Trading pair, e.g. BTCUSDC")
    parser.add_argument("timeframe", help="Binance interval, e.g. 4h, 1h, 15m")
    parser.add_argument("limit", type=int, help=f"Number of recent candles (1-{MAX_KLINE_LIMIT})")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logger = CustomLogger(name="FetchBinanceKlines")
    try:
        output_path = fetch_and_save_klines(
            symbol=args.symbol,
            timeframe=args.timeframe,
            limit=args.limit,
            logger=logger,
        )
        return 0 if output_path else 1
    except ValueError as error:
        logger.error(message=str(error))
        return 2
    except Exception as error:
        logger.error_e(message="Unable to fetch klines", e=error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
