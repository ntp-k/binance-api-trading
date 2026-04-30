from time import sleep
from typing import Optional, Dict, Any, Tuple

from abstracts.base_trade_client import BaseTradeClient
from commons.custom_logger import CustomLogger
from core.position_handler import PositionHandler
from core.trade_handler import TradeHandler
from core.backtest_metrics import BacktestMetrics
from models.bot_config import BotConfig
from models.enum.position_side import PositionSide
from models.enum.run_mode import RunMode
from models.enum.trade_client import TradeClient
from trade_clients.get_trade_client import get_trade_client
import strategies.get_strategy as get_strategy


class Bot:
    """
    Main trading bot class that manages position lifecycle and strategy execution.
    """

    def __init__(self, bot_config: BotConfig):
        # Extract bot_id from bot_name (e.g., 'bot_32' -> '32')
        bot_id = bot_config.bot_name.replace('bot_', '').replace(' ', '_')
        
        self.logger = CustomLogger(
            name=f"{bot_config.bot_name.replace(' ', '_')}",
            bot_id=bot_id
        )
        self.logger.info(message=f'Initializing {self.__class__.__name__}: {bot_config.bot_name}')

        self.bot_config: BotConfig = bot_config

        self.position_handler: PositionHandler = PositionHandler(
            bot_config=bot_config,
            logger=self.logger
        )

        self.trade_client = self._init_trade_client(
            run_mode=bot_config.run_mode,
            trade_client=bot_config.trade_client
        )
        self._set_leverage()
        
        # Pre-fetch and cache exchange info for the symbol
        self.logger.debug(message=f'Fetching exchange info for {bot_config.symbol}')
        self.trade_client.fetch_exchange_info(bot_config.symbol)
        
        # Initialize trade handler
        self.logger.debug(message=f'Initializing trade handler')
        self.trade_handler = TradeHandler(
            trade_client=self.trade_client,
            bot_config=self.bot_config,
            logger=self.logger,
            position_handler=self.position_handler
        )
        
        self.logger.debug(message=f'Initializing strategies')
        self.entry_strategy, self.exit_strategy = get_strategy.init_strategies(
            entry_strategy=self.bot_config.entry_strategy,
            exit_strategy=self.bot_config.exit_strategy,
            dynamic_config=self.bot_config.dynamic_config,
            logger=self.logger
        )
        self.logger.info(
                message=f'Entry Strategy: {self.entry_strategy.__class__.__name__}')
        self.logger.info(
                message=f'Exit Strategy: {self.exit_strategy.__class__.__name__}')
        
        # Initialize backtest metrics and preload data for backtest mode
        self.backtest_metrics: Optional[BacktestMetrics] = None
        if self.bot_config.run_mode == RunMode.BACKTEST:
            self.backtest_metrics = BacktestMetrics(
                bot_name=bot_config.bot_name,
                run_id=bot_config.run_id,
                logger=self.logger
            )
            self._preload_backtest_data()
    
    def _preload_backtest_data(self) -> None:
        """Preload historical data for backtest mode."""
        self.logger.info("Preloading historical data for backtest...")
        
        # Get candle_for_indicator from dynamic_config
        candle_for_indicator = self.bot_config.dynamic_config.get('candle_for_indicator', 10)
        
        # Fetch enough data: we need at least candle_for_indicator candles before we can start trading
        # Fetch 1500 candles (Binance max)
        limit = 1500
        
        self.trade_client.preload_historical_data(  # type: ignore
            symbol=self.bot_config.symbol,
            timeframe=self.bot_config.timeframe,
            limit=limit,
            order_type=self.bot_config.order_type.value,
            leverage=self.bot_config.leverage
        )
        
        # Set initial candle index to start after we have enough history for indicators
        self.trade_client.current_candle_index = candle_for_indicator - 1  # type: ignore
        
        # Set backtest period in metrics using first and last kline timestamps
        if self.backtest_metrics and hasattr(self.trade_client, 'klines_cache'):
            klines_cache = self.trade_client.klines_cache  # type: ignore
            if klines_cache is not None and len(klines_cache) > 0:
                first_kline_time = str(klines_cache.iloc[candle_for_indicator - 1]['open_time']).split('+')[0]
                last_kline_time = str(klines_cache.iloc[-1]['close_time']).split('+')[0].split('.')[0]
                self.backtest_metrics.set_backtest_period(first_kline_time, last_kline_time)
                self.logger.info(f"Backtest period: {first_kline_time} to {last_kline_time}")
        
        self.logger.debug(f"Backtest will start from candle {candle_for_indicator} (index {candle_for_indicator - 1})")

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
                run_mode=run_mode,
                trade_client=trade_client,
                logger=self.logger
            )
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
        self.logger.info(f'Leverage is set to {self.bot_config.leverage}')

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
                # Not in TP/SL mode - position was likely liquidated or closed externally
                self.logger.warning(
                    message="⚠️ Position closed on exchange (likely LIQUIDATED) - clearing local state")
                # clear_position() will update last_position_open_candle to prevent re-entry on same candle
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

    def _fetch_market_data(self):
        """Fetch klines data from exchange."""
        klines_df = self.trade_client.fetch_klines(
            symbol=self.bot_config.symbol,
            timeframe=self.bot_config.timeframe,
            timeframe_limit=self.bot_config.timeframe_limit
        )
        
        if klines_df is None or klines_df.empty:
            self.logger.error(f"Failed to fetch klines data for {self.bot_config.symbol}")
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
            new_position_dict = self.trade_handler.place_order_to_open_position(
                position_side=entry_signal.position_side)
            
            new_position_dict['run_id'] = self.bot_config.run_id
            new_position_dict['open_candle'] = current_candle_open_time
            new_position_dict['open_reason'] = entry_signal.reason
            
            # For backtest mode, explicitly set open_time to candle open time
            if self.bot_config.run_mode == RunMode.BACKTEST:
                new_position_dict['open_time'] = current_candle_open_time
            
            self.position_handler.open_position(position_dict=new_position_dict)
            position = self.position_handler.position
            position_side = position.position_side
            entry_price = position.entry_price

            # Always calculate TP/SL prices for exit strategies to use
            tp_price, sl_price = self.entry_strategy.calculate_tp_sl(
                klines_df=klines_df,
                position_side=position_side,
                entry_price=entry_price
            )

            # Always set TP/SL prices in position handler for exit strategy to use
            self.position_handler.set_tp_price(price=tp_price)
            self.position_handler.set_sl_price(price=sl_price)
            self.logger.debug(message=f'Calculated TP: {tp_price}, SL: {sl_price}')

            # Place TP/SL orders on exchange only if enabled
            if self.bot_config.tp_enabled:
                self.logger.info(message=f'Placing TP order at {tp_price}')
                self.trade_handler.place_tp_order(position_side=position_side, tp_price=tp_price)
            if self.bot_config.sl_enabled:
                self.logger.info(message=f'Placing SL order at {sl_price}')
                self.trade_handler.place_sl_order(position_side=position_side, sl_price=sl_price)
            
            return new_position_dict
        except Exception as e:
            self.logger.error_e(message='Error while opening position', e=e)
            return None
    
    def _handle_tp_sl_monitoring(self, current_candle_open_time: str) -> bool:
        """Monitor TP/SL orders and process if filled."""
        try:
            return self.trade_handler.monitor_tp_sl_fill(
                close_candle_open_time=current_candle_open_time,
                backtest_metrics=self.backtest_metrics
            )
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
        self.logger.debug(message=f'Active position: {active_position_dict}')
        
        try:
            closed_position_dict = self.trade_handler.place_order_to_close_position(
                position_dict=active_position_dict)
            
            # Cancel any active TP/SL orders
            if self.bot_config.tp_enabled:
                self.trade_handler.cancel_tp_order()
            if self.bot_config.sl_enabled:
                self.trade_handler.cancel_sl_order()
            
            self.position_handler.clear_tp_sl_orders()
            
            closed_position_dict['close_reason'] = exit_signal.reason
            closed_position_dict['close_candle_open_time'] = current_candle_open_time
            
            # For backtest mode, explicitly set close_time to candle open time
            if self.bot_config.run_mode == RunMode.BACKTEST:
                # last_kline_time = str(klines_df.iloc[-1]['close_time']).split('+')[0].split('.')[0]
                closed_position_dict['close_time'] = current_candle_open_time
            
            trade_dict = self.position_handler.close_position(position_dict=closed_position_dict)

            # Track trade for backtest
            if self.backtest_metrics and trade_dict:
                self.backtest_metrics.add_trade(trade_dict)
            
            return True
        except ValueError as e:
            # Position already closed (likely by TP/SL)
            self.logger.warning(f'Position already closed: {e}')
            self.position_handler.clear_position()
            self.position_handler.clear_tp_sl_orders()
            return False
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
            self.logger.error(message=f'Failed to fetch market data for {self.bot_config.symbol}')
            return
        
        # Get position state
        active_position_dict, current_candle_open_time = self._get_position_state(klines_df)
        
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
        """Main bot execution loop - handles both live and backtest modes."""

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

            # For backtest mode, advance to next candle
            if self.bot_config.run_mode == RunMode.BACKTEST:
                if not self.trade_client.advance_candle():  # type: ignore
                    self.logger.info("Backtest completed - reached end of data")
                    break
            else:
                # For live mode, wait between iterations
                self.trade_client.wait()
        
        # For backtest mode, print and save results
        if self.bot_config.run_mode == RunMode.BACKTEST and self.backtest_metrics:
            self.logger.info("BACKTEST COMPLETED - Generating results...")
            
            # Print summary to console using visualization methods
            bot_config_dict = self.bot_config.to_dict()
            self.backtest_metrics.print_summary(bot_config=bot_config_dict)
            
            # Save results to file
            results_file = self.backtest_metrics.save_results(bot_config_dict)

            self.logger.info(f"Results saved to: {results_file}")

# EOF
