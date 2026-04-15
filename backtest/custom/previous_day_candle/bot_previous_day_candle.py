import sys
from pathlib import Path
import numpy as np
import pandas as pd
import json
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from trade_clients.binance.binance_live_trade_client import BinanceLiveTradeClient


# ============================================================================
# HELPER FUNCTIONS FOR ADVANCED METRICS
# ============================================================================

def calculate_max_drawdown(equity_curve):
    """
    Calculate maximum drawdown from equity curve
    
    Args:
        equity_curve: List of capital values over time
    
    Returns:
        tuple: (max_drawdown_percent, max_drawdown_value, peak_value, trough_value)
    """
    if not equity_curve or len(equity_curve) < 2:
        return 0, 0, 0, 0
    
    peak = equity_curve[0]
    max_dd = 0
    max_dd_value = 0
    peak_val = equity_curve[0]
    trough_val = equity_curve[0]
    
    for value in equity_curve:
        if value > peak:
            peak = value
        
        drawdown = peak - value
        drawdown_percent = (drawdown / peak * 100) if peak > 0 else 0
        
        if drawdown_percent > max_dd:
            max_dd = drawdown_percent
            max_dd_value = drawdown
            peak_val = peak
            trough_val = value
    
    return max_dd, max_dd_value, peak_val, trough_val


def calculate_profit_factor(trade_details):
    """
    Calculate profit factor (total profits / total losses)
    
    Args:
        trade_details: List of trade dictionaries with 'pnl' key
    
    Returns:
        float: Profit factor (0 if no losses)
    """
    if not trade_details:
        return 0
    
    total_profit = sum(trade['pnl'] for trade in trade_details if trade['pnl'] > 0)
    total_loss = abs(sum(trade['pnl'] for trade in trade_details if trade['pnl'] < 0))
    
    if total_loss == 0:
        return float('inf') if total_profit > 0 else 0
    
    return total_profit / total_loss


def calculate_expectancy(trade_details, win_rate):
    """
    Calculate expectancy per trade: (win_rate × avg_win) - (loss_rate × avg_loss)
    
    Args:
        trade_details: List of trade dictionaries with 'pnl' key
        win_rate: Win rate as percentage (0-100)
    
    Returns:
        float: Expectancy value
    """
    if not trade_details:
        return 0
    
    winning_trades = [trade['pnl'] for trade in trade_details if trade['pnl'] > 0]
    losing_trades = [abs(trade['pnl']) for trade in trade_details if trade['pnl'] < 0]
    
    avg_win = sum(winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(losing_trades) / len(losing_trades) if losing_trades else 0
    
    win_rate_decimal = win_rate / 100
    loss_rate_decimal = 1 - win_rate_decimal
    
    expectancy = (win_rate_decimal * avg_win) - (loss_rate_decimal * avg_loss)
    
    return expectancy


def calculate_sharpe_ratio(equity_curve, risk_free_rate=0.0):
    """
    Calculate Sharpe ratio from equity curve returns (CORRECT METHOD)
    
    Args:
        equity_curve: List of capital values over time
        risk_free_rate: Annual risk-free rate (default 0%)
    
    Returns:
        tuple: (sharpe_ratio, annualized_sharpe_ratio)
    """
    if not equity_curve or len(equity_curve) < 2:
        return 0, 0
    
    # Calculate returns from equity curve: (current - previous) / previous
    returns = []
    for i in range(1, len(equity_curve)):
        if equity_curve[i-1] != 0:
            ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1] * 100
            returns.append(ret)
    
    if len(returns) < 2:
        return 0, 0
    
    mean_return = np.mean(returns)
    std_return = np.std(returns, ddof=1)
    
    if std_return == 0:
        return 0, 0
    
    sharpe = (mean_return - risk_free_rate) / std_return
    
    # Annualized Sharpe: multiply by sqrt(252) for daily-equivalent returns
    annualized_sharpe = sharpe * np.sqrt(252)
    
    return sharpe, annualized_sharpe


def calculate_distribution_stats(trade_details):
    """
    Calculate distribution statistics for trades
    
    Args:
        trade_details: List of trade dictionaries with 'pnl' key
    
    Returns:
        dict: Distribution statistics
    """
    if not trade_details:
        return {
            'best_trade': 0,
            'worst_trade': 0,
            'median_trade': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'best_trade_percent': 0,
            'worst_trade_percent': 0,
            'median_trade_percent': 0
        }
    
    pnls = [trade['pnl'] for trade in trade_details]
    pnl_percents = [trade['pnl_percent'] for trade in trade_details]
    
    winning_trades = [trade['pnl'] for trade in trade_details if trade['pnl'] > 0]
    losing_trades = [trade['pnl'] for trade in trade_details if trade['pnl'] < 0]
    
    return {
        'best_trade': max(pnls),
        'worst_trade': min(pnls),
        'median_trade': np.median(pnls),
        'avg_win': sum(winning_trades) / len(winning_trades) if winning_trades else 0,
        'avg_loss': sum(losing_trades) / len(losing_trades) if losing_trades else 0,
        'best_trade_percent': max(pnl_percents),
        'worst_trade_percent': min(pnl_percents),
        'median_trade_percent': np.median(pnl_percents)
    }


def calculate_consistency_metrics(trade_details):
    """
    Calculate consistency metrics (consecutive wins/losses)
    
    Args:
        trade_details: List of trade dictionaries with 'pnl' key
    
    Returns:
        dict: Consistency metrics
    """
    if not trade_details:
        return {
            'max_consecutive_wins': 0,
            'max_consecutive_losses': 0,
            'current_streak': 0,
            'current_streak_type': 'None'
        }
    
    max_wins = 0
    max_losses = 0
    current_wins = 0
    current_losses = 0
    
    for trade in trade_details:
        if trade['pnl'] > 0:
            current_wins += 1
            current_losses = 0
            max_wins = max(max_wins, current_wins)
        elif trade['pnl'] < 0:
            current_losses += 1
            current_wins = 0
            max_losses = max(max_losses, current_losses)
        else:
            # Break even trade
            current_wins = 0
            current_losses = 0
    
    # Determine current streak
    if current_wins > 0:
        current_streak = current_wins
        streak_type = 'Wins'
    elif current_losses > 0:
        current_streak = current_losses
        streak_type = 'Losses'
    else:
        current_streak = 0
        streak_type = 'None'
    
    return {
        'max_consecutive_wins': max_wins,
        'max_consecutive_losses': max_losses,
        'current_streak': current_streak,
        'current_streak_type': streak_type
    }


def calculate_calmar_ratio(return_percent, max_drawdown_percent):
    """
    Calculate Calmar Ratio (return / max drawdown)
    
    Args:
        return_percent: Total return percentage
        max_drawdown_percent: Maximum drawdown percentage
    
    Returns:
        float: Calmar ratio (0 if MDD is 0)
    """
    if max_drawdown_percent == 0:
        return 0 if return_percent <= 0 else float('inf')
    
    return return_percent / max_drawdown_percent


def calculate_normalized_metrics(trade_count, running_time_days, expectancy):
    """
    Calculate normalized metrics for cross-timeframe comparison
    
    Args:
        trade_count: Total number of trades
        running_time_days: Total running time in days
        expectancy: Expectancy per trade
    
    Returns:
        tuple: (trades_per_day, expectancy_per_day)
    """
    if running_time_days <= 0:
        return 0, 0
    
    trades_per_day = trade_count / running_time_days
    expectancy_per_day = expectancy * trades_per_day
    
    return trades_per_day, expectancy_per_day


def calculate_unified_score(expectancy, profit_factor, calmar_ratio, max_drawdown_percent):
    """
    Calculate unified score for bot ranking
    
    Formula: (expectancy * 100) + (profit_factor * 50) + (calmar_ratio * 30) - (max_drawdown_percent * 1.5)
    
    Args:
        expectancy: Expectancy per trade
        profit_factor: Profit factor
        calmar_ratio: Calmar ratio
        max_drawdown_percent: Maximum drawdown percentage
    
    Returns:
        float: Unified score
    """
    # Handle infinity in profit factor
    pf_value = min(profit_factor, 10.0) if profit_factor != float('inf') else 10.0
    
    # Handle infinity in calmar ratio
    calmar_value = min(calmar_ratio, 10.0) if calmar_ratio != float('inf') else 10.0
    
    score = (expectancy * 100) + (pf_value * 50) + (calmar_value * 30) - (max_drawdown_percent * 1.5)
    
    return score


def calculate_compounded_roi(initial_capital, final_capital, days):
    """
    Calculate compounded annualized ROI
    
    Args:
        initial_capital: Starting capital
        final_capital: Ending capital
        days: Number of days
    
    Returns:
        tuple: (annualized_roi, monthly_roi)
    """
    if initial_capital <= 0 or days <= 0:
        return 0, 0
    
    # Handle edge case: if final capital is <= 0 (total loss), return -100%
    if final_capital <= 0:
        return -100.0, -100.0
    
    ratio = final_capital / initial_capital
    
    # Handle edge case: if ratio is negative (shouldn't happen but just in case)
    if ratio < 0:
        return -100.0, -100.0
    
    # Compounded annualized ROI: ((final/initial)^(365/days)) - 1
    annualized_roi = (pow(ratio, 365 / days) - 1) * 100
    
    # Compounded monthly ROI: ((final/initial)^(30/days)) - 1
    monthly_roi = (pow(ratio, 30 / days) - 1) * 100
    
    return annualized_roi, monthly_roi



def run_backtest(symbol, timeframe, quantity, enable_sl, initial_capital=10, leverage=10, timeframe_limit=100, debug_mode=False, debug_trades_to_show=100):
    """
    Run backtest for previous day candle color strategy
    
    Args:
        symbol: Trading symbol (e.g., "DOGEUSDC")
        timeframe: Timeframe for klines (e.g., "1h", "4h", "1d")
        quantity: Quantity per trade
        enable_sl: Enable stop loss (True/False)
        initial_capital: Starting capital in USDC
        leverage: Leverage multiplier
        timeframe_limit: Number of candles to fetch
        debug_mode: Enable debug output
        debug_trades_to_show: Number of trades to show in debug mode
    
    Returns:
        dict: Backtest results including metrics and trade details
    """
    from datetime import datetime, timedelta
    
    bn_client = BinanceLiveTradeClient()
    bn_client.init()

    # 1. Fetch klines
    klines = bn_client.fetch_klines(symbol=symbol, timeframe=timeframe, timeframe_limit=timeframe_limit)

    if debug_mode:
        print(f"Total klines fetched: {len(klines)}")
    
    # Get start and end times
    start_time = klines.iloc[0]['open_time'] if len(klines) > 0 else None
    end_time = klines.iloc[-1]['close_time'] if len(klines) > 0 else None
    
    # Calculate running time in days
    running_time_days = 0
    start_date_str = 'N/A'
    end_date_str = 'N/A'
    
    if start_time is not None and end_time is not None:
        # Convert to datetime if needed
        if hasattr(start_time, 'timestamp'):
            # It's a pandas Timestamp
            start_dt = start_time.to_pydatetime()
            end_dt = end_time.to_pydatetime()
        else:
            # It's a millisecond timestamp
            start_dt = datetime.fromtimestamp(start_time / 1000)
            end_dt = datetime.fromtimestamp(end_time / 1000)
        
        running_time_days = (end_dt - start_dt).total_seconds() / (24 * 3600)
        start_date_str = start_dt.strftime('%Y-%m-%d %H:%M:%S')
        end_date_str = end_dt.strftime('%Y-%m-%d %H:%M:%S')

    # Initialize tracking variables
    current_capital = initial_capital
    total_pnl = 0
    total_pnl_percent = 0
    trade_count = 0
    winning_trades = 0
    losing_trades = 0
    long_trades = 0
    short_trades = 0
    long_wins = 0
    short_wins = 0
    sl_triggered_count = 0
    trade_details = []
    
    # Equity curve tracking (capital after each trade)
    equity_curve = [initial_capital]

    # Track current position
    current_position = None  # Will store: {'side': 'LONG'/'SHORT', 'entry_price': float, 'entry_time': int, 'sl_price': float}

    # 2. Loop through klines starting from index 1 (we need t-1 to exist)
    for i in range(1, len(klines)):
        candle_t_minus_1 = klines.iloc[i - 1]
        candle_t = klines.iloc[i]
        
        # Extract prices
        open_t_minus_1 = float(candle_t_minus_1['open'])
        close_t_minus_1 = float(candle_t_minus_1['close'])
        high_t_minus_1 = float(candle_t_minus_1['high'])
        low_t_minus_1 = float(candle_t_minus_1['low'])
        open_t = float(candle_t['open'])
        high_t = float(candle_t['high'])
        low_t = float(candle_t['low'])
        
        # Determine if t-1 is red (bearish) or green (bullish)
        is_red = close_t_minus_1 < open_t_minus_1
        is_green = close_t_minus_1 > open_t_minus_1
        
        # Debug output for each iteration
        if debug_mode and i <= debug_trades_to_show:
            print(f"\n{'='*100}")
            print(f"ITERATION {i}")
            print(f"{'='*100}")
            print(f"Candle t-1 (index {i-1}): Open={open_t_minus_1:.6f}, Close={close_t_minus_1:.6f}, High={high_t_minus_1:.6f}, Low={low_t_minus_1:.6f}")
            print(f"  -> Color: {'RED (bearish)' if is_red else 'GREEN (bullish)' if is_green else 'DOJI'}")
            print(f"Candle t   (index {i}):   Open={open_t:.6f}, High={high_t:.6f}, Low={low_t:.6f}")
            if current_position:
                print(f"Current Position: {current_position['side']} @ Entry={current_position['entry_price']:.6f}, SL={current_position['sl_price']:.6f}")
            else:
                print(f"Current Position: None")
        
        # At start of t, close existing position if any
        if current_position is not None:
            entry_price = current_position['entry_price']
            sl_price = current_position['sl_price']
            side = current_position['side']
            sl_hit = False
            exit_price = open_t
            
            if debug_mode and i <= debug_trades_to_show:
                print(f"\n--- CLOSING POSITION ---")
                print(f"Position: {side} @ Entry={entry_price:.6f}, SL={sl_price:.6f}")
                print(f"Candle t-1 High={high_t_minus_1:.6f}, Low={low_t_minus_1:.6f}")
                print(f"Candle t   Open={open_t:.6f}")
            
            # Check if stop loss was hit during candle t-1 (the candle where position was active)
            if enable_sl:
                if side == 'LONG':
                    # For LONG, check if low of candle t-1 hit the SL (below SL price)
                    if low_t_minus_1 <= sl_price:
                        sl_hit = True
                        exit_price = sl_price
                        sl_triggered_count += 1
                        if debug_mode and i <= debug_trades_to_show:
                            print(f"  -> LONG SL HIT! t-1 Low={low_t_minus_1:.6f} <= SL={sl_price:.6f}, Exit @ {exit_price:.6f}")
                else:  # SHORT
                    # For SHORT, check if high of candle t-1 hit the SL (above SL price)
                    if high_t_minus_1 >= sl_price:
                        sl_hit = True
                        exit_price = sl_price
                        sl_triggered_count += 1
                        if debug_mode and i <= debug_trades_to_show:
                            print(f"  -> SHORT SL HIT! t-1 High={high_t_minus_1:.6f} >= SL={sl_price:.6f}, Exit @ {exit_price:.6f}")
            
            if debug_mode and i <= debug_trades_to_show and not sl_hit:
                print(f"  -> Normal exit @ Open={exit_price:.6f}")
            
            # Calculate PnL based on position side
            if side == 'LONG':
                # Long PnL = (exit_price - entry_price) * quantity
                pnl = (exit_price - entry_price) * quantity
                pnl_percent = ((exit_price - entry_price) / entry_price) * 100
            else:  # SHORT
                # Short PnL = (entry_price - exit_price) * quantity
                pnl = (entry_price - exit_price) * quantity
                pnl_percent = ((entry_price - exit_price) / entry_price) * 100
            
            # Update capital
            current_capital += pnl
            
            total_pnl += pnl
            total_pnl_percent += pnl_percent
            trade_count += 1
            
            if pnl > 0:
                winning_trades += 1
                if side == 'LONG':
                    long_wins += 1
                else:
                    short_wins += 1
            
            # Store trade details
            trade_details.append({
                'trade_num': trade_count,
                'side': side,
                'entry_time': current_position['entry_time'],
                'exit_time': candle_t['open_time'],
                'entry_price': entry_price,
                'exit_price': exit_price,
                'sl_price': sl_price,
                'sl_hit': sl_hit,
                'pnl': pnl,
                'pnl_percent': pnl_percent,
                'capital_after': current_capital
            })
            
            # Update equity curve
            equity_curve.append(current_capital)
        
        # At start of t, open new position based on t-1 candle color
        if is_red:
            # t-1 is red (bearish) -> open SHORT position
            # SL is set at previous high (t-1 high)
            current_position = {
                'side': 'SHORT',
                'entry_price': open_t,
                'entry_time': candle_t['open_time'],
                'sl_price': high_t_minus_1
            }
            short_trades += 1
            if debug_mode and i <= debug_trades_to_show:
                print(f"\n--- OPENING NEW POSITION ---")
                print(f"  -> SHORT @ Entry={open_t:.6f}, SL={high_t_minus_1:.6f} (t-1 HIGH)")
        elif is_green:
            # t-1 is green (bullish) -> open LONG position
            # SL is set at previous low (t-1 low)
            current_position = {
                'side': 'LONG',
                'entry_price': open_t,
                'entry_time': candle_t['open_time'],
                'sl_price': low_t_minus_1
            }
            long_trades += 1
            if debug_mode and i <= debug_trades_to_show:
                print(f"\n--- OPENING NEW POSITION ---")
                print(f"  -> LONG @ Entry={open_t:.6f}, SL={low_t_minus_1:.6f} (t-1 LOW)")
        else:
            # Doji or equal open/close - skip this candle
            current_position = None
            if debug_mode and i <= debug_trades_to_show:
                print(f"\n--- NO POSITION OPENED (DOJI) ---")

    # Calculate ROI metrics
    return_percent = ((current_capital - initial_capital) / initial_capital * 100)
    
    # Calculate compounded ROI (improved calculation)
    annualized_roi_compounded, monthly_roi_compounded = calculate_compounded_roi(
        initial_capital, current_capital, running_time_days
    )
    
    # Keep legacy linear calculations for comparison
    annualized_roi_linear = 0
    monthly_roi_linear = 0
    if running_time_days > 0:
        annualized_roi_linear = (return_percent / running_time_days) * 365
        monthly_roi_linear = (return_percent / running_time_days) * 30
    
    # Calculate advanced metrics
    max_dd_percent, max_dd_value, peak_val, trough_val = calculate_max_drawdown(equity_curve)
    profit_factor = calculate_profit_factor(trade_details)
    win_rate = (winning_trades / trade_count * 100) if trade_count > 0 else 0
    expectancy = calculate_expectancy(trade_details, win_rate)
    sharpe_ratio, annualized_sharpe = calculate_sharpe_ratio(equity_curve)  # Fixed: use equity_curve
    distribution_stats = calculate_distribution_stats(trade_details)
    consistency_metrics = calculate_consistency_metrics(trade_details)
    
    # Calculate new metrics
    calmar_ratio = calculate_calmar_ratio(return_percent, max_dd_percent)
    trades_per_day, expectancy_per_day = calculate_normalized_metrics(trade_count, running_time_days, expectancy)
    unified_score = calculate_unified_score(expectancy, profit_factor, calmar_ratio, max_dd_percent)
    
    # Return results as dictionary
    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'timeframe_limit': timeframe_limit,
        'quantity': quantity,
        'leverage': leverage,
        'enable_sl': enable_sl,
        'start_time': start_time,
        'end_time': end_time,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'running_time_days': running_time_days,
        'initial_capital': initial_capital,
        'final_capital': current_capital,
        'total_pnl': total_pnl,
        'total_pnl_percent': total_pnl_percent,
        'return_percent': return_percent,
        
        # ROI metrics (compounded - preferred)
        'annualized_roi': annualized_roi_compounded,
        'monthly_roi': monthly_roi_compounded,
        
        # Legacy linear ROI (for comparison)
        'annualized_roi_linear': annualized_roi_linear,
        'monthly_roi_linear': monthly_roi_linear,
        
        # Trade statistics
        'trade_count': trade_count,
        'winning_trades': winning_trades,
        'losing_trades': trade_count - winning_trades,
        'win_rate': win_rate,
        'sl_triggered_count': sl_triggered_count,
        'sl_triggered_rate': (sl_triggered_count / trade_count * 100) if trade_count > 0 else 0,
        'long_trades': long_trades,
        'short_trades': short_trades,
        'long_wins': long_wins,
        'short_wins': short_wins,
        'long_win_rate': (long_wins / long_trades * 100) if long_trades > 0 else 0,
        'short_win_rate': (short_wins / short_trades * 100) if short_trades > 0 else 0,
        'avg_pnl_per_trade': (total_pnl / trade_count) if trade_count > 0 else 0,
        'avg_pnl_percent_per_trade': (total_pnl_percent / trade_count) if trade_count > 0 else 0,
        
        # Advanced risk metrics
        'max_drawdown_percent': max_dd_percent,
        'max_drawdown_value': max_dd_value,
        'max_drawdown_peak': peak_val,
        'max_drawdown_trough': trough_val,
        'profit_factor': profit_factor,
        'expectancy': expectancy,
        'sharpe_ratio': sharpe_ratio,
        'annualized_sharpe_ratio': annualized_sharpe,
        
        # Distribution statistics
        'best_trade': distribution_stats['best_trade'],
        'worst_trade': distribution_stats['worst_trade'],
        'median_trade': distribution_stats['median_trade'],
        'avg_win': distribution_stats['avg_win'],
        'avg_loss': distribution_stats['avg_loss'],
        'best_trade_percent': distribution_stats['best_trade_percent'],
        'worst_trade_percent': distribution_stats['worst_trade_percent'],
        'median_trade_percent': distribution_stats['median_trade_percent'],
        
        # Consistency metrics
        'max_consecutive_wins': consistency_metrics['max_consecutive_wins'],
        'max_consecutive_losses': consistency_metrics['max_consecutive_losses'],
        'current_streak': consistency_metrics['current_streak'],
        'current_streak_type': consistency_metrics['current_streak_type'],
        
        # New metrics for bot selection
        'calmar_ratio': calmar_ratio,
        'trades_per_day': trades_per_day,
        'expectancy_per_day': expectancy_per_day,
        'unified_score': unified_score,
        
        # Data
        'total_candles': len(klines),
        'equity_curve': equity_curve,
        'trade_details': trade_details
    }


def print_backtest_results(results, show_trades=False):
    """Print formatted backtest results with enhanced analytics"""
    print("=" * 100)
    print("BACKTEST RESULTS - Previous Day Candle Color Strategy")
    print("=" * 100)
    
    # Configuration
    print("\n📋 CONFIGURATION")
    print("-" * 100)
    print(f"Symbol: {results['symbol']}")
    print(f"Timeframe: {results['timeframe']}")
    print(f"Timeframe Limit: {results['timeframe_limit']}")
    print(f"Leverage: {results['leverage']}x")
    print(f"Quantity per trade: {results['quantity']}")
    print(f"Stop Loss: {'ENABLED' if results['enable_sl'] else 'DISABLED'}")
    if results['enable_sl']:
        print(f"  - LONG SL: Previous candle LOW")
        print(f"  - SHORT SL: Previous candle HIGH")
    print(f"Total candles analyzed: {results['total_candles']}")
    
    # Time Period
    print(f"\n📅 TIME PERIOD")
    print("-" * 100)
    print(f"Start Date: {results['start_date']}")
    print(f"End Date: {results['end_date']}")
    print(f"Running Time: {results['running_time_days']:.2f} days")
    
    # Capital & Returns
    print(f"\n💰 CAPITAL & RETURNS")
    print("-" * 100)
    print(f"Initial Capital: ${results['initial_capital']:.2f}")
    print(f"Final Capital: ${results['final_capital']:.2f}")
    print(f"Total Return: ${results['total_pnl']:.2f} ({results['return_percent']:.2f}%)")
    print(f"Annualized ROI (Compounded): {results['annualized_roi']:.2f}%")
    print(f"Monthly ROI (Compounded): {results['monthly_roi']:.2f}%")
    
    # Risk Metrics
    print(f"\n⚠️  RISK METRICS")
    print("-" * 100)
    print(f"Max Drawdown: {results['max_drawdown_percent']:.2f}% (${results['max_drawdown_value']:.2f})")
    print(f"  - Peak: ${results['max_drawdown_peak']:.2f}")
    print(f"  - Trough: ${results['max_drawdown_trough']:.2f}")
    
    pf_display = f"{results['profit_factor']:.2f}" if results['profit_factor'] != float('inf') else "∞ (no losses)"
    calmar_display = f"{results['calmar_ratio']:.2f}" if results['calmar_ratio'] != float('inf') else "∞"
    
    print(f"Profit Factor: {pf_display}")
    print(f"Calmar Ratio: {calmar_display} (Return/MDD)")
    print(f"Expectancy per trade: ${results['expectancy']:.4f}")
    print(f"Sharpe Ratio: {results['sharpe_ratio']:.3f} (from equity curve)")
    print(f"Annualized Sharpe Ratio: {results['annualized_sharpe_ratio']:.3f}")
    
    # Trade Statistics
    print(f"\n📊 TRADE STATISTICS")
    print("-" * 100)
    print(f"Total trades executed: {results['trade_count']}")
    print(f"Winning trades: {results['winning_trades']}")
    print(f"Losing trades: {results['losing_trades']}")
    print(f"Win rate: {results['win_rate']:.2f}%")
    if results['enable_sl']:
        print(f"Stop Loss triggered: {results['sl_triggered_count']} ({results['sl_triggered_rate']:.2f}%)")
    print()
    print(f"Long trades: {results['long_trades']} (Wins: {results['long_wins']}, Win rate: {results['long_win_rate']:.2f}%)")
    print(f"Short trades: {results['short_trades']} (Wins: {results['short_wins']}, Win rate: {results['short_win_rate']:.2f}%)")
    
    # Distribution Analysis
    print(f"\n📈 DISTRIBUTION ANALYSIS")
    print("-" * 100)
    print(f"Best trade: ${results['best_trade']:.2f} ({results['best_trade_percent']:.2f}%)")
    print(f"Worst trade: ${results['worst_trade']:.2f} ({results['worst_trade_percent']:.2f}%)")
    print(f"Median trade: ${results['median_trade']:.2f} ({results['median_trade_percent']:.2f}%)")
    print(f"Average win: ${results['avg_win']:.2f}")
    print(f"Average loss: ${results['avg_loss']:.2f}")
    print(f"Win/Loss ratio: {abs(results['avg_win'] / results['avg_loss']):.2f}x" if results['avg_loss'] != 0 else "N/A")
    
    # Consistency Metrics
    print(f"\n🎯 CONSISTENCY METRICS")
    print("-" * 100)
    print(f"Max consecutive wins: {results['max_consecutive_wins']}")
    print(f"Max consecutive losses: {results['max_consecutive_losses']}")
    print(f"Current streak: {results['current_streak']} {results['current_streak_type']}")
    
    # Average Performance
    print(f"\n📉 AVERAGE PERFORMANCE")
    print("-" * 100)
    print(f"Average PnL per trade: ${results['avg_pnl_per_trade']:.2f}")
    print(f"Average PnL % per trade: {results['avg_pnl_percent_per_trade']:.2f}%")
    print(f"Total PnL: ${results['total_pnl']:.2f}")
    print(f"Total PnL %: {results['total_pnl_percent']:.2f}%")
    
    # Normalized Metrics (for cross-timeframe comparison)
    print(f"\n⚡ NORMALIZED METRICS (Cross-Timeframe Comparison)")
    print("-" * 100)
    print(f"Trades per day: {results['trades_per_day']:.2f}")
    print(f"Expectancy per day: ${results['expectancy_per_day']:.4f}")
    
    # Unified Score
    print(f"\n🏆 UNIFIED SCORE (Bot Selection)")
    print("-" * 100)
    print(f"Score: {results['unified_score']:.2f}")
    print(f"  Formula: (Expectancy×100) + (PF×50) + (Calmar×30) - (MDD%×1.5)")
    print()

    if show_trades:
        # Print ALL trades with dates for validation
        print("\nALL TRADES (with dates and SL details):")
        print("=" * 120)
        for trade in results['trade_details']:
            pnl_sign = "+" if trade['pnl'] >= 0 else ""
            sl_indicator = " [SL HIT]" if trade['sl_hit'] else " [      ]"
            entry_date = str(trade['entry_time'])[:10] if 'entry_time' in trade else 'N/A'
            exit_date = str(trade['exit_time'])[:10] if 'exit_time' in trade else 'N/A'
            print(f"Trade #{trade['trade_num']:3d} | {entry_date} | [{trade['side']:5s}] | "
                  f"Entry ${trade['entry_price']:.6f} | SL ${trade['sl_price']:.6f} | "
                  f"Exit ${trade['exit_price']:.6f}{sl_indicator:8s} | "
                  f"PnL: {pnl_sign}${trade['pnl']:.2f} ({pnl_sign}{trade['pnl_percent']:.2f}%) | "
                  f"Capital: ${trade['capital_after']:.2f}")
        print("=" * 120)


def run_grid_search(configs, initial_capital=10):
    """
    Run grid search over multiple configurations
    
    Args:
        configs: List of configuration dictionaries with keys:
            - symbol: Trading symbol
            - timeframe: Timeframe for klines
            - quantity: Quantity per trade
            - sl_enabled: Enable stop loss
            - timeframe_limit: Number of candles to fetch
        initial_capital: Starting capital for each backtest
    
    Returns:
        list: List of results for each configuration
    """
    all_results = []
    
    print("\n" + "=" * 100)
    print("STARTING GRID SEARCH")
    print("=" * 100)
    print(f"Total configurations to test: {len(configs)}")
    print(f"Initial capital per test: ${initial_capital}")
    print()
    
    for idx, config in enumerate(configs, 1):
        print(f"\n{'='*100}")
        print(f"Running Configuration {idx}/{len(configs)}")
        print(f"{'='*100}")
        print(f"Symbol: {config['symbol']}, Timeframe: {config['timeframe']}, "
              f"Quantity: {config['quantity']}, SL Enabled: {config['sl_enabled']}, "
              f"Timeframe Limit: {config.get('timeframe_limit', 100)}")
        print()
        
        results = run_backtest(
            symbol=config['symbol'],
            timeframe=config['timeframe'],
            quantity=config['quantity'],
            enable_sl=config['sl_enabled'],
            initial_capital=initial_capital,
            timeframe_limit=config.get('timeframe_limit', 100),
            debug_mode=False
        )
        
        all_results.append(results)
        
        # Print summary for this configuration
        print(f"Results: Final Capital=${results['final_capital']:.2f}, "
              f"Return={results['return_percent']:.2f}%, "
              f"Monthly ROI={results['monthly_roi']:.2f}%, "
              f"Trades={results['trade_count']}, "
              f"Win Rate={results['win_rate']:.2f}%")
    
    return all_results


def print_grid_search_summary(all_results):
    """Print two separate tables: Backtest Results and Bot Ranking"""
    
    # Set pandas display options
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.float_format', lambda x: f'{x:.2f}')
    
    # ========================================
    # TABLE 1: BACKTEST RESULTS (All Configs)
    # ========================================
    print("\n" + "=" * 140)
    print("📊 TABLE 1: BACKTEST RESULTS (All Configurations)")
    print("=" * 140)

    symbol = 'NONE'
    if len(all_results) > 0:
        symbol = all_results[0]['symbol']
    
    backtest_data = []
    for idx, result in enumerate(all_results, 1):
        pf_value = result['profit_factor'] if result['profit_factor'] != float('inf') else 999.99
        calmar_value = result['calmar_ratio'] if result['calmar_ratio'] != float('inf') else 999.99
        
        backtest_data.append({
            '#': idx,
            'Symbol': result['symbol'],
            'TF': result['timeframe'],
            'Limit': result['timeframe_limit'],
            'Qty': result['quantity'],
            'SL': 'Y' if result['enable_sl'] else 'N',
            'Days': result['running_time_days'],
            'Trades': result['trade_count'],
            'Win%': result['win_rate'],
            'Capital': result['final_capital'],
            'Ret%': result['return_percent'],
            'Mon%': result['monthly_roi'],
            'MDD%': result['max_drawdown_percent'],
            'PF': pf_value,
            'Calmar': calmar_value,
            'SR': result['sharpe_ratio'],
            'Exp': result['expectancy'],
            'T/day': result['trades_per_day'],
            'Exp/day': result['expectancy_per_day']
        })
    
    df_backtest = pd.DataFrame(backtest_data)
    print(df_backtest.to_string(index=False))
    print("=" * 140)
    
    # ========================================
    # TABLE 2: BOT RANKING (Sorted by Score)
    # ========================================
    print("\n" + "=" * 140)
    print("🏆 TABLE 2: BOT RANKING (Sorted by Unified Score)")
    print("=" * 140)
    print("Score Formula: (Expectancy×100) + (PF×50) + (Calmar×30) - (MDD%×1.5)")
    print("=" * 140)
    
    # Sort by unified score
    sorted_results = sorted(all_results, key=lambda x: x['unified_score'], reverse=True)
    
    ranking_data = []
    for rank, result in enumerate(sorted_results, 1):
        pf_value = result['profit_factor'] if result['profit_factor'] != float('inf') else 999.99
        calmar_value = result['calmar_ratio'] if result['calmar_ratio'] != float('inf') else 999.99
        
        # Add medal emoji for top 3
        rank_display = f"🥇 {rank}" if rank == 1 else f"🥈 {rank}" if rank == 2 else f"🥉 {rank}" if rank == 3 else str(rank)
        
        ranking_data.append({
            'Rank': rank_display,
            'Score': result['unified_score'],
            'Symbol': result['symbol'],
            'TF': result['timeframe'],
            'SL': 'Y' if result['enable_sl'] else 'N',
            'Ret%': result['return_percent'],
            'MDD%': result['max_drawdown_percent'],
            'Calmar': calmar_value,
            'PF': pf_value,
            'SR': result['sharpe_ratio'],
            'Exp': result['expectancy'],
            'Exp/day': result['expectancy_per_day'],
            'Win%': result['win_rate'],
            'Trades': result['trade_count'],
            'T/day': result['trades_per_day']
        })
    
    df_ranking = pd.DataFrame(ranking_data)
    print(df_ranking.to_string(index=False))
    print("=" * 140)
    
    # Print TOP 3 details
    print("\n" + "=" * 140)
    print("🎯 TOP 3 RECOMMENDED CONFIGURATIONS")
    print("=" * 140)
    
    for rank, result in enumerate(sorted_results[:3], 1):
        pf_display = f"{result['profit_factor']:.2f}" if result['profit_factor'] != float('inf') else "∞"
        calmar_display = f"{result['calmar_ratio']:.2f}" if result['calmar_ratio'] != float('inf') else "∞"
        
        medal = '🥇' if rank == 1 else '🥈' if rank == 2 else '🥉'
        print(f"\n{medal} RANK #{rank} - Score: {result['unified_score']:.2f}")
        print(f"   Config: {result['symbol']} | {result['timeframe']} | SL: {'Yes' if result['enable_sl'] else 'No'}")
        print(f"   Return: {result['return_percent']:.2f}% | MDD: {result['max_drawdown_percent']:.2f}% | "
              f"Calmar: {calmar_display} | PF: {pf_display} | SR: {result['sharpe_ratio']:.2f}")
        print(f"   Expectancy/day: ${result['expectancy_per_day']:.4f} | Trades/day: {result['trades_per_day']:.2f} | "
              f"Win Rate: {result['win_rate']:.2f}%")
    
    print("\n" + "=" * 140)
    
    # ========================================
    # SAVE TABLES TO JSON FILES
    # ========================================
    
    # Get current file directory
    current_dir = Path(__file__).parent
    
    # Generate timestamp for filenames
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save Table 1: Backtest Results
    backtest_json_path = current_dir / f'{symbol}_results_{timestamp}.json'
    df_backtest.to_json(backtest_json_path, orient='records', indent=2)
    print(f"\n💾 Table 1 saved: {backtest_json_path}")
    
    # Save Table 2: Bot Ranking
    ranking_json_path = current_dir / f'{symbol}_ranking_{timestamp}.json'
    df_ranking.to_json(ranking_json_path, orient='records', indent=2)
    print(f"💾 Table 2 saved: {ranking_json_path}")
    
    print()
    
    # Return both DataFrames
    return df_backtest, df_ranking

def generate_grid_configs(grid_params):
    """
    Generate all combinations of grid parameters
    
    Args:
        grid_params: Dictionary with structure:
            {
                "SYMBOL": {
                    "sl_enabled": [True, False],
                    "timeframe": [("5m", 1500), ("1h", 1500), ...],
                    "quantity": [500]
                }
            }
    
    Returns:
        list: List of configuration dictionaries
    """
    configs = []
    
    for symbol, params in grid_params.items():
        for sl_enabled in params["sl_enabled"]:
            for timeframe_tuple in params["timeframe"]:
                timeframe, timeframe_limit = timeframe_tuple
                for quantity in params["quantity"]:
                    configs.append({
                        "symbol": symbol,
                        "sl_enabled": sl_enabled,
                        "timeframe": timeframe,
                        "timeframe_limit": timeframe_limit,
                        "quantity": quantity
                    })
    
    return configs


# Grid Search Configuration
if __name__ == "__main__":
    grid_search = {
        # "DOGEUSDC": {
        #     "sl_enabled": [True, False],
        #     "timeframe": [("1h", 1500), ("4h", 600), ("6h", 400), ("8h", 300), ("12h", 200), ("1d", 100)],
        #     "quantity": [500]
        # },
        # "SOLUSDC": {
        #     "sl_enabled": [True, False],
        #     "timeframe": [("1h", 1500), ("4h", 600), ("6h", 400), ("8h", 300), ("12h", 200), ("1d", 100)],
        #     "quantity": [0.5]
        # },
        # "BNBUSDC": {
        #     "sl_enabled": [True, False],
        #     "timeframe": [("5m", 1500), ("15m", 1500), ("30m", 1500), ("1h", 1500), ("4h", 600), ("6h", 400), ("8h", 300), ("12h", 200), ("1d", 100), ("3d", 50)],
        #     "quantity": [0.01]
        # },
        "1000PEPEUSDC": {
            "sl_enabled": [True, False],
            "timeframe": [("5m", 1500), ("15m", 1500), ("30m", 1500), ("1h", 1500), ("4h", 600), ("6h", 400), ("8h", 300), ("12h", 200), ("1d", 100), ("3d", 50)],
            "quantity": [11000]
        }
    }

    # Generate grid configurations
    grid_configs = generate_grid_configs(grid_search)
    
    # Run grid search
    results = run_grid_search(grid_configs, initial_capital=10)
    
    # Print summary
    print_grid_search_summary(results)



'''
Validation Comparison Table: Real vs Simulation Results
Period: April 5-15, 2026 | Symbol: DOGEUSDC | Quantity: 500
┌──────┬───────┬────────────┬────────────┬────────────┬────────────┬─────────────┬─────────────┬───────────┬──────────┬─────────┬───────┐
│ Date │ Side  │ Real Entry │ Sim Entry  │ Real Exit  │ Sim Exit   │ Real SL Hit │ Sim SL Hit  │ Real PnL  │ Sim PnL  │ Δ PnL   │ Match │
├──────┼───────┼────────────┼────────────┼────────────┼────────────┼─────────────┼─────────────┼───────────┼──────────┼─────────┼───────┤
│04-05 │ LONG  │ 0.092100   │ 0.091990   │ 0.090700   │ 0.090660   │     ✅      │     ✅     │  -$0.73   │  -$0.66  │ +$0.07  │  ✅   │
│04-06 │ LONG  │ 0.092500   │ 0.092320   │ 0.090500   │ 0.090530   │     ❌      │     ❌     │  -$1.00   │  -$0.90  │ +$0.10  │  ✅   │
│04-07 │ SHORT │ 0.090400   │ 0.090530   │ 0.093600   │ 0.093570   │     ✅      │     ✅     │  -$1.60   │  -$1.52  │ +$0.08  │  ✅   │
│04-08 │ LONG  │ 0.095000   │ 0.094870   │ 0.092300   │ 0.092360   │     ❌      │     ❌     │  -$1.36   │  -$1.25  │ +$0.11  │  ✅   │
│04-09 │ SHORT │ 0.092300   │ 0.092360   │ 0.092600   │ 0.092560   │     ❌      │     ❌     │  -$0.15   │  -$0.10  │ +$0.05  │  ✅   │
│04-10 │ LONG  │ 0.092600   │ 0.092560   │ 0.093700   │ 0.093660   │     ❌      │     ❌     │  +$0.55   │  +$0.55  │  $0.00  │  ✅   │
│04-11 │ LONG  │ 0.093700   │ 0.093660   │ 0.093000   │ 0.093070   │     ❌      │     ❌     │  -$0.35   │  -$0.29  │ +$0.06  │  ✅   │
│04-12 │ SHORT │ 0.093000   │ 0.093070   │ 0.090800   │ 0.090800   │     ❌      │     ❌     │  +$1.10   │  +$1.13  │ -$0.03  │  ✅   │
│04-13 │ SHORT │ 0.090800   │ 0.090800   │ 0.093200   │ 0.093220   │     ✅      │     ✅     │  -$1.20   │  -$1.21  │ -$0.01  │  ✅   │
└──────┴───────┴────────────┴────────────┴────────────┴────────────┴─────────────┴─────────────┴───────────┴──────────┴─────────┴───────┘

Summary Statistics
Metric	        Real Trades	Simulation	Difference	Accuracy
Total Trades	10	        10	        0	        100%
Total PnL	    -$4.74	    -$4.82	    -$0.08	    98.3%
Winning Trades	2	        2	        0	        100%
Losing Trades	8	        8	        0	        100%
Win Rate	    20%	        20%	        0%	        100%
SL Triggered	3	        3	        0	        100%
SL Hit Rate	    30%	        30%	        0%	        100%
Avg PnL/Trade   -$0.47	    -$0.48	    -$0.01	    97.9%
Max Drawdown    -$2.59	    -$2.56	    +$0.03	    98.8%


'''
