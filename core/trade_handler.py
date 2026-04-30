from time import sleep
from typing import Dict, Any
from decimal import Decimal, ROUND_UP

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


class TradeHandler:
    """
    Handles all trading execution logic including:
    - Order placement (market, limit, maker-only)
    - TP/SL placement & cancellation
    - TP/SL monitoring
    - Position open/close execution
    - Price calculation (maker price, tick rounding)
    - Dynamic quantity calculation from fixed margin
    """

    def __init__(
        self,
        trade_client: BaseTradeClient,
        bot_config: BotConfig,
        logger: CustomLogger,
        position_handler: PositionHandler
    ):
        self.trade_client = trade_client
        self.bot_config = bot_config
        self.logger = logger
        self.position_handler = position_handler
        self._cached_quantity: float = 0.0  # Cache calculated quantity for current position
    
    def calculate_quantity_from_margin(self, current_price: float) -> float:
        """
        Calculate position quantity from fixed margin amount.
        
        Formula: quantity = (position_margin * leverage) / current_price
        
        Example:
        - position_margin = 5 USDC
        - leverage = 10x
        - current_price = 100 USDC
        - quantity = (5 * 10) / 100 = 0.5
        
        Args:
            current_price: Current market price
        
        Returns:
            Calculated quantity rounded to exchange precision
        
        Raises:
            ValueError: If position_margin is not set or price is invalid
        """
        if not self.bot_config.position_margin:
            raise ValueError("position_margin is not set in bot config")
        
        if current_price <= 0:
            raise ValueError(f"Invalid price: {current_price}")
        
        # Calculate raw quantity
        raw_quantity = (self.bot_config.position_margin * self.bot_config.leverage) / current_price
        
        # Get exchange info for quantity precision
        exchange_info = self.trade_client.get_cached_exchange_info(self.bot_config.symbol)
        if not exchange_info:
            self.logger.warning("Exchange info not cached, using raw quantity")
            return raw_quantity
        
        # Round to step size (quantity precision)
        step_size = exchange_info.get('stepSize', 0.001)
        quantity_decimal = Decimal(str(raw_quantity))
        step_decimal = Decimal(str(step_size))
        
        # Round down to nearest step size
        rounded_quantity = float((quantity_decimal // step_decimal) * step_decimal)
        
        self.logger.debug(
            f"Calculated quantity: {rounded_quantity} "
            f"(margin={self.bot_config.position_margin}, "
            f"leverage={self.bot_config.leverage}, "
            f"price={current_price})"
        )
        
        return rounded_quantity
    
    def get_trade_quantity(self) -> float:
        """
        Get the quantity to use for trading.
        
        Returns fixed quantity if configured, otherwise calculates from margin.
        Uses cached quantity if already calculated for current position.
        
        Returns:
            Trade quantity
        """
        # If using fixed quantity mode, return it directly
        if not self.bot_config.uses_fixed_margin():
            if self.bot_config.quantity is None:
                raise ValueError("Quantity is not set and position_margin is not configured")
            return self.bot_config.quantity
        
        # If quantity already cached for this position, use it
        if self._cached_quantity > 0:
            return self._cached_quantity
        
        # Calculate quantity from current price
        current_price = self.trade_client.fetch_price(symbol=self.bot_config.symbol)
        self._cached_quantity = self.calculate_quantity_from_margin(current_price)
        
        return self._cached_quantity
    
    def clear_cached_quantity(self) -> None:
        """Clear cached quantity when position is closed."""
        self._cached_quantity = 0.0

    def round_to_tick_size(self, price: float, tick_size: float, order_side: str) -> float:
        """
        Round price to valid tick size with proper precision.
        
        Args:
            price: Price to round
            tick_size: Minimum price increment
            order_side: 'BUY' or 'SELL'
        
        Returns:
            Rounded price
        """
        price_decimal = Decimal(str(price))
        tick_decimal = Decimal(str(tick_size))
        
        if order_side == OrderSide.BUY.value:
            # Round DOWN for BUY to ensure price < best_bid (maker)
            return float((price_decimal // tick_decimal) * tick_decimal)
        else:
            # Round UP for SELL to ensure price > best_ask (maker)
            return float((price_decimal / tick_decimal).to_integral_value(rounding=ROUND_UP) * tick_decimal)

    def calculate_maker_price(self, order_side: str, tick_size: float, offset_ticks: int = 1) -> float:
        """
        Calculate a maker-only price from order book.
        
        Args:
            order_side: 'BUY' or 'SELL'
            tick_size: Minimum price increment
            offset_ticks: Number of ticks away from best bid/ask
        
        Returns:
            Calculated maker price
        """
        # Fetch order book
        order_book = self.trade_client.fetch_order_book(self.bot_config.symbol, limit=5)
        if not order_book.get('bids') or not order_book.get('asks'):
            self.logger.error("Failed to fetch order book")
            raise ValueError("Failed to fetch order book")
        
        best_bid = Decimal(str(order_book['bids'][0][0]))
        best_ask = Decimal(str(order_book['asks'][0][0]))
        tick = Decimal(str(tick_size))
        offset = Decimal(str(offset_ticks)) * tick
        
        self.logger.debug(f"Order book: Best Bid={best_bid}, Best Ask={best_ask}")
        
        if order_side == OrderSide.BUY.value:
            # For BUY: price must be < best_bid to be maker
            maker_price = best_bid - offset
        else:
            # For SELL: price must be > best_ask to be maker
            maker_price = best_ask + offset
        
        # Round to tick size
        rounded_price = self.round_to_tick_size(
            price=float(maker_price),
            tick_size=tick_size,
            order_side=order_side
        )
        
        self.logger.debug(f"Calculated maker price: {rounded_price} (offset={offset_ticks} ticks)")
        return rounded_price

    def place_tp_order(self, position_side: PositionSide, tp_price: float) -> Dict[str, Any]:
        """
        Place a take profit order.
        
        Args:
            position_side: Current position side (LONG/SHORT)
            tp_price: Take profit trigger price
        
        Returns:
            TP order details
        """
        self.logger.debug(message='Placing take profit order')
        order_side = OrderSide.SELL.value if position_side == PositionSide.LONG else OrderSide.BUY.value
        self.position_handler.set_tp_price(price=tp_price)
        
        # Use cached quantity for TP/SL orders
        quantity = self.get_trade_quantity()

        tp_order = self.trade_client.place_algorithmic_order(
            symbol=self.bot_config.symbol,
            order_side=order_side,
            order_type=OrderType.TAKE_PROFIT_MARKET.value,
            trigger_price=tp_price,
            quantity=quantity
        )
        _order_id = tp_order.get('algoId', '')
        self.logger.info(message=f"TP order placed at {tp_price}, order id: {_order_id}")
        self.position_handler.set_tp_order_id(id=_order_id)
        return tp_order

    def place_sl_order(self, position_side: PositionSide, sl_price: float) -> Dict[str, Any]:
        """
        Place a stop loss order.
        
        Args:
            position_side: Current position side (LONG/SHORT)
            sl_price: Stop loss trigger price
        
        Returns:
            SL order details
        """
        self.logger.debug(message='Placing stop loss order')
        order_side = OrderSide.SELL.value if position_side == PositionSide.LONG else OrderSide.BUY.value
        self.position_handler.set_sl_price(price=sl_price)
        
        # Use cached quantity for TP/SL orders
        quantity = self.get_trade_quantity()

        sl_order = self.trade_client.place_algorithmic_order(
            symbol=self.bot_config.symbol,
            order_side=order_side,
            order_type=OrderType.STOP_MARKET.value,
            trigger_price=sl_price,
            quantity=quantity
        )
        _order_id = sl_order.get('algoId', '')
        self.logger.info(message=f"SL order placed at {sl_price}, order id: {_order_id}")
        self.position_handler.set_sl_order_id(id=_order_id)
        return sl_order

    def place_market_order(self, order_side: str, reduce_only: bool) -> Dict[str, Any]:
        """
        Place a market order.
        
        Args:
            order_side: 'BUY' or 'SELL'
            reduce_only: Whether order should only reduce position
        
        Returns:
            Trade details dictionary
            
        Raises:
            ValueError: If reduce_only order is rejected (no position exists)
        """
        self.logger.debug(message='Placing market order')
        
        # Get quantity (calculated or fixed)
        quantity = self.get_trade_quantity()
        
        try:
            _order = self.trade_client.place_order(
                symbol=self.bot_config.symbol,
                order_side=order_side,
                order_type=OrderType.MARKET.value,
                quantity=quantity,
                reduce_only=reduce_only,
            )
            
            # Check if order placement failed (place_order returns False on HTTP errors)
            if not _order or not _order.get('orderId'):
                # Check if this is a reduce-only rejection
                if reduce_only:
                    self.logger.warning("Market order placement failed with reduce_only=True - checking if position still exists")
                    # Verify position still exists
                    remote_position = self.trade_client.fetch_position(symbol=self.bot_config.symbol)
                    if not remote_position:
                        self.logger.error("Position no longer exists on exchange")
                        raise ValueError("Position already closed, cannot place reduce_only order")
                
                self.logger.error("Market order placement failed - no order ID returned")
                raise ValueError("Market order placement failed")
                
        except Exception as e:
            # Check if it's a reduce_only rejection error (-2022 or -4118)
            error_msg = str(e).lower()
            if reduce_only and ('reduceonly' in error_msg or '-2022' in error_msg or '-4118' in error_msg):
                self.logger.warning("ReduceOnly order rejected - checking if position still exists")
                # Verify position still exists
                try:
                    remote_position = self.trade_client.fetch_position(symbol=self.bot_config.symbol)
                    if not remote_position:
                        self.logger.error("Position no longer exists on exchange")
                        raise ValueError("Position already closed, cannot place reduce_only order") from e
                except Exception as check_error:
                    self.logger.error_e("Error checking position status, assuming position is closed", e=check_error)
                    raise ValueError("Position already closed, cannot place reduce_only order") from e
            raise
        
        # Skip waits in backtest mode
        if self.bot_config.run_mode != RunMode.BACKTEST:
            sleep(ORDER_PLACEMENT_WAIT)  # wait for binance to process order

        _order_id = _order.get('orderId', '')
        _order_filled = False
        while not _order_filled:
            _check_order = self.trade_client.fetch_order(symbol=self.bot_config.symbol, order_id=_order_id)
            _order_filled = _check_order.get('status') == ORDER_STATUS_FILLED

            if not _order_filled:
                self.logger.debug(message="Market Order still pending. Waiting...")
            else:
                self.logger.info(message="Market Order filled")
                break
            
            # Skip waits in backtest mode
            if self.bot_config.run_mode != RunMode.BACKTEST:
                sleep(ORDER_STATUS_CHECK_INTERVAL)  # wait before checking again

        self.logger.debug(message=f'Getting trade history order_id: {_order_id}')
        return self.trade_client.fetch_order_trade(symbol=self.bot_config.symbol, order_id=_order_id)

    def place_limit_order(self, order_side: str, reduce_only: bool) -> Dict[str, Any]:
        """
        Place a limit order with automatic repricing.
        
        Handles partial fills by tracking filled quantity and only placing
        orders for the remaining unfilled quantity.
        
        Args:
            order_side: 'BUY' or 'SELL'
            reduce_only: Whether order should only reduce position
        
        Returns:
            Trade details dictionary
        """
        _order_filled = False
        _order_id = ''
        _ordered_price = None  # Track the price at which order was placed
        _total_filled_qty = 0.0  # Track total filled quantity across all orders
        _target_quantity = self.get_trade_quantity()  # Total quantity we want to fill
        _error_count = 0  # Track consecutive errors
        _max_errors = 3  # Maximum consecutive errors before resetting
        
        while not _order_filled:
            # Calculate remaining quantity to fill
            _remaining_quantity = _target_quantity - _total_filled_qty
            
            if _remaining_quantity <= 0:
                self.logger.info(f"All quantity filled: {_total_filled_qty}/{_target_quantity}")
                break
            
            current_price = self.trade_client.fetch_price(symbol=self.bot_config.symbol)

            # Place order if no active order OR price changed from ordered price
            if _ordered_price != current_price:
                # Check for partial fill before canceling
                if _order_id:
                    try:
                        _check_order = self.trade_client.fetch_order(symbol=self.bot_config.symbol, order_id=_order_id)
                        _order_status = _check_order.get('status', '')
                        _executed_qty = float(_check_order.get('executedQty', 0))
                        
                        # If order is already filled, update total and break out
                        if _order_status == ORDER_STATUS_FILLED:
                            _total_filled_qty += _executed_qty
                            self.logger.info(f"Order already filled: {_executed_qty}, total: {_total_filled_qty}/{_target_quantity}")
                            _order_filled = True
                            break
                        
                        # Track partial fills
                        if _executed_qty > 0:
                            _total_filled_qty += _executed_qty
                            self.logger.info(f"Partial fill detected: {_executed_qty} filled, total: {_total_filled_qty}/{_target_quantity}")
                        
                        # Cancel existing order if not fully filled
                        if _order_status not in [ORDER_STATUS_FILLED, 'CANCELED', 'EXPIRED']:
                            self.trade_client.cancel_order(symbol=self.bot_config.symbol, order_id=_order_id)
                            self.logger.debug(f"Price {_ordered_price} -> {current_price}  |  Canceling order {_order_id}...")
                            
                            # Skip waits in backtest mode
                            if self.bot_config.run_mode != RunMode.BACKTEST:
                                sleep(ORDER_STATUS_CHECK_INTERVAL)  # wait for binance to cancel order
                        
                        # Reset error count on successful operation
                        _error_count = 0
                        
                    except Exception as e:
                        _error_count += 1
                        self.logger.error_e(message=f"Error checking/canceling order (attempt {_error_count}/{_max_errors})", e=e)
                        
                        # If too many consecutive errors, reset order_id to force new order
                        if _error_count >= _max_errors:
                            self.logger.warning(f"Max errors reached, resetting order state")
                            _order_id = ''
                            _ordered_price = None
                            _error_count = 0
                        
                        if self.bot_config.run_mode != RunMode.BACKTEST:
                            sleep(1)
                        continue
                
                # Recalculate remaining quantity
                _remaining_quantity = _target_quantity - _total_filled_qty
                
                if _remaining_quantity <= 0:
                    self.logger.info(f"All quantity filled after partial fills: {_total_filled_qty}/{_target_quantity}")
                    break
                
                # Place new order at current price for remaining quantity
                self.logger.debug(message=f"Placing LIMIT order at price: {current_price} for quantity: {_remaining_quantity}")
                try:
                    _order = self.trade_client.place_order(
                        symbol=self.bot_config.symbol,
                        order_side=order_side,
                        order_type=OrderType.LIMIT.value,
                        quantity=_remaining_quantity,
                        price=current_price,
                        reduce_only=reduce_only,
                    )
                    
                    # Check if order placement failed
                    if not _order or not _order.get('orderId'):
                        # Check if this is a reduce-only rejection
                        if reduce_only:
                            self.logger.warning("Limit order placement failed with reduce_only=True - checking if position still exists")
                            # Verify position still exists before retrying
                            remote_position = self.trade_client.fetch_position(symbol=self.bot_config.symbol)
                            if not remote_position:
                                self.logger.error("Position no longer exists on exchange - stopping order placement")
                                break  # Exit the loop, position is already closed
                        
                        self.logger.error("Order placement failed - no order ID returned")
                        raise ValueError("Order placement failed")
                    
                    _order_id = _order.get('orderId', '')
                    _ordered_price = current_price  # Remember the price we ordered at
                except Exception as e:
                    # Check if it's a reduce_only rejection error (-2022 or -4118)
                    error_msg = str(e).lower()
                    if reduce_only and ('reduceonly' in error_msg or '-2022' in error_msg or '-4118' in error_msg):
                        self.logger.warning("ReduceOnly order rejected - checking if position still exists")
                        # Verify position still exists before retrying
                        try:
                            remote_position = self.trade_client.fetch_position(symbol=self.bot_config.symbol)
                            if not remote_position:
                                self.logger.error("Position no longer exists on exchange - stopping order placement")
                                break  # Exit the loop, position is already closed
                        except Exception as check_error:
                            self.logger.error_e("Error checking position status, assuming position is closed", e=check_error)
                            break  # Exit the loop on error
                    
                    # For other errors, re-raise to exit the loop
                    self.logger.error_e(message="Error placing limit order", e=e)
                    raise
            else:
                self.logger.debug(message="Price unchanged. Keep monitoring order.")

            # Skip waits in backtest mode
            if self.bot_config.run_mode != RunMode.BACKTEST:
                sleep(LIMIT_ORDER_PRICE_CHECK_INTERVAL)  # wait before checking order status

            # Check if order filled
            _check_order = self.trade_client.fetch_order(symbol=self.bot_config.symbol, order_id=_order_id)
            _order_status = _check_order.get('status', '')
            _executed_qty = float(_check_order.get('executedQty', 0))
            
            if _order_status == ORDER_STATUS_FILLED:
                _total_filled_qty += _executed_qty
                self.logger.info(f"Limit Order filled: {_executed_qty}, total: {_total_filled_qty}/{_target_quantity}")
                _order_filled = True
                break
            elif _order_status == 'PARTIALLY_FILLED':
                self.logger.debug(f"Limit Order partially filled: {_executed_qty}/{_remaining_quantity}")
                # Continue loop to check if price changed and handle partial fill
            else:
                self.logger.debug(message="Limit Order still pending. Waiting...")
    
        self.logger.debug(message=f'Getting trade history for symbol: {self.bot_config.symbol}')
        return self.trade_client.fetch_order_trade(symbol=self.bot_config.symbol, order_id=_order_id)

    def place_maker_only_order(self, order_side: str, reduce_only: bool) -> Dict[str, Any]:
        """
        Place a maker-only limit order with automatic repricing.
        
        Uses order book data to calculate maker price and automatically
        reprices if market moves. Ensures orders are always placed as maker
        (adding liquidity) to get reduced fees.
        
        Handles partial fills by tracking filled quantity and only placing
        orders for the remaining unfilled quantity.
        
        Expected behavior:
        1. Get maker price from order book
        2. Place order with maker price (GTX - post-only)
        3. If placement fails (-5022), re-calculate and retry
        4. If placement succeeds, wait before checking status
        5. If order filled, return trade details
        6. If partially filled, track filled quantity and continue with remaining
        7. If not filled and price unchanged, keep monitoring
        8. If not filled and price changed, cancel and place new order for remaining quantity
        
        Args:
            order_side: 'BUY' or 'SELL'
            reduce_only: Whether order should only reduce position
        
        Returns:
            Trade details dictionary
        """
        # Get exchange info from cache (pre-fetched in __init__)
        exchange_info = self.trade_client.get_cached_exchange_info(self.bot_config.symbol)
        if not exchange_info:
            self.logger.error("Exchange info not cached. This should not happen.")
            raise ValueError("Exchange info not available in cache")
        
        tick_size = exchange_info.get('tickSize', 0.01)
        offset_ticks = 0  # Can be made configurable in bot_config if needed
        
        _order_filled = False
        _order_id = ''
        _ordered_maker_price = None
        _total_filled_qty = 0.0  # Track total filled quantity across all orders
        _target_quantity = self.get_trade_quantity()  # Total quantity we want to fill
        _error_count = 0  # Track consecutive errors
        _max_errors = 3  # Maximum consecutive errors before resetting
        
        while not _order_filled:
            # Calculate remaining quantity to fill
            _remaining_quantity = _target_quantity - _total_filled_qty
            
            if _remaining_quantity <= 0:
                self.logger.info(f"All quantity filled: {_total_filled_qty}/{_target_quantity}")
                break
            
            # Calculate current maker price from order book
            try:
                current_maker_price = self.calculate_maker_price(
                    order_side=order_side,
                    tick_size=tick_size,
                    offset_ticks=offset_ticks
                )
            except ValueError as e:
                self.logger.error_e(message="Failed to calculate maker price", e=e)
                
                # Skip waits in backtest mode
                if self.bot_config.run_mode != RunMode.BACKTEST:
                    sleep(ORDER_STATUS_CHECK_INTERVAL)
                continue
            
            # Place or replace order if price changed
            if _ordered_maker_price != current_maker_price:
                # Check for partial fill before canceling
                if _order_id:
                    try:
                        _check_order = self.trade_client.fetch_order(symbol=self.bot_config.symbol, order_id=_order_id)
                        _order_status = _check_order.get('status', '')
                        _executed_qty = float(_check_order.get('executedQty', 0))
                        
                        # If order is already filled, update total and break out
                        if _order_status == ORDER_STATUS_FILLED:
                            _total_filled_qty += _executed_qty
                            self.logger.info(f"Order already filled: {_executed_qty}, total: {_total_filled_qty}/{_target_quantity}")
                            _order_filled = True
                            break
                        
                        # Track partial fills
                        if _executed_qty > 0:
                            _total_filled_qty += _executed_qty
                            self.logger.info(f"Partial fill detected: {_executed_qty} filled, total: {_total_filled_qty}/{_target_quantity}")
                        
                        # Cancel existing order if not fully filled
                        if _order_status not in [ORDER_STATUS_FILLED, 'CANCELED', 'EXPIRED']:
                            self.logger.debug(f"Maker price {_ordered_maker_price} → {current_maker_price}  |  Canceling order {_order_id}...")
                            self.trade_client.cancel_order(symbol=self.bot_config.symbol, order_id=_order_id)
                            
                            # Skip waits in backtest mode
                            if self.bot_config.run_mode != RunMode.BACKTEST:
                                sleep(ORDER_STATUS_CHECK_INTERVAL)  # Wait for cancellation
                        
                        # Reset error count on successful operation
                        _error_count = 0
                        
                    except Exception as e:
                        _error_count += 1
                        self.logger.error_e(message=f"Error checking/canceling order (attempt {_error_count}/{_max_errors})", e=e)
                        
                        # If too many consecutive errors, reset order_id to force new order
                        if _error_count >= _max_errors:
                            self.logger.warning(f"Max errors reached, resetting order state")
                            _order_id = ''
                            _ordered_maker_price = None
                            _error_count = 0
                        
                        if self.bot_config.run_mode != RunMode.BACKTEST:
                            sleep(1)
                        continue
                
                # Recalculate remaining quantity
                _remaining_quantity = _target_quantity - _total_filled_qty
                
                if _remaining_quantity <= 0:
                    self.logger.info(f"All quantity filled after partial fills: {_total_filled_qty}/{_target_quantity}")
                    break
                
                # Place new order at maker price for remaining quantity
                self.logger.debug(f"Placing MAKER order at price: {current_maker_price} for quantity: {_remaining_quantity}")
                try:
                    _order = self.trade_client.place_order(
                        symbol=self.bot_config.symbol,
                        order_side=order_side,
                        order_type=OrderType.LIMIT.value,
                        quantity=_remaining_quantity,
                        price=current_maker_price,
                        reduce_only=reduce_only,
                        time_in_force='GTX'  # Post-only to ensure maker
                    )
                    
                    if not _order or not _order.get('orderId'):
                        # Check if this is a reduce-only rejection
                        if reduce_only:
                            self.logger.warning("Maker order placement failed with reduce_only=True - checking if position still exists")
                            # Verify position still exists before retrying
                            remote_position = self.trade_client.fetch_position(symbol=self.bot_config.symbol)
                            if not remote_position:
                                self.logger.error("Position no longer exists on exchange - stopping order placement")
                                break  # Exit the loop, position is already closed
                        
                        # For other errors (like -5022), retry
                        self.logger.warning("Maker order placement failed (likely -5022), will retry")
                        _ordered_maker_price = None
                        
                        # Skip waits in backtest mode
                        if self.bot_config.run_mode != RunMode.BACKTEST:
                            sleep(1)
                        continue
                except Exception as e:
                    # Check if it's a reduce_only rejection error (-2022 or -4118)
                    error_msg = str(e).lower()
                    if reduce_only and ('reduceonly' in error_msg or '-2022' in error_msg or '-4118' in error_msg):
                        self.logger.warning("ReduceOnly order rejected - checking if position still exists")
                        # Verify position still exists before retrying
                        try:
                            remote_position = self.trade_client.fetch_position(symbol=self.bot_config.symbol)
                            if not remote_position:
                                self.logger.error("Position no longer exists on exchange - stopping order placement")
                                break  # Exit the loop, position is already closed
                        except Exception as check_error:
                            self.logger.error_e("Error checking position status, assuming position is closed", e=check_error)
                            break  # Exit the loop on error
                    
                    # For other errors (like -5022), retry
                    self.logger.warning(f"Maker order placement failed: {e}, will retry")
                    _ordered_maker_price = None
                    
                    # Skip waits in backtest mode
                    if self.bot_config.run_mode != RunMode.BACKTEST:
                        sleep(1)
                    continue
                
                _order_id = _order.get('orderId', '')
                _ordered_maker_price = current_maker_price
                self.logger.debug(f"Maker order placed: ID={_order_id}, Price={current_maker_price}")
            else:
                self.logger.debug("Maker price unchanged. Keep monitoring order.")
            
            # Wait before checking order status (skip in backtest mode)
            if self.bot_config.run_mode != RunMode.BACKTEST:
                sleep(LIMIT_ORDER_PRICE_CHECK_INTERVAL)
            
            # Check if order filled
            _check_order = self.trade_client.fetch_order(symbol=self.bot_config.symbol, order_id=_order_id)
            _order_status = _check_order.get('status', '')
            _executed_qty = float(_check_order.get('executedQty', 0))
            
            if _order_status == ORDER_STATUS_FILLED:
                _total_filled_qty += _executed_qty
                self.logger.info(f"Maker Order filled: {_executed_qty}, total: {_total_filled_qty}/{_target_quantity}")
                _order_filled = True
                break
            elif _order_status == 'PARTIALLY_FILLED':
                self.logger.debug(f"Maker Order partially filled: {_executed_qty}/{_remaining_quantity}")
                # Continue loop to check if price changed and handle partial fill
            else:
                self.logger.debug("Maker Order still pending")
        
        # Fetch all trades for all orders to get complete trade history
        self.logger.debug(f'Getting trade history for symbol: {self.bot_config.symbol}')
        return self.trade_client.fetch_order_trade(symbol=self.bot_config.symbol, order_id=_order_id)

    def place_order_to_open_position(self, position_side: PositionSide) -> Dict[str, Any]:
        """
        Place an order to open a new position.
        
        Args:
            position_side: Position side to open (LONG/SHORT)
        
        Returns:
            New position dictionary with entry details
        """
        _order_side = OrderSide.BUY.value if position_side == PositionSide.LONG else OrderSide.SELL.value
        _order_trade = None

        if self.bot_config.order_type == OrderType.MARKET:
            _order_trade = self.place_market_order(order_side=_order_side, reduce_only=False)
        elif self.bot_config.order_type == OrderType.MAKER_ONLY:
            _order_trade = self.place_maker_only_order(order_side=_order_side, reduce_only=False)
        else:  # LIMIT
            _order_trade = self.place_limit_order(order_side=_order_side, reduce_only=False)

        self.logger.debug(message=f'Order Trade: {_order_trade}')

        new_position_dict: dict = self.trade_client.fetch_position(
            symbol=self.bot_config.symbol)
        if not new_position_dict:
            self.logger.critical(
                message=f'💥 Failed to place order to binance!')
            raise Exception('💥 Failed to place order to binance!')
        
        new_position_dict['open_fee'] = _order_trade['fee']
        self.logger.info(
            message=f"{self.bot_config.symbol} | {'OPEN':<5} | {position_side.value:<5} | {new_position_dict['entry_price']}")
        return new_position_dict

    def place_order_to_close_position(self, position_dict: dict) -> Dict[str, Any]:
        """
        Place an order to close an existing position.
        
        Args:
            position_dict: Current position details
        
        Returns:
            Closed position dictionary with exit details
        
        Raises:
            ValueError: If position doesn't exist on exchange
        """
        # Verify position still exists on exchange before placing reduce_only order
        remote_position = self.trade_client.fetch_position(symbol=self.bot_config.symbol)
        if not remote_position:
            self.logger.error("Cannot close position - no position exists on exchange")
            raise ValueError("Position already closed on exchange")
        
        _order_side = OrderSide.BUY.value if position_dict['position_side'] == PositionSide.SHORT else OrderSide.SELL.value
        _order_trade = None

        self.logger.debug(message='Placing order to close position')
    
        if self.bot_config.order_type == OrderType.MARKET:
            _order_trade = self.place_market_order(order_side=_order_side, reduce_only=True)
        elif self.bot_config.order_type == OrderType.MAKER_ONLY:
            _order_trade = self.place_maker_only_order(order_side=_order_side, reduce_only=True)
        else:  # LIMIT
            _order_trade = self.place_limit_order(order_side=_order_side, reduce_only=True)

        self.logger.debug(message=f'Order Trade: {_order_trade}')

        closed_position_dict = {
            'close_price': _order_trade['price'],
            'close_fee': _order_trade['fee'],
            'pnl': _order_trade['pnl']
        }
        
        # Clear cached quantity after closing position
        self.clear_cached_quantity()

        self.logger.info(
            message=f"{self.bot_config.symbol} | {'CLOSE':<5} | {position_dict['position_side'].value:<5} | {position_dict['entry_price']:.4f} -> {_order_trade['price']:.4f} | {'+' if _order_trade['pnl'] >= 0 else ''}{_order_trade['pnl']:.4f}")
        return closed_position_dict

    def cancel_tp_order(self) -> None:
        """Cancel the active take profit order."""
        order_id = self.position_handler.get_tp_order_id()
        if order_id:
            self.trade_client.cancel_algorithmic_order(order_id=order_id)

    def cancel_sl_order(self) -> None:
        """Cancel the active stop loss order."""
        order_id = self.position_handler.get_sl_order_id()
        if order_id:
            self.trade_client.cancel_algorithmic_order(order_id=order_id)

    def monitor_tp_sl_fill(self, close_candle_open_time: str = '', backtest_metrics=None) -> bool:
        """
        Monitor TP/SL orders and close position if any is filled.
        
        Scenarios:
        1. Both TP and SL enabled: only one can hit; cancel the other.
        2. Only one order enabled: works normally.
        
        Args:
            close_candle_open_time: Candle open time for close timestamp
            backtest_metrics: Optional backtest metrics object to track trades
        
        Returns:
            True if position was closed, False otherwise
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
                if self.bot_config.run_mode == RunMode.BACKTEST:
                    closed_position_dict['close_time'] = close_candle_open_time

                trade_dict = self.position_handler.close_position(position_dict=closed_position_dict)
                self.position_handler.clear_tp_sl_orders()
                
                # Clear cached quantity after closing position
                self.clear_cached_quantity()
                
                # Track trade for backtest
                if backtest_metrics and trade_dict:
                    backtest_metrics.add_trade(trade_dict)

                self.logger.info(
                    message=f"{self.bot_config.symbol} | {'CLOSE':<5} | {order_trade['side']:<5} | {self.position_handler.entry_price:.4f} -> {order_trade['price']:.4f} | {'+' if order_trade['pnl'] >= 0 else ''}{order_trade['pnl']:.4f}")
            
            except (KeyError, ValueError, TypeError) as e:
                self.logger.error_e(
                    message='Error while processing filled TP/SL order', e=e)
                return False

            return True

        return False


# EOF

# Made with Bob
