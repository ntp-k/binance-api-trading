"""
Optimize Wick Mean Reversion Strategy for BTCUSDC
Test multiple timeframes and body filter thresholds
"""

import requests
import pandas as pd
from typing import Dict
from datetime import datetime


def fetch_binance_klines(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    """Fetch kline data"""
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


def calculate_percentiles(df: pd.DataFrame) -> Dict[str, float]:
    """Calculate percentiles"""
    return {
        'upper_25th': df['upper_wick_pct'].quantile(0.25),
        'lower_25th': df['lower_wick_pct'].quantile(0.25),
    }


def test_strategy(df: pd.DataFrame, percentiles: Dict, min_body_pct: float, 
                 margin: float = 5.0, leverage: int = 15):
    """Test mean reversion strategy with body filter"""
    trades = []
    position_size = margin * leverage
    target_pct = percentiles['lower_25th']
    
    for i in range(1, len(df)):
        prev = df.iloc[i-1]
        curr = df.iloc[i]
        entry = curr['open']
        
        # Filter: only trade if previous candle moved enough
        prev_body_change = abs(((prev['close'] - prev['open']) / prev['open']) * 100)
        if prev_body_change < min_body_pct:
            continue
        
        if prev['is_red']:
            # LONG after strong red
            target = entry + (entry * target_pct / 100)
            exit_price = target if curr['high'] >= target else curr['close']
            pnl = position_size * ((exit_price - entry) / entry)
            hit_tp = curr['high'] >= target
            
        elif prev['is_green']:
            # SHORT after strong green
            target = entry - (entry * target_pct / 100)
            exit_price = target if curr['low'] <= target else curr['close']
            pnl = position_size * ((entry - exit_price) / entry)
            hit_tp = curr['low'] <= target
        else:
            continue
        
        trades.append({
            'pnl': pnl,
            'hit_tp': hit_tp,
            'entry': entry,
            'exit': exit_price
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
        'profit_factor': abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else float('inf')
    }


def main():
    SYMBOL = 'BTCUSDC'
    INTERVALS = ['1h', '2h', '4h', '6h', '8h', '12h', '1d']
    BODY_FILTERS = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    MARGIN = 5.0
    LEVERAGE = 15
    LIMIT = 1000
    
    print("="*160)
    print(f"BTCUSDC STRATEGY OPTIMIZATION")
    print(f"Margin: ${MARGIN} | Leverage: {LEVERAGE}x | Position: ${MARGIN * LEVERAGE}")
    print(f"Testing {len(INTERVALS)} timeframes × {len(BODY_FILTERS)} body filters = {len(INTERVALS) * len(BODY_FILTERS)} configurations")
    print("="*160)
    
    all_results = []
    
    for interval in INTERVALS:
        print(f"\n{'='*160}")
        print(f"TESTING {SYMBOL} - {interval}")
        print(f"{'='*160}")
        print(f"Fetching data...")
        
        df = fetch_binance_klines(SYMBOL, interval, LIMIT)
        
        if df.empty:
            print(f"❌ Failed to fetch data for {interval}")
            continue
        
        df = analyze_wicks(df)
        
        # Split data: 300 for training, rest for testing
        training_df = df.iloc[:300].copy()
        testing_df = df.iloc[300:].copy()
        
        print(f"Training: {len(training_df)} candles | Testing: {len(testing_df)} candles")
        
        percentiles = calculate_percentiles(training_df)
        print(f"Target TP: {percentiles['lower_25th']:.3f}%")
        
        print(f"\n{'Body Filter':<12} {'P&L':<10} {'Win%':<8} {'Trades':<8} {'TP Hit%':<10} {'Avg W':<10} {'Avg L':<10} {'PF':<8} {'Result'}")
        print("-"*160)
        
        for body_filter in BODY_FILTERS:
            result = test_strategy(testing_df.reset_index(drop=True), percentiles, 
                                 body_filter, MARGIN, LEVERAGE)
            
            if result:
                all_results.append({
                    'interval': interval,
                    'body_filter': body_filter,
                    **result
                })
                
                profitable = "✅" if result['total_pnl'] > 0 else "❌"
                pf_str = f"{result['profit_factor']:.2f}" if result['profit_factor'] != float('inf') else "∞"
                
                print(f">{body_filter:.1f}%{'':<8} ${result['total_pnl']:>6.2f}{'':<3} "
                      f"{result['win_rate']:>5.1f}%{'':<2} {result['trades']:<8} "
                      f"{result['tp_hit_rate']:>5.1f}%{'':<4} "
                      f"${result['avg_win']:>5.2f}{'':<4} ${result['avg_loss']:>6.2f}{'':<3} "
                      f"{pf_str:<8} {profitable}")
    
    # Final Summary
    print("\n" + "="*160)
    print("COMPLETE RESULTS SUMMARY")
    print("="*160)
    
    profitable_results = [r for r in all_results if r['total_pnl'] > 0]
    print(f"\n📊 OVERALL STATISTICS:")
    print(f"   Total Configurations Tested: {len(all_results)}")
    print(f"   Profitable: {len(profitable_results)} ({len(profitable_results)/len(all_results)*100:.1f}%)")
    print(f"   Unprofitable: {len(all_results) - len(profitable_results)}")
    
    if profitable_results:
        profitable_results.sort(key=lambda x: x['total_pnl'], reverse=True)
        
        print(f"\n🏆 TOP 10 BEST CONFIGURATIONS:")
        print(f"{'Rank':<6} {'Timeframe':<12} {'Body Filter':<12} {'P&L':<10} {'Win%':<8} {'Trades':<8} {'TP Hit%':<10} {'PF':<8}")
        print("-"*160)
        for i, r in enumerate(profitable_results[:10], 1):
            pf_str = f"{r['profit_factor']:.2f}" if r['profit_factor'] != float('inf') else "∞"
            print(f"{i:<6} {r['interval']:<12} >{r['body_filter']:.1f}%{'':<8} "
                  f"${r['total_pnl']:>6.2f}{'':<3} {r['win_rate']:>5.1f}%{'':<2} "
                  f"{r['trades']:<8} {r['tp_hit_rate']:>5.1f}%{'':<4} {pf_str:<8}")
        
        # Best by timeframe
        print(f"\n📈 BEST CONFIGURATION PER TIMEFRAME:")
        print(f"{'Timeframe':<12} {'Body Filter':<12} {'P&L':<10} {'Win%':<8} {'Trades':<8} {'TP Hit%':<10}")
        print("-"*160)
        for interval in INTERVALS:
            interval_results = [r for r in profitable_results if r['interval'] == interval]
            if interval_results:
                best = max(interval_results, key=lambda x: x['total_pnl'])
                print(f"{best['interval']:<12} >{best['body_filter']:.1f}%{'':<8} "
                      f"${best['total_pnl']:>6.2f}{'':<3} {best['win_rate']:>5.1f}%{'':<2} "
                      f"{best['trades']:<8} {best['tp_hit_rate']:>5.1f}%{'':<4}")
        
        # Recommended configuration
        best_config = profitable_results[0]
        print(f"\n✨ RECOMMENDED CONFIGURATION FOR BOT 47:")
        print(f"   Symbol: BTCUSDC")
        print(f"   Timeframe: {best_config['interval']}")
        print(f"   Body Filter: {best_config['body_filter']}% (min_body_pct: {best_config['body_filter']/100})")
        print(f"   Expected P&L: ${best_config['total_pnl']:.2f}")
        print(f"   Win Rate: {best_config['win_rate']:.1f}%")
        print(f"   Number of Trades: {best_config['trades']}")
        print(f"   TP Hit Rate: {best_config['tp_hit_rate']:.1f}%")
        print(f"   Profit Factor: {best_config['profit_factor']:.2f}")
    
    print("\n" + "="*160)
    print("✅ OPTIMIZATION COMPLETE!")
    print("="*160)


if __name__ == "__main__":
    main()

# Made with Bob