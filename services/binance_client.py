import requests
import time
import hashlib
import hmac
import urllib.parse
import os
from dotenv import load_dotenv

import common.common as common

load_dotenv()

class BinanceCredentials:
    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key


def load_binance_cred():
    """
    Load Binance API credentials from environment variables.

    Required environment variables:
        - API_KEY
        - SECRET_KEY

    Returns:
        dict: Dictionary with keys 'api_key' and 'secret_key'.

    Raises:
        EnvironmentError: If any required variable is missing.
    """
    

    binance_api_key = os.getenv('BINANCE_API_KEY', 'default_api_key')
    binance_secret_key = os.getenv('BINANCE_SECRET_KEY', 'defaule_secret_key')

    if not all([binance_api_key, binance_secret_key]):
        raise EnvironmentError("❌ Missing required environment variables: API_KEY or SECRET_KEY")
    
    return BinanceCredentials(api_key=binance_api_key, secret_key=binance_secret_key)


def test_binance_connection():
    url = 'https://fapi.binance.com/fapi/v1/ping'
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200 and response.json() == {}:
            print("✅ Binance connection successful.")
            return True
        else:
            print(f"❌ Unexpected response: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Binance connection error: {e}")
        return False


def sign_request(params: dict, binance_credential) -> tuple:
    """
    Sign Binance API request parameters using credentials.

    Args:
        params (dict): Request parameters (must include 'timestamp').
        binance_credential (BinanceCredentials): 'api_key' and 'secret_key'.

    Returns:
        tuple:
            - signed_params (dict): Parameters with 'signature' added.
            - headers (dict): Headers with 'X-MBX-APIKEY'.
    """

    query_string = urllib.parse.urlencode(params)
    signature = hmac.new(
        binance_credential.secret_key.encode(),
        query_string.encode(),
        hashlib.sha256
    ).hexdigest()
    params['signature'] = signature

    headers = {
        "X-MBX-APIKEY": binance_credential.api_key
    }

    return headers, params
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

        headers, signed_params = sign_request(params=params, binance_credential=self._creds)
        response = requests.post(url, headers=headers, params=signed_params)
        # response.raise_for_status()
        return response

    def place_order(self, symbol: str, order_side: str, order_type: str, quantity: float,
                    price: float = 0, reduce_only: bool = False, time_in_force: str = "GTC"):
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

        headers, signed_params = sign_request(
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
