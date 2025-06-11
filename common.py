import hashlib
import hmac
import urllib.parse
import requests
import os
from dotenv import load_dotenv

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
    load_dotenv()

    api_key = os.getenv('API_KEY')
    secret_key = os.getenv('SECRET_KEY')

    if not all([api_key, secret_key]):
        raise EnvironmentError("❌ Missing required environment variables: API_KEY or SECRET_KEY")
    
    return BinanceCredentials(api_key=api_key, secret_key=secret_key)


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

if __name__ == "__main__":
    test_binance_connection()

# EOF
