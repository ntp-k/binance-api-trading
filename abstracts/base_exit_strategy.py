"""
Base class for exit strategy implementations.
"""
from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd

from commons.custom_logger import CustomLogger
from models.position_signal import PositionSignal
from models.position import Position


class BaseExitStrategy(ABC):
    """
    Abstract base class for exit strategies.
    
    All exit strategies must implement:
    - _process_data: Process klines data and add indicators
    - should_close: Determine if position should be closed
    """
    
    def __init__(self, logger: Optional[CustomLogger] = None) -> None:
        """
        Initialize the exit strategy with logger.
        
        Args:
            logger: Optional logger to inherit from bot. If None, creates own logger.
        """
        if logger:
            self.logger = logger
        else:
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
    def should_close(
        self,
        klines_df: pd.DataFrame,
        position_handler
    ) -> PositionSignal:
        """
        Determine if a position should be closed.
        
        Args:
            klines_df: DataFrame containing klines data with indicators
            position_handler: Position handler with current position state
        
        Returns:
            PositionSignal indicating whether to close (ZERO) or hold position
        """
        pass

# EOF

