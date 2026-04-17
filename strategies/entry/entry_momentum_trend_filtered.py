"""
MomentumTrendFiltered Entry Strategy

A momentum-based entry strategy that combines:
- Candle body size momentum
- Trend filtering with EMA
- Volatility confirmation with ATR
- Market structure-based stop loss

Entry Conditions:
- LONG: Bullish candle with sufficient body size, above EMA(200), high volatility
- SHORT: Bearish candle with sufficient body size, below EMA(200), high volatility

Stop Loss:
- LONG: Previous candle low with buffer (validated to be below entry)
- SHORT: Previous candle high with buffer (validated to be above entry)
"""

from typing import Tuple
import pandas as pd

from abstracts.base_entry_strategy import BaseEntryStrategy
from models.enum.position_side import PositionSide
from models.position_signal import PositionSignal
from core.position_handler import PositionHandler
import strategies.data_processor as data_processor


class EntryMomentumTrendFiltered(BaseEntryStrategy):
    """
    Entry strategy combining momentum, trend, and volatility filters.
    
    Configuration Parameters:
        min_body_pct: Minimum candle body size as percentage (default: 0.005 = 0.5%)
        sl_buffer: Stop loss buffer percentage (default: 0.001 = 0.1%)
        ema_period: EMA period for trend filter (default: 200)
        atr_period: ATR period for volatility (default: 14)
        atr_ma_period: ATR moving average period (default: 20)
        atr_threshold_multiplier: ATR threshold multiplier (default: 0.9)
    """
    
    def __init__(self, dynamic_config: dict, logger=None):
        super().__init__(logger=logger)
        self.dynamic_config = dynamic_config
        
        # Configuration parameters with defaults
        self.min_body_pct = float(dynamic_config.get('min_body_pct', 0.005))
        self.sl_buffer = float(dynamic_config.get('sl_buffer', 0.001))
        self.ema_period = int(dynamic_config.get('ema_period', 200))
        self.atr_period = int(dynamic_config.get('atr_period', 14))
        self.atr_ma_period = int(dynamic_config.get('atr_ma_period', 20))
        self.atr_threshold_multiplier = float(dynamic_config.get('atr_threshold_multiplier', 0.9))
        
        self.logger.info(
            f"Initialized with: min_body={self.min_body_pct:.3%}, "
            f"sl_buffer={self.sl_buffer:.3%}, ema={self.ema_period}, "
            f"atr={self.atr_period}, atr_ma={self.atr_ma_period}, "
            f"atr_mult={self.atr_threshold_multiplier}"
        )
    
    def _process_data(self, klines_df: pd.DataFrame) -> pd.DataFrame:
        """
        Process klines data and add technical indicators.
        
        Adds:
        - EMA for trend filtering
        - ATR for volatility measurement
        - ATR SMA for volatility confirmation
        - Candle body size percentage
        
        Args:
            klines_df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with added indicator columns
        """
        # Calculate EMA for trend filter
        klines_df = data_processor.calculate_ema(
            df=klines_df, 
            ema=self.ema_period
        )
        
        # Calculate ATR for volatility
        klines_df = data_processor.calculate_atr(
            df=klines_df,
            period=self.atr_period
        )
        
        # Calculate ATR moving average for volatility filter
        klines_df[f'atr_sma_{self.atr_ma_period}'] = (
            klines_df['atr'].rolling(window=self.atr_ma_period).mean()
        )
        
        # Calculate candle body size as percentage
        klines_df['body_size_pct'] = (
            abs(klines_df['close'] - klines_df['open']) / klines_df['open']
        )
        
        # Identify bullish/bearish candles
        klines_df['is_bullish'] = klines_df['close'] > klines_df['open']
        klines_df['is_bearish'] = klines_df['close'] < klines_df['open']
        
        return klines_df
    
    def should_open(
        self, 
        klines_df: pd.DataFrame, 
        position_handler: PositionHandler
    ) -> PositionSignal:
        """
        Determine if a position should be opened based on momentum and filters.
        
        Args:
            klines_df: DataFrame with klines and indicators
            position_handler: Handler for position state
            
        Returns:
            PositionSignal with entry decision and reason
        """
        # Process data with indicators
        klines_df = self._process_data(klines_df)
        
        # Default: no entry
        position_signal = PositionSignal(
            position_side=PositionSide.ZERO,
            reason='No entry signal'
        )
        
        # Get previous candle data (entry is triggered at open of new candle)
        prev_candle = klines_df.iloc[-2]
        current_candle = klines_df.iloc[-1]
        
        # Extract values
        prev_close = prev_candle['close']
        prev_open = prev_candle['open']
        prev_high = prev_candle['high']
        prev_low = prev_candle['low']
        prev_body_pct = prev_candle['body_size_pct']
        prev_is_bullish = prev_candle['is_bullish']
        prev_is_bearish = prev_candle['is_bearish']
        
        ema_value = prev_candle[f'ema_{self.ema_period}']
        atr_value = prev_candle['atr']
        atr_sma_value = prev_candle[f'atr_sma_{self.atr_ma_period}']
        
        current_price = current_candle['current_price']
        
        # Check common conditions
        body_size_ok = prev_body_pct >= self.min_body_pct
        # Relaxed volatility filter: ATR > ATR_SMA * 0.9
        atr_threshold = atr_sma_value * self.atr_threshold_multiplier
        volatility_ok = atr_value > atr_threshold
        
        # Build reason components
        reasons = []
        
        # ============================================
        # LONG ENTRY CONDITIONS
        # ============================================
        if prev_is_bullish:
            reasons.append(f"✓ Bullish candle")
            
            if body_size_ok:
                reasons.append(f"✓ Body size {prev_body_pct:.3%} >= {self.min_body_pct:.3%}")
            else:
                reasons.append(f"✗ Body size {prev_body_pct:.3%} < {self.min_body_pct:.3%}")
            
            price_above_ema = prev_close > ema_value
            if price_above_ema:
                reasons.append(f"✓ Price {prev_close:.4f} > EMA {ema_value:.4f}")
            else:
                reasons.append(f"✗ Price {prev_close:.4f} <= EMA {ema_value:.4f}")
            
            if volatility_ok:
                reasons.append(f"✓ ATR {atr_value:.4f} > {atr_threshold:.4f} ({self.atr_threshold_multiplier}*ATR_SMA)")
            else:
                reasons.append(f"✗ ATR {atr_value:.4f} <= {atr_threshold:.4f}")
            
            # All conditions met for LONG
            if body_size_ok and price_above_ema and volatility_ok:
                position_signal.position_side = PositionSide.LONG
                position_signal.reason = f"LONG: {' | '.join(reasons)}"
                self.logger.info(position_signal.reason)
                return position_signal
        
        # ============================================
        # SHORT ENTRY CONDITIONS
        # ============================================
        elif prev_is_bearish:
            reasons.append(f"✓ Bearish candle")
            
            if body_size_ok:
                reasons.append(f"✓ Body size {prev_body_pct:.3%} >= {self.min_body_pct:.3%}")
            else:
                reasons.append(f"✗ Body size {prev_body_pct:.3%} < {self.min_body_pct:.3%}")
            
            price_below_ema = prev_close < ema_value
            if price_below_ema:
                reasons.append(f"✓ Price {prev_close:.4f} < EMA {ema_value:.4f}")
            else:
                reasons.append(f"✗ Price {prev_close:.4f} >= EMA {ema_value:.4f}")
            
            if volatility_ok:
                reasons.append(f"✓ ATR {atr_value:.4f} > {atr_threshold:.4f} ({self.atr_threshold_multiplier}*ATR_SMA)")
            else:
                reasons.append(f"✗ ATR {atr_value:.4f} <= {atr_threshold:.4f}")
            
            # All conditions met for SHORT
            if body_size_ok and price_below_ema and volatility_ok:
                position_signal.position_side = PositionSide.SHORT
                position_signal.reason = f"SHORT: {' | '.join(reasons)}"
                self.logger.info(position_signal.reason)
                return position_signal
        
        # No entry signal
        if reasons:
            position_signal.reason = f"No entry: {' | '.join(reasons)}"
        
        return position_signal
    
    def calculate_tp_sl(
        self,
        klines_df: pd.DataFrame,
        position_side: PositionSide,
        entry_price: float
    ) -> Tuple[float, float]:
        """
        Calculate take profit and stop loss prices based on market structure.
        
        Stop Loss Logic:
        - LONG: Previous candle low with buffer (validated to be below entry)
        - SHORT: Previous candle high with buffer (validated to be above entry)
        
        Take Profit:
        - Uses ATR-based calculation (3x ATR from entry)
        
        Args:
            klines_df: DataFrame with klines data
            position_side: LONG or SHORT
            entry_price: Entry price of position
            
        Returns:
            Tuple of (tp_price, sl_price)
        """
        # Process data to ensure indicators are available
        klines_df = self._process_data(klines_df)
        
        # Get previous candle (the one that triggered entry)
        prev_candle = klines_df.iloc[-2]
        prev_high = prev_candle['high']
        prev_low = prev_candle['low']
        atr_value = prev_candle['atr']
        
        if position_side == PositionSide.LONG:
            # Stop loss: Previous candle low with buffer
            sl_price = prev_low * (1 - self.sl_buffer)
            
            # Validate: SL must be below entry price
            if sl_price >= entry_price:
                self.logger.warning(
                    f"LONG SL {sl_price:.4f} >= entry {entry_price:.4f}. "
                    f"Adjusting to entry - 0.5% for safety."
                )
                sl_price = entry_price * 0.995  # 0.5% below entry as fallback
            
            # Take profit: 3x ATR above entry
            tp_price = entry_price + (3 * atr_value)
            
            self.logger.debug(
                f"LONG TP/SL: Entry={entry_price:.4f}, "
                f"SL={sl_price:.4f} (prev_low={prev_low:.4f}), "
                f"TP={tp_price:.4f} (3xATR={3*atr_value:.4f})"
            )
            
        else:  # SHORT
            # Stop loss: Previous candle high with buffer
            sl_price = prev_high * (1 + self.sl_buffer)
            
            # Validate: SL must be above entry price
            if sl_price <= entry_price:
                self.logger.warning(
                    f"SHORT SL {sl_price:.4f} <= entry {entry_price:.4f}. "
                    f"Adjusting to entry + 0.5% for safety."
                )
                sl_price = entry_price * 1.005  # 0.5% above entry as fallback
            
            # Take profit: 3x ATR below entry
            tp_price = entry_price - (3 * atr_value)
            
            self.logger.debug(
                f"SHORT TP/SL: Entry={entry_price:.4f}, "
                f"SL={sl_price:.4f} (prev_high={prev_high:.4f}), "
                f"TP={tp_price:.4f} (3xATR={3*atr_value:.4f})"
            )
        
        return tp_price, sl_price


# EOF

# Made with Bob
