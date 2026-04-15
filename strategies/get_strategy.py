from typing import Dict, Any, Tuple
from abstracts.base_entry_strategy import BaseEntryStrategy
from abstracts.base_exit_strategy import BaseExitStrategy
from models.enum.entry_strategy import EntryStrategy
from models.enum.exit_strategy import ExitStrategy


# Strategy registry for lazy loading
ENTRY_STRATEGY_REGISTRY = {
    EntryStrategy.MACD_STATE: ('strategies.entry.entry_macd_state', 'EntryMacdState'),
    EntryStrategy.MACDHIST_STATE: ('strategies.entry.entry_macdhist_state', 'EntryMacdHistState'),
    EntryStrategy.MACDHIST_EMA_V1: ('strategies.entry.entry_macdhist_ema_v1', 'EntryMacdHistEMAV1'),
    EntryStrategy.PRICE_CROSS_EMA_RSI: ('strategies.entry.entry_price_cross_ema_rsi', 'EntryPriceCrossEMARSI'),
    EntryStrategy.PREVIOUS_CANDLE: ('strategies.entry.entry_previous_candle', 'EntryPreviousCandle'),
    EntryStrategy.MOMENTUM_TREND_FILTERED: ('strategies.entry.entry_momentum_trend_filtered', 'EntryMomentumTrendFiltered'),
}

EXIT_STRATEGY_REGISTRY = {
    ExitStrategy.MACD_STATE: ('strategies.exit.exit_macd_state', 'ExitMacdState'),
    ExitStrategy.MACDHIST_STATE: ('strategies.exit.exit_macdhist_state', 'ExitMacdHistState'),
    ExitStrategy.TP_SL: ('strategies.exit.exit_tp_sl', 'ExitTPSL'),
    ExitStrategy.CANDLE_CLOSE_WITH_SL: ('strategies.exit.exit_candle_close_with_sl', 'ExitCandleCloseWithSL'),
}


def get_entry_strategy(entry_strategy: EntryStrategy, dynamic_config: Dict[str, Any]) -> BaseEntryStrategy:
    """
    Factory function to create entry strategy instances.
    
    Args:
        entry_strategy: Entry strategy enum
        dynamic_config: Strategy-specific configuration
        
    Returns:
        Entry strategy instance
        
    Raises:
        ValueError: If strategy is not registered
        ImportError: If strategy module cannot be imported
    """
    if entry_strategy not in ENTRY_STRATEGY_REGISTRY:
        raise ValueError(
            f"Unknown entry strategy: {entry_strategy}. "
            f"Available: {list(ENTRY_STRATEGY_REGISTRY.keys())}"
        )
    
    module_path, class_name = ENTRY_STRATEGY_REGISTRY[entry_strategy]
    
    try:
        # Dynamic import
        module = __import__(module_path, fromlist=[class_name])
        strategy_class = getattr(module, class_name)
        return strategy_class(dynamic_config=dynamic_config)
    except ImportError as e:
        raise ImportError(f"Failed to import {class_name} from {module_path}: {e}")
    except AttributeError as e:
        raise ImportError(f"Class {class_name} not found in {module_path}: {e}")


def get_exit_strategy(exit_strategy: ExitStrategy, dynamic_config: Dict[str, Any]) -> BaseExitStrategy:
    """
    Factory function to create exit strategy instances.
    
    Args:
        exit_strategy: Exit strategy enum
        dynamic_config: Strategy-specific configuration
        
    Returns:
        Exit strategy instance
        
    Raises:
        ValueError: If strategy is not registered
        ImportError: If strategy module cannot be imported
    """
    if exit_strategy not in EXIT_STRATEGY_REGISTRY:
        raise ValueError(
            f"Unknown exit strategy: {exit_strategy}. "
            f"Available: {list(EXIT_STRATEGY_REGISTRY.keys())}"
        )
    
    module_path, class_name = EXIT_STRATEGY_REGISTRY[exit_strategy]
    
    try:
        # Dynamic import
        module = __import__(module_path, fromlist=[class_name])
        strategy_class = getattr(module, class_name)
        return strategy_class(dynamic_config=dynamic_config)
    except ImportError as e:
        raise ImportError(f"Failed to import {class_name} from {module_path}: {e}")
    except AttributeError as e:
        raise ImportError(f"Class {class_name} not found in {module_path}: {e}")


def init_strategies(
    entry_strategy: EntryStrategy,
    exit_strategy: ExitStrategy,
    dynamic_config: Dict[str, Any]
) -> Tuple[BaseEntryStrategy, BaseExitStrategy]:
    """
    Initialize both entry and exit strategies.
    
    Args:
        entry_strategy: Entry strategy enum
        exit_strategy: Exit strategy enum
        dynamic_config: Strategy-specific configuration
        
    Returns:
        Tuple of (entry_strategy_instance, exit_strategy_instance)
        
    Raises:
        ValueError: If strategies cannot be initialized
    """
    try:
        entry = get_entry_strategy(
            entry_strategy=entry_strategy,
            dynamic_config=dynamic_config
        )
        exit = get_exit_strategy(
            exit_strategy=exit_strategy,
            dynamic_config=dynamic_config
        )
    except (ValueError, ImportError) as e:
        raise ValueError(f"Failed to initialize strategies: {e}")
    
    if entry is None or exit is None:
        raise ValueError("Strategy initialization returned None")

    return entry, exit


# EOF
