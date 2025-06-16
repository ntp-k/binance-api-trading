from enum import Enum

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    ZERO = "ZERO"  # Represents no position

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_MARKET = "STOP_MARKET"
    TAKE_PROFIT = "TAKE_PROFIT"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"
    TRAILING_STOP_MARKET = "TRAILING_STOP_MARKET"

class TradeSignal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"  # Represents no action


# EOF
