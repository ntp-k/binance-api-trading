from data_adapters.get_data_adapter import get_data_adapter
from core.bot_runner import BotRunner
from commons.common import print_result_table
from commons.custom_logger import CustomLogger
from models.activate_bot import ActivateBot
from models.bot import Bot
from models.enum.run_mode import RunMode
from models.run import Run
from trade_engine.get_trade_engine import get_trade_engine

from concurrent.futures import ThreadPoolExecutor, as_completed

class BotManager:
    def __init__(self, run_mode:RunMode = RunMode.BACKTEST, is_offline: bool = False):
        self.logger = CustomLogger(name=self.__class__.__name__)
        self.run_mode = run_mode
        self.is_offline = is_offline
        
        self.trade_engine = get_trade_engine(is_offline=is_offline)
        self.trade_engine.init()
        self.data_adapter = get_data_adapter(is_offline=is_offline)
        self.logger.info(f'Trade Engine: {self.trade_engine.__class__.__name__}')
        self.logger.info(f'Data Adapter: {self.data_adapter.__class__.__name__}')

        # running vars
        # self.bots =[]
        self.runs = []
        self.bot_runners = []

    def _load_activate_bots(self):
        self.logger.debug("Starting bot(s) Activation...")
    
        activate_bots = self.data_adapter.fetch_activate_bots()
        if not activate_bots:
            self.logger.warning("No bot found.")
            return
    
        self.activate_bots = activate_bots
        self.logger.debug(f"Activating {len(self.activate_bots)} bot(s).")

    def _load_bot(self, bot_id) -> Bot:
        self.logger.debug(f"Loading bot [{bot_id}] 's data")
        bot_data = self.data_adapter.fetch_bot(bot_id)
        if not bot_data:
            self.logger.warning('No data for bot [{bot_id}]')
        return bot_data # type: ignore

    def init_bots(self):
        self.logger.debug("Initializing bot(s)...")
    
        self._load_activate_bots()

        for activate_bot in self.activate_bots:
            try:
                activate_bot: ActivateBot = ActivateBot.from_dict(activate_bot) # type: ignore
                
                bot_data = self._load_bot(bot_id=activate_bot.bot_id)
                bot: Bot = Bot.from_dict(bot_data) # type: ignore

                bot_runner: BotRunner = BotRunner(
                    activate_bot,
                    bot,
                    self.trade_engine, # type: ignore
                    self.data_adapter  # type: ignore
                )

                self.logger.debug(f"{bot_runner.bot_fullname}")
                # self.bots.append(bot)
                self.bot_runners.append(bot_runner)
            except Exception as e:
                self.logger.error_e(f"Failed to create bot runner:", e)

        self.logger.info(f"🚀  {len(self.bot_runners)}  bot(s)")


    def run_bots(self):
        # run in backtest mode
        if self.run_mode == RunMode.BACKTEST:
            for bot_runner in self.bot_runners:
                if bot_runner.activate_bot.mode != RunMode.BACKTEST:
                    continue
                self.logger.info(f'Runnig  🤖   {bot_runner.bot_fullname}')
                run_dict = bot_runner.run_bot()
        
                self.runs.append(run_dict)

            print_result_table(self.runs)

            self.logger.info(f"Total   🤖   run:  {len(self.runs)}")
            self.logger.info(f"Bye!")
            return

        # run forwardtest or live mode
        while True:
            for bot_runner in self.bot_runners:
                if bot_runner.activate_bot.mode == RunMode.BACKTEST:
                    continue
                self.logger.info(f'Runnig  🤖   {bot_runner.bot_fullname}')
                run_dict = bot_runner.run_bot()
            self.logger.info(f"Total   🤖   run:  {len(self.runs)}")

# EOF
