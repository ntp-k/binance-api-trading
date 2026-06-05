"""
Guaranteed Scalp Strategy - Target 100% Win Rate
Use fixed small TP target that covers fees + small profit
"""

import requests
import pandas as pd
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


def analyze_candles(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze candles"""
    df['is_green'] = df['close'] > df['open']
    df['is_red'] = df['close'] < df['open']
    df['range_pct'] = ((df['high'] - df['low']) / df['open']) * 100
    return df


def test_guaranteed_scalp(df: pd.DataFrame, tp_pct: float = 0.10,
                          margin: float = 5.0, leverage: int = 15, fee_pct: float = 0.04):
    """Test guaranteed scalp strategy with fixed TP
    
    Logic:
    - If previous candle is GREEN → LONG next
    - If previous candle is RED → SHORT next
    - TP at fixed small percentage (e.g., 0.10%)
    - Account for trading fees
    """
    trades = []
    position_size = margin * leverage
    
    for i in range(1, len(df)):
        prev = df.iloc[i-1]
        curr = df.iloc[i]
        entry = curr['open']
        
        # Calculate fee cost (entry + exit)
        fee_cost = position_size * (fee_pct / 100) * 2
        
        if prev['is_green']:
            # Previous GREEN → LONG
            target = entry + (entry * tp_pct / 100)
            hit_tp = curr['high'] >= target
            
            if hit_tp:
                exit_price = target
                gross_pnl = position_size * ((exit_price - entry) / entry)
                net_pnl = gross_pnl - fee_cost
            else:
                exit_price = curr['close']
                gross_pnl = position_size * ((exit_price - entry) / entry)
                net_pnl = gross_pnl - fee_cost
            
            direction = 'LONG'
            
        elif prev['is_red']:
            # Previous RED → SHORT
            target = entry - (entry * tp_pct / 100)
            hit_tp = curr['low'] <= target
            
            if hit_tp:
                exit_price = target
                gross_pnl = position_size * ((entry - exit_price) / entry)
                net_pnl = gross_pnl - fee_cost
            else:
                exit_price = curr['close']
                gross_pnl = position_size * ((entry - exit_price) / entry)
                net_pnl = gross_pnl - fee_cost
            
            direction = 'SHORT'
        else:
            continue
        
        trades.append({
            'pnl': net_pnl,
            'gross_pnl': gross_pnl,
            'fees': fee_cost,
            'hit_tp': hit_tp,
            'entry': entry,
            'exit': exit_price,
            'direction': direction,
        })
    
    if len(trades) == 0:
        return None
    
    df_trades = pd.DataFrame(trades)
    wins = df_trades[df_trades['pnl'] > 0]
    losses = df_trades[df_trades['pnl'] <= 0]
    
    return {
        'total_pnl': df_trades['pnl'].sum(),
        'total_gross_pnl': df_trades['gross_pnl'].sum(),
        'total_fees': df_trades['fees'].sum(),
        'win_rate': (df_trades['pnl'] > 0).sum() / len(df_trades) * 100,
        'trades': len(df_trades),
        'avg_win': wins['pnl'].mean() if len(wins) > 0 else 0,
        'avg_loss': losses['pnl'].mean() if len(losses) > 0 else 0,
        'tp_hit_rate': (df_trades['hit_tp']).sum() / len(df_trades) * 100,
        'profit_factor': abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else float('inf'),
        'long_trades': (df_trades['direction'] == 'LONG').sum(),
        'short_trades': (df_trades['direction'] == 'SHORT').sum(),
    }


def main():
    # Configuration
    SYMBOLS = ['BNBUSDC']
    INTERVALS = ['5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d']
    TP_TARGETS = [0.05, 0.08, 0.10, 0.12, 0.15, 0.20]  # Different TP targets to test
    MARGIN = 5.0
    LEVERAGE = 15
    FEE_PCT = 0
    LIMIT = 1500
    
    print("="*140)
    print(f"GUARANTEED SCALP STRATEGY - TARGET 100% WIN RATE")
    print(f"Strategy: GREEN → LONG, RED → SHORT with fixed small TP")
    print(f"Margin: ${MARGIN} | Leverage: {LEVERAGE}x | Position: ${MARGIN * LEVERAGE}")
    print(f"Fee: {FEE_PCT}% per trade (total {FEE_PCT*2}% round-trip)")
    print("="*140)
    
    all_results = []
    
    for symbol in SYMBOLS:
        print(f"\n{'='*140}")
        print(f"TESTING {symbol}")
        print(f"{'='*140}")
        
        for interval in INTERVALS:
            print(f"\n{interval}:")
            
            df = fetch_binance_klines(symbol, interval, LIMIT)
            if df.empty:
                continue
            
            df = analyze_candles(df)
            
            for tp_pct in TP_TARGETS:
                result = test_guaranteed_scalp(df, tp_pct, MARGIN, LEVERAGE, FEE_PCT)
                
                if result:
                    result['symbol'] = symbol
                    result['interval'] = interval
                    result['tp_pct'] = tp_pct
                    all_results.append(result)
                    
                    profitable = "✅" if result['total_pnl'] > 0 else "❌"
                    pf_str = f"{result['profit_factor']:.2f}" if result['profit_factor'] != float('inf') else "∞"
                    
                    print(f"  TP {tp_pct:>5.2f}% | Net P&L: ${result['total_pnl']:>7.2f} | "
                          f"Gross: ${result['total_gross_pnl']:>7.2f} | Fees: ${result['total_fees']:>6.2f} | "
                          f"Win: {result['win_rate']:>5.1f}% | TP Hit: {result['tp_hit_rate']:>5.1f}% | "
                          f"Trades: {result['trades']:<4} | PF: {pf_str:<6} {profitable}")
    
    # Summary
    print(f"\n{'='*140}")
    print("SUMMARY - GUARANTEED SCALP RESULTS")
    print(f"{'='*140}")
    
    profitable_results = [r for r in all_results if r['total_pnl'] > 0]
    
    print(f"\nTotal Configurations: {len(all_results)}")
    print(f"Profitable: {len(profitable_results)} ({len(profitable_results)/len(all_results)*100:.1f}%)")
    print(f"Unprofitable: {len(all_results) - len(profitable_results)}")
    
    if profitable_results:
        profitable_results.sort(key=lambda x: x['total_pnl'], reverse=True)
        
        print(f"\n🏆 TOP 10 PROFITABLE CONFIGURATIONS:")
        print(f"{'Rank':<6} {'Symbol':<10} {'Interval':<10} {'TP%':<8} {'Net P&L':<12} {'Win%':<10} {'TP Hit%':<10} {'Trades':<8}")
        print("-"*140)
        for i, r in enumerate(profitable_results[:10], 1):
            print(f"{i:<6} {r['symbol']:<10} {r['interval']:<10} {r['tp_pct']:<8.2f} "
                  f"${r['total_pnl']:>8.2f}{'':<3} {r['win_rate']:>6.1f}%{'':<3} "
                  f"{r['tp_hit_rate']:>6.1f}%{'':<3} {r['trades']:<8}")
        
        print(f"\n✨ BEST CONFIGURATION:")
        best = profitable_results[0]
        print(f"   Symbol: {best['symbol']}")
        print(f"   Timeframe: {best['interval']}")
        print(f"   TP Target: {best['tp_pct']}%")
        print(f"   Net P&L: ${best['total_pnl']:.2f}")
        print(f"   Gross P&L: ${best['total_gross_pnl']:.2f}")
        print(f"   Total Fees: ${best['total_fees']:.2f}")
        print(f"   Win Rate: {best['win_rate']:.1f}%")
        print(f"   TP Hit Rate: {best['tp_hit_rate']:.1f}%")
        print(f"   Trades: {best['trades']}")
        print(f"   Profit Factor: {best['profit_factor']:.2f}")
        
        # Find highest win rate
        highest_wr = max(profitable_results, key=lambda x: x['win_rate'])
        print(f"\n🎯 HIGHEST WIN RATE:")
        print(f"   {highest_wr['symbol']} {highest_wr['interval']} with TP {highest_wr['tp_pct']}%")
        print(f"   Win Rate: {highest_wr['win_rate']:.1f}%")
        print(f"   TP Hit Rate: {highest_wr['tp_hit_rate']:.1f}%")
        print(f"   Net P&L: ${highest_wr['total_pnl']:.2f}")
    else:
        print(f"\n❌ NO PROFITABLE CONFIGURATIONS FOUND")
        print("Fees are eating all profits. Need larger TP targets or lower fees.")
    
    print("\n" + "="*140)
    print("✅ TEST COMPLETE!")
    print("="*140)


if __name__ == "__main__":
    main()

# Made with Bob