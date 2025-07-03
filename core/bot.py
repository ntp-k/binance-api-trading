from abstracts.base_entry_strategy import BaseEntryStrategy
from abstracts.base_exit_strategy import BaseExitStrategy
from abstracts.base_trade_client import BaseTradeClient
from commons.custom_logger import CustomLogger
from core.position_handler import PositionHandler
from models import position
from models.bot_config import BotConfig
from models.enum import order_side
from models.enum.order_side import OrderSide
from models.enum.order_type import OrderType
from models.enum.position_side import PositionSide
from models.enum.run_mode import RunMode
from models.enum.trade_client import TradeClient
from models.position import Position
from models.position_signal import PositionSignal
from time import sleep
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
        self._set_leverage()

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

    def _set_leverage(self):
        self.trade_client.set_leverage(symbol=self.bot_config.symbol, leverage=self.bot_config.leverage)
        self.logger.debug(f'Leverage is setted to {self.bot_config.leverage}')

    def _sync_position_state(self, active_position_dict, candle_open_time):
        # if the client has NO position but our bot has one in memory, maybe reload it
        if not active_position_dict and self.position_handler.is_open():
            self.logger.warning(message="Bot has position in memory but trade client has none; resetting state.")
            self.position_handler.clear_position()
        elif active_position_dict and not self.position_handler.is_open():
            active_position_dict['run_id'] = self.bot_config.run_id
            active_position_dict['open_candle'] = candle_open_time
            self.position_handler.open_position(position_dict=active_position_dict)
        elif active_position_dict:
            if (active_position_dict['position_side'] != self.position_handler.position.position_side) or \
            (active_position_dict['entry_price'] != self.position_handler.position.entry_price):
                self.logger.warning(message="Trade client position and Bot in memory position is not sync; resetting state")

    def _place_order_to_open_position(self, position_side: PositionSide):
        _order_side = OrderSide.BUY.value if position_side == PositionSide.LONG else OrderSide.SELL.value
        _order = self.trade_client.place_order(
            symbol=self.bot_config.symbol,
            order_side=_order_side,
            order_type=OrderType.MARKET.value,
            quantity=self.bot_config.quantity,
            reduce_only=False,
        )
        self.logger.debug(message=f'placed order: {_order}')

        sleep(2) # wait for binance to process order

        new_position_dict: dict = self.trade_client.fetch_position(symbol=self.bot_config.symbol)
        if not new_position_dict:
            self.logger.critical(message=f'💥 Failed to place order to binance!')
            raise Exception('💥 Failed to place order to binance!')
        
        self.logger.info(message=f"{self.bot_config.symbol} | {'OPEN':<5} | {position_side.value:<5} | {new_position_dict["entry_price"]}")
        return new_position_dict

    def _place_order_to_close_position(self, position_dict: dict):
        _order_side = OrderSide.BUY.value if position_dict['position_side'] == PositionSide.SHORT else OrderSide.SELL.value
        _order = self.trade_client.place_order(
            symbol=self.bot_config.symbol,
            order_side=_order_side,
            order_type=OrderType.MARKET.value,
            quantity=self.bot_config.quantity,
            reduce_only=True,
        )
        self.logger.debug(message=f'placed order: {_order}')

        close_price = position_dict['mark_price']
        pnl = position_dict['pnl']
        self.logger.info(message=f"{self.bot_config.symbol} | {'CLOSE':<5} | {position_dict['position_side'].value:<5} | {position_dict['entry_price']:.2f} -> {close_price:.2f} | {'+' if pnl >= 0 else ''}{pnl:.2f}")


    def execute(self):
        klines_df = self.trade_client.fetch_klines(
            symbol=self.bot_config.symbol,
            timeframe=self.bot_config.timeframe,
            timeframe_limit=self.bot_config.timeframe_limit
        )
        active_position_dict: dict = self.trade_client.fetch_position(symbol=self.bot_config.symbol)
        self._sync_position_state(active_position_dict=active_position_dict, candle_open_time=str(klines_df.iloc[-1]["open_time"]))

        # CASE 1: no active trade position
        if not active_position_dict:
            entry_signal: PositionSignal = self.entry_strategy.should_open(klines_df=klines_df, position_handler=self.position_handler)
            self.logger.debug(entry_signal.position_side)
            self.logger.info(entry_signal.reason)

            if entry_signal.position_side != PositionSide.ZERO:
                self.logger.debug(message=f'{self.bot_config.symbol} Entry signal triggered')

                _new_positino_dict = self._place_order_to_open_position(position_side=entry_signal.position_side)
                
                _new_positino_dict['run_id'] = self.bot_config.run_id
                _new_positino_dict['open_candle'] = str(object=klines_df.iloc[-1]["open_time"])
                _new_positino_dict['open_reason'] = entry_signal.reason
                self.position_handler.open_position(position_dict=_new_positino_dict)

        # CASE 2: active trade position
        else:
            exit_signal: PositionSignal = self.exit_strategy.should_close(klines_df=klines_df, position_handler=self.position_handler)
            self.logger.debug(exit_signal.position_side)
            self.logger.info(exit_signal.reason)

            if exit_signal.position_side == PositionSide.ZERO:
                self.logger.debug(message=f'{self.bot_config.symbol} Exit signal triggered')
                self.logger.debug(message=f'Active position: {active_position_dict}')

                self._place_order_to_close_position(position_dict=active_position_dict)

                active_position_dict['close_reason'] = exit_signal.reason
                self.position_handler.close_position(position_dict=active_position_dict)
        
        if self.position_handler.position is not None:
            self.position_handler.dump_position_state()

    def run(self):
        while self.trade_client.running:
            self.execute()
            self.trade_client.wait()

# EOF
