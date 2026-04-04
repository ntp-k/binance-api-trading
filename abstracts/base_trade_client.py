"""
Base class for trade client implementations.
"""
from abc import ABC, abstractmethod
from time import sleep
from typing import Dict, Any, Optional
import pandas as pd
import random

from commons.custom_logger import CustomLogger
from commons.constants import JITTER_SECONDS


class BaseTradeClient(ABC):
    """
    Abstract base class for trade clients (live or backtest).
    
    Provides common functionality for:
    - Position management
    - Order placement and cancellation
    - Market data fetching
    - Leverage configuration
    """
    
    wait_time: int = 0
    running: bool = False

    def __init__(self) -> None:
        """Initialize the trade client with logger."""
        self.logger = CustomLogger(name=self.__class__.__name__)
        self.logger.debug(message=f'Initializing {self.__class__.__name__}')

    @abstractmethod
    def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """
        Set leverage for a trading symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            leverage: Leverage multiplier (1-125)
        
        Returns:
            Response dictionary from the exchange
        """
        pass
       
    @abstractmethod
    def fetch_position(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch current position for a symbol.
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            Dictionary containing position details or empty dict if no position
        """
        pass

    @abstractmethod
    def fetch_price(self, symbol: str) -> float:
        """
        Fetch current market price for a symbol.
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            Current market price
        """
        pass

    @abstractmethod
    def fetch_klines(
        self,
        symbol: str,
        timeframe: str,
        timeframe_limit: int = 100
    ) -> pd.DataFrame:
        """
        Fetch candlestick (klines) data.
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe interval (e.g., '1m', '5m', '1h')
            timeframe_limit: Number of candles to fetch
        
        Returns:
            DataFrame containing klines data
        """
        pass

    @abstractmethod
    def fetch_order(self, symbol: str, order_id: str = '') -> Dict[str, Any]:
        """
        Fetch order details.
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID to fetch
        
        Returns:
            Dictionary containing order details
        """
        pass

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        order_side: str,
        order_type: str,
        quantity: float,
        price: float = 0,
        reduce_only: bool = False,
        time_in_force: str = "GTC"
    ) -> Dict[str, Any]:
        """
        Place a new order.
        
        Args:
            symbol: Trading pair symbol
            order_side: 'BUY' or 'SELL'
            order_type: 'MARKET' or 'LIMIT'
            quantity: Order quantity
            price: Limit price (required for LIMIT orders)
            reduce_only: If True, order will only reduce position
            time_in_force: Time in force (default 'GTC')
        
        Returns:
            Dictionary containing order response
        """
        pass

    @abstractmethod
    def cancel_order(self, symbol: str, order_id: str = '') -> Dict[str, Any]:
        """
        Cancel an existing order.
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID to cancel
        
        Returns:
            Dictionary containing cancellation response
        """
        pass

    @abstractmethod
    def fetch_algorithmic_order(self, order_id: str) -> Dict[str, Any]:
        """
        Fetch algorithmic order details (TP/SL orders).
        
        Args:
            order_id: Algorithmic order ID
        
        Returns:
            Dictionary containing order details
        """
        pass

    @abstractmethod
    def place_algorithmic_order(
        self,
        symbol: str,
        order_side: str,
        order_type: str,
        quantity: float,
        trigger_price: float
    ) -> Dict[str, Any]:
        """
        Place an algorithmic order (TP/SL).
        
        Args:
            symbol: Trading pair symbol
            order_side: 'BUY' or 'SELL'
            order_type: 'STOP_MARKET' or 'TAKE_PROFIT_MARKET'
            quantity: Order quantity
            trigger_price: Price at which order triggers
        
        Returns:
            Dictionary containing order response
        """
        pass

    @abstractmethod
    def cancel_algorithmic_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an algorithmic order.
        
        Args:
            order_id: Algorithmic order ID to cancel
        
        Returns:
            Dictionary containing cancellation response
        """
        pass

    @abstractmethod
    def fetch_trades(
        self,
        symbol: str = '',
        order_id: str = ''
    ) -> Dict[str, Any]:
        """
        Fetch trade history.
        
        Args:
            symbol: Trading pair symbol (optional)
            order_id: Order ID to filter trades (optional)
        
        Returns:
            Dictionary containing trade history
        """
        pass

    @abstractmethod
    def fetch_order_trade(
        self,
        symbol: str = '',
        order_id: str = ''
    ) -> Dict[str, Any]:
        """
        Fetch aggregated trade details for an order.
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID
        
        Returns:
            Dictionary with aggregated trade details (price, fee, pnl, side)
        """
        pass

    @abstractmethod
    def fetch_order_book(self, symbol: str, limit: int = 5) -> Dict[str, Any]:
        """
        Fetch order book depth for a symbol.
        
        Args:
            symbol: Trading pair symbol
            limit: Number of price levels to fetch
        
        Returns:
            Dictionary with 'bids' and 'asks' arrays
        """
        pass

    @abstractmethod
    def fetch_exchange_info(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch exchange trading rules for a symbol.
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            Dictionary with trading rules (tickSize, stepSize, etc.)
        """
        pass

    @abstractmethod
    def has_exchange_info_cached(self, symbol: str) -> bool:
        """
        Check if exchange info is cached for a symbol.
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            True if cached, False otherwise
        """
        pass

    @abstractmethod
    def get_cached_exchange_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get cached exchange info without making API call.
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            Cached exchange info or None if not cached
        """
        pass

    def set_wait_time(self, wait_time_sec: int) -> None:
        """
        Set wait time between bot iterations.
        
        Args:
            wait_time_sec: Wait time in seconds
        """
        self.wait_time = wait_time_sec

    def set_running(self, running: bool = False) -> None:
        """
        Set running state of the client.
        
        Args:
            running: True to enable, False to disable
        """
        self.running = running

    def wait(self) -> None:
        """
        Wait for a randomized duration before next iteration.
        Adds jitter to prevent synchronized API calls.
        """
        _min_wait_time = max(0, self.wait_time - JITTER_SECONDS)
        _wait_time = random.randint(a=_min_wait_time, b=self.wait_time)
        sleep(_wait_time)

# EOF
