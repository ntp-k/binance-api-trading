from dotenv import load_dotenv

load_dotenv()

from data_adapters.azure_sql_adapter import AzureSQLAdapter
from models.bot import Bot

from core.bot_runner import BotRunner
from commons.custom_logger import CustomLogger
from commons.common import print_result_table
from trade_engine.binance.binance_client import BinanceClient
from models.enum.run_mode import RunMode
from models.run import Run

class BotManager:
    def __init__(self, run_mode:RunMode = RunMode.BACKTEST):
        self.logger = CustomLogger(name=self.__class__.__name__)
        self.run_mode = run_mode
        self.data_adapter = AzureSQLAdapter()
        self.binance_client = BinanceClient()

        self.bots = []
        self.runs = []

    def load_active_bots(self):
        self.logger.debug("Loading bot configurations...")
        configs = self.data_adapter.fetch_active_bots()
        if not configs:
            self.logger.warning("No active bot configurations found.")
            return
        self.raw_bot_configs = configs
        self.logger.debug(f"Found {len(self.raw_bot_configs)} bot(s).")


    def init_bots(self):
        self.logger.debug("Initializing bots...")
        for config_data in self.raw_bot_configs:
            try:
                active_bots = self.load_active_bots()
                

                # bot: Bot = BotConfig.from_dict(config_data)
                # bot_runner: BotRunner = BotRunner(self.run_mode, bot_config, self.data_adapter, self.binance_client)
                # self.logger.debug(f"{bot_runner.bot_fullname}")
                # self.bots.append(bot_runner)
                pass
            except Exception as e:
                self.logger.error_e(f"Failed to create bot runner:", e)

        self.logger.info(f"🚀  {len(self.bots)}  bot(s)")


    def run_bots(self):
        for bot in self.bots:
            self.logger.info(f'Runnig  🤖   {bot.bot_fullname}')
            bot_run = bot.run()
            self.bots_run.append(bot_run.to_dict())

        print_result_table(self.bots_run)

        self.logger.info(f"Total  🤖  run:  {len(self.bots_run)}")
        self.logger.info(f"Bye!")

# EOF
