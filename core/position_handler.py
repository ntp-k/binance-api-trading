import json
import os
from typing import Optional

from commons.constants import (
    POSITION_RECORDS_DIR,
    POSITION_RECORD_FILENAME_TEMPLATE,
    POSITION_STATES_DIR,
    POSITION_STATES_FILENAME_TEMPLATE
)
from commons.custom_logger import CustomLogger
from models.bot_config import BotConfig
from models.position import Position
from commons.common import get_datetime_now_string_gmt_plus_7


class PositionHandler:
    """
    Manages position state, including opening, closing, and persisting positions.
    
    Handles TP/SL order tracking and position state persistence to disk.
    """
    
    def __init__(self, bot_config: BotConfig, logger: Optional[CustomLogger] = None):
        """
        Initialize position handler.
        
        Args:
            bot_config: Bot configuration
            logger: Optional logger to inherit from bot. If None, creates own logger.
        """
        if logger:
            self.logger = logger
        else:
            self.logger = CustomLogger(name=f"PositionHandler:{bot_config.bot_name}")
        self.bot_config: BotConfig = bot_config
        self.position: Optional[Position] = None
        self._entry_price: float = 0.0
        self._tp_order_id: str = ''
        self._tp_price: float = 0.0
        self._sl_order_id: str = ''
        self._sl_price: float = 0.0
        self.last_position_open_candle: str = ''

        # Ensure directories exist
        self._ensure_directories()
        
        # Set up position state file path
        position_state_filename = POSITION_STATES_FILENAME_TEMPLATE.format(
            run_id=self.bot_config.run_id
        )
        self.position_state_file_path = os.path.join(
            POSITION_STATES_DIR, position_state_filename
        )
        
        # Restore previous state if exists
        self.read_position_state()
    
    def _ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        os.makedirs(POSITION_RECORDS_DIR, exist_ok=True)
        os.makedirs(POSITION_STATES_DIR, exist_ok=True)
    
    # Property decorators for better encapsulation
    @property
    def tp_order_id(self) -> str:
        """Get take profit order ID."""
        return self._tp_order_id
    
    @tp_order_id.setter
    def tp_order_id(self, value: str) -> None:
        """Set take profit order ID and sync with position."""
        self._tp_order_id = value
        if self.position:
            self.position.tp_order_id = value
    
    @property
    def tp_price(self) -> float:
        """Get take profit price."""
        return self._tp_price
    
    @tp_price.setter
    def tp_price(self, value: float) -> None:
        """Set take profit price and sync with position."""
        self._tp_price = value
        if self.position:
            self.position.tp_price = value
    
    @property
    def sl_order_id(self) -> str:
        """Get stop loss order ID."""
        return self._sl_order_id
    
    @sl_order_id.setter
    def sl_order_id(self, value: str) -> None:
        """Set stop loss order ID and sync with position."""
        self._sl_order_id = value
        if self.position:
            self.position.sl_order_id = value
    
    @property
    def sl_price(self) -> float:
        """Get stop loss price."""
        return self._sl_price
    
    @sl_price.setter
    def sl_price(self, value: float) -> None:
        """Set stop loss price and sync with position."""
        self._sl_price = value
        if self.position:
            self.position.sl_price = value
    
    @property
    def entry_price(self) -> float:
        """Get entry price."""
        return self._entry_price
    
    # Legacy methods for backward compatibility
    def set_tp_order_id(self, id: str) -> None:
        """Set TP order ID (legacy method)."""
        self.tp_order_id = id
    
    def set_tp_price(self, price: float) -> None:
        """Set TP price (legacy method)."""
        self.tp_price = price
    
    def get_tp_order_id(self) -> str:
        """Get TP order ID (legacy method)."""
        return self.tp_order_id
    
    def set_sl_order_id(self, id: str) -> None:
        """Set SL order ID (legacy method)."""
        self.sl_order_id = id
    
    def set_sl_price(self, price: float) -> None:
        """Set SL price (legacy method)."""
        self.sl_price = price
    
    def get_sl_order_id(self) -> str:
        """Get SL order ID (legacy method)."""
        return self.sl_order_id

    def clear_tp_sl_orders(self) -> None:
        """Clear all TP/SL order information."""
        self._entry_price = 0.0
        self._tp_order_id = ''
        self._tp_price = 0.0
        self._sl_order_id = ''
        self._sl_price = 0.0

    def open_position(self, position_dict: dict) -> None:
        """
        Open a new position from dictionary data.
        
        Args:
            position_dict: Dictionary containing position data including entry_price
        """
        try:
            self._entry_price = position_dict.get('entry_price', 0.0)
            self.position = Position.from_dict(position_dict)
        except Exception as e:
            self.logger.error_e(message="Error while opening position from dict", e=e)
            raise

    def close_position(self, position_dict: dict) -> Optional[dict]:
        """
        Close the current position and save record.
        
        Args:
            position_dict: Dictionary with close_fee, close_reason, close_price, pnl,
                          and optionally close_time (for backtest mode)
        
        Returns:
            Dictionary with trade details for backtest tracking, or None
        """
        if not self.position:
            self.logger.warning("Attempted to close position but no position is open")
            return None
        
        self.position.close_fee = position_dict.get('close_fee', 0.0)
        self.position.close_reason = position_dict.get('close_reason', '')
        self.position.close_price = position_dict.get('close_price', 0.0)
        
        # Use close_time from dict if provided (backtest mode), otherwise use current time
        if 'close_time' in position_dict:
            self.position.close_time = position_dict['close_time']
        else:
            self.position.close_time = get_datetime_now_string_gmt_plus_7(
                format='%Y-%m-%d %H:%M:%S'
            )
        
        self.position.pnl = position_dict.get('pnl', 0.0)
        self.last_position_open_candle = self.position.open_candle

        # Create trade dict for backtest tracking
        trade_dict = self.position.to_dict()

        self._dump_position_record()
        self.position = None
        self._remove_state_file()
        
        return trade_dict

    def update_pnl(self, pnl: float) -> None:
        """
        Update position PnL and track max/min values.
        
        Args:
            pnl: Current profit/loss value
        """
        if not self.position:
            return
        
        self.position.max_pnl = max(pnl, self.position.max_pnl)
        self.position.min_pnl = min(pnl, self.position.min_pnl)
        self.position.pnl = pnl

    def is_open(self) -> bool:
        """Check if a position is currently open."""
        return self.position is not None

    def clear_position(self) -> None:
        """Clear position and remove state file."""
        # Update last_position_open_candle to prevent re-entry on same candle
        if self.position:
            self.last_position_open_candle = self.position.open_candle
        self.position = None
        self._remove_state_file()

    def get_position(self) -> Optional[Position]:
        """Get the current position."""
        return self.position
    
    def _remove_state_file(self) -> None:
        """Remove position state file if it exists."""
        if os.path.exists(self.position_state_file_path):
            try:
                os.remove(self.position_state_file_path)
            except OSError as e:
                self.logger.error_e(message="Failed to remove state file", e=e)

    def _dump_position(self, file_path: str) -> None:
        """
        Write position data to file.
        
        Args:
            file_path: Path to write position data
        """
        if not self.position:
            self.logger.warning("No position to dump.")
            return
        
        try:
            with open(file=file_path, mode="w", encoding="utf-8") as f:
                json.dump(obj=self.position.to_dict(), fp=f, indent=4)
        except IOError as e:
            self.logger.error_e(message=f"Failed to dump position to {file_path}", e=e)

    def _dump_position_record(self) -> None:
        """Save position record with timestamp."""
        timestamp = get_datetime_now_string_gmt_plus_7(format='%Y%m%d_%H%M%S')
        file_name = POSITION_RECORD_FILENAME_TEMPLATE.format(
            run_id=self.bot_config.run_id, dt=timestamp
        )
        file_path = os.path.join(POSITION_RECORDS_DIR, file_name)
        self._dump_position(file_path=file_path)

    def dump_position_state(self) -> None:
        """Save current position state to file."""
        self._dump_position(file_path=self.position_state_file_path)

    def read_position_state(self) -> None:
        """Restore position state from file if it exists."""
        if not os.path.exists(self.position_state_file_path):
            return
        
        try:
            with open(file=self.position_state_file_path, mode='r', encoding="utf-8") as f:
                data = json.load(fp=f)
                self.position = Position.from_dict(data=data)
                self.position.run_id = self.bot_config.run_id
                
                # Restore TP/SL prices and order IDs from position
                self._entry_price = self.position.entry_price
                self._tp_price = self.position.tp_price
                self._sl_price = self.position.sl_price
                self._tp_order_id = self.position.tp_order_id
                self._sl_order_id = self.position.sl_order_id
                
                self.logger.info(message=f"Position state restored successfully (TP: {self._tp_price}, SL: {self._sl_price})")
        except (IOError, json.JSONDecodeError, KeyError) as e:
            self.logger.error_e(message="Could not restore position state", e=e)
            self.position = None


if __name__ == "__main__":
    pass

# EOF
