"""
Binance Backtest Trade Client
Simulates Binance API responses using cached historical data.
Only fetches klines from Binance; all other operations are simulated.
"""
from pandas.core.frame import DataFrame


import requests
import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime

from abstracts.base_backtest_trade_client import BaseBacktestTradeClient
from commons.custom_logger import CustomLogger
from models.enum.position_side import PositionSide
import trade_clients.binance.binance_auth as binance_auth
from commons.fee_calculator import calculate_open_fee, calculate_close_fee

GET_KLINES_URL = 'https://fapi.binance.com/fapi/v1/klines'
GET_EXCHANGE_INFO_URL = 'https://fapi.binance.com/fapi/v1/exchangeInfo'


class BinanceBacktestTradeClient(BaseBacktestTradeClient):
    """
    Backtest trade client that simulates Binance API responses.
    Fetches real klines data but simulates all trading operations.
    """
    
    def __init__(self, logger: Optional[CustomLogger] = None) -> None:
        super().__init__(logger=logger)
        self.set_wait_time(wait_time_sec=0)  # No wait time for backtest
        self.set_running(running=True)
        
        # Klines cache - stores all historical data
        self.klines_cache: Optional[pd.DataFrame] = None
        self.current_candle_index = 0  # Current position in backtest
        
        # Exchange info cache
        self._exchange_info_cache: Dict[str, Dict[str, Any]] = {}
        
        # Simulated position state
        self.simulated_position: Optional[Dict[str, Any]] = None
        
        # Simulated TP/SL orders
        self.simulated_tp_order: Optional[Dict[str, Any]] = None
        self.simulated_sl_order: Optional[Dict[str, Any]] = None
        self.last_closed_position: Optional[Dict[str, Any]] = None
        
        # Track candle index when TP/SL orders were placed
        self.tp_sl_placement_candle_index: Optional[int] = None
        
        # Trading parameters (set during preload)
        self.order_type: str = 'MAKER_ONLY'
        self.leverage: int = 1
        
        # Credentials for data fetching
        self.__creds = None
    
    def init(self):
        """Initialize Binance credentials for data fetching."""
        self.__creds = binance_auth.load_binance_cred()
        self.logger.debug(message=f"Initialized {self.__class__.__name__}")
    
    def preload_historical_data(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 1500,
        order_type: str = 'MAKER_ONLY',
        leverage: int = 1
    ) -> None:
        """
        Preload historical klines data from Binance.
        This is called once before backtest starts.
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe interval
            limit: Number of candles to fetch (max 1500)
            order_type: Order type for fee calculation
            leverage: Position leverage
        """
        self.logger.info(f"Preloading {limit} historical candles for {symbol} {timeframe}")
        
        # Store trading parameters for fee calculation
        self.order_type = order_type
        self.leverage = leverage
        
        params = {
            'symbol': symbol,
            'interval': timeframe,
            'limit': min(limit, 1500)
        }
        
        headers, signed_params = binance_auth.sign_request(
            params=params,
            binance_credential=self.__creds
        )
        
        try:
            response = requests.get(
                url=GET_KLINES_URL,
                headers=headers,
                params=signed_params
            )
            response.raise_for_status()
            data = response.json()
            
            # Define column names for Binance klines data
            klines_columns = [
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'num_trades',
                'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
            ]
            
            # Create DataFrame - pass data as first positional arg, columns as keyword arg
            df = pd.DataFrame(data, columns=klines_columns)  # type: ignore[call-overload]
            
            # Convert timestamps
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Bangkok')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Bangkok')
            
            # Convert price columns to float
            for col in ['high', 'low', 'close', 'open', 'volume']:
                df[col] = df[col].astype(float)

            self.klines_cache = df
            self.logger.info(f"Preloaded {len(df)} candles from {df.iloc[0]['open_time']} to {df.iloc[-1]['open_time']}")
            
        except Exception as e:
            self.logger.error_e(message="Failed to preload historical data", e=e)
            raise
    
    def advance_candle(self) -> bool:
        """
        Advance to next candle in backtest.
        
        Returns:
            True if advanced successfully, False if reached end
        """
        if self.klines_cache is None:
            return False
        
        self.current_candle_index += 1
        
        if self.current_candle_index >= len(self.klines_cache):
            self.logger.info("Reached end of historical data")
            self.set_running(False)
            return False
        
        # Check and auto-trigger TP/SL after advancing to new candle
        self._check_and_trigger_tp_sl()
        
        return True
    
    def _check_and_trigger_tp_sl(self) -> None:
        """
        Automatically check if TP/SL should be triggered based on current candle.
        This simulates Binance's automatic TP/SL execution.
        
        Called automatically after advancing to a new candle.
        """
        if not self.simulated_position:
            return
        
        # Don't check on the same candle where TP/SL were placed
        if self.tp_sl_placement_candle_index is not None and self.current_candle_index == self.tp_sl_placement_candle_index:
            return
        
        current_candle = self.get_current_candle()
        if current_candle is None:
            return
        
        position_side = self.simulated_position['position_side']
        candle_high = current_candle['high']
        candle_low = current_candle['low']
        
        # Check SL first (stop loss has priority)
        if self.simulated_sl_order:
            sl_trigger_price = self.simulated_sl_order['triggerPrice']
            sl_triggered = False
            
            if position_side == PositionSide.LONG:
                # For LONG: SL triggers if price drops to or below SL
                if candle_low <= sl_trigger_price:
                    sl_triggered = True
            else:  # SHORT
                # For SHORT: SL triggers if price rises to or above SL
                if candle_high >= sl_trigger_price:
                    sl_triggered = True
            
            if sl_triggered:
                self.logger.info(f"[BACKTEST] SL auto-triggered @ {sl_trigger_price} on candle {self.current_candle_index}")
                # Mark SL as triggered by updating its status
                self.simulated_sl_order['algoStatus'] = 'FINISHED'
                self.simulated_sl_order['actualOrderId'] = f"sl_filled_{self.current_candle_index}"
                
                # Close position at SL price
                self._close_position_at_price(sl_trigger_price, 'SL')
                
                # Cancel TP order if exists
                if self.simulated_tp_order:
                    self.simulated_tp_order = None
                    self.logger.debug("[BACKTEST] TP order auto-cancelled due to SL trigger")
                
                return  # SL triggered, don't check TP
        
        # Check TP only if SL didn't trigger
        if self.simulated_tp_order:
            tp_trigger_price = self.simulated_tp_order['triggerPrice']
            tp_triggered = False
            
            if position_side == PositionSide.LONG:
                # For LONG: TP triggers if price rises to or above TP
                if candle_high >= tp_trigger_price:
                    tp_triggered = True
            else:  # SHORT
                # For SHORT: TP triggers if price drops to or below TP
                if candle_low <= tp_trigger_price:
                    tp_triggered = True
            
            if tp_triggered:
                self.logger.info(f"[BACKTEST] TP auto-triggered @ {tp_trigger_price} on candle {self.current_candle_index}")
                # Mark TP as triggered
                self.simulated_tp_order['algoStatus'] = 'FINISHED'
                self.simulated_tp_order['actualOrderId'] = f"tp_filled_{self.current_candle_index}"
                
                # Close position at TP price
                self._close_position_at_price(tp_trigger_price, 'TP')
                
                # Cancel SL order if exists
                if self.simulated_sl_order:
                    self.simulated_sl_order = None
                    self.logger.debug("[BACKTEST] SL order auto-cancelled due to TP trigger")
    
    def _close_position_at_price(self, close_price: float, reason: str) -> None:
        """
        Close the simulated position at a specific price.
        
        Args:
            close_price: Price at which position is closed
            reason: Reason for closing ('TP' or 'SL')
        """
        if not self.simulated_position:
            return
        
        # Store position data before closing
        self.last_closed_position = {
            'entry_price': self.simulated_position['entry_price'],
            'quantity': abs(self.simulated_position['quantity']),
            'position_side': self.simulated_position['position_side'],
            'close_price': close_price,
            'close_reason': reason
        }
        
        # Clear position
        self.simulated_position = None
        self.tp_sl_placement_candle_index = None
        
        self.logger.debug(f"[BACKTEST] Position closed at {close_price} due to {reason}")
    
    def get_current_candle(self) -> Optional[pd.Series]:
        """Get current candle in backtest."""
        if self.klines_cache is None or self.current_candle_index >= len(self.klines_cache):
            return None
        return self.klines_cache.iloc[self.current_candle_index]
    
    # ========== Simulated Binance API Methods ==========
    
    def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """Simulate setting leverage."""
        self.logger.debug(f"[BACKTEST] Set leverage {symbol} to {leverage}")
        return {'leverage': leverage, 'symbol': symbol}
    
    def fetch_position(self, symbol: str) -> Dict[str, Any]:
        """
        Return simulated position state.
        Calculates current PnL based on current candle price.
        """
        if self.simulated_position is None:
            return {}
        
        # Update PnL with current price
        current_candle = self.get_current_candle()
        if current_candle is not None:
            current_price = current_candle['close']
            entry_price = self.simulated_position['entry_price']
            quantity = abs(self.simulated_position['quantity'])
            position_side = self.simulated_position['position_side']
            
            # Calculate unrealized PnL
            if position_side == PositionSide.LONG:
                pnl = (current_price - entry_price) * quantity
            else:  # SHORT
                pnl = (entry_price - current_price) * quantity
            
            self.simulated_position['pnl'] = pnl
            self.simulated_position['mark_price'] = current_price
        
        return self.simulated_position.copy()
    
    def fetch_price(self, symbol: str) -> float:
        """Return current candle's close price."""
        current_candle = self.get_current_candle()
        if current_candle is None:
            return 0.0
        return float(current_candle['close'])
    
    def fetch_klines(
        self,
        symbol: str,
        timeframe: str,
        timeframe_limit: int = 100
    ) -> pd.DataFrame:
        """
        Return klines from cache up to current candle.
        Simulates fetching recent klines as bot would do in live mode.
        """
        if self.klines_cache is None:
            raise RuntimeError("No klines cached. Call preload_historical_data first.")
        
        # Return window ending at current candle
        end_idx = self.current_candle_index + 1
        start_idx = max(0, end_idx - timeframe_limit)
        
        df = self.klines_cache.iloc[start_idx:end_idx].copy()
        
        # Add current_price column (last candle uses close price)
        df['current_price'] = df['close']
        if len(df) > 0:
            df.loc[df.index[-1], 'current_price'] = df.iloc[-1]['close']
        
        return df
    
    def place_order(
        self,
        symbol: str,
        order_side: str,
        order_type: str,
        quantity: float,
        price: float = 0,
        reduce_only: bool = False,
        time_in_force: str = "GTC"
    ) -> Dict[str, Any]:
        """
        Simulate placing an order.
        Immediately fills at current candle's close price.
        """
        current_candle = self.get_current_candle()
        if current_candle is None:
            return {}
        
        execution_price = price if price > 0 else current_candle['close']
        order_id = f"backtest_{self.current_candle_index}_{order_side}"
        
        self.logger.debug(
            f"[BACKTEST] {order_type} {order_side} order: {quantity} @ {execution_price}"
        )
        
        # If opening position, create simulated position
        if not reduce_only:
            position_side = PositionSide.LONG if order_side == 'BUY' else PositionSide.SHORT
            signed_quantity = quantity if order_side == 'BUY' else -quantity
            
            self.simulated_position = {
                'symbol': symbol,
                'quantity': signed_quantity,
                'position_side': position_side,
                'entry_price': execution_price,
                'pnl': 0.0,
                'mark_price': execution_price
            }
        else:
            # Closing position - store last position data for PnL calculation
            if self.simulated_position:
                self.last_closed_position = {
                    'entry_price': self.simulated_position['entry_price'],
                    'quantity': abs(self.simulated_position['quantity']),
                    'position_side': self.simulated_position['position_side'],
                    'close_price': execution_price
                }
            self.simulated_position = None
        
        return {
            'orderId': order_id,
            'symbol': symbol,
            'status': 'FILLED',
            'side': order_side,
            'type': order_type,
            'price': execution_price,
            'executedQty': quantity
        }
    
    def fetch_order(self, symbol: str, order_id: str = '') -> Dict[str, Any]:
        """Simulate fetching order - always returns FILLED."""
        return {
            'orderId': order_id,
            'status': 'FILLED',
            'symbol': symbol
        }
    
    def cancel_order(self, symbol: str, order_id: str = '') -> Dict[str, Any]:
        """Simulate canceling order."""
        self.logger.debug(f"[BACKTEST] Cancel order {order_id}")
        return {'orderId': order_id, 'status': 'CANCELED'}
    
    def place_algorithmic_order(
        self,
        symbol: str,
        order_side: str,
        order_type: str,
        quantity: float,
        trigger_price: float
    ) -> Dict[str, Any]:
        """
        Simulate placing TP/SL order.
        Stores order for checking in subsequent candles.
        """
        algo_id = f"backtest_algo_{self.current_candle_index}_{order_type}"
        
        order = {
            'algoId': algo_id,
            'symbol': symbol,
            'side': order_side,
            'type': order_type,
            'quantity': quantity,
            'triggerPrice': trigger_price,
            'algoStatus': 'WORKING'
        }
        
        if 'TAKE_PROFIT' in order_type:
            self.simulated_tp_order = order
            self.tp_sl_placement_candle_index = self.current_candle_index
            self.logger.debug(f"[BACKTEST] TP order placed @ {trigger_price} on candle {self.current_candle_index}")
        elif 'STOP' in order_type:
            self.simulated_sl_order = order
            self.tp_sl_placement_candle_index = self.current_candle_index
            self.logger.debug(f"[BACKTEST] SL order placed @ {trigger_price} on candle {self.current_candle_index}")
        
        return order
    
    def fetch_algorithmic_order(self, order_id: str) -> Dict[str, Any]:
        """
        Check if TP/SL order was triggered.
        
        In backtest mode, TP/SL orders are automatically triggered by _check_and_trigger_tp_sl()
        when advancing candles. This method just returns the current status.
        """
        # Check TP order status
        if self.simulated_tp_order and self.simulated_tp_order['algoId'] == order_id:
            status = self.simulated_tp_order.get('algoStatus', 'WORKING')
            if status == 'FINISHED':
                return {
                    'algoId': order_id,
                    'algoStatus': 'FINISHED',
                    'actualOrderId': self.simulated_tp_order.get('actualOrderId', f"tp_filled_{self.current_candle_index}")
                }
            return {'algoId': order_id, 'algoStatus': 'WORKING'}
        
        # Check SL order status
        if self.simulated_sl_order and self.simulated_sl_order['algoId'] == order_id:
            status = self.simulated_sl_order.get('algoStatus', 'WORKING')
            if status == 'FINISHED':
                return {
                    'algoId': order_id,
                    'algoStatus': 'FINISHED',
                    'actualOrderId': self.simulated_sl_order.get('actualOrderId', f"sl_filled_{self.current_candle_index}")
                }
            return {'algoId': order_id, 'algoStatus': 'WORKING'}
        
        return {'algoId': order_id, 'algoStatus': 'WORKING'}
    
    def cancel_algorithmic_order(self, order_id: str) -> Dict[str, Any]:
        """Simulate canceling TP/SL order."""
        if self.simulated_tp_order and self.simulated_tp_order['algoId'] == order_id:
            self.simulated_tp_order = None
            self.logger.debug(f"[BACKTEST] TP order canceled")
        
        if self.simulated_sl_order and self.simulated_sl_order['algoId'] == order_id:
            self.simulated_sl_order = None
            self.logger.debug(f"[BACKTEST] SL order canceled")
        
        # Reset placement candle index if both orders are cancelled
        if self.simulated_tp_order is None and self.simulated_sl_order is None:
            self.tp_sl_placement_candle_index = None
        
        return {'algoId': order_id, 'algoStatus': 'CANCELLED'}
    
    def fetch_trades(
        self,
        symbol: str = '',
        order_id: str = ''
    ) -> Dict[str, Any]:
        """Simulate fetching trades."""
        return {}
    
    def fetch_order_trade(
        self,
        symbol: str = '',
        order_id: str = ''
    ) -> Dict[str, Any]:
        """
        Simulate fetching trade details for an order.
        Returns execution price, calculates PnL and fees.
        """
        current_candle = self.get_current_candle()
        if current_candle is None:
            return {}
        
        execution_price: float = float(current_candle['close'])
        
        # Determine if this is TP/SL fill
        if 'tp_filled' in order_id or 'sl_filled' in order_id:
            # Use trigger price for TP/SL
            if self.simulated_tp_order:
                execution_price = self.simulated_tp_order['triggerPrice']
            elif self.simulated_sl_order:
                execution_price = self.simulated_sl_order['triggerPrice']
        
        # Calculate PnL and fees if closing position
        pnl = 0.0
        fee = 0.0
        position_data = self.simulated_position or self.last_closed_position
        
        if position_data:
            entry_price = position_data['entry_price']
            quantity = abs(position_data.get('quantity', 0))
            position_side = position_data['position_side']
            
            # Use stored close_price if available, otherwise use execution_price
            close_price = position_data.get('close_price', execution_price)
            
            # Calculate gross PnL
            if position_side == PositionSide.LONG:
                pnl = (close_price - entry_price) * quantity
            else:
                pnl = (entry_price - close_price) * quantity
            
            # Calculate fee based on order type
            # Determine if this is opening or closing
            is_closing = 'close_price' in position_data or self.last_closed_position is not None
            
            if is_closing:
                fee = calculate_close_fee(
                    order_type=self.order_type,
                    close_price=close_price,
                    quantity=quantity,
                    leverage=self.leverage
                )
            else:
                fee = calculate_open_fee(
                    order_type=self.order_type,
                    entry_price=execution_price,
                    quantity=quantity,
                    leverage=self.leverage
                )
        
        side = 'SELL' if 'SELL' in order_id or (position_data and position_data['position_side'] == PositionSide.LONG) else 'BUY'
        
        return {
            'price': execution_price,
            'side': side,
            'fee': fee,
            'pnl': pnl
        }
    
    def fetch_order_book(self, symbol: str, limit: int = 5) -> Dict[str, Any]:
        """Simulate order book with current price."""
        current_candle = self.get_current_candle()
        if current_candle is None:
            return {'bids': [], 'asks': []}
        
        price = current_candle['close']
        return {
            'bids': [[price, 1000.0]],
            'asks': [[price, 1000.0]]
        }
    
    def fetch_exchange_info(self, symbol: str) -> Dict[str, Any]:
        """Fetch and cache exchange info."""
        if symbol in self._exchange_info_cache:
            return self._exchange_info_cache[symbol]
        
        self.logger.debug(f"Fetching exchange info for {symbol}")
        
        params = {'symbol': symbol}
        headers, signed_params = binance_auth.sign_request(
            params=params,
            binance_credential=self.__creds
        )
        
        try:
            response = requests.get(
                url=GET_EXCHANGE_INFO_URL,
                headers=headers,
                params=signed_params
            )
            response.raise_for_status()
            data = response.json()
            
            for symbol_info in data.get('symbols', []):
                if symbol_info['symbol'] == symbol:
                    tick_size = 0.01
                    step_size = 0.01
                    
                    for filter_item in symbol_info.get('filters', []):
                        if filter_item['filterType'] == 'PRICE_FILTER':
                            tick_size = float(filter_item['tickSize'])
                        elif filter_item['filterType'] == 'LOT_SIZE':
                            step_size = float(filter_item['stepSize'])
                    
                    exchange_info = {
                        'symbol': symbol,
                        'tickSize': tick_size,
                        'stepSize': step_size
                    }
                    
                    self._exchange_info_cache[symbol] = exchange_info
                    return exchange_info
            
            return {}
            
        except Exception as e:
            self.logger.error_e(message=f"Failed to fetch exchange info", e=e)
            return {}
    
    def has_exchange_info_cached(self, symbol: str) -> bool:
        """Check if exchange info is cached."""
        return symbol in self._exchange_info_cache
    
    def get_cached_exchange_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached exchange info."""
        return self._exchange_info_cache.get(symbol)


# EOF

# Made with Bob

