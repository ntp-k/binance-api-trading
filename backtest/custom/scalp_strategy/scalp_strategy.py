"""
Backtest optimizer for the live `scalp_body_filter_momentum` + `countdown` strategy.

Parity with live strategy:
- Entry on current candle open using previous candle direction
- Previous candle body percentage must be >= min_body_pct
- LONG on previous green candle, SHORT on previous red candle
- TP price derived from tp_pct and rounded by decimal
- SL price derived from sl_target_pnl using quantity from margin * leverage / entry_price
- Exit on first event among:
  - SL hit
  - TP hit
  - countdown_minutes expiry, then close at that candle close
- No same-candle TP/SL check on entry candle, matching backtest trade client behavior
"""

from __future__ import annotations

import itertools
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests


GET_KLINES_URL = "https://fapi.binance.com/fapi/v1/klines"


def fetch_binance_klines(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    """Fetch kline data from Binance futures."""
    params = {"symbol": symbol, "interval": interval, "limit": min(limit, 1500)}
    response = requests.get(GET_KLINES_URL, params=params, timeout=30)
    response.raise_for_status()
    klines = response.json()

    df = pd.DataFrame(klines, columns=[
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_volume",
        "trades",
        "taker_buy_base",
        "taker_buy_quote",
        "ignore",
    ])  # type: ignore[call-overload]

    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    df["body_pct"] = (df["close"] - df["open"]).abs() / df["open"]
    return df


def calculate_tp_sl_prices(
    side: str,
    entry_price: float,
    tp_pct: float,
    decimal: int,
    sl_target_pnl: float,
    quantity: float,
) -> Tuple[float, float]:
    """Mirror live strategy TP/SL calculation."""
    if side == "LONG":
        tp_price = round(entry_price * (1 + tp_pct), decimal)
        sl_price = round(entry_price + (sl_target_pnl / quantity), decimal) if sl_target_pnl < 0 else -1.0
    else:
        tp_price = round(entry_price * (1 - tp_pct), decimal)
        sl_price = round(entry_price - (sl_target_pnl / quantity), decimal) if sl_target_pnl < 0 else -1.0
    return tp_price, sl_price


def simulate_strategy(
    df: pd.DataFrame,
    *,
    min_body_pct: float,
    tp_pct: float,
    decimal: int,
    countdown_minutes: int,
    sl_target_pnl: float,
    position_margin: float,
    leverage: int,
    initial_capital: float = 100.0,
) -> Optional[Dict]:
    """
    Simulate the live scalp_body_filter_momentum + countdown strategy.

    Notes:
    - First candle is skipped because live strategy stores initial candle state first.
    - Entry occurs at current candle open based on previous candle.
    - TP/SL are only checked starting from the next candle after entry.
    """
    if len(df) < 3:
        return None

    capital = initial_capital
    equity_curve = [capital]
    trades: List[Dict] = []

    i = 1
    while i < len(df):
        prev_candle = df.iloc[i - 1]
        entry_candle = df.iloc[i]

        if prev_candle["body_pct"] < min_body_pct:
            i += 1
            continue

        if prev_candle["close"] > prev_candle["open"]:
            side = "LONG"
        elif prev_candle["close"] < prev_candle["open"]:
            side = "SHORT"
        else:
            i += 1
            continue

        entry_price = float(entry_candle["open"])
        notional = position_margin * leverage
        quantity = notional / entry_price if entry_price > 0 else 0.0
        if quantity <= 0:
            i += 1
            continue

        tp_price, sl_price = calculate_tp_sl_prices(
            side=side,
            entry_price=entry_price,
            tp_pct=tp_pct,
            decimal=decimal,
            sl_target_pnl=sl_target_pnl,
            quantity=quantity,
        )

        exit_price = float(entry_candle["close"])
        exit_reason = "COUNTDOWN"
        exit_index = i

        j = i + 1
        while j < len(df):
            candle = df.iloc[j]
            elapsed_minutes = (candle["open_time"] - entry_candle["open_time"]).total_seconds() / 60.0

            if side == "LONG":
                if tp_price > 0 and candle["high"] >= tp_price:
                    exit_price = tp_price
                    exit_reason = "TP"
                    exit_index = j
                    break
                if sl_price > 0 and candle["low"] <= sl_price:
                    exit_price = sl_price
                    exit_reason = "SL"
                    exit_index = j
                    break

            else:
                if tp_price > 0 and candle["low"] <= tp_price:
                    exit_price = tp_price
                    exit_reason = "TP"
                    exit_index = j
                    break
                if sl_price > 0 and candle["high"] >= sl_price:
                    exit_price = sl_price
                    exit_reason = "SL"
                    exit_index = j
                    break

            if elapsed_minutes >= countdown_minutes:
                exit_price = float(candle["close"])
                exit_reason = "COUNTDOWN"
                exit_index = j
                break

            j += 1

        if side == "LONG":
            pnl = (exit_price - entry_price) * quantity
        else:
            pnl = (entry_price - exit_price) * quantity

        capital += pnl
        equity_curve.append(capital)

        trades.append(
            {
                "entry_time": str(entry_candle["open_time"]),
                "exit_time": str(df.iloc[exit_index]["close_time"]),
                "side": side,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "tp_price": tp_price,
                "sl_price": sl_price,
                "pnl": pnl,
                "exit_reason": exit_reason,
                "body_pct": float(prev_candle["body_pct"]),
            }
        )

        i = exit_index + 1

    if not trades:
        return None

    trade_df = pd.DataFrame(trades)
    wins = trade_df[trade_df["pnl"] > 0]
    losses = trade_df[trade_df["pnl"] < 0]

    gross_profit = wins["pnl"].sum() if not wins.empty else 0.0
    gross_loss = abs(losses["pnl"].sum()) if not losses.empty else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    peak = equity_curve[0]
    max_drawdown_pct = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        drawdown_pct = ((peak - value) / peak * 100) if peak > 0 else 0.0
        max_drawdown_pct = max(max_drawdown_pct, drawdown_pct)

    return {
        "trades": len(trades),
        "win_rate": float((trade_df["pnl"] > 0).mean() * 100),
        "total_pnl": float(trade_df["pnl"].sum()),
        "final_capital": float(capital),
        "avg_pnl": float(trade_df["pnl"].mean()),
        "profit_factor": float(profit_factor) if profit_factor != float("inf") else float("inf"),
        "max_drawdown_pct": float(max_drawdown_pct),
        "tp_hits": int((trade_df["exit_reason"] == "TP").sum()),
        "sl_hits": int((trade_df["exit_reason"] == "SL").sum()),
        "countdown_exits": int((trade_df["exit_reason"] == "COUNTDOWN").sum()),
        "trade_details": trades,
    }


def rank_score(result: Dict) -> float:
    """Simple ranking score favoring pnl and profit factor, penalizing drawdown."""
    pf = min(result["profit_factor"], 10.0) if result["profit_factor"] != float("inf") else 10.0
    return result["total_pnl"] * 10 + pf * 20 + result["win_rate"] - result["max_drawdown_pct"] * 2


def run_grid_search(
    *,
    symbol: str,
    decimal: int,
    leverage: int,
    position_margin: float,
    intervals: List[str],
    limit: int,
    min_body_pcts: List[float],
    tp_pcts: List[float],
    countdown_minutes_list: List[int],
    sl_target_pnls: List[float],
) -> List[Dict]:
    """Run parameter search."""
    all_results: List[Dict] = []

    for interval in intervals:
        print(f"\nFetching {symbol} {interval}...")
        df = fetch_binance_klines(symbol=symbol, interval=interval, limit=limit)

        for min_body_pct, tp_pct, countdown_minutes, sl_target_pnl in itertools.product(
            min_body_pcts, tp_pcts, countdown_minutes_list, sl_target_pnls
        ):
            result = simulate_strategy(
                df,
                min_body_pct=min_body_pct,
                tp_pct=tp_pct,
                decimal=decimal,
                countdown_minutes=countdown_minutes,
                sl_target_pnl=sl_target_pnl,
                position_margin=position_margin,
                leverage=leverage,
            )

            if result is None:
                continue

            result.update(
                {
                    "symbol": symbol,
                    "interval": interval,
                    "limit": limit,
                    "min_body_pct": min_body_pct,
                    "tp_pct": tp_pct,
                    "countdown_minutes": countdown_minutes,
                    "sl_target_pnl": sl_target_pnl,
                    "score": rank_score(result),
                }
            )
            all_results.append(result)

            pf_str = f"{result['profit_factor']:.2f}" if result["profit_factor"] != float("inf") else "∞"
            print(
                f"{interval:>3} | body>={min_body_pct:.4f} | tp={tp_pct:.4f} | cd={countdown_minutes:>3}m | "
                f"sl={sl_target_pnl:>5.1f} | pnl={result['total_pnl']:>8.2f} | "
                f"win={result['win_rate']:>5.1f}% | trades={result['trades']:>4} | "
                f"mdd={result['max_drawdown_pct']:>6.2f}% | pf={pf_str}"
            )

    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results


def save_results(results: List[Dict], symbol: str) -> Tuple[Path, Path]:
    """Save full results and ranking summary."""
    output_dir = Path("backtest/custom/scalp_strategy")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_path = output_dir / f"{symbol}_results_{timestamp}.json"
    ranking_path = output_dir / f"{symbol}_ranking_{timestamp}.json"

    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    ranking = []
    for idx, item in enumerate(results[:20], 1):
        ranking.append(
            {
                "rank": idx,
                "symbol": item["symbol"],
                "interval": item["interval"],
                "min_body_pct": item["min_body_pct"],
                "tp_pct": item["tp_pct"],
                "countdown_minutes": item["countdown_minutes"],
                "sl_target_pnl": item["sl_target_pnl"],
                "total_pnl": item["total_pnl"],
                "win_rate": item["win_rate"],
                "trades": item["trades"],
                "profit_factor": item["profit_factor"],
                "max_drawdown_pct": item["max_drawdown_pct"],
                "score": item["score"],
            }
        )

    with open(ranking_path, "w", encoding="utf-8") as f:
        json.dump(ranking, f, indent=2, ensure_ascii=False)

    return full_path, ranking_path


def print_top_results(results: List[Dict], top_n: int = 10) -> None:
    """Print top ranked configurations."""
    print("\n" + "=" * 160)
    print("TOP CONFIGURATIONS")
    print("=" * 160)
    print(
        f"{'Rank':<6} {'Symbol':<10} {'TF':<6} {'Body%':<10} {'TP%':<10} {'CD(min)':<10} "
        f"{'SL PnL':<10} {'PnL':<10} {'Win%':<8} {'Trades':<8} {'MDD%':<8} {'PF':<8} {'Score':<10}"
    )
    print("-" * 160)

    for idx, r in enumerate(results[:top_n], 1):
        pf_str = f"{r['profit_factor']:.2f}" if r["profit_factor"] != float("inf") else "∞"
        print(
            f"{idx:<6} {r['symbol']:<10} {r['interval']:<6} {r['min_body_pct']:<10.4f} {r['tp_pct']:<10.4f} "
            f"{r['countdown_minutes']:<10} {r['sl_target_pnl']:<10.1f} {r['total_pnl']:<10.2f} "
            f"{r['win_rate']:<8.2f} {r['trades']:<8} {r['max_drawdown_pct']:<8.2f} {pf_str:<8} {r['score']:<10.2f}"
        )


def main() -> None:
    # Match current live configs first; adjust symbol manually when needed.
    symbol = "DOGEUSDC"
    decimal = 5

    intervals = ["1h", "4h", "6h", "12h", "1d"]
    limit = 500
    leverage = 15
    position_margin = 5.0

    min_body_pcts = [0.0005, 0.0010, 0.0015, 0.0020, 0.0030]
    tp_pcts = [0.0005, 0.0010, 0.0015, 0.0020, 0.0025, 0.0030]
    countdown_minutes_list = [60, 120, 180, 300, 480]
    sl_target_pnls = [-1.5, -2.0, -3.0, -4.0, -5.0]

    print("=" * 160)
    print("SCALP BODY FILTER MOMENTUM + COUNTDOWN GRID SEARCH")
    print("=" * 160)
    print(f"Symbol: {symbol}")
    print(f"Intervals: {intervals}")
    print(f"Leverage: {leverage}x | Position Margin: ${position_margin}")
    print(f"Search space: {len(intervals) * len(min_body_pcts) * len(tp_pcts) * len(countdown_minutes_list) * len(sl_target_pnls)} configs")
    print("=" * 160)

    results = run_grid_search(
        symbol=symbol,
        decimal=decimal,
        leverage=leverage,
        position_margin=position_margin,
        intervals=intervals,
        limit=limit,
        min_body_pcts=min_body_pcts,
        tp_pcts=tp_pcts,
        countdown_minutes_list=countdown_minutes_list,
        sl_target_pnls=sl_target_pnls,
    )

    if not results:
        print("No valid results.")
        return

    print_top_results(results, top_n=15)
    full_path, ranking_path = save_results(results, symbol=symbol)

    best = results[0]
    print("\nBEST CONFIGURATION")
    print("-" * 80)
    print(json.dumps(
        {
            "symbol": best["symbol"],
            "interval": best["interval"],
            "min_body_pct": best["min_body_pct"],
            "tp_pct": best["tp_pct"],
            "countdown_minutes": best["countdown_minutes"],
            "sl_target_pnl": best["sl_target_pnl"],
            "total_pnl": best["total_pnl"],
            "win_rate": best["win_rate"],
            "trades": best["trades"],
            "profit_factor": best["profit_factor"],
            "max_drawdown_pct": best["max_drawdown_pct"],
            "score": best["score"],
        },
        indent=2,
    ))
    print(f"\nSaved full results: {full_path}")
    print(f"Saved ranking: {ranking_path}")


if __name__ == "__main__":
    main()

# Made with Bob
