"""
Configuration validation utilities.

Provides schema validation and business rule checking for bot configurations.
"""

from typing import Dict, Any, List, Optional
from models.enum.entry_strategy import EntryStrategy
from models.enum.exit_strategy import ExitStrategy
from models.enum.run_mode import RunMode
from models.enum.trade_client import TradeClient
from models.enum.order_type import OrderType


class ValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigValidator:
    """Validates bot configuration against schema and business rules."""
    
    # Valid timeframe values
    VALID_TIMEFRAMES = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
    
    # Leverage limits
    MIN_LEVERAGE = 1
    MAX_LEVERAGE = 125
    
    # Quantity limits
    MIN_QUANTITY = 0.001
    
    @classmethod
    def validate_config_dict(cls, config: Dict[str, Any]) -> List[str]:
        """
        Validate configuration dictionary.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors: List[str] = []
        
        # Required fields
        required_fields = [
            'is_enabled', 'bot_id', 'run_id', 'bot_name', 'run_mode',
            'trade_client', 'entry_strategy', 'exit_strategy', 'symbol',
            'leverage', 'quantity', 'timeframe', 'timeframe_limit', 'order_type'
        ]
        
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            return errors  # Return early if required fields missing
        
        # Validate types
        errors.extend(cls._validate_types(config))
        
        # Validate enums
        errors.extend(cls._validate_enums(config))
        
        # Validate business rules
        errors.extend(cls._validate_business_rules(config))
        
        return errors
    
    @classmethod
    def _validate_types(cls, config: Dict[str, Any]) -> List[str]:
        """Validate field types."""
        errors: List[str] = []
        
        type_checks = {
            'is_enabled': bool,
            'bot_id': int,
            'run_id': int,
            'bot_name': str,
            'tp_enabled': bool,
            'sl_enabled': bool,
            'symbol': str,
            'leverage': int,
            'quantity': (int, float),
            'timeframe': str,
            'timeframe_limit': int,
        }
        
        for field, expected_type in type_checks.items():
            if field in config and not isinstance(config[field], expected_type):
                errors.append(
                    f"Field '{field}' must be {expected_type.__name__}, "
                    f"got {type(config[field]).__name__}"
                )
        
        return errors
    
    @classmethod
    def _validate_enums(cls, config: Dict[str, Any]) -> List[str]:
        """Validate enum fields."""
        errors: List[str] = []
        
        # Validate run_mode
        if 'run_mode' in config:
            try:
                if isinstance(config['run_mode'], str):
                    RunMode(value=config['run_mode'].upper())
            except ValueError:
                valid_modes = [mode.value for mode in RunMode]
                errors.append(
                    f"Invalid run_mode '{config['run_mode']}'. "
                    f"Valid: {', '.join(valid_modes)}"
                )
        
        # Validate trade_client
        if 'trade_client' in config:
            try:
                if isinstance(config['trade_client'], str):
                    TradeClient(value=config['trade_client'].upper())
            except ValueError:
                valid_clients = [client.value for client in TradeClient]
                errors.append(
                    f"Invalid trade_client '{config['trade_client']}'. "
                    f"Valid: {', '.join(valid_clients)}"
                )
        
        # Validate entry_strategy
        if 'entry_strategy' in config:
            try:
                if isinstance(config['entry_strategy'], str):
                    EntryStrategy(value=config['entry_strategy'].upper())
            except ValueError:
                valid_strategies = [s.value for s in EntryStrategy]
                errors.append(
                    f"Invalid entry_strategy '{config['entry_strategy']}'. "
                    f"Valid: {', '.join(valid_strategies)}"
                )
        
        # Validate exit_strategy
        if 'exit_strategy' in config:
            try:
                if isinstance(config['exit_strategy'], str):
                    ExitStrategy(value=config['exit_strategy'].upper())
            except ValueError:
                valid_strategies = [s.value for s in ExitStrategy]
                errors.append(
                    f"Invalid exit_strategy '{config['exit_strategy']}'. "
                    f"Valid: {', '.join(valid_strategies)}"
                )
        
        # Validate order_type
        if 'order_type' in config:
            try:
                if isinstance(config['order_type'], str):
                    OrderType(value=config['order_type'].upper())
            except ValueError:
                valid_types = [ot.value for ot in OrderType]
                errors.append(
                    f"Invalid order_type '{config['order_type']}'. "
                    f"Valid: {', '.join(valid_types)}"
                )
        
        return errors
    
    @classmethod
    def _validate_business_rules(cls, config: Dict[str, Any]) -> List[str]:
        """Validate business rules."""
        errors: List[str] = []
        
        # Validate bot_name
        if 'bot_name' in config:
            if not config['bot_name'] or not config['bot_name'].strip():
                errors.append("bot_name cannot be empty")
        
        # Validate symbol
        if 'symbol' in config:
            if not config['symbol'] or not config['symbol'].strip():
                errors.append("symbol cannot be empty")
            elif not config['symbol'].isupper():
                errors.append(f"symbol should be uppercase: {config['symbol']}")
        
        # Validate leverage
        if 'leverage' in config:
            leverage = config['leverage']
            if leverage < cls.MIN_LEVERAGE or leverage > cls.MAX_LEVERAGE:
                errors.append(
                    f"leverage must be between {cls.MIN_LEVERAGE} and {cls.MAX_LEVERAGE}, "
                    f"got {leverage}"
                )
        
        # Validate quantity
        if 'quantity' in config:
            quantity = config['quantity']
            if quantity < cls.MIN_QUANTITY:
                errors.append(
                    f"quantity must be at least {cls.MIN_QUANTITY}, got {quantity}"
                )
        
        # Validate timeframe
        if 'timeframe' in config:
            if config['timeframe'] not in cls.VALID_TIMEFRAMES:
                errors.append(
                    f"Invalid timeframe '{config['timeframe']}'. "
                    f"Valid: {', '.join(cls.VALID_TIMEFRAMES)}"
                )
        
        # Validate timeframe_limit
        if 'timeframe_limit' in config:
            if config['timeframe_limit'] <= 0:
                errors.append(
                    f"timeframe_limit must be positive, got {config['timeframe_limit']}"
                )
            elif config['timeframe_limit'] > 1500:
                errors.append(
                    f"timeframe_limit too large (max 1500), got {config['timeframe_limit']}"
                )
        
        return errors
    
    @classmethod
    def validate_and_raise(cls, config: Dict[str, Any]) -> None:
        """
        Validate configuration and raise exception if invalid.
        
        Args:
            config: Configuration to validate
            
        Raises:
            ValidationError: If validation fails
        """
        errors = cls.validate_config_dict(config)
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(
                f"  - {err}" for err in errors
            )
            raise ValidationError(error_msg)


# EOF

# Made with Bob
