
import requests
import hashlib
import hmac
import time
import urllib.parse
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv('API_KEY')
secret_key = os.getenv('SECRET_KEY')
base_endpoint = os.getenv('BASE_ENDPOUNT')
endpoint = '/fapi/v1/leverage'
print(api_key)
print(secret_key)


# Binance API endpoint
url = f'{base_endpoint}{endpoint}'

# Create the query string with a timestamp
params = {
    "timestamp": int(time.time() * 1000),
    "symbol": "BTCUSDT",
    "leverage": 10
}
query_string = urllib.parse.urlencode(params)

# Generate the HMAC SHA256 signature
signature = hmac.new(secret_key.encode(), query_string.encode(), hashlib.sha256).hexdigest()

# Add the signature to the parameters
params["signature"] = signature

# Set headers with API key
headers = {
    "X-MBX-APIKEY": api_key
}

# Make the request
response = requests.post(url, headers=headers, params=params)

# Print response
print(response.status_code)
print(response.json())

# EOF
