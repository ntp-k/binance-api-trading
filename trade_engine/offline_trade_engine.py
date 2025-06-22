import pandas as pd
import random
from datetime import datetime, timedelta
from commons.custom_logger import CustomLogger
from models.enum.position_side import PositionSide

class OfflineTradeEngine:
    def __init__(self):
        self.logger = CustomLogger(name=OfflineTradeEngine.__name__)

    def init(self):    
        self.logger.debug("OfflineTradeEngine initialized.")

    def set_leverage(self, symbol: str, leverage: int) -> dict:
        self.logger.debug(f"[MOCK] set_leverage called for {symbol} to {leverage}")
        return {"symbol": symbol, "leverage": leverage}

    def place_order(self, symbol: str, order_side: str, order_type: str, quantity: float,
                    price: float = 0, reduce_only: bool = False, time_in_force: str = "GTC") -> dict:
        self.logger.debug(f"[MOCK] place_order: {order_type} {order_side} {quantity} {symbol} (reduce_only={reduce_only})")
        return {
            "orderId": random.randint(10000, 99999),
            "status": "FILLED",
            "symbol": symbol,
            "side": order_side,
            "type": order_type,
            "price": price,
            "quantity": quantity,
            "reduceOnly": reduce_only,
            "timeInForce": time_in_force
        }

    def get_position(self, symbol: str) -> dict:
        self.logger.info(f"[MOCK] get_position called for {symbol}")
        side = random.choice([PositionSide.LONG, PositionSide.SHORT])
        amount = round(random.uniform(0.01, 1.0), 3)
        return {
            "symbol": symbol,
            "amount": amount if side == PositionSide.LONG else -amount,
            "side": side,
            "entry_price": round(random.uniform(20000, 30000), 2),
            "unrealized_profit": round(random.uniform(-10, 10), 2),
            "mark_price": round(random.uniform(20000, 30000), 2)
        }

    def fetch_klines(self, symbol, timeframe, timeframe_limit=100):
        self.logger.debug(f"[MOCK] fetch_klines for {symbol}, interval {timeframe}, limit {timeframe_limit}")
        base_time = datetime.now() - timedelta(minutes=int(timeframe_limit) * 15)
        times = [base_time + timedelta(minutes=15 * i) for i in range(timeframe_limit)]
        
        df = pd.DataFrame({
            "open_time": times,
            "open": [random.uniform(25000, 26000) for _ in range(timeframe_limit)],
            "high": [random.uniform(26000, 27000) for _ in range(timeframe_limit)],
            "low": [random.uniform(24000, 25000) for _ in range(timeframe_limit)],
            "close": [random.uniform(25000, 26000) for _ in range(timeframe_limit)],
            "volume": [random.uniform(10, 100) for _ in range(timeframe_limit)],
        })

        df["open_time"] = pd.to_datetime(df["open_time"]).dt.tz_localize("Asia/Bangkok")
        return df

# EOF
