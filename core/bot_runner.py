from datetime import datetime

from commons.custom_logger import CustomLogger
from core.engines.get_bot_engine import get_bot_engine
from core.handler.position_handler import PositionHandler
from data_adapters.base_adapter import BaseAdapter
from models.activate_bot import ActivateBot
from models.bot import Bot
from models.run import Run
from strategies.get_strategy_engine import get_strategy_engine
from trade_engine.base_trade_engine import BaseTradeEngine


class BotRunner:
    def __init__(
            self,
            activate_bot: ActivateBot,
            bot: Bot,
            trade_engine: BaseTradeEngine,
            data_adapter: BaseAdapter
    ):
        self.bot_fullname = f'{activate_bot.mode.value}|{bot.strategy.value}|{bot.symbol}|{bot.timeframe}'
        self.bot_enging_fullname = f'{self.__class__.__name__}_{self.bot_fullname}'
        self.logger = CustomLogger(name=self.bot_enging_fullname)

        self.logger.debug('Initializing bot runner')

        self.activate_bot: ActivateBot = activate_bot
        self.bot: Bot = bot
        self.trade_engine: BaseTradeEngine = trade_engine
        self.data_adapter: BaseAdapter = data_adapter

        self.run = self._init_run()

        self.strategy_engine = self._init_strategy(self.bot.strategy, self.bot_fullname)
        self.logger.debug(f'Loaded strategy engine: {self.strategy_engine.__class__.__name__}')

        self.bot_engine = self._init_bot_engine(self)
        self.logger.debug(f'Loaded bot engine: {self.bot_engine.__class__.__name__}')

        self.position_handler = PositionHandler(self)
        self.logger.debug('Loaded position handler')       

    def _init_strategy(self, strategy, bot_fullname):
        try:
            self.logger.debug(f'Initializing strategy engine for strategy {strategy.value}')
            return get_strategy_engine(strategy=strategy, bot_fullname=bot_fullname)
        except Exception as e:
            self.logger.error_e(f'Unexpected error initializing strategy engine for strategy {strategy.value}:', e)
            raise e
    
    def _init_bot_engine(self, bot_runner):
        try:
            self.logger.debug(f'Initializing bot engine for run mode: {self.run.mode.value}')
            return get_bot_engine(bot_runner)
        except Exception as e:
            self.logger.error_e(f'Unexpected error initializing bot engine for run mode {self.run.mode.value}:', e)
            raise e

    def _create_run(self, bot_id: int, mode: str, init_balance: float, s_time) -> int:
        return self.data_adapter.create_run(
            bot_id,
            mode,
            init_balance,
            s_time
        )

    def _update_run(self, run_dict):
        self.run.end_time = run_dict.get('end_time')
        self.run.total_trades = run_dict.get('total_trades')
        self.run.total_positions = run_dict.get('total_positions')
        self.run.winning_positions = run_dict.get('winning_positions')
        self.run.final_balance = run_dict.get('final_balance')
        self.data_adapter.update_run(run = self.run)

    def _init_run(self):
        run_id: int = self._create_run(
            bot_id=self.bot.bot_id,
            mode=self.activate_bot.mode,
            init_balance=self.activate_bot.initial_balance,
            s_time=datetime.now()
        )
        run: Run = Run.from_dict({
            'run_id': run_id,
            'bot_id': self.bot.bot_id,
            'mode': self.activate_bot.mode,
            'start_time': datetime.now(),
            'initial_balance': self.activate_bot.initial_balance
        })
        return run

    def run_bot(self):
        try:
            self.logger.info(f'Starting bot runner for {self.bot_fullname}')
            _run_dict = self.bot_engine.run() # type: ignore
            self._update_run(_run_dict)
            self.logger.info(f'Bot runner for {self.bot_fullname} completed successfully')
            self.logger.debug(_run_dict)
            return _run_dict

        except Exception as e:
            self.logger.error_e(f'Error running bot {self.bot_fullname}:', e)
            raise e


if __name__ == "__main__":
    pass

# EOF
