from models.enum.entry_strategy import EntryStrategy
from models.enum.exit_strategy import ExitStrategy

def get_entry_strategy(entry_strategy, dynamic_config):
    if entry_strategy == EntryStrategy.MACD_STATE:
        from strategies.entry.entry_macd_state import EntryMacdState
        return EntryMacdState(dynamic_config=dynamic_config)
    elif entry_strategy == EntryStrategy.MACDHIST_STATE:
        from strategies.entry.entry_macdhist_state import EntryMacdHistState
        return EntryMacdHistState(dynamic_config=dynamic_config)
    elif entry_strategy == EntryStrategy.MACDHIST_EMA_V1:
        from strategies.entry.entry_macdhist_ema_v1 import EntryMacdHistEMAV1
        return EntryMacdHistEMAV1(dynamic_config=dynamic_config)
    elif entry_strategy == EntryStrategy.PRICE_CROSS_EMA_RSI:
        from strategies.entry.entry_price_cross_ema_rsi import EntryPriceCrossEMARSI
        return EntryPriceCrossEMARSI(dynamic_config=dynamic_config)

def get_exit_strategy(exit_strategy, dynamic_config):
    if exit_strategy == ExitStrategy.MACD_STATE:
        from strategies.exit.exit_macd_state import ExitMacdState
        return ExitMacdState(dynamic_config=dynamic_config)
    elif exit_strategy == ExitStrategy.MACDHIST_STATE:
        from strategies.exit.exit_macdhist_state import ExitMacdHistState
        return ExitMacdHistState(dynamic_config=dynamic_config)
    elif exit_strategy == ExitStrategy.TP_SL:
        from strategies.exit.exit_tp_sl import ExitTPSL
        return ExitTPSL(dynamic_config=dynamic_config)

def init_strategies(entry_strategy, exit_strategy, dynamic_config):
    try:
        entry = get_entry_strategy(entry_strategy=entry_strategy, dynamic_config=dynamic_config)
        exit = get_exit_strategy(exit_strategy=exit_strategy, dynamic_config=dynamic_config)
    except Exception as e:
        raise ValueError(f"Failed to initialize strategies: {e}")
 
    if entry is None or exit is None:
        raise ValueError("Invalid entry or exit strategy provided.")

    return entry, exit


# EOF
