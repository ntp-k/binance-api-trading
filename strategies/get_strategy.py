from models.enum.entry_strategy import EntryStrategy

def get_entry(entry_strategy, dynamic_config):
    if entry_strategy == EntryStrategy.MACDHIST_EMA_V1:
        from strategies.entry.macdhist_ema_v1 import MacdHistEMAV1Strategy
        return MacdHistEMAV1Strategy(dynamic_config=dynamic_config)

# EOF
