"""
Multi-Symbol Wick Mean Reversion Strategy Optimization
Test BTC and ETH across multiple timeframes and body filters
"""

import requests
import pandas as pd
from typing import Dict, List
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


def calculate_percentiles(df: pd.DataFrame, percentile: float = 0.25) -> Dict[str, float]:
    """Calculate percentiles for TP targets
    
    Args:
        df: DataFrame with wick data
        percentile: Percentile value (0.0 to 1.0), default 0.25 for 25th percentile
    """
    return {
        'upper_percentile': df['upper_wick_pct'].quantile(percentile),
        'lower_percentile': df['lower_wick_pct'].quantile(percentile),
    }


def test_strategy(df: pd.DataFrame, percentiles: Dict, min_body_pct: float,
                 margin: float = 5.0, leverage: int = 15):
    """Test mean reversion strategy with body filter"""
    trades = []
    position_size = margin * leverage
    target_pct = percentiles['lower_percentile']
    
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


def optimize_symbol(symbol: str, intervals: List[str], body_filters: List[float],
                    margin: float, leverage: int, limit: int, percentiles: List[float]):
    """Optimize strategy for a single symbol across multiple percentiles
    
    Args:
        symbol: Trading symbol
        intervals: List of timeframe intervals
        body_filters: List of minimum body percentage filters
        margin: Margin amount
        leverage: Leverage multiplier
        limit: Number of candles to fetch
        percentiles: List of percentiles for TP target calculation
    """
    print(f"\n{'='*160}")
    print(f"OPTIMIZING {symbol}")
    print(f"{'='*160}")
    
    all_results = []
    
    for interval in intervals:
        print(f"\n{'='*160}")
        print(f"TESTING {symbol} - {interval}")
        print(f"{'='*160}")
        print(f"Fetching data...")
        
        df = fetch_binance_klines(symbol, interval, limit)
        
        if df.empty:
            print(f"❌ Failed to fetch data for {interval}")
            continue
        
        df = analyze_wicks(df)
        
        # Split data: 300 for training, rest for testing
        training_df = df.iloc[:300].copy()
        testing_df = df.iloc[300:].copy()
        
        print(f"Training: {len(training_df)} candles | Testing: {len(testing_df)} candles")
        
        # Test all percentiles on the same data
        for percentile in percentiles:
            percentile_targets = calculate_percentiles(training_df, percentile)
            
            print(f"\n--- Testing {int(percentile*100)}th Percentile (TP: {percentile_targets['lower_percentile']:.3f}%) ---")
            print(f"{'Body Filter':<12} {'P&L':<10} {'Win%':<8} {'Trades':<8} {'TP Hit%':<10} {'Avg W':<10} {'Avg L':<10} {'PF':<8} {'Result'}")
            print("-"*160)
            
            for body_filter in body_filters:
                result = test_strategy(testing_df.reset_index(drop=True), percentile_targets,
                                     body_filter, margin, leverage)
                
                if result:
                    all_results.append({
                        'symbol': symbol,
                        'interval': interval,
                        'body_filter': body_filter,
                        'percentile': percentile,
                        **result
                    })
                    
                    profitable = "✅" if result['total_pnl'] > 0 else "❌"
                    pf_str = f"{result['profit_factor']:.2f}" if result['profit_factor'] != float('inf') else "∞"
                    
                    print(f">{body_filter:.1f}%{'':<8} ${result['total_pnl']:>6.2f}{'':<3} "
                          f"{result['win_rate']:>5.1f}%{'':<2} {result['trades']:<8} "
                          f"{result['tp_hit_rate']:>5.1f}%{'':<4} "
                          f"${result['avg_win']:>5.2f}{'':<4} ${result['avg_loss']:>6.2f}{'':<3} "
                          f"{pf_str:<8} {profitable}")
    
    return all_results


def print_summary(all_results: List[Dict], symbol: str):
    """Print summary for a symbol"""
    symbol_results = [r for r in all_results if r['symbol'] == symbol]
    profitable_results = [r for r in symbol_results if r['total_pnl'] > 0]
    
    print(f"\n{'='*160}")
    print(f"{symbol} SUMMARY")
    print(f"{'='*160}")
    
    print(f"\n📊 STATISTICS:")
    print(f"   Total Configurations: {len(symbol_results)}")
    print(f"   Profitable: {len(profitable_results)} ({len(profitable_results)/len(symbol_results)*100:.1f}%)")
    print(f"   Unprofitable: {len(symbol_results) - len(profitable_results)}")
    
    if profitable_results:
        profitable_results.sort(key=lambda x: x['total_pnl'], reverse=True)
        
        print(f"\n🏆 TOP 5 CONFIGURATIONS:")
        print(f"{'Rank':<6} {'Timeframe':<12} {'Body Filter':<12} {'Percentile':<12} {'P&L':<10} {'Win%':<8} {'Trades':<8} {'TP Hit%':<10} {'PF':<8}")
        print("-"*160)
        for i, r in enumerate(profitable_results[:5], 1):
            pf_str = f"{r['profit_factor']:.2f}" if r['profit_factor'] != float('inf') else "∞"
            percentile_str = f"{int(r.get('percentile', 0.25)*100)}th" if 'percentile' in r else "25th"
            print(f"{i:<6} {r['interval']:<12} >{r['body_filter']:.1f}%{'':<8} "
                  f"{percentile_str:<12} ${r['total_pnl']:>6.2f}{'':<3} {r['win_rate']:>5.1f}%{'':<2} "
                  f"{r['trades']:<8} {r['tp_hit_rate']:>5.1f}%{'':<4} {pf_str:<8}")
        
        # Best configuration
        best = profitable_results[0]
        percentile_str = f"{int(best.get('percentile', 0.25)*100)}th" if 'percentile' in best else "25th"
        print(f"\n✨ RECOMMENDED CONFIGURATION:")
        print(f"   Symbol: {symbol}")
        print(f"   Timeframe: {best['interval']}")
        print(f"   Body Filter: {best['body_filter']}% (min_body_pct: {best['body_filter']/100})")
        print(f"   Percentile: {percentile_str}")
        print(f"   Expected P&L: ${best['total_pnl']:.2f}")
        print(f"   Win Rate: {best['win_rate']:.1f}%")
        print(f"   Trades: {best['trades']}")
        print(f"   TP Hit Rate: {best['tp_hit_rate']:.1f}%")
        print(f"   Profit Factor: {best['profit_factor']:.2f}")
    else:
        print(f"\n❌ No profitable configurations found for {symbol}")


def print_percentile_analysis(all_results: List[Dict]):
    """Analyze and print best percentile for each symbol"""
    print(f"\n{'='*160}")
    print("PERCENTILE ANALYSIS")
    print(f"{'='*160}")
    
    symbols = list(set([r['symbol'] for r in all_results]))
    percentiles = sorted(list(set([r.get('percentile', 0.25) for r in all_results if 'percentile' in r])))
    
    for symbol in symbols:
        print(f"\n{symbol}:")
        print(f"{'Percentile':<15} {'Profitable':<12} {'Total P&L':<12} {'Avg P&L':<12} {'Best Config P&L':<15}")
        print("-"*160)
        
        for percentile in percentiles:
            symbol_percentile_results = [r for r in all_results
                                        if r['symbol'] == symbol and r.get('percentile') == percentile]
            profitable = [r for r in symbol_percentile_results if r['total_pnl'] > 0]
            total_pnl = sum([r['total_pnl'] for r in profitable])
            avg_pnl = total_pnl / len(profitable) if profitable else 0
            best_pnl = max([r['total_pnl'] for r in profitable]) if profitable else 0
            
            percentile_str = f"{int(percentile*100)}th"
            print(f"{percentile_str:<15} {len(profitable)}/{len(symbol_percentile_results):<10} "
                  f"${total_pnl:>8.2f}{'':<3} ${avg_pnl:>8.2f}{'':<3} ${best_pnl:>10.2f}")


def main():
    # Configuration
    SYMBOLS = ['BTCUSDC', 'ETHUSDC']
    INTERVALS = ['5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d']
    BODY_FILTERS = [
        # Fine-grained low range (0.05% - 0.5%)
        0.05, 0.08, 0.1, 0.12, 0.15, 0.18, 0.2, 0.22, 0.25, 0.28, 0.3, 0.35, 0.4, 0.45, 0.5,
        # Medium range (0.5% - 1.5%)
        0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5,
        # Higher range (1.5% - 3.0%)
        1.6, 1.7, 1.8, 1.9, 2.0, 2.2, 2.4, 2.5, 2.6, 2.8, 3.0,
        # Extended range (3.0% - 5.0%)
        3.5, 4.0, 4.5, 5.0
    ]
    PERCENTILES = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]  # Test multiple percentiles
    MARGIN = 5.0
    LEVERAGE = 15
    LIMIT = 500
    
    print("="*160)
    print(f"MULTI-SYMBOL WICK STRATEGY OPTIMIZATION WITH PERCENTILE SEARCH")
    print(f"Symbols: {', '.join(SYMBOLS)}")
    print(f"Margin: ${MARGIN} | Leverage: {LEVERAGE}x | Position: ${MARGIN * LEVERAGE}")
    print(f"Testing Percentiles: {[int(p*100) for p in PERCENTILES]}")
    print(f"Testing {len(SYMBOLS)} symbols × {len(INTERVALS)} timeframes × {len(BODY_FILTERS)} body filters × {len(PERCENTILES)} percentiles")
    print(f"Total configurations: {len(SYMBOLS) * len(INTERVALS) * len(BODY_FILTERS) * len(PERCENTILES)}")
    print(f"API calls optimized: Fetching each symbol/interval only once, testing all percentiles on same data")
    print("="*160)
    
    all_results = []
    
    for symbol in SYMBOLS:
        symbol_results = optimize_symbol(symbol, INTERVALS, BODY_FILTERS, MARGIN, LEVERAGE, LIMIT, PERCENTILES)
        all_results.extend(symbol_results)
    
    # Print summaries
    for symbol in SYMBOLS:
        print_summary(all_results, symbol)
    
    # Percentile analysis
    print_percentile_analysis(all_results)
    
    # Overall comparison
    print(f"\n{'='*160}")
    print("OVERALL COMPARISON - BEST CONFIGURATION PER SYMBOL")
    print(f"{'='*160}")
    
    for symbol in SYMBOLS:
        symbol_results = [r for r in all_results if r['symbol'] == symbol and r['total_pnl'] > 0]
        if symbol_results:
            best = max(symbol_results, key=lambda x: x['total_pnl'])
            percentile_str = f"{int(best.get('percentile', 0.25)*100)}th" if 'percentile' in best else "25th"
            print(f"\n{symbol}:")
            print(f"  Best: {best['interval']} with >{best['body_filter']:.1f}% body filter, {percentile_str} percentile")
            print(f"  P&L: ${best['total_pnl']:.2f} | Win Rate: {best['win_rate']:.1f}% | Trades: {best['trades']} | PF: {best['profit_factor']:.2f}")
    
    print("\n" + "="*160)
    print("✅ OPTIMIZATION COMPLETE!")
    print("="*160)


if __name__ == "__main__":
    main()

# Made with Bob