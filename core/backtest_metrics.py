"""
Backtest Metrics Tracker
Tracks all trades and calculates performance metrics for backtesting.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os
import sys

from commons.custom_logger import CustomLogger
from commons.constants import POSITION_RECORDS_DIR

# Import visualization methods
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest.visualize_backtest_result import (
    visualize_position_records,
    visualize_bot_config,
    visualize_summary
)


class BacktestMetrics:
    """
    Tracks and calculates backtest performance metrics.
    """
    
    def __init__(self, bot_name: str, run_id: int):
        self.logger = CustomLogger(name=f"BacktestMetrics:{bot_name}")
        self.bot_name = bot_name
        self.run_id = run_id
        self.trades: List[Dict[str, Any]] = []
        self.initial_capital = 10.0  # Default initial capital
        self.backtest_start_time: Optional[str] = None
        self.backtest_end_time: Optional[str] = None
    
    def set_backtest_period(self, start_time: str, end_time: str) -> None:
        """
        Set the backtest period from kline timestamps.
        
        Args:
            start_time: First kline timestamp
            end_time: Last kline timestamp
        """
        self.backtest_start_time = start_time
        self.backtest_end_time = end_time
        self.logger.debug(f"Backtest period set: {start_time} to {end_time}")
    
    def add_trade(self, trade: Dict[str, Any]) -> None:
        """Add a completed trade to the metrics."""
        self.trades.append(trade)
        self.logger.debug(f"Trade added: {trade.get('position_side')} | PnL: {trade.get('pnl', 0):.2f}")
    
    def calculate_summary(self) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics.
        
        Returns:
            Dictionary with all performance metrics
        """
        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'total_fees': 0.0,
                'net_pnl': 0.0
            }
        
        # Basic counts
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in self.trades if t.get('pnl', 0) < 0]
        breakeven_trades = [t for t in self.trades if t.get('pnl', 0) == 0]
        
        num_wins = len(winning_trades)
        num_losses = len(losing_trades)
        num_breakeven = len(breakeven_trades)
        
        # Win rates
        win_rate = num_wins / total_trades if total_trades > 0 else 0.0
        
        # PnL calculations
        total_pnl = sum(t.get('pnl', 0) for t in self.trades)
        total_fees = sum(t.get('open_fee', 0) + t.get('close_fee', 0) for t in self.trades)
        net_pnl = total_pnl - total_fees
        
        # Average win/loss
        avg_win = sum(t.get('pnl', 0) for t in winning_trades) / num_wins if num_wins > 0 else 0.0
        avg_loss = sum(t.get('pnl', 0) for t in losing_trades) / num_losses if num_losses > 0 else 0.0
        
        # Profit factor
        gross_profit = sum(t.get('pnl', 0) for t in winning_trades)
        gross_loss = abs(sum(t.get('pnl', 0) for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        
        # ROI
        roi = net_pnl / self.initial_capital if self.initial_capital > 0 else 0.0
        
        # Calculate trading period using backtest period if available
        if self.backtest_start_time and self.backtest_end_time:
            try:                
                # Parse kline timestamps (format: 2024-04-01 00:00:00)
                start_date = datetime.strptime(self.backtest_start_time, '%Y-%m-%d %H:%M:%S')
                end_date = datetime.strptime(self.backtest_end_time, '%Y-%m-%d %H:%M:%S')
                days_traded = (end_date - start_date).days + 1
                self.logger.debug(f"Days calculated from klines: {days_traded} ({start_date.date()} to {end_date.date()})")
            except Exception as e:
                self.logger.warning(f"Failed to parse backtest period: {e}")
                days_traded = 1
        else:
            # Fallback to trade timestamps
            if self.trades:
                first_trade = self.trades[0]
                last_trade = self.trades[-1]
                
                try:
                    start_date = datetime.strptime(first_trade.get('open_time', ''), '%Y-%m-%d %H:%M:%S')
                    end_date = datetime.strptime(last_trade.get('close_time', ''), '%Y-%m-%d %H:%M:%S')
                    days_traded = (end_date - start_date).days + 1
                except:
                    days_traded = 1
            else:
                days_traded = 1
        
        # Monthly ROI (annualized)
        monthly_roi = (roi / days_traded) * 30 if days_traded > 0 else 0.0
        
        # Max consecutive wins/losses
        max_consecutive_wins = self._calculate_max_consecutive(winning=True)
        max_consecutive_losses = self._calculate_max_consecutive(winning=False)
        
        # Max drawdown
        max_drawdown, max_drawdown_pct = self._calculate_max_drawdown()
        return {
            'total_trades': total_trades,
            'winning_trades': num_wins,
            'losing_trades': num_losses,
            'breakeven_trades': num_breakeven,
            'win_rate': round(win_rate, 4),
            'total_pnl': round(total_pnl, 2),
            'total_fees': round(total_fees, 2),
            'net_pnl': round(net_pnl, 2),
            'gross_profit': round(gross_profit, 2),
            'gross_loss': round(gross_loss, 2),
            'roi': round(roi, 4),
            'monthly_roi': round(monthly_roi, 4),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses,
            'max_drawdown': round(max_drawdown, 2),
            'max_drawdown_percent': round(max_drawdown_pct, 4),
            'days_traded': days_traded
        }
    
    def _calculate_max_consecutive(self, winning: bool) -> int:
        """Calculate maximum consecutive wins or losses."""
        max_consecutive = 0
        current_consecutive = 0
        
        for trade in self.trades:
            pnl = trade.get('pnl', 0)
            is_win = pnl > 0
            
            if is_win == winning:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def _calculate_max_drawdown(self) -> tuple:
        """
        Calculate maximum drawdown.
        
        Returns:
            Tuple of (max_drawdown_amount, max_drawdown_percentage)
        """
        if not self.trades:
            return 0.0, 0.0
        
        equity = self.initial_capital
        peak_equity = equity
        max_drawdown = 0.0
        max_drawdown_pct = 0.0
        
        for trade in self.trades:
            pnl = trade.get('pnl', 0)
            fees = trade.get('open_fee', 0) + trade.get('close_fee', 0)
            equity += (pnl - fees)
            
            if equity > peak_equity:
                peak_equity = equity
            
            drawdown = peak_equity - equity
            drawdown_pct = drawdown / peak_equity if peak_equity > 0 else 0.0
            
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_pct = drawdown_pct
        
        return max_drawdown, max_drawdown_pct
    
    def save_results(self, bot_config: Dict[str, Any]) -> str:
        """
        Save backtest results to file.
        
        Args:
            bot_config: Bot configuration dictionary
        
        Returns:
            Path to saved results file
        """
        # Create backtest_results directory if it doesn't exist
        results_dir = "backtest/results"
        os.makedirs(results_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"runid_{self.run_id}_backtest_{timestamp}.json"
        filepath = os.path.join(results_dir, filename)
        
        # Calculate summary
        summary = self.calculate_summary()
        
        # Prepare results
        results = {
            'bot_config': bot_config,
            'summary': summary,
            'trades': self.trades
        }
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        self.logger.info(f"Backtest results saved to: {filepath}")
        return filepath
    
    def print_summary(self, bot_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Print formatted summary to console using visualization methods.
        
        Args:
            bot_config: Optional bot configuration dictionary for display
        """
        summary = self.calculate_summary()
        
        # Display in order: 1. Records, 2. Config, 3. Performance
        visualize_position_records(self.trades)
        
        if bot_config:
            visualize_bot_config(bot_config)
        
        visualize_summary(summary)


# EOF

# Made with Bob
