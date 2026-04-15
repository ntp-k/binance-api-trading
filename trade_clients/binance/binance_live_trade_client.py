import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import pandas as pd
from typing import Optional, Dict, Any

from abstracts.base_live_trade_client import BaseLiveTradeClient
from models.enum.position_side import PositionSide
import trade_clients.binance.binance_auth as binance_auth
from models.enum.order_type import OrderType

SET_LEVERAGE_URL = 'https://fapi.binance.com/fapi/v1/leverage'
GET_POSITION_URL = 'https://fapi.binance.com/fapi/v2/positionRisk'
SET_ORDER_URL = 'https://fapi.binance.com/fapi/v1/order'
SET_ALGO_ORDER_URL = 'https://fapi.binance.com/fapi/v1/algoOrder'
GET_KLINES_URL = 'https://fapi.binance.com/fapi/v1/klines'
GET_TICKER_PRICE_URL = 'https://fapi.binance.com/fapi/v1/ticker/price'
GET_ORDER = 'https://fapi.binance.com/fapi/v1/order'
GET_TRADE = 'https://fapi.binance.com/fapi/v1/userTrades'
GET_ORDER_BOOK_URL = 'https://fapi.binance.com/fapi/v1/depth'
GET_EXCHANGE_INFO_URL = 'https://fapi.binance.com/fapi/v1/exchangeInfo'

API_WEIGHT_LIMIT = 2000
API_ORDER_10s_LIMIT = 50
API_ORDER_1m_LIMIT = 1600

class BinanceLiveTradeClient(BaseLiveTradeClient):
    def __init__(self) -> None:
        super().__init__()
        self.set_wait_time(wait_time_sec=20)
        self.set_running(running=True)
        
        # Initialize session with connection pooling and retry strategy
        self.session = self._create_session()
        
        # Cache for exchange info to avoid repeated API calls
        self._exchange_info_cache: Dict[str, Dict[str, Any]] = {}
    
    def _create_session(self) -> requests.Session:
        """Create requests session with connection pooling and retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "DELETE"]
        )
        
        # Mount adapter with retry strategy
        adapter = HTTPAdapter(
            pool_connections=8,
            pool_maxsize=16,
            max_retries=retry_strategy
        )
        session.mount("https://", adapter)
        
        return session
    
    def init(self):
        """Initialize Binance credentials."""
        self.__creds = binance_auth.load_binance_cred()
        self.logger.debug(message=f"Initialized {self.__class__.__name__}")
    
    def _get_timestamp(self) -> int:
        """Get current timestamp in milliseconds."""
        return int(time.time() * 1000)
    
    def _make_request(
        self,
        method: str,
        url: str,
        params: Dict[str, Any],
        operation: str
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Binance API.
        
        Args:
            method: HTTP method ('GET', 'POST', 'DELETE')
            url: API endpoint URL
            params: Request parameters
            operation: Description of operation for logging
        
        Returns:
            Response dictionary or empty dict on error
        """
        headers, signed_params = binance_auth.sign_request(
            params=params,
            binance_credential=self.__creds
        )
        
        try:
            if method == 'GET':
                response = self.session.get(url=url, headers=headers, params=signed_params)
            elif method == 'POST':
                response = self.session.post(url=url, headers=headers, params=signed_params)
            elif method == 'DELETE':
                response = self.session.delete(url=url, headers=headers, params=signed_params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.HTTPError as e:
            self.logger.error_e(message=f"HTTP error during {operation}", e=e)
            self.logger.error(message=f"Response: {response.text}")
            return {}
        except requests.exceptions.RequestException as e:
            self.logger.error_e(message=f"Network error during {operation}", e=e)
            return {}
        except Exception as e:
            self.logger.error_e(message=f"Unexpected error during {operation}", e=e)
            return {}

    def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """
        Change leverage for a given futures trading pair on Binance.
        
        Args:
            symbol: Trading pair symbol
            leverage: Leverage multiplier (1-125)
        
        Returns:
            Response dictionary from Binance
        """
        self.logger.debug(message=f"Setting leverage for {symbol} to {leverage}")
        
        params = {
            "timestamp": self._get_timestamp(),
            "symbol": symbol.upper(),
            "leverage": leverage
        }
        
        result = self._make_request('POST', SET_LEVERAGE_URL, params, "set leverage")
        if result:
            self.logger.debug(message=f"Leverage set successfully: {result}")
        return result

    def fetch_position(self, symbol: str) -> Dict[str, Any]:
        """
        Get the current futures position for a given symbol.
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            Dictionary with position details or empty dict if no position
        """
        params = {'timestamp': self._get_timestamp()}
        positions = self._make_request('GET', GET_POSITION_URL, params, "fetch position")
        
        if not positions:
            return {}
        
        for pos in positions:
            if pos['symbol'] == symbol:
                position_amt = float(pos['positionAmt'])
                if position_amt == 0:
                    continue
                
                pnl = float(pos['unRealizedProfit'])
                position_side = PositionSide.LONG if position_amt >= 0 else PositionSide.SHORT
                
                self.logger.info(
                    message=f"Position found: {pos['symbol']} | {position_side.value} | "
                    f"{'+' if pnl >= 0 else ''}{pnl:.2f}"
                )
                
                return {
                    'symbol': pos['symbol'],
                    'quantity': position_amt,
                    'position_side': position_side,
                    'entry_price': float(pos['entryPrice']),
                    'pnl': pnl,
                    'mark_price': float(pos['markPrice'])
                }
        
        self.logger.debug(message=f"No active position found for {symbol}")
        return {}

    def fetch_price(self, symbol: str, use_cache: bool = True) -> float:
        """
        Fetch current price with optional caching to reduce API calls.
        
        Args:
            symbol: Trading pair symbol
            use_cache: Whether to use cached price if available and fresh
        
        Returns:
            Current market price
        """
        
        # Fetch fresh price
        params = {'symbol': symbol}
        headers, signed_params = binance_auth.sign_request(params=params, binance_credential=self.__creds)
        try:
            response = self.session.get(url=GET_TICKER_PRICE_URL, headers=headers, params=signed_params)
            response.raise_for_status()
            current_price = float(response.json()["price"])

            return current_price
        except Exception as e:
            self.logger.error_e(message=f"error getting price", e=e)
            return 0.0

    def fetch_klines(self, symbol, timeframe, timeframe_limit=100):
        df = None

        # fetch klines
        params = {
            'symbol': symbol,
            'interval': timeframe,
            'limit': timeframe_limit
        }
        # self.logger.debug(message=f'Fetching Klines of {params}')

        headers, signed_params = binance_auth.sign_request(params=params, binance_credential=self.__creds)
        try:
            response = self.session.get(url=GET_KLINES_URL, headers=headers, params=signed_params)
            response.raise_for_status()

            used_weight_1m = response.headers.get("X-MBX-USED-WEIGHT-1M", 0)
            order_count_10s = response.headers.get("X-MBX-ORDER-COUNT-10S", 0)
            order_count_1m = response.headers.get("X-MBX-ORDER-COUNT-1M", 0)

            self.logger.debug(
                message=f"[RATE LIMIT] weight_1m={used_weight_1m}/{API_WEIGHT_LIMIT}, orders_10s={order_count_10s}/{API_ORDER_10s_LIMIT}, orders_1m={order_count_1m}/{API_ORDER_1m_LIMIT}"
            )

            data = response.json()
            # Define column names for Binance klines data
            klines_columns = [
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'num_trades',
                'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
            ]
            
            # Create DataFrame - pass data as first positional arg, columns as keyword arg
            df = pd.DataFrame(data, columns=klines_columns)  # type: ignore[call-overload]

            df['open_time'] = pd.to_datetime(arg=df['open_time'], unit='ms').dt.tz_localize(tz='UTC').dt.tz_convert(tz='Asia/Bangkok') # type: ignore
            df['close_time'] = pd.to_datetime(arg=df['close_time'], unit='ms').dt.tz_localize(tz='UTC').dt.tz_convert(tz='Asia/Bangkok') # type: ignore
            df['high'] = df['high'].astype(dtype=float)
            df['low'] = df['low'].astype(dtype=float)
            df['close'] = df['close'].astype(dtype=float)
            df['open'] = df['open'].astype(dtype=float)
            # self.logger.debug(message=f"Fetched {len(df)} Klines for {symbol} at {timeframe} interval.")
        except requests.exceptions.HTTPError as e:
            self.logger.error_e(message=f"HTTP error getting Klines", e=e)
            self.logger.debug(message=f"Response: {response.text}") # type: ignore
            return df
        except requests.exceptions.RequestException as e:
            self.logger.error_e(message=f"Network error getting Klines", e=e)
            return df

        # fetch current price
        current_price = self.fetch_price(symbol=symbol)
        df["current_price"] = df["close"]
        df.loc[df.index[-1], "current_price"] = current_price

        return df 

    def fetch_order(self, symbol: str, order_id: str = '') -> Dict[str, Any]:
        """Fetch order details by order ID."""
        params = {
            'symbol': symbol,
            'orderId': order_id,
            'timestamp': self._get_timestamp()
        }
        result = self._make_request('GET', GET_ORDER, params, "fetch order")
        if result:
            self.logger.debug(message=f"Order fetched: {result}")
        return result

    def cancel_order(self, symbol: str, order_id: str = '') -> Dict[str, Any]:
        """Cancel an existing order."""
        params = {
            'symbol': symbol,
            'orderId': order_id,
            'timestamp': self._get_timestamp()
        }
        return self._make_request('DELETE', GET_ORDER, params, "cancel order")

    def place_order(self, symbol: str, order_side: str, order_type: str, quantity: float,
                    price: float = 0, reduce_only: bool = False, time_in_force: str = "GTC", close_position: bool = False, stop_price: float = -1) -> dict:
        """
        Place a futures order on Binance USDT-Margined Futures.

        Args:
            symbol (str): Trading symbol (e.g., 'BTCUSDT').
            order_side (str): 'BUY' or 'SELL'.
            order_type (str): 'MARKET' or 'LIMIT'.
            quantity (float): Order quantity.
            price (float, optional): Required for LIMIT orders.
            reduce_only (bool): True will ensures your order will only reduce, close, or flatten an existing position.
            time_in_force (str, optional): Default is 'GTC' (Good Till Cancelled).

        Returns:
            dict or None: Response from Binance API.
        """

        self.logger.debug(message=f"Placing order: {order_type} {order_side} {quantity} {symbol} (reduce_only={reduce_only})")

        # Base parameters
        params = {
            'symbol': symbol.upper(),
            'side': order_side.upper(),
            'type': order_type.upper(),
            'reduceOnly': reduce_only,
            'quantity': quantity,
            'timestamp': int(time.time() * 1000)
        }

        if order_type == OrderType.LIMIT.value:
            if not price:
                raise ValueError("Price must be specified for LIMIT orders.")
            params.update({
                'price': price,
                'timeInForce': time_in_force
            })

        headers, signed_params = binance_auth.sign_request(params=params, binance_credential=self.__creds)
        try:
            response = self.session.post(url=SET_ORDER_URL, headers=headers, params=signed_params)
            response.raise_for_status()
            self.logger.debug(message=f"Order placed: {response.json()}")
            return response.json()
        except requests.exceptions.HTTPError as e:
            self.logger.error_e(message=f"Error placing order", e=e)
            self.logger.error(message=f"Response: {response.text}") # type: ignore
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error_e(message=f"Network error placing order", e=e)
            return False

    def fetch_algorithmic_order(self, order_id: str) -> dict:
        # Base parameters
        params = {
            'algoId': order_id,
            'timestamp': int(time.time() * 1000)
        }

        headers, signed_params = binance_auth.sign_request(params=params, binance_credential=self.__creds)
        try:
            response = self.session.get(url=SET_ALGO_ORDER_URL, headers=headers, params=signed_params)
            response.raise_for_status()
            self.logger.debug(message=f"Order fetched: {response.json()}")
            return response.json()
        except requests.exceptions.HTTPError as e:
            self.logger.error_e(message=f"Error getting algo order", e=e)
            self.logger.error(message=f"Response: {response.text}") # type: ignore
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error_e(message=f"Network error getting algo order", e=e)
            return False

    def cancel_algorithmic_order(self, order_id: str):
        params = {
            'algoId': order_id,
            'timestamp': int(time.time() * 1000)
        }
        headers, signed_params = binance_auth.sign_request(params=params, binance_credential=self.__creds)
        try:
            response = self.session.delete(url=SET_ALGO_ORDER_URL, headers= headers, params=signed_params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error_e(message=f"error canceling algo order", e=e)
            return {}

    def place_algorithmic_order(self, symbol: str, order_side: str, order_type: str,
                               quantity: float, trigger_price: float) -> Dict[str, Any]:
        """Place an algorithmic order (conditional order) on Binance Futures."""
        params = {
            'algoType': 'CONDITIONAL',
            'symbol': symbol.upper(),
            'side': order_side.upper(),
            'type': order_type.upper(),
            'timestamp': self._get_timestamp()
        }

        # Configure order based on type
        if order_type == OrderType.STOP_MARKET.value or order_type == OrderType.TAKE_PROFIT_MARKET.value:
            params.update({
                'triggerPrice': trigger_price,
                'closePosition': 'true'
            })
        else:
            params.update({
                'quantity': quantity,
                'reduceOnly': 'true',
            })

        result = self._make_request('POST', SET_ALGO_ORDER_URL, params, "place algo order")
        if result:
            self.logger.debug(message=f"Algo order placed: {result}")
        return result

    def fetch_trades(self, symbol: str = '', order_id: str = '') -> Dict[str, Any]:
        """Fetch trade history for a symbol or specific order."""
        params = {'timestamp': self._get_timestamp()}

        if symbol:
            params['symbol'] = symbol
        if order_id:
            params['orderId'] = order_id

        return self._make_request('GET', GET_TRADE, params, "fetch trades")
    
    def fetch_order_trade(self, symbol: str = '', order_id: str = '') -> Dict[str, Any]:
        """
        Fetch and aggregate trade details for a specific order.
        
        Returns aggregated trade information including average price, total fees, and PnL.
        """
        trades = self.fetch_trades(symbol=symbol, order_id=order_id)
        self.logger.debug(message=f"{symbol} trades: {trades}")

        # Return default values if no trades found
        if not trades:
            return {
                "price": 0.0,
                "fee": 0.0,
                "pnl": 0.0,
                "side": "ZERO"
            }

        # Aggregate trade data
        total_quote = 0.0
        total_qty = 0.0
        total_fee = 0.0
        total_pnl = 0.0

        for trade in trades:
            total_qty += float(trade["qty"])
            total_quote += float(trade["quoteQty"])
            total_fee += float(trade["commission"])
            total_pnl += float(trade["realizedPnl"])

        # Calculate average price
        avg_price = total_quote / total_qty if total_qty > 0 else 0.0

        return {
            "price": avg_price,
            "fee": total_fee,
            "pnl": total_pnl,
            "side": trades[0]["side"]
        }

    def fetch_order_book(self, symbol: str, limit: int = 5) -> Dict[str, Any]:
        """
        Fetch order book depth for a symbol.
        
        Args:
            symbol: Trading pair symbol
            limit: Number of price levels to fetch (default: 5, max: 1000)
        
        Returns:
            Dictionary with 'bids' and 'asks' arrays
            Example: {'bids': [[price, qty], ...], 'asks': [[price, qty], ...]}
        """
        params = {
            'symbol': symbol.upper(),
            'limit': limit
        }
        
        headers, signed_params = binance_auth.sign_request(params=params, binance_credential=self.__creds)
        try:
            response = self.session.get(url=GET_ORDER_BOOK_URL, headers=headers, params=signed_params)
            response.raise_for_status()
            data = response.json()
            
            # Convert string prices to floats for easier manipulation
            bids = [[float(price), float(qty)] for price, qty in data.get('bids', [])]
            asks = [[float(price), float(qty)] for price, qty in data.get('asks', [])]
            
            return {
                'bids': bids,  # Sorted descending (highest bid first)
                'asks': asks   # Sorted ascending (lowest ask first)
            }
        except Exception as e:
            self.logger.error_e(message=f"Error fetching order book for {symbol}", e=e)
            return {'bids': [], 'asks': []}

    def has_exchange_info_cached(self, symbol: str) -> bool:
        """
        Check if exchange info is cached for a symbol.
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            True if cached, False otherwise
        """
        return symbol in self._exchange_info_cache
    
    def get_cached_exchange_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get cached exchange info without making API call.
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            Cached exchange info or None if not cached
        """
        return self._exchange_info_cache.get(symbol)

    def fetch_exchange_info(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch exchange trading rules for a symbol (with caching).
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            Dictionary with trading rules including tickSize, stepSize, minQty, etc.
        """
        # Check cache first
        if symbol in self._exchange_info_cache:
            return self._exchange_info_cache[symbol]
        
        params = {'symbol': symbol.upper()}
        headers, signed_params = binance_auth.sign_request(params=params, binance_credential=self.__creds)
        
        try:
            response = self.session.get(url=GET_EXCHANGE_INFO_URL, headers=headers, params=signed_params)
            response.raise_for_status()
            data = response.json()
            
            # Find the symbol in the response
            for symbol_info in data.get('symbols', []):
                if symbol_info['symbol'] == symbol.upper():
                    # Extract relevant filters
                    # Store tickSize and stepSize as strings to preserve precision
                    # (avoid float scientific notation like 1e-05)
                    filters = {}
                    for filter_item in symbol_info.get('filters', []):
                        filter_type = filter_item.get('filterType')
                        if filter_type == 'PRICE_FILTER':
                            filters['tickSize'] = filter_item.get('tickSize', '0.01')
                            filters['minPrice'] = filter_item.get('minPrice', 0)
                            filters['maxPrice'] = filter_item.get('maxPrice', 0)
                        elif filter_type == 'LOT_SIZE':
                            filters['stepSize'] = filter_item.get('stepSize', '0.001')
                            filters['minQty'] = filter_item.get('minQty', 0)
                            filters['maxQty'] = filter_item.get('maxQty', 0)
                    
                    # Cache the result
                    self._exchange_info_cache[symbol] = filters
                    self.logger.debug(message=f"Cached exchange info for {symbol}: {filters}")
                    return filters
            
            self.logger.warning(message=f"Symbol {symbol} not found in exchange info")
            return {}
            
        except Exception as e:
            self.logger.error_e(message=f"Error fetching exchange info for {symbol}", e=e)
            return {}


if __name__ == "__main__":
    pass

# EOF
