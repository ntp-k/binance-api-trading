import os
from commons.custom_logger import CustomLogger
from strategies import get_strategy
from modes import run_backtest, run_simulation, run_live

class BotRunner:
    def __init__(self, bot_config: dict):
        self.config = bot_config
        self.logger = CustomLogger(name=BotRunner.__name__)

        self.strategy_name = self.config.get("strategy")
        self.trade_mode = self.config.get("mode")
        self.symbol = self.config.get("symbol")

        if not self.strategy_name or not self.trade_mode:
            raise ValueError("Both 'strategy' and 'mode' are required in bot config.")

        self.strategy = get_strategy(self.strategy_name, self.config)

    def run(self):
        self.logger.info(f"🧠 Starting bot: strategy={self.strategy_name}, mode={self.trade_mode}, symbol={self.symbol}")

        if self.trade_mode == "backtest":
            run_backtest(self.strategy, self.config)
        elif self.trade_mode == "simulation":
            run_simulation(self.strategy, self.config)
        elif self.trade_mode == "live":
            run_live(self.strategy, self.config)
        else:
            raise ValueError(f"❌ Unknown trade mode: {self.trade_mode}")

        self.logger.info("✅ Bot execution complete.")


if __name__ == "__main__":
    # 👇 Replace with actual config loading (e.g., from Azure SQL)
    sample_config = {
        "bot_name": "btc_macd_bot_1",
        "strategy": "macd",
        "mode": "simulation",  # Options: backtest, simulation, live
        "symbol": "BTCUSDT",
        "interval": "1h",
        "quantity": 0.01,
        "settings": {
            "fast": 12,
            "slow": 26,
            "signal": 9
        }
    }

    bot = BotRunner(sample_config)
    bot.run()