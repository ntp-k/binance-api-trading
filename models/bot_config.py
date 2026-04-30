from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

from models.enum.entry_strategy import EntryStrategy
from models.enum.exit_strategy import ExitStrategy
from models.enum.run_mode import RunMode
from models.enum.trade_client import TradeClient
from models.enum.order_type import OrderType
from commons.config_validator import ConfigValidator, ValidationError


@dataclass
class BotConfig:
    """
    Configuration for a trading bot instance.
    
    Contains all parameters needed to initialize and run a trading bot,
    including strategy selection, risk management, and execution settings.
    
    Position Sizing:
    - Use `quantity` for fixed quantity per trade (legacy mode)
    - Use `position_margin` for fixed margin per trade (recommended)
    - If both are provided, `position_margin` takes precedence
    """
    is_enabled: bool
    bot_id: int
    run_id: int
    bot_name: str
    run_mode: RunMode
    trade_client: TradeClient
    entry_strategy: EntryStrategy
    exit_strategy: ExitStrategy
    tp_enabled: bool
    sl_enabled: bool
    symbol: str
    leverage: int
    quantity: Optional[float]
    timeframe: str
    timeframe_limit: int
    order_type: OrderType
    dynamic_config: Dict[str, Any]
    created_at: datetime
    position_margin: Optional[float] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BotConfig':
        """
        Create BotConfig from dictionary with validation and type conversion.
        
        Args:
            data: Dictionary containing bot configuration
            
        Returns:
            BotConfig instance
            
        Raises:
            ValueError: If required fields are missing or invalid
            KeyError: If enum conversion fails
        """
        # Use ConfigValidator for comprehensive validation
        try:
            ConfigValidator.validate_and_raise(data)
        except ValidationError as e:
            raise ValueError(str(e))
        
        # Convert string enums to enum types
        if isinstance(data['run_mode'], str):
            data['run_mode'] = RunMode(value=data['run_mode'].upper())
        
        if isinstance(data['entry_strategy'], str):
            data['entry_strategy'] = EntryStrategy(value=data['entry_strategy'].upper())
        
        if isinstance(data['exit_strategy'], str):
            data['exit_strategy'] = ExitStrategy(value=data['exit_strategy'].upper())
        
        if isinstance(data['trade_client'], str):
            data['trade_client'] = TradeClient(value=data['trade_client'].upper())
        
        if isinstance(data['order_type'], str):
            data['order_type'] = OrderType(value=data['order_type'].upper())
        
        # Validate numeric fields
        if data['leverage'] <= 0:
            raise ValueError(f"Leverage must be positive, got {data['leverage']}")
        
        # Validate position sizing: either quantity or position_margin must be provided
        has_quantity = 'quantity' in data and data['quantity'] is not None
        has_position_margin = 'position_margin' in data and data['position_margin'] is not None
        
        if not has_quantity and not has_position_margin:
            raise ValueError("Either 'quantity' or 'position_margin' must be provided")
        
        if has_quantity and data['quantity'] <= 0:
            raise ValueError(f"Quantity must be positive, got {data['quantity']}")
        
        if has_position_margin and data['position_margin'] <= 0:
            raise ValueError(f"Position margin must be positive, got {data['position_margin']}")
        
        if data['timeframe_limit'] <= 0:
            raise ValueError(f"Timeframe limit must be positive, got {data['timeframe_limit']}")
        
        # Set defaults for optional fields
        data.setdefault('tp_enabled', False)
        data.setdefault('sl_enabled', False)
        data.setdefault('dynamic_config', {})
        data.setdefault('created_at', datetime.now())
        data.setdefault('quantity', None)
        data.setdefault('position_margin', None)
        
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert BotConfig to dictionary for serialization."""
        result = {
            'is_enabled': self.is_enabled,
            'bot_id': self.bot_id,
            'run_id': self.run_id,
            'bot_name': self.bot_name,
            'run_mode': self.run_mode.value,
            'trade_client': self.trade_client.value,
            'entry_strategy': self.entry_strategy.value,
            'exit_strategy': self.exit_strategy.value,
            'tp_enabled': self.tp_enabled,
            'sl_enabled': self.sl_enabled,
            'symbol': self.symbol,
            'leverage': self.leverage,
            'timeframe': self.timeframe,
            'timeframe_limit': self.timeframe_limit,
            'order_type': self.order_type.value,
            'dynamic_config': self.dynamic_config,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }
        
        # Include quantity or position_margin based on what's set
        if self.position_margin is not None:
            result['position_margin'] = self.position_margin
        if self.quantity is not None:
            result['quantity'] = self.quantity
            
        return result
    
    def uses_fixed_margin(self) -> bool:
        """
        Check if bot uses fixed margin mode (position_margin) instead of fixed quantity.
        
        Returns:
            True if using position_margin, False if using fixed quantity
        """
        return self.position_margin is not None
    
    def validate(self) -> bool:
        """
        Validate bot configuration.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        if not self.bot_name:
            raise ValueError("Bot name cannot be empty")
        
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        
        if self.leverage < 1 or self.leverage > 125:
            raise ValueError(f"Leverage must be between 1 and 125, got {self.leverage}")
        
        # Validate position sizing
        if not self.quantity and not self.position_margin:
            raise ValueError("Either quantity or position_margin must be set")
        
        return True

# EOF
