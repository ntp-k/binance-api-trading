import requests
import time
import common


binance_cred = common.load_binance_cred()


def set_leverage(symbol: str, leverage: int):
    """
    Change leverage for a given futures trading pair on Binance.

    Args:
        symbol (str): The trading pair symbol, e.g., 'BTCUSDT'.
        leverage (int): The desired leverage level, e.g., 10.
        api_key (str): Binance API key.
        secret_key (str): Binance Secret key.

    Returns:
        dict: JSON response from Binance API or None if request fails.
    """

    url = 'https://fapi.binance.com/fapi/v1/leverage'

    params = {
        "timestamp": int(time.time() * 1000),
        "symbol": symbol.upper(),
        "leverage": leverage
    }

    headers, signed_params = common.sign_request(params=params, binance_credential=binance_cred)
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
        api_key (str): Binance API key.
        secret_key (str): Binance secret key.
        price (float, optional): Required for LIMIT orders.
        time_in_force (str, optional): Default is 'GTC' (Good Till Cancelled).

    Returns:
        dict or None: Response from Binance API.
    """

    url = 'https://fapi.binance.com/fapi/v1/order'
    timestamp = int(time.time() * 1000)

    # Base parameters
    params = {
        'symbol': symbol.upper(),
        'side': order_side.upper(),
        'type': order_type.upper(),
        'quantity': quantity,
        'reduceOnly': reduce_only,
        'timestamp': timestamp
    }

    # Add optional parameters for limit orders
    if order_type.upper() == 'LIMIT':
        if price is None:
            raise ValueError("Price must be specified for LIMIT orders.")
        params['price'] = price
        params['timeInForce'] = time_in_force

    headers, signed_params = common.sign_request(params=params, binance_credential=binance_cred)
    response = requests.post(url, headers=headers, params=signed_params)

    try:
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print("HTTP error:", e)
        print("Response:", response.text)
        return None



if __name__ == "__main__":
    symbol = "SOLUSDT"
    leverage = 100

    response= set_leverage(symbol=symbol, leverage=leverage)
    if response.status_code == 200:
        print(f'set leverage of {symbol} to {leverage}')
    else:
        print(f'error setting leverage of {symbol} to {leverage}')
        exit()

    position = place_order(
        symbol=symbol,
        order_side='SELL', # BUY, SELL
        order_type='MARKET', # LIMIT, MARKET, STOP, STOP_MARKET ...
        quantity=1,
        reduce_only=False
    )
    print(position)

# EOF
