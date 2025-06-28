from commons.custom_logger import CustomLogger
from models.bot_config import BotConfig
import core.bot_config_loader as bot_config_loader

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
                self.logger.debug(bot_config)

                # self.bots.append(bot)
                # self.bot_runners.append(bot_runner)
            except Exception as e:
                self.logger.error_e(f"Failed to create bot runner:", e)

        self.logger.info(f"Loaded  {len(self.bots_config)}  🤖")


    # def run_bots(self):
    #     # run in backtest mode
    #     if self.run_mode == RunMode.BACKTEST:
    #         for bot_runner in self.bot_runners:
    #             if bot_runner.activate_bot.mode != RunMode.BACKTEST:
    #                 continue
    #             self.logger.info(f'Runnig  🤖   {bot_runner.bot_fullname}')
    #             run_dict = bot_runner.run_bot()
        
    #             self.runs.append(run_dict)

    #         print_result_table(self.runs)

    #         self.logger.info(f"Total   🤖   run:  {len(self.runs)}")
    #         self.logger.info(f"Bye!")
    #         return

    #     # run forwardtest or live mode
    #     while True:
    #         for bot_runner in self.bot_runners:
    #             if bot_runner.activate_bot.mode == RunMode.BACKTEST:
    #                 continue
    #             self.logger.info(f'Runnig  🤖   {bot_runner.bot_fullname}')
    #             run_dict = bot_runner.run_bot()
    #         self.logger.info(f"Total   🤖   run:  {len(self.runs)}")

# EOF
