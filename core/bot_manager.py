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
                self.logger.debug(f"{bot_runner.bot_fullname}")
                self.bots.append(bot_runner)
            except Exception as e:
                self.logger.error(f"Failed to create bot runner: {e}")

        self.logger.info(f"🚀  {len(self.bots)}  bot(s)")


    def run_bots(self):
        for bot in self.bots:
            self.logger.info(f'Runnig  🤖   {bot.bot_fullname}')
            bot.run()


