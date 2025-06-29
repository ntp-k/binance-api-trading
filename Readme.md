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

# Configuration
- see example of bot configuration in `config/bots_config_example.json`

# Run Bot
```
python3 main.py
```