
import requests
import hashlib
import hmac
import time
import urllib.parse
from dotenv import load_dotenv
import os

load_dotenv()

binance_api_key = os.getenv('BINANCE_API_KEY', 'Not Set')
binance_secret_key = os.getenv('BINANCE_SECRET_KEY', 'Not Set')
if binance_api_key == 'Not Set' or binance_secret_key == "Not Set":
    raise OSError("Missing required environment variables: BINANCE_API_KEY or BINANCE_SECRET_KEY")

# Binance API endpoint
url = 'https://fapi.binance.com/fapi/v1/leverage'

# Create the query string with a timestamp
params = {
    "timestamp": int(time.time() * 1000),
    "symbol": "BTCUSDT",
    "leverage": 10
}
query_string = urllib.parse.urlencode(params)

# Generate the HMAC SHA256 signature
signature = hmac.new(binance_secret_key.encode(), query_string.encode(), hashlib.sha256).hexdigest()

# Add the signature to the parameters
params["signature"] = signature

# Set headers with API key
headers = {
    "X-MBX-APIKEY": binance_api_key
}

# Make the request
response = requests.post(url, headers=headers, params=params)

# Print response
print(response.status_code)
print(response.json())

# EOF
