import json
from typing import List, Optional
from pathlib import Path

from models.bot_config import BotConfig


class ConfigLoadError(Exception):
    """Raised when configuration loading fails."""
    pass


def load_single_bot_config(file_path: str) -> BotConfig:
    """
    Load a single bot configuration from JSON file.
    Each file contains exactly one bot configuration (JSON object).
    
    Args:
        file_path: Path to configuration JSON file
        
    Returns:
        Validated BotConfig instance
        
    Raises:
        ConfigLoadError: If file is invalid or config is invalid
        FileNotFoundError: If config file doesn't exist
    """
    config_path = Path(file_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    
    if not config_path.is_file():
        raise ConfigLoadError(f"Path is not a file: {file_path}")
    
    try:
        with open(file=config_path, mode="r", encoding="utf-8") as f:
            raw_data = json.load(fp=f)
    except json.JSONDecodeError as e:
        raise ConfigLoadError(f"Invalid JSON in {file_path}: {e}")
    except IOError as e:
        raise ConfigLoadError(f"Failed to read {file_path}: {e}")
    
    if not isinstance(raw_data, dict):
        raise ConfigLoadError(
            f"Config file must contain a JSON object, got {type(raw_data).__name__}"
        )
    
    try:
        config = BotConfig.from_dict(data=raw_data)
        config.validate()
        return config
    except (ValueError, KeyError) as e:
        raise ConfigLoadError(f"Invalid configuration in {file_path}: {e}")


def load_bot_configs_by_ids(
    bot_ids: List[str],
    config_dir: str = "config"
) -> List[BotConfig]:
    """
    Load specific bot configurations by their IDs.
    
    Args:
        bot_ids: List of bot IDs (e.g., ['25', 'aa', 'bb'])
        config_dir: Directory containing bot config files
        
    Returns:
        List of validated BotConfig instances
        
    Raises:
        ConfigLoadError: If any specified bot config cannot be loaded
    """
    configs: List[BotConfig] = []
    errors: List[str] = []
    
    for bot_id in bot_ids:
        file_path = Path(config_dir) / f"bot_{bot_id}.json"
        
        try:
            config = load_single_bot_config(str(file_path))
            configs.append(config)
        except (ConfigLoadError, FileNotFoundError) as e:
            errors.append(f"bot_{bot_id}.json: {str(e)}")
    
    if errors:
        error_msg = "Failed to load some bot configurations:\n" + "\n".join(f"  - {err}" for err in errors)
        raise ConfigLoadError(error_msg)
    
    if not configs:
        raise ConfigLoadError(f"No valid bot configurations loaded for IDs: {bot_ids}")
    
    return configs


def load_all_bot_configs(
    config_dir: str = "config",
    enabled_only: bool = True
) -> List[BotConfig]:
    """
    Load all bot configurations from directory.
    Reads all bot_*.json files in the config directory.
    
    Args:
        config_dir: Directory containing bot config files
        enabled_only: If True, only load enabled bots
        
    Returns:
        List of validated BotConfig instances
        
    Raises:
        ConfigLoadError: If directory doesn't exist or no valid configs found
    """
    config_path = Path(config_dir)
    
    if not config_path.exists():
        raise ConfigLoadError(f"Config directory not found: {config_dir}")
    
    if not config_path.is_dir():
        raise ConfigLoadError(f"Path is not a directory: {config_dir}")
    
    # Find all bot_*.json files
    json_files = sorted(config_path.glob("bot_*.json"))
    
    if not json_files:
        raise ConfigLoadError(f"No bot_*.json files found in: {config_dir}")
    
    configs: List[BotConfig] = []
    errors: List[str] = []
    skipped_count = 0
    
    for json_file in json_files:
        try:
            config = load_single_bot_config(str(json_file))
            
            # Filter by enabled status if requested
            if enabled_only and not config.is_enabled:
                skipped_count += 1
                continue
            
            configs.append(config)
            
        except (ConfigLoadError, FileNotFoundError) as e:
            errors.append(f"{json_file.name}: {str(e)}")
    
    if not configs:
        error_msg = f"No valid bot configurations found in {config_dir}"
        if enabled_only:
            error_msg += f" (skipped {skipped_count} disabled bots)"
        if errors:
            error_msg += ":\n" + "\n".join(f"  - {err}" for err in errors)
        raise ConfigLoadError(error_msg)
    
    return configs


def load_config(file_path: str) -> List[BotConfig]:
    """
    Legacy function for backward compatibility.
    Load bot configurations from a single JSON file (array format).
    
    Args:
        file_path: Path to configuration JSON file
        
    Returns:
        List of validated BotConfig instances
    """
    config_path = Path(file_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    
    if not config_path.is_file():
        raise ConfigLoadError(f"Path is not a file: {file_path}")
    
    try:
        with open(file=config_path, mode="r", encoding="utf-8") as f:
            raw_data = json.load(fp=f)
    except json.JSONDecodeError as e:
        raise ConfigLoadError(f"Invalid JSON in config file: {e}")
    except IOError as e:
        raise ConfigLoadError(f"Failed to read config file: {e}")
    
    # Support both single dict and array format
    if isinstance(raw_data, dict):
        raw_data = [raw_data]
    elif not isinstance(raw_data, list):
        raise ConfigLoadError(
            f"Config file must contain a JSON object or array, got {type(raw_data).__name__}"
        )
    
    if not raw_data:
        raise ConfigLoadError("Config file contains empty data")
    
    configs: List[BotConfig] = []
    errors: List[str] = []
    
    for idx, item in enumerate(raw_data):
        try:
            if not isinstance(item, dict):
                errors.append(f"Item {idx}: Expected dict, got {type(item).__name__}")
                continue
            
            config = BotConfig.from_dict(data=item)
            config.validate()
            configs.append(config)
            
        except (ValueError, KeyError) as e:
            errors.append(f"Item {idx} ({item.get('bot_name', 'unknown')}): {e}")
    
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
