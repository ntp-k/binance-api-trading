"""Wick mean-reversion entry strategy with a directional-efficiency filter.

The strategy preserves the Wick Mean Reversion body, wick, TP, and SL rules.
It blocks a reversal entry only when the last completed candles moved efficiently
in the direction opposite to the proposed position.
"""

import math

import pandas as pd

from core.position_handler import PositionHandler
from models.bot_config import BotConfig
from models.enum.position_side import PositionSide
from models.position_signal import PositionSignal
from strategies.entry.entry_wick_mean_reversion import EntryWickMeanReversion


class EntryWickMeanReversionEfficiencyFilter(EntryWickMeanReversion):
    """Wick mean reversion with a 24-hour directional-efficiency gate.

    ``directional_efficiency_lookback`` is the number of close-to-close changes.
    On a 4-hour timeframe, its default value of six measures the preceding 24
    hours from seven fully closed candle closes.
    """

    def __init__(self, bot_config: BotConfig, logger=None):
        super().__init__(bot_config=bot_config, logger=logger)
        self.directional_efficiency_lookback = int(
            self.dynamic_config.get('directional_efficiency_lookback', 6)
        )
        self.directional_efficiency_threshold = float(
            self.dynamic_config.get('directional_efficiency_threshold', 0.60)
        )

        if self.directional_efficiency_lookback < 1:
            raise ValueError('directional_efficiency_lookback must be at least 1')
        if not 0.0 <= self.directional_efficiency_threshold <= 1.0:
            raise ValueError('directional_efficiency_threshold must be between 0 and 1')

        self.logger.info(
            'Initialized directional efficiency filter: '
            f'lookback={self.directional_efficiency_lookback} close changes, '
            f'threshold={self.directional_efficiency_threshold:.3f}'
        )

    def should_open(
        self,
        klines_df: pd.DataFrame,
        position_handler: PositionHandler,
    ) -> PositionSignal:
        """Return the base signal unless an opposing efficient move is present."""
        base_signal = super().should_open(
            klines_df=klines_df,
            position_handler=position_handler,
        )
        if base_signal.position_side == PositionSide.ZERO:
            return base_signal

        # The final row is the currently forming candle.  It is intentionally
        # excluded so a live decision cannot use its future close.
        completed_candles = klines_df.iloc[:-1]
        required_closes = self.directional_efficiency_lookback + 1
        if len(completed_candles) < required_closes:
            return PositionSignal(
                position_side=PositionSide.ZERO,
                reason=(
                    f'{base_signal.reason} | Directional efficiency needs '
                    f'{required_closes} completed closes; only '
                    f'{len(completed_candles)} available: ❌'
                ),
            )

        closes = completed_candles['close'].tail(required_closes)
        net_move = float(closes.iloc[-1] - closes.iloc[0])
        path_length = float(closes.diff().abs().iloc[1:].sum())

        if not math.isfinite(net_move) or not math.isfinite(path_length):
            return PositionSignal(
                position_side=PositionSide.ZERO,
                reason=f'{base_signal.reason} | Directional efficiency data is invalid: ❌',
            )

        efficiency = 0.0 if path_length == 0.0 else abs(net_move) / path_length
        opposes_position = (
            (base_signal.position_side == PositionSide.LONG and net_move < 0.0)
            or (base_signal.position_side == PositionSide.SHORT and net_move > 0.0)
        )
        blocks_entry = (
            opposes_position
            and efficiency >= self.directional_efficiency_threshold
        )

        filter_reason = (
            f'Directional efficiency ({self.directional_efficiency_lookback} '
            f'completed close changes): net={net_move:.4f}, '
            f'path={path_length:.4f}, ER={efficiency:.3f} '
            f'(threshold={self.directional_efficiency_threshold:.3f}), '
            f'opposes {base_signal.position_side.value}: '
            f'{"❌ skip entry" if blocks_entry else "✅ allow entry"}'
        )

        return PositionSignal(
            position_side=(PositionSide.ZERO if blocks_entry else base_signal.position_side),
            reason=f'{base_signal.reason} | {filter_reason}',
        )


# EOF
