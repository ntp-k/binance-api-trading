from enum import Enum

class BotRunMode(Enum):
    BACKTEST = "backtest"
    FORWARDTEST = "forwardtest"
    LIVE = "live"



'''
Params Mapping from BotConfig

BACKTEST
    BotConfig.params_1 = Trading Interval in minutes (ex. 86400 = backtest for 1 day (yesterday)
    BotConfig.params_2 = Initial Balance in USD (ex. 100.0)
    BotConfig.params_3 = None
    BotConfig.params_4 = None
    BotConfig.params_5 = None

FORWARDTEST
    BotConfig.params_1 = None
    BotConfig.params_2 = None
    BotConfig.params_3 = None
    BotConfig.params_4 = None
    BotConfig.params_5 = None

LIVE
    BotConfig.params_1 = None
    BotConfig.params_2 = None
    BotConfig.params_3 = None
    BotConfig.params_4 = None
    BotConfig.params_5 = None
'''