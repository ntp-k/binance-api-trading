from abstracts.base_entry_strategy import BaseEntryStrategy
from abstracts.base_exit_strategy import BaseExitStrategy
from abstracts.base_trade_client import BaseTradeClient
from commons.custom_logger import CustomLogger
from core.position_handler import PositionHandler
from models.bot_config import BotConfig
from models.enum.position_side import PositionSide
from models.enum.run_mode import RunMode
from models.enum.trade_client import TradeClient
from models.position_signal import PositionSignal
from trade_clients.get_trade_client import get_trade_client
import strategies.get_strategy as get_strategy

class Bot:
    bot_config: BotConfig
    entry_strategy: BaseEntryStrategy
    exit_strategy: BaseExitStrategy
    position_handler: PositionHandler
    trade_client: BaseTradeClient

    def __init__(self, bot_config: BotConfig):
        self.logger = CustomLogger(name=f"{self.__class__.__name__}:{bot_config.bot_name.replace(' ', '_')}")
        self.logger.debug(message=f'Initializing {self.__class__.__name__}')

        self.bot_config: BotConfig = bot_config
        self.position_handler: PositionHandler = PositionHandler(bot_config=bot_config)

        self.trade_client = self._init_trade_client(run_mode=bot_config.run_mode, trade_client=bot_config.trade_client)
        self.entry_strategy = self._init_entry_strategy(entry_strategy=self.bot_config.entry_strategy, dynamic_config=self.bot_config.dynamic_config)
        self.exit_strategy = self._init_exit_strategy(exit_strategy=self.bot_config.exit_strategy, dynamic_config=self.bot_config.dynamic_config)

    def _init_trade_client(self, run_mode: RunMode, trade_client: TradeClient):
        try:
            self.logger.debug(message=f'Initializing trade client')
            _trade_client: BaseTradeClient = get_trade_client(run_mode=run_mode, trade_client=trade_client) # type: ignore
            _trade_client.set_running(running=True)
            self.logger.debug(message=f'Initialized trade client {_trade_client.__class__.__name__}')
            return _trade_client
        except Exception as e:
            self.logger.error_e(message='Error while initializing trade client', e=e)

    def _init_entry_strategy(self, entry_strategy, dynamic_config):
        try:
            self.logger.debug(message=f'Initializing entry strategy')
            _entry_strategy = get_strategy.get_entry_strategy(entry_strategy=entry_strategy, dynamic_config=dynamic_config)
            self.logger.debug(message=f'Entry Strategy {_entry_strategy.__class__.__name__}')
            return _entry_strategy
        except Exception as e:
            self.logger.error_e(message='Error while initializing entry strategy', e=e)

    def _init_exit_strategy(self, exit_strategy, dynamic_config):
        try:
            self.logger.debug(message=f'Initializing exit strategy')
            _exit_strategy = get_strategy.get_exit_strategy(exit_strategy=exit_strategy, dynamic_config=dynamic_config)
            self.logger.debug(message=f'Exit Strategy {_exit_strategy.__class__.__name__}')
            return _exit_strategy
        except Exception as e:
            self.logger.error_e(message='Error while initializing exit strategy', e=e)


    def execute(self):
        klines_df = self.trade_client.fetch_klines(
            symbol=self.bot_config.symbol,
            timeframe=self.bot_config.timeframe,
            timeframe_limit=self.bot_config.timeframe_limit
        )
        active_position_dict: dict = self.trade_client.fetch_position(symbol=self.bot_config.symbol)

        if len(active_position_dict) != 0 and self.position_handler.position is None:
            self.position_handler.update_pnl(position_dict=active_position_dict)
            self.logger.debug(f'Active position: {active_position_dict}')
            exit_signal: PositionSignal = self.exit_strategy.should_close(klines_df=klines_df, position=self.position_handler.position)

            if exit_signal.position_side == PositionSide.ZERO:
                pass
                # close position
                # update pnl
                # log position record

        elif len(active_position_dict) == 1 and self.position_handler.position is not None:
            entry_signal: PositionSignal = self.entry_strategy.should_open(klines_df=klines_df)

            if entry_signal.position_side != PositionSide.ZERO:
                pass
                # open position
                # update position
        

    def run(self):
        while self.trade_client.running:
            self.execute()
            self.trade_client.wait()

# EOF
