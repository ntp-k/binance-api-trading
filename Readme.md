# Binance Futures Trading Bot

A sophisticated automated trading system for Binance Futures with multi-strategy support, backtesting capabilities, and live trading with comprehensive position management.

## 🏗️ Architecture Overview

```
main.py → BotManager → Multiple Bot Instances (threaded)
                           ├── Trade Client (Binance/Offline)
                           ├── Entry Strategy
                           ├── Exit Strategy
                           └── Position Handler
```

![](./img/architecture_overview.png)

### Core Components

#### 1. **Bot Manager** (`core/bot_manager.py`)
- Loads bot configurations from `config/bots_config.json`
- Creates and manages multiple bot instances
- Runs each bot in separate threads for parallel execution

#### 2. **Bot** (`core/bot.py`)
Main trading logic with three operational states:

**State 1: Looking for Entry** (No Position)
- Fetches klines (candlestick data) from Binance
- Runs entry strategy to detect signals
- Places MARKET/LIMIT orders to open positions
- Optionally sets TP (Take Profit) and SL (Stop Loss) orders

**State 2: Monitoring TP/SL** (Orders Active)
- Checks if TP or SL orders are filled
- Cancels opposite order when one hits
- Records closed position

**State 3: Looking for Exit** (Position Active)
- Updates PnL continuously
- Runs exit strategy to detect close signals
- Places orders to close position
- Cancels any active TP/SL orders

#### 3. **Position Handler** (`core/position_handler.py`)
- Manages position state in memory
- Persists position state to JSON files in `position_states/`
- Records completed trades in `position_records/`
- Tracks max/min PnL during position lifetime

#### 4. **Trade Clients**

**Binance Live Client** (`trade_clients/binance/binance_live_trade_client.py`)
- Connects to Binance Futures API
- Fetches real-time klines, positions, prices
- Places/cancels orders (MARKET, LIMIT, STOP_MARKET)
- Sets leverage for trading pairs

**Offline Client** (`trade_clients/offline/offline_live_client.py`)
- For backtesting mode
- Uses historical data instead of live API

## 📊 Trading Strategies

### Entry Strategies

1. **MACD Histogram EMA V1** (`strategies/entry/entry_macdhist_ema_v1.py`)
   - **LONG**: Price above EMA-200 + MACD histogram crosses from negative to positive (2 increasing candles)
   - **SHORT**: Price below EMA-200 + MACD histogram crosses from positive to negative (2 decreasing candles)

2. **MACD Histogram State** (`strategies/entry/entry_macdhist_state.py`)
   - Simpler MACD histogram state changes

3. **MACD State** (`strategies/entry/entry_macd_state.py`)
   - MACD line state changes

4. **Price Cross EMA RSI** (`strategies/entry/entry_price_cross_ema_rsi.py`)
   - Combines price/EMA crossover with RSI conditions

5. **Previous Candle** (`strategies/entry/entry_previous_candle.py`)
   - Entry based on previous candle patterns

### Exit Strategies

1. **MACD Histogram State** (`strategies/exit/exit_macdhist_state.py`)
   - Closes LONG when histogram goes negative
   - Closes SHORT when histogram goes positive
   - **Safety checks**:
     - Must be different candle than entry
     - Price must move beyond threshold (prevents premature exits)

2. **MACD State** (`strategies/exit/exit_macd_state.py`)
   - Exit based on MACD line state changes

3. **TP/SL Exit** (`strategies/exit/exit_tp_sl.py`)
   - Fixed take profit and stop loss levels

4. **Candle Close** (`strategies/exit/exit_candle_close.py`)
   - Exits based on candle patterns

## 📈 Technical Indicators

The bot uses various technical indicators calculated in `strategies/data_processor.py`:

- **MACD** (Moving Average Convergence Divergence) - Trend following momentum indicator
- **EMA** (Exponential Moving Average) - Smoothed price average giving more weight to recent prices
- **RSI** (Relative Strength Index) - Momentum oscillator measuring speed and magnitude of price changes
- **ATR** (Average True Range) - Volatility indicator

## ⚙️ Configuration

### Bot Configuration (`config/bots_config.json`)

Each bot is configured with the following parameters:

```json
{
  "is_enabled": true,
  "bot_id": 1,
  "run_id": 1,
  "bot_name": "bot 1",
  "run_mode": "live",
  "trade_client": "binance",
  "entry_strategy": "macdhist_ema_v1",
  "exit_strategy": "macdhist_state",
  "tp_enabled": false,
  "sl_enabled": false,
  "symbol": "BTCUSDT",
  "leverage": 10,
  "quantity": 0.001,
  "timeframe": "15m",
  "timeframe_limit": 1500,
  "order_type": "MARKET",
  "dynamic_config": {
    "macd_decimal": 2,
    "candle_for_indicator": 500,
    "close_price_diff_thsd": 0.1,
    "ema_period": 200
  },
  "created_at": "2024-06-20T12:00:00"
}
```

**Configuration Parameters:**
- `is_enabled`: Enable/disable the bot
- `run_mode`: `"live"` or `"backtest"`
- `trade_client`: `"binance"` or `"offline"`
- `entry_strategy`: Strategy name for opening positions
- `exit_strategy`: Strategy name for closing positions
- `tp_enabled`/`sl_enabled`: Enable take profit/stop loss orders
- `symbol`: Trading pair (e.g., "BTCUSDT", "ETHUSDT")
- `leverage`: Leverage multiplier (1-125)
- `quantity`: Position size
- `timeframe`: Candlestick interval ("1m", "5m", "15m", "1h", etc.)
- `timeframe_limit`: Number of historical candles to fetch
- `order_type`: `"MARKET"` or `"LIMIT"`
- `dynamic_config`: Strategy-specific parameters

See `config/bots_config.json.example` for more examples.

## 🔧 Key Features

- ✅ **Multi-bot support** - Run multiple strategies simultaneously in parallel threads
- ✅ **Flexible order types** - MARKET and LIMIT orders with intelligent retry logic
- ✅ **TP/SL management** - Automatic take profit and stop loss order placement and monitoring
- ✅ **Position sync** - Syncs local state with Binance positions to handle external changes
- ✅ **Backtesting mode** - Test strategies on historical data before live trading
- ✅ **Comprehensive logging** - Custom logger with configurable log levels
- ✅ **State persistence** - Survives restarts by saving position state to JSON files
- ✅ **Thread-safe** - Each bot runs in its own thread with proper error handling
- ✅ **Google Sheets integration** - Optional logging to Google Sheets for analysis

## 💾 Data Persistence

- **Position States** (`position_states/`): Active position snapshots saved as JSON
  - Format: `runid_{run_id}_state.json`
  - Contains current position details, TP/SL orders, PnL tracking
  - Deleted when position closes

- **Position Records** (`position_records/`): Completed trade history
  - Format: `runid_{run_id}_record_{timestamp}.json`
  - Permanent record of all closed positions
  - Includes entry/exit prices, fees, PnL, reasons

- **Google Sheets** (Optional): Use `standalone_services/update_position_record_to_google_sheet.py` to sync records to Google Sheets for analysis

## 🚀 How It Works

### Main Execution Flow

1. **Startup**: `main.py` → `BotManager` loads configurations from `config/bots_config.json`
2. **Initialization**: Each `Bot` initializes:
   - Trade client (Binance or Offline)
   - Entry and exit strategies
   - Position handler
   - Sets leverage on Binance
3. **Main Loop**: Each bot continuously:
   - Fetches latest klines (candlestick data)
   - Syncs position state with Binance
   - Executes appropriate state logic:
     - **No position**: Check for entry signals
     - **TP/SL active**: Monitor for filled orders
     - **Position active**: Check for exit signals, update PnL
   - Persists position state to disk
4. **Order Execution**: 
   - MARKET orders: Place and wait for fill confirmation
   - LIMIT orders: Place at current price, cancel and re-place if price changes
5. **Position Management**: 
   - Tracks real-time PnL
   - Records max/min PnL during position lifetime
   - Manages TP/SL orders (cancels opposite when one hits)

### Order Execution Logic

**MARKET Orders:**
- Places order immediately
- Polls order status until filled
- Fetches trade details for accurate entry/exit price

**LIMIT Orders:**
- Places order at current market price
- Monitors price changes every 5 seconds
- Cancels and replaces order if price moves
- Continues until filled

## 📋 Prerequisite(s)

- Python 3.8+
- Binance Global Account with Futures enabled
- Binance API Key and Secret Key

## 🛠️ Prepare Environment

### 1. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

### 2. Create `.env` File

```bash
# Binance API Credentials
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here

# Google Sheet (Optional)
GOOGLE_SHEET_SERVICE_ACCOUNT_FILE=_private_binance-trading-logger-cred.json
GOOGLE_SHEET_SPREADSHEET_KEY=your_spreadsheet_key
GOOGLE_SHEET_WORKSHEET_INDEX=0

# Logging Level
LOG_LEVELS=DEBUG
# LOG_LEVELS=INFO
# LOG_LEVELS=WARNING
# LOG_LEVELS=ERROR
# LOG_LEVELS=CRITICAL
```

### 3. Configure Bots

Edit `config/bots_config.json` with your desired bot configurations. See `config/bots_config.json.example` for reference.

### 4. Google Sheets Setup (Optional)

If using Google Sheets integration:
1. Create a Google Cloud project
2. Enable Google Sheets API
3. Create a service account and download credentials
4. Save credentials as `_private_binance-trading-logger-cred.json`
5. Share your spreadsheet with the service account email

## 🎮 Run Bot

```bash
./start_bot_services.sh
```

Or manually:

```bash
python3 main.py
```

## 📚 API Documentation

- [Binance Futures API Documentation](https://developers.binance.com/docs/derivatives/Introduction)

## ⚠️ Important Notes

- **Risk Warning**: Cryptocurrency trading carries significant risk. Only trade with funds you can afford to lose.
- **Test First**: Always test strategies in backtest mode before live trading
- **Start Small**: Begin with small position sizes and low leverage
- **Monitor Closely**: Keep an eye on your bots, especially when first starting
- **API Limits**: Be aware of Binance API rate limits
- **Network Issues**: Ensure stable internet connection for live trading

## 🔍 Troubleshooting

- **Bot not starting**: Check `.env` file has correct API keys
- **Orders not placing**: Verify Binance Futures is enabled on your account
- **Position sync issues**: Check if you have manual positions open on Binance
- **Strategy not triggering**: Review `dynamic_config` parameters and log output

## 📝 License

This project is for educational purposes. Use at your own risk.