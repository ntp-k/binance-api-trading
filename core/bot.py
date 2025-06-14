from adapters.azure_sql import AzureSQLAdapter
from core.bot import TradingBot
from core.modes import Mode

class BotManager:
    def __init__(self):
        self.config_adapter = AzureSQLAdapter()
        self.bots = []

    def run(self):
        configs = self.config_adapter.fetch_bot_configs()
        for cfg in configs:
            bot = TradingBot(cfg)
            bot.run()
``
