import requests
import time
import common


class BinanceClient:
    def __init__(self, credentials):
        self._creds = credentials

    def set_leverage(self, symbol: str, leverage: int):
        url = 'https://fapi.binance.com/fapi/v1/leverage'

        params = {
            "timestamp": int(time.time() * 1000),
            "symbol": symbol.upper(),
            "leverage": leverage
        }

        headers, signed_params = common.sign_request(params=params, binance_credential=self._creds)
        response = requests.post(url, headers=headers, params=signed_params)
        # response.raise_for_status()
        return response

    def place_order(symbol: str, order_side: str, order_type: str, quantity: float,
                    price: float = None, reduce_only: bool = False, time_in_force: str = "GTC"):
        """
        Place a futures order on Binance USDT-Margined Futures.

        Args:
            symbol (str): Trading symbol (e.g., 'BTCUSDT').
            order_side (str): 'BUY' or 'SELL'.
            order_type (str): 'MARKET' or 'LIMIT'.
            quantity (float): Order quantity.
            price (float, optional): Required for LIMIT orders.
            reduce_only (bool): True = Effect only the openned position, False can open new order
            time_in_force (str, optional): Default is 'GTC' (Good Till Cancelled).

        Returns:
            dict or None: Response from Binance API.
        """

    def get_position(self, symbol):
        url = "https://fapi.binance.com/fapi/v2/positionRisk"

        headers, signed_params = common.sign_request(
            params={'timestamp': int(time.time() * 1000)}, binance_credential=self._creds
        )

        response = requests.get(url, headers=headers, params=signed_params)
        response.raise_for_status()

        positions = response.json()

        # Filter for selected symbol
        for pos in positions:
            if pos['symbol'] == symbol:
                return {
                    'symbol': pos['symbol'],
                    # >0 long, <0 short, 0 no position
                    'position_amt': float(pos['positionAmt']),
                    'entry_price': float(pos['entryPrice']),
                    'unrealized_profit': float(pos['unRealizedProfit']),
                    'mark_price': float(pos['markPrice'])
                }

        return None  # No position for this symbol

# EOF
