"""
Visualize Backtest Results using Pandas DataFrames
Displays backtest summary and trade history in pandas DataFrames.

Usage:
    python3 standalone_services/visualize_backtest_result.py
    
The script will list available backtest results and let you select one.
"""

import json
import os
import sys
from typing import Dict, Any, List
import pandas as pd


def list_backtest_results() -> List[str]:
    """List all available backtest result files."""
    results_dir = "backtest/results"
    
    if not os.path.exists(results_dir):
        print(f"Error: Directory '{results_dir}' not found.")
        return []
    
    files = [f for f in os.listdir(results_dir) if f.endswith('.json')]
    files.sort(reverse=True)  # Most recent first
    
    return files


def select_backtest_file(files: List[str]) -> str:
    """Display files and let user select one."""
    if not files:
        print("No backtest result files found.")
        sys.exit(1)
    
    print("\n" + "=" * 80)
    print("Available Backtest Results:")
    print("=" * 80)
    
    for idx, filename in enumerate(files, 1):
        # Extract info from filename
        filepath = os.path.join("backtest/results", filename)
        file_size = os.path.getsize(filepath)
        file_time = os.path.getmtime(filepath)
        
        from datetime import datetime
        mod_time = datetime.fromtimestamp(file_time).strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"{idx:3}. {filename:<50} ({file_size:>8} bytes) - {mod_time}")
    
    print("=" * 80)
    
    while True:
        try:
            selection = input(f"\nSelect a file (1-{len(files)}) or 'q' to quit: ").strip()
            
            if selection.lower() == 'q':
                print("Exiting...")
                sys.exit(0)
            
            idx = int(selection)
            if 1 <= idx <= len(files):
                return os.path.join("backtest/results", files[idx - 1])
            else:
                print(f"Please enter a number between 1 and {len(files)}")
        except ValueError:
            print("Invalid input. Please enter a number or 'q' to quit.")
        except KeyboardInterrupt:
            print("\n\nExiting...")
            sys.exit(0)


def load_backtest_results(filepath: str) -> Dict[str, Any]:
    """Load backtest results from JSON file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON file: {filepath}")
        sys.exit(1)


def visualize_bot_config(bot_config: Dict[str, Any]) -> pd.DataFrame:
    """
    Create and display pandas DataFrame of bot configuration.
    
    Args:
        bot_config: Dictionary containing bot configuration
        
    Returns:
        pandas DataFrame with bot configuration
    """
    config_data = {
        'Parameter': [
            'Bot Name',
            'Run ID',
            'Symbol',
            'Timeframe',
            'Entry Strategy',
            'Exit Strategy',
            'Order Type',
            'Leverage',
            'SL Enabled',
            'TP Enabled',
            'Run Mode',
            'Trade Client'
        ],
        'Value': [
            bot_config.get('bot_name', 'N/A'),
            bot_config.get('run_id', 'N/A'),
            bot_config.get('symbol', 'N/A'),
            bot_config.get('timeframe', 'N/A'),
            bot_config.get('entry_strategy', 'N/A'),
            bot_config.get('exit_strategy', 'N/A'),
            bot_config.get('order_type', 'N/A'),
            bot_config.get('leverage', 'N/A'),
            bot_config.get('sl_enabled', 'N/A'),
            bot_config.get('tp_enabled', 'N/A'),
            bot_config.get('run_mode', 'N/A'),
            bot_config.get('trade_client', 'N/A')
        ]
    }
    
    df = pd.DataFrame(config_data)
    
    print("\n" + "=" * 80)
    print("BOT CONFIGURATION")
    print("=" * 80)
    print(df.to_string(index=False))
    print("=" * 80)
    
    return df


def visualize_summary(summary: Dict[str, Any]) -> pd.DataFrame:
    """
    Create and display pandas DataFrame of summary metrics.
    
    Args:
        summary: Dictionary containing summary metrics
        
    Returns:
        pandas DataFrame with summary metrics
    """
    # Organize metrics into categories
    data = {
        'Metric': [],
        'Value': []
    }
    
    # Trade Statistics
    data['Metric'].extend([
        'Total Trades',
        'Winning Trades',
        'Losing Trades',
        'Breakeven Trades',
        'Win Rate'
    ])
    data['Value'].extend([
        summary.get('total_trades', 0),
        summary.get('winning_trades', 0),
        summary.get('losing_trades', 0),
        summary.get('breakeven_trades', 0),
        f"{summary.get('win_rate', 0):.2%}"
    ])
    
    # Financial Metrics
    data['Metric'].extend([
        'Total PnL',
        'Gross Profit',
        'Gross Loss',
        'Total Fees',
        'Net PnL',
        'ROI',
        'Monthly ROI'
    ])
    data['Value'].extend([
        f"${summary.get('total_pnl', 0):.2f}",
        f"${summary.get('gross_profit', 0):.2f}",
        f"${summary.get('gross_loss', 0):.2f}",
        f"${summary.get('total_fees', 0):.2f}",
        f"${summary.get('net_pnl', 0):.2f}",
        f"{summary.get('roi', 0):.2%}",
        f"{summary.get('monthly_roi', 0):.2%}"
    ])
    
    # Performance Metrics
    data['Metric'].extend([
        'Average Win',
        'Average Loss',
        'Profit Factor',
        'Max Consecutive Wins',
        'Max Consecutive Losses',
        'Max Drawdown',
        'Max Drawdown %',
        'Days Traded'
    ])
    data['Value'].extend([
        f"${summary.get('avg_win', 0):.2f}",
        f"${summary.get('avg_loss', 0):.2f}",
        f"{summary.get('profit_factor', 0):.2f}",
        summary.get('max_consecutive_wins', 0),
        summary.get('max_consecutive_losses', 0),
        f"${summary.get('max_drawdown', 0):.2f}",
        f"{summary.get('max_drawdown_pct', 0):.2%}",
        summary.get('days_traded', 0)
    ])
    
    df = pd.DataFrame(data)
    
    print("\n" + "=" * 80)
    print("BACKTEST SUMMARY")
    print("=" * 80)
    print(df.to_string(index=False))
    print("=" * 80 + "\n")
    
    return df


def visualize_position_records(trades: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Create and display pandas DataFrame of position records.
    
    Args:
        trades: List of trade dictionaries
        
    Returns:
        pandas DataFrame with trade records
    """
    if not trades:
        print("No trades to display.\n")
        return pd.DataFrame()
    
    # Prepare data for DataFrame
    records = []
    cumulative_pnl = 0.0
    
    for idx, trade in enumerate(trades, 1):
        '''
        {
            "run_id": 31,
            "symbol": "DOGEUSDC",
            "position_side": "SHORT",
            "entry_price": 0.08051,
            "open_candle": "2024-01-22 07:00:00+07:00",
            "open_reason": "DOGEUSDC Entry Signal | Previous candle negative -> SHORT: \u2705, sl price 0.09037 > current price 0.08051: \u2705",
            "open_time": "2024-01-22 07:00:00+07:00",
            "open_fee": 0.0,
            "close_time": "2024-01-23 07:00:00+07:00",
            "close_price": 0.07816,
            "pnl": 1.1750000000000025,
            "close_reason": "DOGEUSDC Exit Signal | SHORT | price 0.07816 >= SL 0.09037: \u274c | New Candle - pos 01-22 07:00 / cur 01-23 07:00: \u2705",
            "close_fee": 0.0,
            "max_pnl": 1.1750000000000025,
            "min_pnl": 0.0
        }
        '''
        pnl = trade.get('pnl', 0)
        open_fee = trade.get('open_fee', 0)
        close_fee = trade.get('close_fee', 0)
        total_fee = open_fee + close_fee
        net_pnl = pnl - total_fee
        cumulative_pnl += net_pnl
        
        # Extract date from open_time
        open_time = trade.get('open_time', '')
        trade_date = open_time.split(' ')[0] if open_time else 'N/A'
        
        record = {
            '#': idx,
            'Date': trade_date,
            'PnL': round(pnl, 4),
            'Net PnL': round(net_pnl, 4),
            'Cumulative PnL': round(cumulative_pnl, 4),
            'Total Fee': round(total_fee, 4),
            'Open Fee': round(open_fee, 4),
            'Close Fee': round(close_fee, 4),
            'Side': trade.get('position_side', 'N/A'),
            'Entry Price': round(trade.get('entry_price', 0), 4),
            'Close Price': round(trade.get('close_price', 0), 4),
            'Max PnL': round(trade.get('max_pnl', 0), 4),
            'Min PnL': round(trade.get('min_pnl', 0), 4),
            'Open Time': trade.get('open_time', 'N/A'),
            'Close Time': trade.get('close_time', 'N/A'),
            'Open Reason': trade.get('open_reason', 'N/A'),
            'Close Reason': trade.get('close_reason', 'N/A')
        }
        records.append(record)
    
    df = pd.DataFrame(records)
    
    print("\n" + "=" * 200)
    print("POSITION RECORDS")
    print("=" * 200)
    
    # Display with pandas options for better formatting
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 200)
    pd.set_option('display.max_rows', None)
    
    print(df.to_string(index=False))
    print("=" * 200 + "\n")
    
    # Print summary
    print(f"Total Trades: {len(trades)}")
    print(f"Final Cumulative PnL: ${cumulative_pnl:.2f}\n")
    
    return df


def main():
    """Main function to visualize backtest results."""
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS VISUALIZER")
    print("=" * 80)
    
    # List and select backtest file
    files = list_backtest_results()
    filepath = select_backtest_file(files)
    
    print(f"\nLoading: {filepath}")
    results = load_backtest_results(filepath)
    
    # Extract data
    bot_config = results.get('bot_config', {})
    summary = results.get('summary', {})
    trades = results.get('trades', [])
    
    # Visualize in order: 1. Records, 2. Config, 3. Performance
    
    # 1. Visualize position records
    trades_df = visualize_position_records(trades)
    
    # 2. Visualize bot configuration
    config_df = visualize_bot_config(bot_config)
    
    # 3. Visualize summary (performance)
    summary_df = visualize_summary(summary)
    
    # Option to save to CSV
    print("\nOptions:")
    print("1. Save config to CSV")
    print("2. Save summary to CSV")
    print("3. Save trades to CSV")
    print("4. Save all to CSV")
    print("5. Exit")
    
    try:
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == '1':
            filename = filepath.replace('.json', '_config.csv')
            config_df.to_csv(filename, index=False)
            print(f"Config saved to: {filename}")
        elif choice == '2':
            filename = filepath.replace('.json', '_summary.csv')
            summary_df.to_csv(filename, index=False)
            print(f"Summary saved to: {filename}")
        elif choice == '3':
            filename = filepath.replace('.json', '_trades.csv')
            trades_df.to_csv(filename, index=False)
            print(f"Trades saved to: {filename}")
        elif choice == '4':
            config_filename = filepath.replace('.json', '_config.csv')
            summary_filename = filepath.replace('.json', '_summary.csv')
            trades_filename = filepath.replace('.json', '_trades.csv')
            config_df.to_csv(config_filename, index=False)
            summary_df.to_csv(summary_filename, index=False)
            trades_df.to_csv(trades_filename, index=False)
            print(f"Config saved to: {config_filename}")
            print(f"Summary saved to: {summary_filename}")
            print(f"Trades saved to: {trades_filename}")
        elif choice == '5':
            print("Exiting...")
        else:
            print("Invalid choice. Exiting...")
    except KeyboardInterrupt:
        print("\n\nExiting...")
    
    print("\nDone!\n")


if __name__ == "__main__":
    main()

# Made with Bob
