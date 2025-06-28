from commons.custom_logger import CustomLogger
from models.bot_config import BotConfig
import core.bot_config_loader as bot_config_loader
from core.bot import Bot

BOT_CONFIG_PATH = 'config/bots_config.json'

class BotManager:
    def __init__(self):
        self.logger = CustomLogger(name=self.__class__.__name__)
        self.bot_config_loader = bot_config_loader


    def _load_bots_config(self):
        return self.bot_config_loader.load_config(file_path=BOT_CONFIG_PATH)


    def init_bots(self):
        self.logger.debug(message="Initializing bot(s)...")
    
        self.bots_config: list[BotConfig] = self._load_bots_config()

        for bot_config in self.bots_config:
            try:
                self.logger.debug(message=bot_config)
                self.logger.info(message=f'Loading {bot_config.bot_name}')
                bot: Bot = Bot(bot_config=bot_config)

            except Exception as e:
                self.logger.error_e(message=f"Failed to create bot runner:", e=e)

        self.logger.info(message=f"Loaded  {len(self.bots_config)}  🤖")



# self.logger.info(f'Runnig  🤖   {bot_runner.bot_fullname}')
# self.logger.info(f"Total   🤖   run:  {len(self.runs)}")
# self.logger.info(f'Runnig  🤖   {bot_runner.bot_fullname}')
# self.logger.info(f"Total   🤖   run:  {len(self.runs)}")

# EOF
