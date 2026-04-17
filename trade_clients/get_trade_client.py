from typing import Dict, Tuple, Type, Optional
from abstracts.base_trade_client import BaseTradeClient
from commons.custom_logger import CustomLogger
from models.enum.run_mode import RunMode
from models.enum.trade_client import TradeClient


# Trade client registry: (TradeClient, RunMode) -> (module_path, class_name, needs_init)
TRADE_CLIENT_REGISTRY: Dict[Tuple[TradeClient, RunMode], Tuple[str, str, bool]] = {
    (TradeClient.BINANCE, RunMode.LIVE): (
        'trade_clients.binance.binance_live_trade_client',
        'BinanceLiveTradeClient',
        True  # Needs init() call
    ),
    (TradeClient.BINANCE, RunMode.BACKTEST): (
        'trade_clients.binance.binance_backtest_trade_client',
        'BinanceBacktestTradeClient',
        True  # Needs init() call
    ),
    (TradeClient.OFFLINE, RunMode.LIVE): (
        'trade_clients.offline.offline_live_client',
        'OfflineLiveTradeClient',
        False  # No init needed
    ),
}


def get_trade_client(run_mode: RunMode, trade_client: TradeClient, logger: Optional[CustomLogger] = None) -> BaseTradeClient:
    """
    Factory function to create trade client instances.
    
    Args:
        run_mode: Trading mode (LIVE, BACKTEST, etc.)
        trade_client: Client type (BINANCE, OFFLINE, etc.)
        logger: Optional logger to inherit from bot
        
    Returns:
        Initialized trade client instance
        
    Raises:
        ValueError: If combination of run_mode and trade_client is not supported
        ImportError: If client module cannot be imported
    """
    registry_key = (trade_client, run_mode)
    
    if registry_key not in TRADE_CLIENT_REGISTRY:
        available = [f"{tc.value}/{rm.value}" for tc, rm in TRADE_CLIENT_REGISTRY.keys()]
        raise ValueError(
            f"Unsupported combination: {trade_client.value}/{run_mode.value}. "
            f"Available: {', '.join(available)}"
        )
    
    module_path, class_name, needs_init = TRADE_CLIENT_REGISTRY[registry_key]
    
    try:
        # Dynamic import
        module = __import__(module_path, fromlist=[class_name])
        client_class: Type[BaseTradeClient] = getattr(module, class_name)
        
        # Instantiate client with logger
        client = client_class(logger=logger)
        
        # Call init() if required and available
        if needs_init and hasattr(client, 'init'):
            client.init()  # type: ignore
        
        return client
        
    except ImportError as e:
        raise ImportError(f"Failed to import {class_name} from {module_path}: {e}")
    except AttributeError as e:
        raise ImportError(f"Class {class_name} not found in {module_path}: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to initialize {class_name}: {e}")

# EOF
