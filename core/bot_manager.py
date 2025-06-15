from dotenv import load_dotenv
import os


load_dotenv()



from data_adapters.azure_sql_adapter import AzureSQLAdapter
from core.bot_config import BotConfig
from core.bot_runner import BotRunner
from commons.custom_logger import CustomLogger


class BotManager:
    def __init__(self):
        self.logger = CustomLogger(name=self.__class__.__name__)
        self.adapter = AzureSQLAdapter()
        self.bots = []

    def load_bot_configs(self):
        self.logger.debug("Loading active bot configurations...")
        configs = self.adapter.fetch_bot_configs()
        if not configs:
            self.logger.warning("No active bot configurations found.")
            return
        self.raw_bot_configs = configs
        self.logger.debug(f"Found {len(self.raw_bot_configs)} bot(s).")


    def init_bots(self):
        self.logger.debug("Initializing bots...")
        for config_data in self.raw_bot_configs:
            try:
                bot_config = BotConfig.from_dict(config_data)
                bot_runner = BotRunner(bot_config)
                self.logger.info(f"🤖  {bot_config.run_mode}  {bot_config.strategy}  {bot_config.symbol}  {bot_config.timeframe}")
                self.bots.append(bot_runner)
            except Exception as e:
                self.logger.error(f"Failed to create bot runner: {e}")

        self.logger.info(f"🚀  {len(self.bots)}  bot(s)")


    def run_bots(self):
        self.logger.info(f'Initializing {len(self.raw_bot_configs)} bot(s)')

        for config_data in self.raw_bot_configs:
            try:
                bot_config = BotConfig.from_dict(config_data)
                self.logger.info(f"Loaded bot config: Strategy={bot_config.strategy}, Symbol: {bot_config.symbol}, TF: {bot_config.timeframe}")

                bot_runner = BotRunner(bot_config)
                self.bots.append(bot_runner)

                bot_runner.run()  # For threaded or async, consider bot_runner.start()
            except Exception as e:
                self.logger.error(f"Failed to create bot runner: {e}")

        self.logger.info(f"🚀 Total bots started: {len(self.bots)}")

