# Trading Bot Cooldown System

## Overview

The cooldown system prevents the bot from immediately re-entering positions after closure, providing a "cooling off" period. This is particularly useful after stop-loss hits or specific exit conditions to avoid revenge trading or entering during unfavorable market conditions.

## Architecture

### Centralized Management
All cooldown logic is centralized in the [`PositionHandler`](../core/position_handler.py) class, with the [`Bot`](../core/bot.py) class coordinating when to set cooldowns based on position closure reasons.

### Key Components

1. **PositionHandler** - Tracks cooldown state and expiry time
2. **Bot** - Sets cooldowns after position closure (SL or exit strategy)
3. **Exit Strategies** - Define cooldown durations for different exit conditions
4. **BotConfig** - Configures SL cooldown duration

## Features

### 1. Stop Loss (SL) Cooldown
When a position is closed by stop-loss, a cooldown is automatically applied.

**Configuration:**
```json
{
  "cooldown_after_sl_seconds": 3600
}
```

**Behavior:**
- Triggered when TP/SL monitoring detects SL fill
- Duration configured at bot level in [`bot_config.json`](../config/_example_bots_config.json)
- Applied regardless of profit/loss

### 2. Exit Strategy Cooldown
Exit strategies can specify custom cooldown durations based on exit conditions.

**Configuration Example (exit_countdown_with_max_loss):**
```json
{
  "exit_strategy": "exit_countdown_with_max_loss",
  "dynamic_config": {
    "countdown_minutes": 230,
    "max_loss_percent": 0.5,
    "cooldown_after_countdown_seconds": 1800,
    "cooldown_after_max_loss_seconds": 3600
  }
}
```

**Behavior:**
- Each exit condition can have different cooldown duration
- Exit strategy's [`get_cooldown_seconds()`](../abstracts/base_exit_strategy.py:46) method determines duration
- Receives `close_reason` and `pnl` for conditional logic

### 3. PnL-Based Conditional Cooldown
Exit strategies can apply cooldown conditionally based on profit/loss.

**Example Implementation:**
```python
def get_cooldown_seconds(self, close_reason: str = '', pnl: float = 0.0) -> float:
    if close_reason.startswith('Countdown'):
        # Only apply cooldown if position closed with loss
        if pnl < 0:
            return self.cooldown_after_countdown_seconds
        else:
            return 0.0  # No cooldown for profitable exits
    return 0.0
```

**Use Cases:**
- Skip cooldown for profitable exits
- Apply longer cooldown for larger losses
- Different cooldowns based on profit thresholds

### 4. Intra-Candle Protection
Prevents immediate re-entry when cooldown expires mid-candle.

**Mechanism:**
- When cooldown expires, [`is_in_cooldown()`](../core/position_handler.py:89) updates `last_position_close_candle`
- Entry strategies checking for "new candle" won't enter on the same candle
- Ensures at least one full candle passes before re-entry

## Implementation Details

### PositionHandler Methods

#### `is_in_cooldown(current_candle_open_time: str) -> bool`
Checks if bot is currently in cooldown period.

**Parameters:**
- `current_candle_open_time`: Current candle's open time for intra-candle protection

**Returns:**
- `True` if still in cooldown
- `False` if cooldown expired or not set

**Side Effects:**
- Updates `last_position_close_candle` when cooldown expires
- Clears cooldown state when expired

#### `set_cooldown(cooldown_seconds: float, reason: str)`
Sets cooldown with expiry time.

**Parameters:**
- `cooldown_seconds`: Duration in seconds
- `reason`: Reason for cooldown (logged for debugging)

**Behavior:**
- Calculates expiry time in GMT+7
- Stores reason for logging
- Logs cooldown activation

#### `clear_cooldown(current_candle_open_time: str)`
Clears cooldown state and prevents intra-candle entry.

**Parameters:**
- `current_candle_open_time`: Current candle's open time

**Behavior:**
- Resets cooldown fields
- Updates `last_position_close_candle` to prevent same-candle entry
- Logs cooldown expiry

### Bot Integration

#### Entry Signal Handling
```python
# Check cooldown before evaluating entry signal
if self.position_handler.is_in_cooldown(current_candle_open_time=current_candle_open_time):
    self.logger.info(f"[{self.bot_id}] Skipping entry - bot in cooldown")
    return None
```

#### SL Cooldown Setting
```python
# After SL fill detected
if sl_filled and self.bot_config.cooldown_after_sl_seconds > 0:
    self.position_handler.set_cooldown(
        cooldown_seconds=self.bot_config.cooldown_after_sl_seconds,
        reason="SL Hit"
    )
```

#### Exit Strategy Cooldown Setting
```python
# After exit strategy closure
pnl = closed_position_dict.get('pnl', 0.0)
cooldown_seconds = self.exit_strategy.get_cooldown_seconds(
    close_reason=exit_signal.reason,
    pnl=pnl
)
if cooldown_seconds and cooldown_seconds > 0:
    self.position_handler.set_cooldown(
        cooldown_seconds=cooldown_seconds,
        reason=exit_signal.reason
    )
```

### Exit Strategy Implementation

Exit strategies implement [`get_cooldown_seconds()`](../abstracts/base_exit_strategy.py:46) to specify cooldown behavior:

```python
def get_cooldown_seconds(self, close_reason: str = '', pnl: float = 0.0) -> float:
    """
    Return cooldown duration based on exit condition and PnL.
    
    Args:
        close_reason: Reason for position closure
        pnl: Profit/loss of closed position
        
    Returns:
        Cooldown duration in seconds, or 0.0 for no cooldown
    """
    # Implementation specific to exit strategy
    pass
```

## Configuration Examples

### Example 1: Basic SL Cooldown
```json
{
  "bot_id": 76,
  "symbol": "BTCUSDC",
  "cooldown_after_sl_seconds": 3600,
  "exit_strategy": "exit_tp_sl"
}
```
- 1 hour cooldown after SL hit
- No exit strategy cooldown

### Example 2: Multi-Condition Exit with Different Cooldowns
```json
{
  "bot_id": 77,
  "symbol": "ETHUSDC",
  "cooldown_after_sl_seconds": 7200,
  "exit_strategy": "exit_countdown_with_max_loss",
  "dynamic_config": {
    "countdown_minutes": 230,
    "max_loss_percent": 0.5,
    "cooldown_after_countdown_seconds": 1800,
    "cooldown_after_max_loss_seconds": 3600
  }
}
```
- 2 hours cooldown after SL hit
- 30 minutes cooldown after countdown exit (if loss)
- 1 hour cooldown after max loss exit

### Example 3: PnL-Based Conditional Cooldown
```json
{
  "bot_id": 78,
  "symbol": "SOLUSDC",
  "cooldown_after_sl_seconds": 3600,
  "exit_strategy": "exit_countdown_with_max_loss",
  "dynamic_config": {
    "countdown_minutes": 120,
    "max_loss_percent": 1.0,
    "cooldown_after_countdown_seconds": 1800,
    "cooldown_after_max_loss_seconds": 3600
  }
}
```
- Countdown exit: 30 min cooldown only if PnL < 0
- Countdown exit: No cooldown if PnL >= 0 (profitable)
- Max loss exit: Always 1 hour cooldown

## Close Reason Format

Exit strategies should use simple, parseable close reason formats:

### SL Hit Format
```
"SL Hit - {actual_price} ({sl_target})"
```
Example: `"SL Hit - 1734.22 (1796.29)"`

### Countdown Format
```
"Countdown {elapsed}min ({configured}min)"
```
Example: `"Countdown 230min (230min)"`

### Custom Formats
Exit strategies can define custom formats, but should:
- Use consistent prefixes for parsing
- Include relevant context for debugging
- Keep format simple and readable

## Logging

Cooldown events are logged at INFO level:

```
[Bot 76] Setting cooldown: 3600.0 seconds (reason: SL Hit)
[Bot 76] Cooldown active until: 2026-07-08 23:53:54 (GMT+7)
[Bot 76] Skipping entry - bot in cooldown until 2026-07-08 23:53:54 (GMT+7)
[Bot 76] Cooldown expired - ready for new entries
```

## Best Practices

1. **SL Cooldown**: Set longer cooldowns (1-2 hours) after SL hits to avoid revenge trading
2. **Exit Strategy Cooldown**: Use shorter cooldowns (15-30 min) for normal exits
3. **PnL-Based Logic**: Skip cooldown for profitable exits to maximize opportunities
4. **Intra-Candle Protection**: Always pass `current_candle_open_time` to prevent same-candle entry
5. **Testing**: Test cooldown behavior in backtest mode before live trading
6. **Monitoring**: Review cooldown logs to ensure expected behavior

## Troubleshooting

### Bot Not Entering After Cooldown
- Check if `last_position_close_candle` is being updated correctly
- Verify entry strategy checks for new candle
- Review cooldown expiry logs

### Cooldown Not Applied
- Verify `get_cooldown_seconds()` returns non-zero value
- Check if `close_reason` format matches expected pattern
- Review exit strategy configuration

### Unexpected Cooldown Duration
- Verify configuration values in `bot_config.json`
- Check if PnL-based logic is working as expected
- Review `get_cooldown_seconds()` implementation

## Related Files

- [`core/position_handler.py`](../core/position_handler.py) - Cooldown state management
- [`core/bot.py`](../core/bot.py) - Cooldown coordination
- [`abstracts/base_exit_strategy.py`](../abstracts/base_exit_strategy.py) - Exit strategy interface
- [`strategies/exit/exit_countdown_with_max_loss.py`](../strategies/exit/exit_countdown_with_max_loss.py) - Multi-condition example
- [`strategies/exit/exit_countdown.py`](../strategies/exit/exit_countdown.py) - Simple cooldown example
- [`models/bot_config.py`](../models/bot_config.py) - Configuration model