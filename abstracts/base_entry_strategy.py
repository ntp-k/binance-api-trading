"""
Base class for entry strategy implementations.
"""
from abc import ABC, abstractmethod
from typing import Tuple
import pandas as pd

from commons.custom_logger import CustomLogger
from models.position_signal import PositionSignal
from models.enum.position_side import PositionSide
from core.position_handler import PositionHandler


class BaseEntryStrategy(ABC):
    """
    Abstract base class for entry strategies.
    
    All entry strategies must implement:
    - _process_data: Process klines data and add indicators
    - should_open: Determine if position should be opened
    - calculate_tp_sl: Calculate take profit and stop loss prices
    """
    
    def __init__(self) -> None:
        """Initialize the entry strategy with logger."""
        self.logger = CustomLogger(name=self.__class__.__name__)
        self.logger.debug(f'Initializing {self.__class__.__name__}')
    
    @abstractmethod
    def _process_data(self, klines_df: pd.DataFrame) -> pd.DataFrame:
        """
        Process klines data and add technical indicators.
        
        Args:
            klines_df: DataFrame containing klines data
        
        Returns:
            DataFrame with added indicator columns
        """
        pass

    @abstractmethod
    def should_open(
        self,
        klines_df: pd.DataFrame,
        position_handler: PositionHandler
    ) -> PositionSignal:
        """
        Determine if a position should be opened.
        
        Args:
            klines_df: DataFrame containing klines data with indicators
            position_handler: Handler for position state management
        
        Returns:
            PositionSignal indicating whether to open LONG, SHORT, or ZERO
        """
        pass

    @abstractmethod
    def calculate_tp_sl(
        self,
        klines_df: pd.DataFrame,
        position_side: PositionSide,
        entry_price: float
    ) -> Tuple[float, float]:
        """
        Calculate take profit and stop loss prices.
        
        Args:
            klines_df: DataFrame containing klines data with indicators
            position_side: Side of the position (LONG or SHORT)
            entry_price: Entry price of the position
        
        Returns:
            Tuple of (tp_price, sl_price)
        """
        pass


# EOF

