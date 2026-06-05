"""
Simple Momentum Wick Strategy
- Open position on EVERY candle open
- If previous candle is GREEN → LONG
- If previous candle is RED → SHORT
- TP at MINIMUM wick amount found in training data
"""

import requests
import pandas as pd
from typing import Dict
from datetime import datetime


def fetch_binance_klines(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    """Fetch kline data from Binance"""
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        klines = response.json()
        
        df = pd.DataFrame(klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
        for col in ['open', 'high', 'low', 'close']:
            df[col] = df[col].astype(float)
        
        return df
    except Exception as e:
        print(f"Error fetching {symbol} {interval}: {e}")
        return pd.DataFrame()


def analyze_wicks(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze wicks from OPEN price"""
    df['is_green'] = df['close'] > df['open']
    df['is_red'] = df['close'] < df['open']
    df['upper_wick'] = df['high'] - df['open']
    df['upper_wick_pct'] = (df['upper_wick'] / df['open']) * 100
    df['lower_wick'] = df['open'] - df['low']
    df['lower_wick_pct'] = (df['lower_wick'] / df['open']) * 100
    return df


def test_rolling_momentum_strategy(df: pd.DataFrame, lookback: int = 200,
                                   margin: float = 5.0, leverage: int = 15):
    """Test momentum strategy with rolling window for min_wick calculation
    
    Logic:
    - Start trading at candle [lookback]
    - For each candle, calculate min_wick from previous [lookback] candles
    - If previous candle is GREEN → open LONG on current candle open
    - If previous candle is RED → open SHORT on current candle open
    - TP at MINIMUM wick from rolling window
    """
    trades = []
    position_size = margin * leverage
    
    # Start from lookback+1 (need lookback candles + 1 previous candle)
    for i in range(lookback + 1, len(df)):
        # Get rolling window for min_wick calculation
        window_start = i - lookback - 1
        window_end = i - 1
        window_df = df.iloc[window_start:window_end]
        
        # Calculate min_wick from rolling window
        # If min is 0, use first non-zero value
        upper_wicks_sorted = window_df['upper_wick_pct'].sort_values()
        lower_wicks_sorted = window_df['lower_wick_pct'].sort_values()
        
        # Get minimum (or first non-zero if min is 0)
        min_upper_wick_pct = upper_wicks_sorted.iloc[0]
        if min_upper_wick_pct == 0 and len(upper_wicks_sorted) > 1:
            non_zero_upper = upper_wicks_sorted[upper_wicks_sorted > 0]
            min_upper_wick_pct = non_zero_upper.iloc[0] if len(non_zero_upper) > 0 else 0
        
        min_lower_wick_pct = lower_wicks_sorted.iloc[0]
        if min_lower_wick_pct == 0 and len(lower_wicks_sorted) > 1:
            non_zero_lower = lower_wicks_sorted[lower_wicks_sorted > 0]
            min_lower_wick_pct = non_zero_lower.iloc[0] if len(non_zero_lower) > 0 else 0
        
        prev = df.iloc[i-1]
        curr = df.iloc[i]
        entry = curr['open']
        
        if prev['is_green']:
            # Previous GREEN → LONG (follow momentum up)
            target_pct = min_upper_wick_pct
            target = entry + (entry * target_pct / 100)
            exit_price = target if curr['high'] >= target else curr['close']
            pnl = position_size * ((exit_price - entry) / entry)
            hit_tp = curr['high'] >= target
            direction = 'LONG'
            
        elif prev['is_red']:
            # Previous RED → SHORT (follow momentum down)
            target_pct = min_lower_wick_pct
            target = entry - (entry * target_pct / 100)
            exit_price = target if curr['low'] <= target else curr['close']
            pnl = position_size * ((entry - exit_price) / entry)
            hit_tp = curr['low'] <= target
            direction = 'SHORT'
        else:
            # Doji or no clear direction - skip
            continue
        
        trades.append({
            'pnl': pnl,
            'hit_tp': hit_tp,
            'entry': entry,
            'exit': exit_price,
            'direction': direction,
            'min_upper_wick': min_upper_wick_pct,
            'min_lower_wick': min_lower_wick_pct,
        })
    
    if len(trades) == 0:
        return None
    
    df_trades = pd.DataFrame(trades)
    wins = df_trades[df_trades['pnl'] > 0]
    losses = df_trades[df_trades['pnl'] <= 0]
    
    return {
        'total_pnl': df_trades['pnl'].sum(),
        'win_rate': (df_trades['pnl'] > 0).sum() / len(df_trades) * 100,
        'trades': len(df_trades),
        'avg_win': wins['pnl'].mean() if len(wins) > 0 else 0,
        'avg_loss': losses['pnl'].mean() if len(losses) > 0 else 0,
        'tp_hit_rate': (df_trades['hit_tp']).sum() / len(df_trades) * 100,
        'max_win': wins['pnl'].max() if len(wins) > 0 else 0,
        'max_loss': losses['pnl'].min() if len(losses) > 0 else 0,
        'profit_factor': abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else float('inf'),
        'long_trades': (df_trades['direction'] == 'LONG').sum(),
        'short_trades': (df_trades['direction'] == 'SHORT').sum(),
        'avg_min_upper_wick': df_trades['min_upper_wick'].mean(),
        'avg_min_lower_wick': df_trades['min_lower_wick'].mean(),
    }


def test_symbol_interval(symbol: str, interval: str, margin: float, leverage: int,
                        limit: int, lookback: int):
    """Test strategy for a single symbol and interval with rolling window"""
    print(f"\nFetching {symbol} {interval} data...")
    
    df = fetch_binance_klines(symbol, interval, limit)
    
    if df.empty:
        print(f"❌ Failed to fetch data")
        return None
    
    df = analyze_wicks(df)
    
    print(f"Total candles: {len(df)} | Lookback: {lookback} | Trading candles: {len(df) - lookback - 1}")
    
    # Test strategy with rolling window
    result = test_rolling_momentum_strategy(df, lookback, margin, leverage)
    
    if result:
        result['symbol'] = symbol
        result['interval'] = interval
        result['lookback'] = lookback
    
    return result


def main():
    # Configuration
    SYMBOLS = ['BTCUSDC', 'ETHUSDC']
    INTERVALS = ['5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d']
    LOOKBACK = 200  # Rolling window size for min_wick calculation
    MARGIN = 5.0
    LEVERAGE = 15
    LIMIT = 1500  # Fetch more candles for rolling window
    
    print("="*120)
    print(f"ROLLING MOMENTUM WICK STRATEGY TEST")
    print(f"Strategy: GREEN candle → LONG next, RED candle → SHORT next")
    print(f"TP: Minimum wick from rolling {LOOKBACK}-candle window")
    print(f"Trade: EVERY candle (no filters)")
    print(f"Margin: ${MARGIN} | Leverage: {LEVERAGE}x | Position: ${MARGIN * LEVERAGE}")
    print("="*120)
    
    all_results = []
    
    for symbol in SYMBOLS:
        print(f"\n{'='*120}")
        print(f"TESTING {symbol}")
        print(f"{'='*120}")
        
        for interval in INTERVALS:
            result = test_symbol_interval(symbol, interval, MARGIN, LEVERAGE, LIMIT, LOOKBACK)
            
            if result:
                all_results.append(result)
                
                profitable = "✅" if result['total_pnl'] > 0 else "❌"
                pf_str = f"{result['profit_factor']:.2f}" if result['profit_factor'] != float('inf') else "∞"
                
                print(f"\n{interval:>4} | P&L: ${result['total_pnl']:>7.2f} | Win: {result['win_rate']:>5.1f}% | "
                      f"Trades: {result['trades']:<4} | TP Hit: {result['tp_hit_rate']:>5.1f}% | "
                      f"L/S: {result['long_trades']}/{result['short_trades']} | PF: {pf_str:<6} {profitable}")
                print(f"      Avg Min Upper Wick: {result['avg_min_upper_wick']:.6f}% | Avg Min Lower Wick: {result['avg_min_lower_wick']:.6f}%")
    
    # Summary
    print(f"\n{'='*120}")
    print("SUMMARY - MOMENTUM STRATEGY RESULTS")
    print(f"{'='*120}")
    
    profitable_results = [r for r in all_results if r['total_pnl'] > 0]
    
    print(f"\nTotal Configurations: {len(all_results)}")
    print(f"Profitable: {len(profitable_results)} ({len(profitable_results)/len(all_results)*100:.1f}%)")
    print(f"Unprofitable: {len(all_results) - len(profitable_results)}")
    
    if profitable_results:
        profitable_results.sort(key=lambda x: x['total_pnl'], reverse=True)
        
        print(f"\n🏆 TOP 5 PROFITABLE CONFIGURATIONS:")
        print(f"{'Rank':<6} {'Symbol':<12} {'Interval':<10} {'P&L':<12} {'Win%':<10} {'Trades':<10} {'PF':<10}")
        print("-"*120)
        for i, r in enumerate(profitable_results[:5], 1):
            pf_str = f"{r['profit_factor']:.2f}" if r['profit_factor'] != float('inf') else "∞"
            print(f"{i:<6} {r['symbol']:<12} {r['interval']:<10} ${r['total_pnl']:>8.2f}{'':<3} "
                  f"{r['win_rate']:>6.1f}%{'':<3} {r['trades']:<10} {pf_str:<10}")
        
        print(f"\n✨ BEST CONFIGURATION:")
        best = profitable_results[0]
        print(f"   Symbol: {best['symbol']}")
        print(f"   Timeframe: {best['interval']}")
        print(f"   P&L: ${best['total_pnl']:.2f}")
        print(f"   Win Rate: {best['win_rate']:.1f}%")
        print(f"   Trades: {best['trades']}")
        print(f"   TP Hit Rate: {best['tp_hit_rate']:.1f}%")
        print(f"   Profit Factor: {best['profit_factor']:.2f}")
        print(f"   Long/Short: {best['long_trades']}/{best['short_trades']}")
    else:
        print(f"\n❌ NO PROFITABLE CONFIGURATIONS FOUND")
        print("This momentum strategy does not appear to be profitable.")
    
    print("\n" + "="*120)
    print("✅ TEST COMPLETE!")
    print("="*120)


if __name__ == "__main__":
    main()

# Made with Bob