from threading import Thread
from typing import List

from commons.custom_logger import CustomLogger
from models.bot_config import BotConfig
import core.bot_config_loader as bot_config_loader
from core.bot import Bot

BOT_CONFIG_PATH = 'config/bots_config.json'

class BotManager:
    bots: List[Bot]
    threads: List[Thread]

    def __init__(self):
        self.logger = CustomLogger(name=self.__class__.__name__)
        self.bots: List[Bot] = []
        self.threads: List[Thread] = []


    def _load_bots_config(self):
        return bot_config_loader.load_config(file_path=BOT_CONFIG_PATH)


    def _init_bots(self):
        self.logger.debug(message="Initializing bot(s)...")
    
        self.bots_config: list[BotConfig] = self._load_bots_config()

        for bot_config in self.bots_config:
            try:
                self.logger.debug(message=bot_config)
                self.logger.info(message=f'Loading 🤖  [{bot_config.bot_name}] ...')
                bot: Bot = Bot(bot_config=bot_config)
                self.bots.append(bot)

            except Exception as e:
                self.logger.error_e(message=f"Failed to create bot runner:", e=e)

        self.logger.info(message=f"Loaded  {len(self.bots_config)}  🤖")

    def execute(self):
        for bot in self.bots:
            self.logger.debug(message=f"Starting thread for 🤖  [{bot.bot_config.bot_name}] ...")
            thread = Thread(target=bot.run, name=bot.bot_config.bot_name)
            thread.start()
            self.threads.append(thread)
            self.logger.debug(message=f"Started thread for 🤖  [{bot.bot_config.bot_name}]")

        # Optionally, wait for all threads to finish
        for thread in self.threads:
            thread.join()

        self.logger.info(message="All bots completed.")

    def run(self):
        self._init_bots()
        self.execute()
        self.logger.info(f"Total   🤖   run:  {len(self.bots)}")

# EOF
