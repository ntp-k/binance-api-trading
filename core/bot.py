from abstracts.base_entry_strategy import BaseEntryStrategy
from abstracts.base_exit_strategy import BaseExitStrategy
from abstracts.base_trade_client import BaseTradeClient
from commons.custom_logger import CustomLogger
from core.position_handler import PositionHandler
from models.bot_config import BotConfig
from models.enum.order_side import OrderSide
from models.enum.order_type import OrderType
from models.enum.position_side import PositionSide
from models.enum.run_mode import RunMode
from models.enum.trade_client import TradeClient
from models.position_signal import PositionSignal
from time import sleep
from trade_clients.get_trade_client import get_trade_client
import strategies.get_strategy as get_strategy
from models.enum.exit_strategy import ExitStrategy


class Bot:
    bot_config: BotConfig
    entry_strategy: BaseEntryStrategy
    exit_strategy: BaseExitStrategy
    position_handler: PositionHandler
    trade_client: BaseTradeClient

    def __init__(self, bot_config: BotConfig):
        self.logger = CustomLogger(
            name=f"{self.__class__.__name__}:{bot_config.bot_name.replace(' ', '_')}")
        self.logger.debug(message=f'Initializing {self.__class__.__name__}')

        self.bot_config: BotConfig = bot_config
        self.position_handler: PositionHandler = PositionHandler(
            bot_config=bot_config)

        self.trade_client = self._init_trade_client(
            run_mode=bot_config.run_mode, trade_client=bot_config.trade_client)
        self._set_leverage()
        
        self.logger.debug(message=f'Initializing strategies')
        self.entry_strategy, self.exit_strategy = get_strategy.init_strategies(
            entry_strategy=self.bot_config.entry_strategy,
            exit_strategy=self.bot_config.exit_strategy,
            dynamic_config=self.bot_config.dynamic_config
        )
        self.logger.debug(
                message=f'Entry Strategy { self.entry_strategy.__class__.__name__}')
        self.logger.debug(
                message=f'Exit Strategy { self.exit_strategy.__class__.__name__}')

    def _init_trade_client(self, run_mode: RunMode, trade_client: TradeClient):
        try:
            self.logger.debug(message=f'Initializing trade client')
            _trade_client: BaseTradeClient = get_trade_client(
                run_mode=run_mode, trade_client=trade_client)  # type: ignore
            _trade_client.set_running(running=True)
            self.logger.debug(
                message=f'Initialized trade client {_trade_client.__class__.__name__}')
            return _trade_client
        except Exception as e:
            self.logger.error_e(
                message='Error while initializing trade client', e=e)

    def _set_leverage(self):
        self.trade_client.set_leverage(
            symbol=self.bot_config.symbol, leverage=self.bot_config.leverage)
        self.logger.debug(f'Leverage is setted to {self.bot_config.leverage}')

    def _sync_position_state(self, remote_position_dict, candle_open_time):
        # if the client has NO position but our bot has one in memory, maybe reload it

        # CASE 1: no position on remote but has position in mem -> out of sync or TP/SL hit
        #   1.1: not TP/SL mode, should have same position on remote and local -> sync local with remote
        #   1.2: TP/SL mode, maybe TP/SL were hitted -> proceed to CASE 2 of main process -> monitor TP/SL
        if not remote_position_dict and self.position_handler.is_open():
            if not (self.bot_config.tp_enabled or self.bot_config.sl_enabled):
                self.logger.warning(
                    message="Bot has position in memory but trade client has none; resetting state.")
                self.position_handler.clear_position()
            else:
                self.logger.debug('Suspect TP/SL were hitted')

        # CASE 2: have position on remote but no position in local -> sync local with remote
        elif remote_position_dict and not self.position_handler.is_open():
            remote_position_dict['run_id'] = self.bot_config.run_id
            remote_position_dict['open_candle'] = candle_open_time
            self.position_handler.open_position(
                position_dict=remote_position_dict)
        # CASE 3: have position on remote and local -> verify position integrity
        elif remote_position_dict:
            if (remote_position_dict['position_side'] != self.position_handler.position.position_side) or \
                    (remote_position_dict['entry_price'] != self.position_handler.position.entry_price):
                self.logger.warning(
                    message="Trade client position and Bot in memory position is not sync; resetting state")
        
        return remote_position_dict

    def _place_tp_order(self, position_side, tp_price):
        self.logger.info(message='Placing new take profit order')
        order_side = OrderSide.SELL.value if position_side == PositionSide.LONG else OrderSide.BUY.value

        tp_order = self.trade_client.place_order(
            symbol=self.bot_config.symbol,
            order_side=order_side,
            order_type=OrderType.LIMIT.value,
            price=tp_price,
            quantity=self.bot_config.quantity,
            reduce_only=True
        )
        _order_id = tp_order.get('orderId')
        self.logger.info(message=f"TP order placed at {tp_price}, order id: {_order_id}")
        self.position_handler.set_tp_order_id(id=_order_id)
        self.position_handler.set_tp_price(price=tp_price)
        return tp_order

    def _place_sl_order(self, position_side, sl_price):
        self.logger.info(message='Placing new stop loss order')
        order_side = OrderSide.SELL.value if position_side == PositionSide.LONG else OrderSide.BUY.value

        sl_order = self.trade_client.place_order(
            symbol=self.bot_config.symbol,
            order_side=order_side,
            order_type=OrderType.STOP_MARKET.value,
            stop_price=sl_price,
            quantity=self.bot_config.quantity,
            close_position=True
        )
        _order_id = sl_order.get('orderId')
        self.logger.info(message=f"SL order placed at {sl_price}, order id: {_order_id}")
        self.position_handler.set_sl_order_id(id=_order_id)
        self.position_handler.set_sl_price(price=sl_price)
        return sl_order

    def _place_market_order(self, order_side, reduce_only):
        self.logger.info(message='Placing new market order')
        _order = self.trade_client.place_order(
            symbol=self.bot_config.symbol,
            order_side=order_side,
            order_type=OrderType.MARKET.value,
            quantity=self.bot_config.quantity,
            reduce_only=reduce_only,
        )
        sleep(2) # wait for binance to process order

        _order_id = _order.get('orderId')
        _order_filled = False
        while not _order_filled:
            _order_status = self.trade_client.fetch_order(symbol=self.bot_config.symbol, order_id=_order_id)
            _order_filled = _order_status.get('status') == 'FILLED'

            if not _order_filled:
                self.logger.info(message="Order still pending. Waiting...")
            else:
                self.logger.info(message="Order filled")
                break
            sleep(1)  # wait before checking again

        self.logger.debug(message=f'Getting trade history order_id: {_order_id}')
        return self.trade_client.fetch_order_trade(symbol=self.bot_config.symbol, order_id=_order_id) 

    def _place_limit_order(self, order_side, reduce_only):
        _order_filled = False
        _order_id = ''
        _last_price = None
        while not _order_filled:
            price_now = self.trade_client.fetch_price(symbol=self.bot_config.symbol)

            if _last_price != price_now:
                self.logger.info(message=f"Placing new LIMIT order at price: {price_now}")

                _order = self.trade_client.place_order(
                    symbol=self.bot_config.symbol,
                    order_side=order_side,
                    order_type=OrderType.LIMIT.value,
                    quantity=self.bot_config.quantity,
                    price=price_now,
                    reduce_only=reduce_only,
                )
                self.logger.debug(message=f"New order: {_order}")
                _order_id = _order.get('orderId')
            else:
                self.logger.debug(message="Price unchanged. Skipping re-order.")

            sleep(5)  # wait for order to filled

            _check_order = self.trade_client.fetch_order(symbol=self.bot_config.symbol, order_id=_order_id)
            self.logger.debug(message=f"Order status: {_check_order}")
            _order_filled = _check_order.get('status') == 'FILLED'
            self.logger.debug(message=f"Order filled: {_order_filled}")

            if not _order_filled and _last_price != price_now:
                self.trade_client.cancel_order(symbol=self.bot_config.symbol, order_id=_order_id)
                self.logger.info(message="Order canceled due to price change")
                sleep(1) # wait for binance to cancle order
            elif not _order_filled:
                self.logger.info(message="Order still pending. Waiting...")
            else: # order filled
                self.logger.info(message="Order filled")
                break
            
            _last_price = price_now
    
        self.logger.debug(message=f'Getting trade history order_id: {_order_id}')
        return self.trade_client.fetch_order_trade(symbol=self.bot_config.symbol, order_id=_order_id)
                
    def _place_order_to_open_position(self, position_side: PositionSide):
        _order_side = OrderSide.BUY.value if position_side == PositionSide.LONG else OrderSide.SELL.value
        _order_trade = None

        self.logger.debug(message='Placing order to open position')

        if self.bot_config.order_type == OrderType.MARKET:
            _order_trade = self._place_market_order(order_side=_order_side, reduce_only=False)
        else:  # LIMIT
            _order_trade = self._place_limit_order(order_side=_order_side, reduce_only=False)

        self.logger.debug(message=f'Order Trade: {_order_trade}')

        new_position_dict: dict = self.trade_client.fetch_position(
            symbol=self.bot_config.symbol)
        if not new_position_dict:
            self.logger.critical(
                message=f'💥 Failed to place order to binance!')
            raise Exception('💥 Failed to place order to binance!')
        
        new_position_dict['open_fee'] = _order_trade['fee']
        self.logger.info(
            message=f"{self.bot_config.symbol} | {'OPEN':<5} | {position_side.value:<5} | {new_position_dict["entry_price"]}")
        return new_position_dict

    def _place_order_to_close_position(self, position_dict: dict):
        _order_side = OrderSide.BUY.value if position_dict['position_side'] == PositionSide.SHORT else OrderSide.SELL.value
        _order_trade = None

        self.logger.debug(message='Placing order to close position')
    
        if self.bot_config.order_type == OrderType.MARKET:
            _order_trade = self._place_market_order(order_side=_order_side, reduce_only=True)
        else:
            _order_trade = self._place_limit_order(order_side=_order_side, reduce_only=True)

        self.logger.debug(message=f'Order Trade: {_order_trade}')

        closed_position_dict = {
            'close_price': _order_trade['price'],
            'close_fee': _order_trade['fee'],
            'pnl': _order_trade['pnl']
        }

        self.logger.info(
            message=f"{self.bot_config.symbol} | {'CLOSE':<5} | {position_dict['position_side'].value:<5} | {position_dict['entry_price']:.2f} -> {_order_trade['price']:.2f} | {'+' if _order_trade['pnl'] >= 0 else ''}{_order_trade['pnl']:.2f}")
        return closed_position_dict

    def _place_position_tp_sl(self, klines_df):
        position = self.position_handler.position
        position_side = position.position_side
        entry_price = position.entry_price

        tp_price, sl_price = self.entry_strategy.calculate_tp_sl(
            klines_df=klines_df,
            position_side=position_side,
            entry_price=entry_price
        )
        if self.bot_config.tp_enabled:
            self.logger.info(message=f'Setting TP at {tp_price}')
            _tp_order = self._place_tp_order(position_side=position_side, tp_price=tp_price)
        if self.bot_config.sl_enabled:
            self.logger.info(message=f'Setting SL at {sl_price}')
            _sl_order = self._place_sl_order(position_side=position_side, sl_price=sl_price)

    def _cancel_tp_order(self):
        order_id = self.position_handler.get_tp_order_id()
        if order_id:
            self.trade_client.cancel_order(symbol=self.bot_config.symbol, order_id=order_id)

    def _cancel_sl_order(self):
        order_id = self.position_handler.get_sl_order_id()
        if order_id:
            self.trade_client.cancel_order(symbol=self.bot_config.symbol, order_id=order_id)

    def _monitor_tp_sl_fill(self, close_candle_open_time=''):
        """
        Monitor TP/SL orders and close position if any is filled.
        Scenarios:
        1. Both TP and SL enabled: only one can hit; cancel the other.
        2. Only one order enabled: works normally.
        """
        filled_order_id = ''
        close_reason = ''

        # Check SL first
        if self.bot_config.sl_enabled:
            sl_order_id = self.position_handler.get_sl_order_id()
            if sl_order_id:
                sl_status = self.trade_client.fetch_order(
                    symbol=self.bot_config.symbol, order_id=sl_order_id).get('status')
                if sl_status == 'FILLED':
                    self.logger.info("SL hit ✅")
                    filled_order_id = sl_order_id
                    close_reason = 'SL Hit'
                    if self.bot_config.tp_enabled:
                        self._cancel_tp_order()
                        self.logger.info("Cancelling TP due to SL hit")
            else:
                self.logger.debug("No SL order in memory")

        # Check TP only if no order has already been filled
        if self.bot_config.tp_enabled and not filled_order_id:
            tp_order_id = self.position_handler.get_tp_order_id()
            if tp_order_id:
                tp_status = self.trade_client.fetch_order(
                    symbol=self.bot_config.symbol, order_id=tp_order_id).get('status')
                if tp_status == 'FILLED':
                    self.logger.info("TP hit ✅")
                    filled_order_id = tp_order_id
                    close_reason = 'TP Hit'
                    if self.bot_config.sl_enabled:
                        self._cancel_sl_order()
                        self.logger.info("Cancelling SL due to TP hit")
            else:
                self.logger.debug("No TP order in memory")

        # Process filled order
        if filled_order_id:
            try:
                self.logger.debug(f'Getting trade history for filled order_id: {filled_order_id}')
                order_trade = self.trade_client.fetch_order_trade(
                    symbol=self.bot_config.symbol, order_id=filled_order_id)

                closed_position_dict = {
                    'close_fee': order_trade['fee'],
                    'close_reason': close_reason,
                    'close_price': order_trade['price'],
                    'pnl': order_trade['pnl'],
                    'close_candle_open_time': close_candle_open_time
                }

                self.position_handler.close_position(position_dict=closed_position_dict)
                self.position_handler.clear_tp_sl_orders()

                self.logger.info(
                message=f"{self.bot_config.symbol} | {'CLOSE':<5} | {order_trade['side']:<5} | {self.position_handler.entry_price:.2f} -> {order_trade['price']:.2f} | {'+' if order_trade['pnl'] >= 0 else ''}{order_trade['pnl']:.2f}")
            
            except Exception as e:  
                self.logger.error_e(
                    message='Error while processing filled TP/SL order', e=e)
                return False

            return True

        return False

    def execute(self):
        klines_df = self.trade_client.fetch_klines(
            symbol=self.bot_config.symbol,
            timeframe=self.bot_config.timeframe,
            timeframe_limit=self.bot_config.timeframe_limit
        )

        # get active position from binance and sync with bot memory
        try:
            remote_position_dict: dict = self.trade_client.fetch_position(
                symbol=self.bot_config.symbol)
            active_position_dict = self._sync_position_state(
                                            remote_position_dict=remote_position_dict,
                                            candle_open_time=str(klines_df.iloc[-1]["open_time"])
                                        )
        except Exception as e:
            self.logger.critical_e(message='Failed to fetch or sync position', e=e)

        have_position = bool(active_position_dict)
        have_tp = bool(self.position_handler.tp_order_id)
        have_sl = bool(self.position_handler.sl_order_id)

        # CASE 1: no active position and no TP/SL orders in memory -> looking for entry signal
        if not have_position and not have_tp and not have_sl:
            try:
                entry_signal: PositionSignal = self.entry_strategy.should_open(
                    klines_df=klines_df, position_handler=self.position_handler)
                self.logger.debug(message=entry_signal.position_side)
                self.logger.debug(message=entry_signal.reason)
            except Exception as e:
                self.logger.error_e(message='Error while checking entry signal', e=e)

            # open new position
            if entry_signal.position_side != PositionSide.ZERO:
                self.logger.info(
                    message=f'{self.bot_config.symbol} Entry signal triggered')

                _new_position_dict = self._place_order_to_open_position(
                    position_side=entry_signal.position_side)

                _new_position_dict['run_id'] = self.bot_config.run_id
                _new_position_dict['open_candle'] = str(
                    object=klines_df.iloc[-1]["open_time"])
                _new_position_dict['open_reason'] = entry_signal.reason
                self.position_handler.open_position(
                    position_dict=_new_position_dict)
                active_position_dict = _new_position_dict

                try:
                    if self.bot_config.tp_enabled or self.bot_config.sl_enabled:
                        self._place_position_tp_sl(klines_df=klines_df)
                except Exception as e:
                    self.logger.error_e(
                        message='Error while placing TP/SL orders', e=e)

        # CASE 2: monitoring TL/SL
        #   if no active position on binance, but TP/SL orders in memory -> clear TP/SL order and record position
        if have_tp or have_sl:
            if not have_position:
                try:
                    self.logger.debug(message='Checking TP/SL orders')
                    if self._monitor_tp_sl_fill(close_candle_open_time=str(klines_df.iloc[-1]["open_time"])):
                        active_position_dict = None  # position closed
                except Exception as e:
                    self.logger.error_e(
                        message='Error while checking TP/SL orders', e=e)

        # CASE 3: active position, loogking for exit signal
        if have_position:
            pnl = active_position_dict.get('pnl', 0.0)
            self.logger.debug(message=f"Updating position pnl {'+' if pnl >= 0 else ''}{pnl:.2f}")
            self.position_handler.update_pnl(pnl=pnl)

            try:
                exit_signal: PositionSignal = self.exit_strategy.should_close(
                    klines_df=klines_df, position_handler=self.position_handler)
                # self.logger.debug(exit_signal.position_side)
                self.logger.debug(message=exit_signal.reason)
            except Exception as e:
                self.logger.error_e(message='Error while checking exit signal', e=e)

            if exit_signal.position_side == PositionSide.ZERO:
                try:
                    self.logger.info(
                        message=f'{self.bot_config.symbol} Exit signal triggered')
                    self.logger.info(
                        message=f'Active position: {active_position_dict}')

                    closed_position_dict = self._place_order_to_close_position(
                        position_dict=active_position_dict)
                    if self.bot_config.tp_enabled:
                        self._cancel_tp_order()
                    if self.bot_config.sl_enabled:
                        self._cancel_sl_order()
                    self.position_handler.clear_tp_sl_orders()

                    closed_position_dict['close_reason'] = exit_signal.reason
                    closed_position_dict['close_candle_open_time'] = str(klines_df.iloc[-1]["open_time"])
                    self.position_handler.close_position(
                        position_dict=closed_position_dict)
                except Exception as e:
                    self.logger.error_e(
                        message='Error while placing order to close position', e=e)

        try:
            if have_position and self.position_handler.position is not None:
                self.position_handler.dump_position_state()
        except Exception as e:
            self.logger.error_e(
                message='Error while dumping position state', e=e)

    def run(self):
        while self.trade_client.running:
            try:
                self.execute()
            except Exception as e:
                self.logger.error_e(message='Error executing bot', e=e)

            self.trade_client.wait()

# EOF
