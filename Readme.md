# Prerequisite(s)
- Binance Global Account

# Binance API
- [Derivatives](https://developers.binance.com/docs/derivatives/Introduction)

# Prepare Environment
- create virtual environment
```
python3 -m venv <dir_name>
source <dir_name>/bin/activate
python3 -m pip install -r requirements.txt

# example
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

- create .env
```
# Binance
BINANCE_API_KEY=xxx
BINANCE_SECRET_KEY=xxx

# Google Sheet
GOOGLE_SHEET_SERVICE_ACCOUNT_FILE=_private_binance-trading-logger-cred.json
GOOGLE_SHEET_SPREADSHEET_KEY=xxx
GOOGLE_SHEET_WORKSHEET_INDEX=0

LOG_LEVELS=DEBUG
# LOG_LEVELS=INFO
# LOG_LEVELS=WARNING
# LOG_LEVELS=ERROR
# LOG_LEVELS=CRITICAL
```

- ./_private_binance-trading-logger-cred.json

# Bot Configuration
- see example of bot configuration in `config/bots_config_example.json`

# Run Bot
```
./start_bot_services.sh
```