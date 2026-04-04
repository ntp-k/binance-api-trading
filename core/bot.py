from time import sleep
from typing import Optional, Dict, Any, Tuple
from decimal import Decimal, ROUND_UP

from abstracts.base_entry_strategy import BaseEntryStrategy
from abstracts.base_exit_strategy import BaseExitStrategy
from abstracts.base_trade_client import BaseTradeClient
from commons.constants import (
    ORDER_PLACEMENT_WAIT,
    ORDER_STATUS_CHECK_INTERVAL,
    LIMIT_ORDER_PRICE_CHECK_INTERVAL,
    ORDER_STATUS_FILLED,
    ALGO_ORDER_STATUS_FINISHED
)
from commons.custom_logger import CustomLogger
from core.position_handler import PositionHandler
from models.bot_config import BotConfig
from models.enum.order_side import OrderSide
from models.enum.order_type import OrderType
from models.enum.position_side import PositionSide
from models.enum.run_mode import RunMode
from models.enum.trade_client import TradeClient
from models.position_signal import PositionSignal
from trade_clients.get_trade_client import get_trade_client
import strategies.get_strategy as get_strategy


class Bot:
    """
    Main trading bot class that manages position lifecycle and strategy execution.
    """

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

    def _init_trade_client(self, run_mode: RunMode, trade_client: TradeClient) -> BaseTradeClient:
        """
        Initialize trade client with proper error handling.
        
        Args:
            run_mode: Trading mode (LIVE, BACKTEST)
            trade_client: Client type (BINANCE, OFFLINE)
            
        Returns:
            Initialized trade client instance
            
        Raises:
            RuntimeError: If trade client initialization fails
        """
        try:
            self.logger.debug(message=f'Initializing trade client')
            _trade_client: BaseTradeClient = get_trade_client(
                run_mode=run_mode, trade_client=trade_client)
            _trade_client.set_running(running=True)
            self.logger.debug(
                message=f'Initialized trade client {_trade_client.__class__.__name__}')
            return _trade_client
        except (ImportError, ValueError) as e:
            self.logger.error_e(
                message='Error while initializing trade client', e=e)
            raise RuntimeError(f"Failed to initialize trade client: {e}") from e

    def _set_leverage(self):
        self.trade_client.set_leverage(
            symbol=self.bot_config.symbol, leverage=self.bot_config.leverage)
        self.logger.debug(f'Leverage is set to {self.bot_config.leverage}')

    def _sync_position_state(
        self,
        remote_position_dict: Optional[Dict[str, Any]],
        candle_open_time: str
    ) -> Optional[Dict[str, Any]]:
        """
        Synchronize position state between local memory and remote exchange.
        
        Args:
            remote_position_dict: Position data from exchange
            candle_open_time: Current candle open time
            
        Returns:
            The remote position dictionary (may be None)
        """
        # CASE 1: No position on remote but has position in memory
        if not remote_position_dict and self.position_handler.is_open():
            if not (self.bot_config.tp_enabled or self.bot_config.sl_enabled):
                # Not in TP/SL mode - positions should match, clear local state
                self.logger.warning(
                    message="Bot has position in memory but trade client has none; resetting state.")
                self.position_handler.clear_position()
            else:
                # In TP/SL mode - position might have been closed by TP/SL
                self.logger.debug(message='Suspect TP/SL were hit - position closed on exchange')

        # CASE 2: Have position on remote but no position in local -> sync local with remote
        elif remote_position_dict and not self.position_handler.is_open():
            self.logger.info(message="Found position on exchange, syncing to local state")
            remote_position_dict['run_id'] = self.bot_config.run_id
            remote_position_dict['open_candle'] = candle_open_time
            self.position_handler.open_position(position_dict=remote_position_dict)
            
        # CASE 3: Have position on both remote and local -> verify position integrity
        elif remote_position_dict and self.position_handler.is_open():
            if (remote_position_dict['position_side'] != self.position_handler.position.position_side) or \
                    (remote_position_dict['entry_price'] != self.position_handler.position.entry_price):
                self.logger.warning(
                    message="Position mismatch between exchange and local state; resetting local state")
                self.position_handler.clear_position()
        
        return remote_position_dict

    def _place_tp_order(self, position_side: PositionSide, tp_price: float) -> Dict[str, Any]:
        self.logger.debug(message='Placing new take profit order')
        order_side = OrderSide.SELL.value if position_side == PositionSide.LONG else OrderSide.BUY.value
        self.position_handler.set_tp_price(price=tp_price)

        tp_order = self.trade_client.place_algorithmic_order(
            symbol=self.bot_config.symbol,
            order_side=order_side,
            order_type=OrderType.TAKE_PROFIT_MARKET.value,
            trigger_price=tp_price,
            quantity=self.bot_config.quantity
        )
        _order_id = tp_order.get('algoId')
        self.logger.info(message=f"TP order placed at {tp_price}, order id: {_order_id}")
        self.position_handler.set_tp_order_id(id=_order_id)
        return tp_order

    def _place_sl_order(self, position_side: PositionSide, sl_price: float) -> Dict[str, Any]:
        self.logger.debug(message='Placing new stop loss order')
        order_side = OrderSide.SELL.value if position_side == PositionSide.LONG else OrderSide.BUY.value
        self.position_handler.set_sl_price(price=sl_price)

        sl_order = self.trade_client.place_algorithmic_order(
            symbol=self.bot_config.symbol,
            order_side=order_side,
            order_type=OrderType.STOP_MARKET.value,
            trigger_price=sl_price,
            quantity=self.bot_config.quantity
        )
        _order_id = sl_order.get('algoId')
        self.logger.info(message=f"SL order placed at {sl_price}, order id: {_order_id}")
        self.position_handler.set_sl_order_id(id=_order_id)
        return sl_order

    def _place_market_order(self, order_side: str, reduce_only: bool) -> Dict[str, Any]:
        self.logger.debug(message='Placing new market order')
        _order = self.trade_client.place_order(
            symbol=self.bot_config.symbol,
            order_side=order_side,
            order_type=OrderType.MARKET.value,
            quantity=self.bot_config.quantity,
            reduce_only=reduce_only,
        )
        sleep(ORDER_PLACEMENT_WAIT)  # wait for binance to process order

        _order_id = _order.get('orderId')
        _order_filled = False
        while not _order_filled:
            _check_order = self.trade_client.fetch_order(symbol=self.bot_config.symbol, order_id=_order_id)
            _order_filled = _check_order.get('status') == ORDER_STATUS_FILLED

            if not _order_filled:
                self.logger.info(message="Market Order still pending. Waiting...")
            else:
                self.logger.info(message="Market Order filled")
                break
            sleep(ORDER_STATUS_CHECK_INTERVAL)  # wait before checking again

        self.logger.debug(message=f'Getting trade history order_id: {_order_id}')
        return self.trade_client.fetch_order_trade(symbol=self.bot_config.symbol, order_id=_order_id) 

    def _place_limit_order(self, order_side: str, reduce_only: bool) -> Dict[str, Any]:
        _order_filled = False
        _order_id = ''
        _ordered_price = None  # Track the price at which order was placed
        
        while not _order_filled:
            current_price = self.trade_client.fetch_price(symbol=self.bot_config.symbol)

            # Place order if no active order OR price changed from ordered price
            if _ordered_price != current_price:
                # Cancel existing order if price changed
                if _order_id:
                    self.trade_client.cancel_order(symbol=self.bot_config.symbol, order_id=_order_id)
                    self.logger.info(f"Price {_ordered_price} -> {current_price}  |  Canceling order {_order_id}...")
                    sleep(ORDER_STATUS_CHECK_INTERVAL)  # wait for binance to cancel order
                
                # Place new order at current price
                self.logger.info(message=f"Placing new LIMIT order at price: {current_price}")
                _order = self.trade_client.place_order(
                    symbol=self.bot_config.symbol,
                    order_side=order_side,
                    order_type=OrderType.LIMIT.value,
                    quantity=self.bot_config.quantity,
                    price=current_price,
                    reduce_only=reduce_only,
                )
                _order_id = _order.get('orderId', '')
                _ordered_price = current_price  # Remember the price we ordered at
            else:
                self.logger.debug(message="Price unchanged. Keep monitoring order.")

            sleep(LIMIT_ORDER_PRICE_CHECK_INTERVAL)  # wait before checking order status

            # Check if order filled
            _check_order = self.trade_client.fetch_order(symbol=self.bot_config.symbol, order_id=_order_id)
            _order_filled = _check_order.get('status') == ORDER_STATUS_FILLED
            
            if _order_filled:
                self.logger.info(message="Limit Order filled")
                break
            else:
                self.logger.info(message="Limit Order still pending. Waiting...")
    
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
            message=f"{self.bot_config.symbol} | {'CLOSE':<5} | {position_dict['position_side'].value:<5} | {position_dict['entry_price']:.4f} -> {_order_trade['price']:.4f} | {'+' if _order_trade['pnl'] >= 0 else ''}{_order_trade['pnl']:.4f}")
        return closed_position_dict

    def _place_position_tp_sl(self, klines_df) -> None:
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

    def _cancel_tp_order(self) -> None:
        order_id = self.position_handler.get_tp_order_id()
        if order_id:
            self.trade_client.cancel_algorithmic_order(order_id=order_id)

    def _cancel_sl_order(self) -> None:
        order_id = self.position_handler.get_sl_order_id()
        if order_id:
            self.trade_client.cancel_algorithmic_order(order_id=order_id)

    def _monitor_tp_sl_fill(self, close_candle_open_time: str = '') -> bool:
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
                _check_sl_order = self.trade_client.fetch_algorithmic_order(order_id=sl_order_id)
                sl_status = _check_sl_order.get('algoStatus')
                if sl_status == ALGO_ORDER_STATUS_FINISHED:
                    self.logger.info("SL hit ✅")
                    filled_order_id = _check_sl_order.get('actualOrderId')
                    close_reason = 'SL Hit'
                    # if self.bot_config.tp_enabled:
                    #     self.logger.info("Cancelling TP due to SL hit")
                    #     self._cancel_tp_order()
            else:
                self.logger.debug("No SL order in memory")

        # Check TP only if no order has already been filled
        if self.bot_config.tp_enabled and not filled_order_id:
            tp_order_id = self.position_handler.get_tp_order_id()
            if tp_order_id:
                _check_tp_order = self.trade_client.fetch_algorithmic_order(order_id=tp_order_id)
                tp_status = _check_tp_order.get('algoStatus')
                if tp_status == ALGO_ORDER_STATUS_FINISHED:
                    self.logger.info("TP hit ✅")
                    filled_order_id = _check_tp_order.get('actualOrderId')
                    close_reason = 'TP Hit'
                    # if self.bot_config.sl_enabled:
                    #     self.logger.info("Cancelling SL due to TP hit")
                    #     self._cancel_sl_order()
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
                message=f"{self.bot_config.symbol} | {'CLOSE':<5} | {order_trade['side']:<5} | {self.position_handler.entry_price:.4f} -> {order_trade['price']:.4f} | {'+' if order_trade['pnl'] >= 0 else ''}{order_trade['pnl']:.4f}")
            
            except (KeyError, ValueError, TypeError) as e:
                self.logger.error_e(
                    message='Error while processing filled TP/SL order', e=e)
                return False

            return True

        return False

    def _fetch_market_data(self):
        """Fetch klines data from exchange."""
        klines_df = self.trade_client.fetch_klines(
            symbol=self.bot_config.symbol,
            timeframe=self.bot_config.timeframe,
            timeframe_limit=self.bot_config.timeframe_limit
        )
        
        if klines_df is None or klines_df.empty:
            self.logger.error("Failed to fetch klines data")
            return None
        
        return klines_df
    
    def _get_position_state(self, klines_df) -> Tuple[Optional[Dict[str, Any]], str]:
        """Get and sync position state with exchange."""
        current_candle_open_time = str(klines_df.iloc[-1]["open_time"])
        
        try:
            remote_position_dict = self.trade_client.fetch_position(
                symbol=self.bot_config.symbol)
            active_position_dict = self._sync_position_state(
                remote_position_dict=remote_position_dict,
                candle_open_time=current_candle_open_time
            )
            return active_position_dict, current_candle_open_time
        except Exception as e:
            self.logger.critical_e(message='Failed to fetch or sync position', e=e)
            return None, current_candle_open_time
    
    def _handle_entry_signal(self, klines_df, current_candle_open_time: str) -> Optional[Dict[str, Any]]:
        """Check for entry signals and open position if triggered."""
        try:
            entry_signal = self.entry_strategy.should_open(
                klines_df=klines_df, position_handler=self.position_handler)
            self.logger.debug(message=f"Entry signal: {entry_signal.position_side} - {entry_signal.reason}")
        except Exception as e:
            self.logger.error_e(message='Error while checking entry signal', e=e)
            return None
        
        if entry_signal.position_side == PositionSide.ZERO:
            return None
        
        # Open new position
        self.logger.info(message=f'{self.bot_config.symbol} Entry signal triggered')
        
        try:
            new_position_dict = self._place_order_to_open_position(
                position_side=entry_signal.position_side)
            
            new_position_dict['run_id'] = self.bot_config.run_id
            new_position_dict['open_candle'] = current_candle_open_time
            new_position_dict['open_reason'] = entry_signal.reason
            
            self.position_handler.open_position(position_dict=new_position_dict)
            
            # Place TP/SL if enabled
            if self.bot_config.tp_enabled or self.bot_config.sl_enabled:
                self._place_position_tp_sl(klines_df=klines_df)
            
            return new_position_dict
        except Exception as e:
            self.logger.error_e(message='Error while opening position', e=e)
            return None
    
    def _handle_tp_sl_monitoring(self, current_candle_open_time: str) -> bool:
        """Monitor TP/SL orders and process if filled."""
        try:
            self.logger.debug(message='Checking TP/SL orders')
            return self._monitor_tp_sl_fill(close_candle_open_time=current_candle_open_time)
        except Exception as e:
            self.logger.error_e(message='Error while checking TP/SL orders', e=e)
            return False
    
    def _handle_exit_signal(
        self,
        klines_df,
        active_position_dict: Dict[str, Any],
        current_candle_open_time: str
    ) -> bool:
        """Check for exit signals and close position if triggered."""
        # Update PnL
        pnl = active_position_dict.get('pnl', 0.0)
        self.logger.debug(message=f"Updating position pnl {'+' if pnl >= 0 else ''}{pnl:.2f}")
        self.position_handler.update_pnl(pnl=pnl)
        
        # Check exit signal
        try:
            exit_signal = self.exit_strategy.should_close(
                klines_df=klines_df, position_handler=self.position_handler)
            self.logger.debug(message=f"Exit signal: {exit_signal.reason}")
        except Exception as e:
            self.logger.error_e(message='Error while checking exit signal', e=e)
            return False
        
        if exit_signal.position_side != PositionSide.ZERO:
            return False
        
        # Close position
        self.logger.info(message=f'{self.bot_config.symbol} Exit signal triggered')
        self.logger.info(message=f'Active position: {active_position_dict}')
        
        try:
            closed_position_dict = self._place_order_to_close_position(
                position_dict=active_position_dict)
            
            self.position_handler.clear_tp_sl_orders()
            
            closed_position_dict['close_reason'] = exit_signal.reason
            closed_position_dict['close_candle_open_time'] = current_candle_open_time
            
            self.position_handler.close_position(position_dict=closed_position_dict)
            return True
        except Exception as e:
            self.logger.error_e(message='Error while closing position', e=e)
            return False
    
    def _save_position_state(self) -> None:
        """Save position state to disk if position exists."""
        try:
            if self.position_handler.position is not None:
                self.position_handler.dump_position_state()
        except Exception as e:
            self.logger.error_e(message='Error while dumping position state', e=e)

    def execute(self):
        """
        Main execution loop for the bot.
        
        Handles three main states:
        1. Looking for entry (no position, no TP/SL)
        2. Monitoring TP/SL (TP/SL active, no position on exchange)
        3. Looking for exit (active position)
        """
        # Fetch market data
        klines_df = self._fetch_market_data()
        if klines_df is None:
            self.logger.critical(message='Error while fetching market data')
        
        # Get position state
        active_position_dict, current_candle_open_time = self._get_position_state(klines_df)
        # if active_position_dict is None and current_candle_open_time is None:
        #     return
        
        # Cache state flags
        have_position = bool(active_position_dict)
        have_tp = bool(self.position_handler.tp_order_id)
        have_sl = bool(self.position_handler.sl_order_id)
        
        # STATE 1: Looking for entry signal
        if not have_position and not have_tp and not have_sl:
            new_position = self._handle_entry_signal(klines_df, current_candle_open_time)
            if new_position:
                active_position_dict = new_position
                have_position = True

        # STATE 2: Monitoring TP/SL
        if (have_tp or have_sl) and not have_position:
            if self._handle_tp_sl_monitoring(current_candle_open_time):
                active_position_dict = None
                have_position = False
        
        # STATE 3: Looking for exit signal
        if have_position and active_position_dict:
            if self._handle_exit_signal(klines_df, active_position_dict, current_candle_open_time):
                have_position = False
        
        # Save position state
        if have_position:
            self._save_position_state()

    def run(self) -> None:
        """Main bot execution loop."""
        while self.trade_client.running:
            try:
                self.execute()
            except KeyboardInterrupt:
                self.logger.info(message='Bot stopped by user')
                break
            except (ConnectionError, TimeoutError) as e:
                self.logger.error_e(message='Network error in bot execution', e=e)
                sleep(30)  # Wait before retry on network errors
            except Exception as e:
                self.logger.error_e(message='Unexpected error executing bot', e=e)
                sleep(10)  # Brief pause before continuing

            self.trade_client.wait()

# EOF
