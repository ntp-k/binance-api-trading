from models.enum.strategies import Strategies

def get_strategy_engine(strategy: Strategies, bot_fullname: str):
    if strategy == Strategies.MACDHIST:
        from strategies.macdhist.macdhist import MACDHistStrategy
        return MACDHistStrategy(bot_fullname=bot_fullname)
    else:
        pass

# EOF
