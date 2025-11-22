import requests
import time
import pandas as pd

from abstracts.base_live_trade_client import BaseLiveTradeClient
from models.enum.position_side import PositionSide
import trade_clients.binance.binance_auth as binance_auth

SET_LEVERAGE_URL = 'https://fapi.binance.com/fapi/v1/leverage'
GET_POSITION_URL = 'https://fapi.binance.com/fapi/v2/positionRisk'
SET_ORDER_URL = 'https://fapi.binance.com/fapi/v1/order'
GET_KLINES_URL = 'https://fapi.binance.com/fapi/v1/klines'
GET_TICKER_PRICE_URL = 'https://fapi.binance.com/fapi/v1/ticker/price'
GET_ORDER = 'https://fapi.binance.com/fapi/v1/order'
GET_TRADE = 'https://fapi.binance.com/fapi/v1/userTrades'

class BinanceLiveTradeClient(BaseLiveTradeClient):
    def __init__(self) -> None:
        super().__init__()
        self.set_wait_time(wait_time_sec=20)
        self.set_running(running=True)
    
    def init(self):
        self.__creds = binance_auth.load_binance_cred()
        self.logger.debug(message=f"Initialized {self.__class__.__name__}")

    def set_leverage(self, symbol: str, leverage: int) -> dict:
        """
        Change leverage for a given futures trading pair on Binance.
        """
        self.logger.debug(message=f"Setting leverage for {symbol} to {leverage}.")
        params = {
            "timestamp": int(time.time() * 1000),
            "symbol": symbol.upper(),
            "leverage": leverage
        }

        headers, signed_params = binance_auth.sign_request(params=params, binance_credential=self.__creds)
        try:
            response = requests.post(url=SET_LEVERAGE_URL, headers=headers, params=signed_params)
            response.raise_for_status()
            self.logger.debug(message=f"Leverage set successfully: {response.json()}")
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(message=f"Failed to set leverage: {e}")
            return {"error": str(object=e)}

    def fetch_position(self, symbol):
        """
        Get the current futures position for a given symbol.
        """
        # self.logger.debug(message=f"Fetching position for {symbol}...")

        params = {'timestamp': int(time.time() * 1000)}
        headers, signed_params = binance_auth.sign_request(params=params, binance_credential=self.__creds)

        try:
            response = requests.get(url=GET_POSITION_URL, headers=headers, params=signed_params)
            response.raise_for_status()
            positions = response.json()

            for pos in positions:
                if pos['symbol'] == symbol:
                    if float(pos['positionAmt']) == 0:
                        continue

                    pnl = float(pos['unRealizedProfit'])
                    position_side = PositionSide.LONG if float(pos['positionAmt']) >= 0 else PositionSide.SHORT
                    self.logger.info(message=f"Position found: {pos['symbol']} | {position_side.value} | {'+' if pnl >= 0 else ''}{pnl:.2f}")

                    return {
                        'symbol': pos['symbol'],
                        'quantity': float(pos['positionAmt']),
                        'position_side': position_side,
                        'entry_price': float(pos['entryPrice']),
                        'pnl': pnl,
                        'mark_price': float(pos['markPrice'])
                    }

            self.logger.debug(message=f"No active position found for {symbol}.")
            return {}

        except requests.exceptions.RequestException as e:
            self.logger.error(message=f"Failed to fetch position: {e}")
            return {"error": str(object=e)}

    def fetch_price(self, symbol):
        params = {'symbol': symbol}
        # self.logger.debug(message=f'Fetching current price of {params_2}')
        headers, signed_params = binance_auth.sign_request(params=params, binance_credential=self.__creds)
        try:
            response = requests.get(url=GET_TICKER_PRICE_URL, headers= headers, params=signed_params)
            response.raise_for_status()
            current_price = float(response.json()["price"])
            return current_price
            # self.logger.debug(message=f"Fetched current price for {symbol}: {current_price}")
        except Exception as e:
            self.logger.error_e(message=f"error getting price", e=e)
            return 0.0

    def fetch_klines(self, symbol, timeframe, timeframe_limit=100):
        df = None

        # fetch klines
        params = {
            'symbol': symbol,
            'interval': timeframe,
            'limit': timeframe_limit
        }
        # self.logger.debug(message=f'Fetching Klines of {params}')

        headers, signed_params = binance_auth.sign_request(params=params, binance_credential=self.__creds)
        try:
            response = requests.get(url=GET_KLINES_URL, headers= headers, params=signed_params)
            response.raise_for_status()
            data = response.json()
            df = pd.DataFrame(data=data, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'num_trades',
                'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
            ])
            df['open_time'] = pd.to_datetime(arg=df['open_time'], unit='ms').dt.tz_localize(tz='UTC').dt.tz_convert(tz='Asia/Bangkok') # type: ignore
            df['high'] = df['high'].astype(dtype=float)
            df['low'] = df['low'].astype(dtype=float)
            df['close'] = df['close'].astype(dtype=float)
            df['open'] = df['open'].astype(dtype=float)
            # self.logger.debug(message=f"Fetched {len(df)} Klines for {symbol} at {timeframe} interval.")
        except requests.exceptions.HTTPError as e:
            self.logger.error_e(message=f"HTTP error getting Klines", e=e)
            self.logger.debug(message=f"Response: {response.text}") # type: ignore
            return df
        except requests.exceptions.RequestException as e:
            self.logger.error_e(message=f"Network error getting Klines", e=e)
            return df

        # fetch current price
        current_price = self.fetch_price(symbol=symbol)
        df["current_price"] = df["close"]
        df.loc[df.index[-1], "current_price"] = current_price

        return df 

    def fetch_order(self, symbol, order_id: str = ''):
        params = {
            'symbol': symbol,
            'orderId': order_id,
            'timestamp': int(time.time() * 1000)
        }
        headers, signed_params = binance_auth.sign_request(params=params, binance_credential=self.__creds)
        try:
            response = requests.get(url=GET_ORDER, headers= headers, params=signed_params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error_e(message=f"error getting order", e=e)
            return {}

    def cancel_order(self, symbol, order_id: str = ''):
        params = {
            'symbol': symbol,
            'orderId': order_id,
            'timestamp': int(time.time() * 1000)
        }
        headers, signed_params = binance_auth.sign_request(params=params, binance_credential=self.__creds)
        try:
            response = requests.delete(url=GET_ORDER, headers= headers, params=signed_params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error_e(message=f"error canceling order", e=e)
            return {}

    def place_order(self, symbol: str, order_side: str, order_type: str, quantity: float,
                    price: float = 0, reduce_only: bool = False, time_in_force: str = "GTC", close_position: bool = False, stop_price: float = -1) -> dict:
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

        self.logger.debug(message=f"Placing order: {order_type} {order_side} {quantity} {symbol} (reduce_only={reduce_only})")

        # Base parameters
        params = {
            'symbol': symbol.upper(),
            'side': order_side.upper(),
            'type': order_type.upper(),
            'quantity': quantity,
            'reduceOnly': reduce_only,
            'closePosition': 'true' if close_position else 'false',
            'timestamp': int(time.time() * 1000)
        }

        if order_type.upper() == 'LIMIT':
            if not price:
                raise ValueError("Price must be specified for LIMIT orders.")
            params.update({
                'price': price,
                'timeInForce': time_in_force
            })
        if stop_price != -1:
            params.update({
                'stopPrice': stop_price
            })
            del params['reduceOnly']

        headers, signed_params = binance_auth.sign_request(params=params, binance_credential=self.__creds)
        try:
            response = requests.post(url=SET_ORDER_URL, headers=headers, params=signed_params)
            response.raise_for_status()
            self.logger.debug(message=f"Order placed: {response.json()}")
            return response.json()
        except requests.exceptions.HTTPError as e:
            self.logger.error(message=f"HTTP error placing order: {e}")
            self.logger.debug(message=f"Response: {response.text}") # type: ignore
            return {"error": str(object=e), "response": response.text} # type: ignore
        except requests.exceptions.RequestException as e:
            self.logger.error(message=f"Network error placing order: {e}")
            return {"error": str(object=e)}

    def fetch_trades(self, symbol: str = '', order_id: str = ''):
        params = {
            'timestamp': int(time.time() * 1000)
        }

        if symbol != '':
            params['symbol'] = symbol

        if order_id != '':
            params['orderId'] = order_id

        headers, signed_params = binance_auth.sign_request(params=params, binance_credential=self.__creds)
        try:
            response = requests.get(url=GET_TRADE, headers= headers, params=signed_params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error_e(message=f"error getting order", e=e)
            return {}
    
    def fetch_order_trade(self, symbol: str = '', order_id: str = ''):
        trades = self.fetch_trades(symbol=symbol, order_id=order_id)

        if not trades:
            return {
            "price": 0.0,
            "fee": 0.0,
            "pnl": 0.0,
            "side": "ZERO"
        }

        total_quote = 0.0
        total_qty = 0.0
        total_fee = 0.0
        total_pnl = 0.0

        for t in trades:
            qty = float(t["qty"])
            quoteQty = float(t["quoteQty"])
            fee = float(t["commission"])
            pnl = float(t["realizedPnl"])

            total_qty += qty
            total_quote += quoteQty
            total_fee += fee
            total_pnl += pnl

        avg_price = total_quote / total_qty if total_qty > 0 else 0.0

        return {
            "price": avg_price,
            "fee": total_fee,
            "pnl": total_pnl,
            "side": trades[0]["side"]
        }

if __name__ == "__main__":
    pass

# EOF
