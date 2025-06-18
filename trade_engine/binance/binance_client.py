import requests
import time
import pandas as pd

from trade_engine.binance import binance_auth
from commons.custom_logger import CustomLogger
from models.enum.positino_side import PositionSide

SET_LEVERAGE_URL = 'https://fapi.binance.com/fapi/v1/leverage'
GET_POSITION_URL = 'https://fapi.binance.com/fapi/v2/positionRisk'
SET_ORDER_URL = 'https://fapi.binance.com/fapi/v1/order'
GET_KLINES_URL = 'https://fapi.binance.com/fapi/v1/klines'

class BinanceClient:
    def __init__(self):
        self.logger = CustomLogger(name=BinanceClient.__name__)
        self.logger.debug("BinanceClient initialized.")
        self.__creds = binance_auth.load_binance_cred()

    def set_leverage(self, symbol: str, leverage: int) -> dict:
        """
        Change leverage for a given futures trading pair on Binance.
        """
        self.logger.info(f"Setting leverage for {symbol} to {leverage}.")
        params = {
            "timestamp": int(time.time() * 1000),
            "symbol": symbol.upper(),
            "leverage": leverage
        }

        headers, signed_params = binance_auth.sign_request(params=params, binance_credential=self.__creds)
        try:
            response = requests.post(SET_LEVERAGE_URL, headers=headers, params=signed_params)
            response.raise_for_status()
            self.logger.info(f"Leverage set successfully: {response.json()}")
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to set leverage: {e}")
            return {"error": str(e)}

    def place_order(self, symbol: str, order_side: str, order_type: str, quantity: float,
                    price: float = 0, reduce_only: bool = False, time_in_force: str = "GTC") -> dict:
        """
        Place a futures order on Binance USDT-Margined Futures.

        Args:
            symbol (str): Trading symbol (e.g., 'BTCUSDT').
            order_side (str): 'BUY' or 'SELL'.
            order_type (str): 'MARKET' or 'LIMIT'.
            quantity (float): Order quantity.
            price (float, optional): Required for LIMIT orders.
            reduce_only (bool): True will ensures your order will only reduce, close, or flatten an existing position.
            time_in_force (str, optional): Default is 'GTC' (Good Till Cancelled).

        Returns:
            dict or None: Response from Binance API.
        """

        self.logger.info(f"Placing order: {order_type} {order_side} {quantity} {symbol} (reduce_only={reduce_only})")

        # Base parameters
        params = {
            'symbol': symbol.upper(),
            'side': order_side.upper(),
            'type': order_type.upper(),
            'quantity': quantity,
            'reduceOnly': reduce_only,
            'timestamp': int(time.time() * 1000)
        }

        if order_type.upper() == 'LIMIT':
            if not price:
                raise ValueError("Price must be specified for LIMIT orders.")
            params.update({
                'price': price,
                'timeInForce': time_in_force
            })


        headers, signed_params = binance_auth.sign_request(params=params, binance_credential=self.__creds)
        try:
            response = requests.post(SET_ORDER_URL, headers=headers, params=signed_params)
            response.raise_for_status()
            self.logger.debug(f"Order placed: {response.json()}")
            return response.json()
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error placing order: {e}")
            self.logger.debug(f"Response: {response.text}") # type: ignore
            return {"error": str(e), "response": response.text} # type: ignore
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error placing order: {e}")
            return {"error": str(e)}

    def get_position(self, symbol):
        """
        Get the current futures position for a given symbol.
        """
        self.logger.debug(f"Fetching position for {symbol}...")

        params = {'timestamp': int(time.time() * 1000)}
        headers, signed_params = binance_auth.sign_request(params=params, binance_credential=self.__creds)

        try:
            response = requests.get(GET_POSITION_URL, headers=headers, params=signed_params)
            response.raise_for_status()
            positions = response.json()

            for pos in positions:
                if pos['symbol'] == symbol:
                    self.logger.debug(f"Position found: {pos}")
                    return {
                        'symbol': pos['symbol'],
                        'amount': float(pos['positionAmt']),
                        'side': PositionSide.LONG if float(pos['positionAmt']) >= 0 else PositionSide.SHORT,
                        'entry_price': float(pos['entryPrice']),
                        'unrealized_profit': float(pos['unRealizedProfit']),
                        'mark_price': float(pos['markPrice'])
                    }

            self.logger.debug(f"No active position found for {symbol}.")
            return {}

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch position: {e}")
            return {"error": str(e)}


    # Step 1: Get Kline (candlestick) data
    def fetch_klines(self, symbol, timeframe, timeframe_limit=100):
        params = {
            'symbol': symbol,
            'interval': timeframe,
            'limit': timeframe_limit
        }
        self.logger.debug(f'Fetching Klines of {params}')

        headers, signed_params = binance_auth.sign_request(params=params, binance_credential=self.__creds)

        try:
            response = requests.get(GET_KLINES_URL, headers= headers, params=signed_params)
            response.raise_for_status()
            data = response.json()
            df = pd.DataFrame(data, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'num_trades',
                'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
            ])
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Bangkok')
            df['close'] = df['close'].astype(float)
            df['open'] = df['open'].astype(float)
            self.logger.debug(f"Fetched {len(df)} Klines for {symbol} at {timeframe} interval.")

            return df
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error getting Klines: {e}")
            self.logger.debug(f"Response: {response.text}") # type: ignore
            return {"error": str(e), "response": response.text} # type: ignore
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error getting Klines: {e}")
            return {"error": str(e)}
       

# EOF
