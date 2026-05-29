"""
Wick Strategy Backtest
Analyzes candle wick percentage changes for BTCUSDC 1h timeframe
"""

import requests
import json
import pandas as pd
from datetime import datetime
from typing import List, Dict


def fetch_binance_klines(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    """
    Fetch historical kline data from Binance Futures API and return as DataFrame
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDC')
        interval: Timeframe (e.g., '1h', '4h', '1d')
        limit: Number of candles to fetch (max 1500)
    
    Returns:
        DataFrame with kline data
    """
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    
    print(f"Fetching {limit} candles for {symbol} {interval}...")
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        klines = response.json()
        print(f"Successfully fetched {len(klines)} candles")
        
        # Convert to DataFrame
        df = pd.DataFrame(klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        # Convert data types
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
        df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        return df
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()


def analyze_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze candles and add wick metrics to DataFrame
    
    Args:
        df: DataFrame with OHLC data
    
    Returns:
        DataFrame with added analysis columns
    """
    # Calculate body size and change
    df['body_size'] = abs(df['close'] - df['open'])
    df['body_change_pct'] = ((df['close'] - df['open']) / df['open']) * 100
    
    # Calculate upper wick (high - open) and percentage
    df['upper_wick'] = df['high'] - df['open']
    df['upper_wick_pct'] = (df['upper_wick'] / df['open']) * 100
    
    # Calculate lower wick (open - low) and percentage
    df['lower_wick'] = df['open'] - df['low']
    df['lower_wick_pct'] = (df['lower_wick'] / df['open']) * 100
    
    return df


def print_summary_statistics(df: pd.DataFrame):
    """
    Print summary statistics of the analysis
    
    Args:
        df: DataFrame with analysis results
    """
    print("\n" + "="*120)
    print("SUMMARY STATISTICS")
    print("="*120)
    print(f"Total Candles Analyzed: {len(df)}")
    
    print("\n" + "-"*120)
    print("PERCENTILE EXPLANATION:")
    print("- 10th percentile: 10% of candles have values below this, 90% above")
    print("- 25th percentile: 25% of candles have values below this, 75% above")
    print("- 50th percentile (Median): Half of candles are below, half above this value")
    print("- 75th percentile: 75% of candles have values below this, 25% above")
    print("- 90th percentile: 90% of candles have values below this, 10% above")
    print("-"*120)
    
    print("\n--- Body Change % ---")
    print(f"Average:      {df['body_change_pct'].mean():.4f}%")
    print(f"Median (50%): {df['body_change_pct'].median():.4f}%")
    print(f"Min:          {df['body_change_pct'].min():.4f}%")
    print(f"Max:          {df['body_change_pct'].max():.4f}%")
    print(f"10th %ile:    {df['body_change_pct'].quantile(0.10):.4f}%")
    print(f"25th %ile:    {df['body_change_pct'].quantile(0.25):.4f}%")
    print(f"75th %ile:    {df['body_change_pct'].quantile(0.75):.4f}%")
    print(f"90th %ile:    {df['body_change_pct'].quantile(0.90):.4f}%")
    
    print("\n--- Upper Wick % ---")
    print(f"Average:      {df['upper_wick_pct'].mean():.4f}%")
    print(f"Median (50%): {df['upper_wick_pct'].median():.4f}%")
    print(f"Min:          {df['upper_wick_pct'].min():.4f}%")
    print(f"Max:          {df['upper_wick_pct'].max():.4f}%")
    print(f"10th %ile:    {df['upper_wick_pct'].quantile(0.10):.4f}%")
    print(f"25th %ile:    {df['upper_wick_pct'].quantile(0.25):.4f}%")
    print(f"75th %ile:    {df['upper_wick_pct'].quantile(0.75):.4f}%")
    print(f"90th %ile:    {df['upper_wick_pct'].quantile(0.90):.4f}%")
    
    print("\n--- Lower Wick % ---")
    print(f"Average:      {df['lower_wick_pct'].mean():.4f}%")
    print(f"Median (50%): {df['lower_wick_pct'].median():.4f}%")
    print(f"Min:          {df['lower_wick_pct'].min():.4f}%")
    print(f"Max:          {df['lower_wick_pct'].max():.4f}%")
    print(f"10th %ile:    {df['lower_wick_pct'].quantile(0.10):.4f}%")
    print(f"25th %ile:    {df['lower_wick_pct'].quantile(0.25):.4f}%")
    print(f"75th %ile:    {df['lower_wick_pct'].quantile(0.75):.4f}%")
    print(f"90th %ile:    {df['lower_wick_pct'].quantile(0.90):.4f}%")
    
    max_upper_idx = df['upper_wick_pct'].idxmax()
    max_lower_idx = df['lower_wick_pct'].idxmax()
    
    print(f"\nMax Upper Wick at: {df.loc[max_upper_idx, 'open_time']}")
    print(f"Max Lower Wick at: {df.loc[max_lower_idx, 'open_time']}")
    print("="*120)


def save_results_to_file(df: pd.DataFrame, symbol: str, interval: str):
    """
    Save analysis results to CSV file
    
    Args:
        df: DataFrame with analysis results
        symbol: Trading pair symbol
        interval: Timeframe
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"backtest/custom/wick_strategy/{symbol}_{interval}_wick_analysis_{timestamp}.csv"
    
    df.to_csv(filename, index=False)
    
    print(f"\nResults saved to: {filename}")


def main():
    """
    Main function to run the wick analysis backtest
    """
    # Configuration
    SYMBOL = "BTCUSDC"
    INTERVAL = "1h"
    LIMIT = 24*30
    
    print("="*120)
    print("WICK STRATEGY BACKTEST")
    print(f"Symbol: {SYMBOL}")
    print(f"Timeframe: {INTERVAL}")
    print(f"Candles: {LIMIT}")
    print("="*120)
    
    # Fetch kline data as DataFrame
    df = fetch_binance_klines(SYMBOL, INTERVAL, LIMIT)
    
    if df.empty:
        print("Failed to fetch kline data. Exiting.")
        return

    df.tail()
    
    # Analyze candles
    print("\nAnalyzing candles...")
    df = analyze_dataframe(df)
    
    # Display last 20 rows with key columns
    print("\n" + "="*120)
    print("LAST 20 CANDLES WITH WICK ANALYSIS")
    print("="*120)
    
    # Select columns to display
    display_cols = ['open_time', 'open', 'high', 'low', 'close',
                    'body_change_pct', 'upper_wick_pct', 'lower_wick_pct']
    
    # Configure pandas display options
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 120)
    pd.set_option('display.float_format', '{:.4f}'.format)
    
    print(df[display_cols].tail(20).to_string(index=False))
    print("="*120)
    
    # Print summary statistics
    print_summary_statistics(df)
    
    # Save results to file
    save_results_to_file(df, SYMBOL, INTERVAL)
    
    print("\nAnalysis complete!")


if __name__ == "__main__":
    main()
