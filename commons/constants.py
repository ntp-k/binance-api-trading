"""
Constants and configuration values used across the trading bot application.
"""

# Directory paths
POSITION_RECORDS_DIR = "position_records"
POSITION_STATES_DIR = "position_states"
LOGS_DIR = "logs"

# File name templates
POSITION_RECORD_FILENAME_TEMPLATE = "runid_{run_id}_record_{dt}.json"
POSITION_STATES_FILENAME_TEMPLATE = "runid_{run_id}_state.json"

# Bot configuration
BOT_CONFIG_PATH = "config/bots_config.json"

# Order execution timing (seconds)
ORDER_PLACEMENT_WAIT = 2  # Wait time after placing order for exchange processing
ORDER_STATUS_CHECK_INTERVAL = 1  # Interval to check order status
LIMIT_ORDER_PRICE_CHECK_INTERVAL = 5  # Interval to check price changes for limit orders
JITTER_SECONDS = 5  # Random jitter to prevent synchronized API calls

# Technical indicator defaults
MACD_12 = 12
MACD_26 = 26
MACD_9 = 9
EMA_200 = 200
RSI_14 = 14
ATR_14 = 14

# Order status
ORDER_STATUS_FILLED = "FILLED"
ALGO_ORDER_STATUS_FINISHED = "FINISHED"

# Time format
DATETIME_FORMAT_GMT7 = "%Y-%m-%d %H:%M:%S"
DATETIME_FORMAT_FILE = "%Y%m%d_%H%M%S"
DATETIME_FORMAT_LOG = "%Y%m%d_%H%M"

# Logging
DEFAULT_LOG_LEVEL = "INFO"

# EOF

# Made with Bob
