import os
import hmac
import requests
import hashlib
import urllib.parse

from commons.custom_logger import CustomLogger

logger = CustomLogger(name=os.path.basename(__file__)[:-3])

class BinanceCredentials:
    def __init__(self, binance_api_key: str, binance_secret_key: str):
        self.logger = CustomLogger(name=str(BinanceCredentials.__name__))

        self.binance_api_key = binance_api_key
        self.binance_secret_key = binance_secret_key

        self.logger.debug(message="Initialized BinanceCredentials")

def load_binance_cred():
    """
    Load Binance API credentials from environment variables.

    Required environment variables:
        - BINANCE_API_KEY
        - BINANCE_SECRET_KEY

    Returns:
        BinanceCredentials

    Raises:
        EnvironmentError: If any required variable is missing.
    """
    
    logger.debug("Attempting to load Binance credentials from .env flie.")


    binance_api_key = os.getenv('BINANCE_API_KEY', 'Not Set')
    binance_secret_key = os.getenv('BINANCE_SECRET_KEY', 'Not Set')
    if binance_api_key == 'Not Set' or binance_secret_key == "Not Set":
        log = "Missing required environment variables: BINANCE_API_KEY or BINANCE_SECRET_KEY"
        logger.critical(log)
        raise OSError(log)

    logger.debug(f"Loaded binance api key: {binance_api_key[:2]}***{binance_api_key[-2:]}")
    logger.debug("Loaded binance secret key: ******")
    return BinanceCredentials(binance_api_key, binance_secret_key)


def sign_request(params: dict, binance_credential) -> tuple:
    """
    Sign Binance API request parameters using credentials.

    Args:
        params (dict): Request parameters (must include 'timestamp').
        binance_credential (BinanceCredentials): 'binance_api_key' and 'binance_secret_key'.

    Returns:
        tuple:
            - signed_params (dict): Parameters with 'signature' added.
            - headers (dict): Headers with 'X-MBX-APIKEY'.
    """
    logger.debug(f"Signing request with params: {params}")

    query_string = urllib.parse.urlencode(params)
    logger.debug(f"Query string to sign: {query_string}")

    signature = hmac.new(
        binance_credential.binance_secret_key.encode(),
        query_string.encode(),
        hashlib.sha256
    ).hexdigest()
    logger.debug(f"Signature generated: {signature[:2]}***{signature[-2:]}")

    params['signature'] = signature

    headers = {
        "X-MBX-APIKEY": binance_credential.binance_api_key
    }

    logger.debug(f"Headers set with API key prefix: {binance_credential.binance_api_key[:2]}***{binance_credential.binance_api_key[-2:]}")
    params_str = str(params).split('signature')[0] + 'signature' + str(params).split('signature')[1][:6] + '***' + str(params).split('signature')[1][-4:]
    logger.debug(f"Params set: {params_str}")

    return headers, params


def test_binance_connection() -> bool:
    logger.info("Checking Binance API connectivity...")

    try:
        response = requests.get(
            'https://fapi.binance.com/fapi/v1/ping', timeout=5)

        if response.status_code == 200 and response.json() == {}:
            logger.info("Binance connection successful.")
            return True
        else:
            logger.error(f"unexpected response code: {response.status_code}")
            logger.debug(f"unexpected response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"Binance connection error: {e}")
        return False


if __name__ == "__main__":
    bcred = load_binance_cred()
    test_binance_connection()
    _, __ = sign_request(params={"aaa": "bbb", 'ccc': 'ddd'}, binance_credential=bcred)

# EOF
