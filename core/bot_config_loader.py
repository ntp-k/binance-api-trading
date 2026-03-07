import json
from typing import List
from pathlib import Path

from models.bot_config import BotConfig


class ConfigLoadError(Exception):
    """Raised when configuration loading fails."""
    pass


def load_config(file_path: str) -> List[BotConfig]:
    """
    Load and validate bot configurations from JSON file.
    
    Args:
        file_path: Path to configuration JSON file
        
    Returns:
        List of validated BotConfig instances
        
    Raises:
        ConfigLoadError: If file doesn't exist, is invalid JSON, or contains invalid configs
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    config_path = Path(file_path)
    
    # Validate file exists
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    
    # Validate file is readable
    if not config_path.is_file():
        raise ConfigLoadError(f"Path is not a file: {file_path}")
    
    try:
        with open(file=config_path, mode="r", encoding="utf-8") as f:
            raw_data = json.load(fp=f)
    except json.JSONDecodeError as e:
        raise ConfigLoadError(f"Invalid JSON in config file: {e}")
    except IOError as e:
        raise ConfigLoadError(f"Failed to read config file: {e}")
    
    # Validate data structure
    if not isinstance(raw_data, list):
        raise ConfigLoadError(
            f"Config file must contain a JSON array, got {type(raw_data).__name__}"
        )
    
    if not raw_data:
        raise ConfigLoadError("Config file contains empty array")
    
    # Parse and validate each config
    configs: List[BotConfig] = []
    errors: List[str] = []
    
    for idx, item in enumerate(raw_data):
        try:
            if not isinstance(item, dict):
                errors.append(f"Item {idx}: Expected dict, got {type(item).__name__}")
                continue
            
            config = BotConfig.from_dict(data=item)
            config.validate()  # Additional validation
            configs.append(config)
            
        except (ValueError, KeyError) as e:
            errors.append(f"Item {idx} ({item.get('bot_name', 'unknown')}): {e}")
    
    # Report all errors if any
    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {err}" for err in errors)
        raise ConfigLoadError(error_msg)
    
    return configs


def validate_config_file(file_path: str) -> bool:
    """
    Validate configuration file without loading configs.
    
    Args:
        file_path: Path to configuration file
        
    Returns:
        True if valid, False otherwise
    """
    try:
        load_config(file_path)
        return True
    except (ConfigLoadError, FileNotFoundError, json.JSONDecodeError):
        return False

# EOF
