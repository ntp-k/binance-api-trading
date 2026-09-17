#!/usr/bin/env python3
"""Continuously record the kline data a live bot sees, for later replay.

Usage:
    python3 standalone_services/record_bot_klines.py
    python3 standalone_services/record_bot_klines.py 89

By default, reads every enabled ``config/bot_<id>.json`` for symbol / timeframe /
timeframe_limit, then polls Binance on the same cadence as the live bot. Each bot
gets its own JSONL file under ``resources/klines/``. Passing a bot ID records only
that bot, including when its config is disabled.

File layout:
    line 0   ``meta``      capture settings, so the file is self-describing
    line 1   ``snapshot``  ``timeframe_limit`` candles - the bot's starting window
    line 2+  ``delta``     the 3 most recent candles

Three candles per delta carries the forming candle plus any candle that closed
since the previous poll, with room to spare.  Replay = load the snapshot, then
for each delta drop cached candles at or after the delta's first ``open_time``
and concatenate - the same merge the live bot would do against its own cache.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional


# Allow execution directly from the repository root or any other directory.
REPOSITORY_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPOSITORY_ROOT)

from commons.custom_logger import CustomLogger
from trade_clients.binance.binance_live_trade_client import BinanceLiveTradeClient


CONFIG_DIR = os.path.join(REPOSITORY_ROOT, "config")
OUTPUT_DIR = os.path.join(REPOSITORY_ROOT, "resources", "klines")

DELTA_LIMIT = 3
PROGRESS_EVERY = 100  # Log a heartbeat every N polls

# Fields the strategies actually read.  Timestamps are stored as epoch ms.
COMPACT_COLUMNS = ["open_time", "open", "high", "low", "close", "volume"]
FULL_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_asset_volume", "num_trades",
    "taker_buy_base_volume", "taker_buy_quote_volume", "ignore",
]
TIME_COLUMNS = {"open_time", "close_time"}


def load_bot_config(bot_id: str) -> Dict[str, Any]:
    """
    Read the raw bot config JSON.

    Deliberately skips ConfigValidator: the recorder only needs the market
    parameters and should run regardless of whether the bot is enabled when a
    specific bot ID is supplied.
    """
    config_path = os.path.join(CONFIG_DIR, f"bot_{bot_id}.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Bot config not found: {config_path}")

    with open(config_path, "r") as config_file:
        return json.load(config_file)


def load_enabled_bot_ids() -> List[str]:
    """Return IDs for enabled bot configs in the active config directory."""
    bot_ids: List[str] = []
    for config_path in sorted(os.listdir(CONFIG_DIR)):
        if not (config_path.startswith("bot_") and config_path.endswith(".json")):
            continue

        bot_id = config_path[len("bot_"):-len(".json")]
        with open(os.path.join(CONFIG_DIR, config_path), "r") as config_file:
            bot_config = json.load(config_file)

        if bot_config.get("is_enabled", False):
            bot_ids.append(bot_id)

    return bot_ids


def _json_safe(column: str, value: Any) -> Any:
    """Convert a DataFrame cell into something json.dumps accepts."""
    if column in TIME_COLUMNS:
        return int(value.timestamp() * 1000)
    if hasattr(value, "item"):  # numpy scalar -> native Python
        return value.item()
    return value


def candles_from_df(klines_df, columns: List[str]) -> List[List[Any]]:
    """Convert a klines DataFrame into positional rows matching ``columns``."""
    return [
        [_json_safe(column, value) for column, value in zip(columns, record)]
        for record in klines_df[columns].itertuples(index=False, name=None)
    ]


def record_bot_klines(
    bot_id: str,
    interval: Optional[int] = None,
    full_columns: bool = False,
    logger: Optional[CustomLogger] = None,
) -> str:
    """Poll Binance on the bot's cadence and append every response to a JSONL file."""
    if logger is None:
        logger = CustomLogger(name=f"RecordKlines_{bot_id}")

    bot_config = load_bot_config(bot_id=bot_id)
    symbol = bot_config["symbol"]
    timeframe = bot_config["timeframe"]
    timeframe_limit = int(bot_config["timeframe_limit"])
    columns = FULL_COLUMNS if full_columns else COMPACT_COLUMNS

    client = BinanceLiveTradeClient(logger=logger)
    client.init()
    if interval is not None:
        client.set_wait_time(wait_time_sec=interval)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    started_at = datetime.now().astimezone()
    output_path = os.path.join(
        OUTPUT_DIR,
        f"bot_{bot_id}_{started_at.strftime('%Y%m%dT%H%M%S')}.jsonl"
    )

    logger.info(message="=" * 60)
    logger.info(message=f"Recording klines for bot {bot_id}: {symbol} {timeframe}")
    logger.info(message=f"Snapshot={timeframe_limit} candles, delta={DELTA_LIMIT} candles")
    logger.info(message="This is a read-only market-data service; no orders will be placed.")
    logger.info(message=f"Writing to: {output_path}")
    logger.info(message="=" * 60)

    meta = {
        "type": "meta",
        "bot_id": bot_id,
        "started_at": started_at.isoformat(),
        "symbol": symbol,
        "timeframe": timeframe,
        "timeframe_limit": timeframe_limit,
        "delta_limit": DELTA_LIMIT,
        "columns": columns,
    }

    seq = 0
    recorded = 0
    errors = 0
    snapshot_written = False

    with open(output_path, "a") as output_file:
        output_file.write(json.dumps(meta, separators=(",", ":")) + "\n")
        output_file.flush()

        try:
            while client.running:
                # Stay on the full window until a snapshot actually lands, otherwise
                # a failed first poll would leave deltas with no base to merge onto.
                limit = DELTA_LIMIT if snapshot_written else timeframe_limit
                polled_at = datetime.now().astimezone()

                try:
                    klines_df = client.fetch_klines(
                        symbol=symbol,
                        timeframe=timeframe,
                        timeframe_limit=limit,
                    )
                except Exception as e:
                    logger.error_e(message="Unexpected error fetching klines", e=e)
                    klines_df = None

                if klines_df is None or klines_df.empty:
                    errors += 1
                    row: Dict[str, Any] = {
                        "seq": seq,
                        "ts": polled_at.isoformat(),
                        "type": "error",
                    }
                else:
                    row = {
                        "seq": seq,
                        "ts": polled_at.isoformat(),
                        "type": "snapshot" if not snapshot_written else "delta",
                        "current_price": float(klines_df.iloc[-1]["current_price"]),
                        "candles": candles_from_df(klines_df=klines_df, columns=columns),
                    }
                    snapshot_written = True
                    recorded += 1

                output_file.write(json.dumps(row, separators=(",", ":")) + "\n")
                output_file.flush()

                seq += 1
                if recorded and recorded % PROGRESS_EVERY == 0:
                    size_kb = os.path.getsize(output_path) / 1024
                    logger.info(
                        message=f"{recorded} polls recorded ({errors} errors)  |  {size_kb:.1f} KB")

                client.wait()

        except KeyboardInterrupt:
            logger.info(message="Recorder stopped by user")

    size_kb = os.path.getsize(output_path) / 1024
    logger.info(message="=" * 60)
    logger.info(message=f"Recorded {recorded} polls ({errors} errors) to: {output_path}")
    logger.info(message=f"File size: {size_kb:.1f} KB")
    logger.info(message="=" * 60)
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record klines for all enabled bots, or one specified bot (read-only)."
    )
    parser.add_argument(
        "bot_id",
        nargs="?",
        help="Optional bot id matching config/bot_<id>.json; default: all enabled bots",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Seconds between polls (default: same 15-20s jitter as the live bot)",
    )
    parser.add_argument(
        "--full-columns",
        action="store_true",
        help=f"Store all 12 Binance kline fields instead of the {len(COMPACT_COLUMNS)} the strategies read",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.bot_id is not None:
        bot_ids = [args.bot_id]
    else:
        bot_ids = load_enabled_bot_ids()

    logger = CustomLogger(name="RecordKlines")
    if not bot_ids:
        logger.warning(message="No enabled bot configs found in config/.")
        return 1

    logger.info(message=f"Starting kline recorders for bot(s): {', '.join(bot_ids)}")

    # Each bot has an independent client and wait cadence, matching the live bot
    # behavior while allowing all enabled bots to be recorded concurrently.
    from threading import Thread

    def run_recorder(bot_id: str) -> None:
        bot_logger = CustomLogger(name=f"RecordKlines_{bot_id}")
        try:
            record_bot_klines(
                bot_id=bot_id,
                interval=args.interval,
                full_columns=args.full_columns,
                logger=bot_logger,
            )
        except Exception as error:
            bot_logger.error_e(message=f"Recorder failed for bot {bot_id}", e=error)

    threads = [
        Thread(target=run_recorder, args=(bot_id,), name=f"RecordKlines_{bot_id}", daemon=True)
        for bot_id in bot_ids
    ]
    for thread in threads:
        thread.start()

    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        logger.info(message="\nRecorders stopped by user")
        return 130

    return 0


if __name__ == "__main__":
    sys.exit(main())
