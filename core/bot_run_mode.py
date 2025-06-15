from enum import Enum

class BotRunMode(Enum):
    BACKTEST = "backtest"
    SIMULATION = "simulation"
    LIVE = "live"
