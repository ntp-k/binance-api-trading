# Fixed Margin Position Sizing

## Overview

The bot now supports **fixed margin position sizing** in addition to the legacy fixed quantity mode. This feature allows you to specify a fixed margin amount (e.g., 5 USDC) for each position, and the bot will automatically calculate the appropriate quantity based on the current market price and leverage.

## Benefits

### 1. **Consistent Risk Per Trade**
- Each position uses the same margin amount regardless of price
- Example: 5 USDC margin per trade = consistent risk exposure

### 2. **Prevents Margin Spikes**
- Fixed quantity can cause varying margin usage as price changes
- Fixed margin ensures predictable capital allocation

### 3. **Better Capital Management**
- Easier to calculate total capital requirements
- Simpler portfolio allocation across multiple bots

## Configuration

### Using Fixed Margin (Recommended)

```json
{
    "symbol": "SOLUSDT",
    "leverage": 10,
    "position_margin": 5.0,
    "order_type": "LIMIT"
}
```

**Calculation Example:**
- `position_margin` = 5 USDC
- `leverage` = 10x
- Current price = 100 USDC
- **Calculated quantity** = (5 × 10) / 100 = **0.5 SOL**

If price changes to 200 USDC:
- **Calculated quantity** = (5 × 10) / 200 = **0.25 SOL**
- Margin still = 5 USDC ✅

### Using Fixed Quantity (Legacy)

```json
{
    "symbol": "SOLUSDT",
    "leverage": 10,
    "quantity": 0.5,
    "order_type": "LIMIT"
}
```

**Issue with Fixed Quantity:**
- At 100 USDC: margin = (0.5 × 100) / 10 = 5 USDC
- At 200 USDC: margin = (0.5 × 200) / 10 = **10 USDC** ❌ (doubled!)

## Implementation Details

### How It Works

1. **Position Opening:**
   - Bot fetches current market price
   - Calculates quantity: `(position_margin × leverage) / current_price`
   - Rounds to exchange's step size precision
   - Caches the calculated quantity for the position lifetime

2. **TP/SL Orders:**
   - Uses the same cached quantity
   - Ensures TP/SL orders match the opened position exactly

3. **Position Closing:**
   - Uses cached quantity to close the position
   - Clears cached quantity after position is closed

### Code Flow

```
Entry Signal Triggered
    ↓
Fetch Current Price
    ↓
Calculate Quantity = (position_margin × leverage) / price
    ↓
Round to Step Size
    ↓
Cache Quantity
    ↓
Open Position with Calculated Quantity
    ↓
Place TP/SL with Same Quantity
    ↓
Position Closed
    ↓
Clear Cached Quantity
```

## Configuration Options

### Required Fields

Either `quantity` OR `position_margin` must be provided:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `position_margin` | float | Fixed margin per position in USDC | `5.0` |
| `quantity` | float | Fixed quantity per position | `0.5` |
| `leverage` | int | Leverage multiplier | `10` |

### Priority

If both `quantity` and `position_margin` are provided, **`position_margin` takes precedence**.

## Migration Guide

### From Fixed Quantity to Fixed Margin

**Before:**
```json
{
    "symbol": "BTCUSDT",
    "leverage": 20,
    "quantity": 0.01
}
```

**After:**
```json
{
    "symbol": "BTCUSDT",
    "leverage": 20,
    "position_margin": 10.0
}
```

**Calculation:**
- Old: 0.01 BTC at $50,000 = $500 position / 20 leverage = $25 margin
- New: Set `position_margin: 25.0` to maintain same risk

### Recommended Settings

| Account Size | Position Margin | Leverage | Risk Per Trade |
|--------------|----------------|----------|----------------|
| $100 | 2.0 | 5x | 2% |
| $500 | 5.0 | 10x | 1% |
| $1,000 | 10.0 | 10x | 1% |
| $5,000 | 25.0 | 20x | 0.5% |

## Examples

### Example 1: Conservative Trading

```json
{
    "bot_name": "Conservative BTC Bot",
    "symbol": "BTCUSDT",
    "leverage": 5,
    "position_margin": 10.0,
    "tp_enabled": true,
    "sl_enabled": true
}
```

- Margin per trade: 10 USDC
- Effective position size: 50 USDC (10 × 5)
- Risk: Fixed at 10 USDC regardless of BTC price

### Example 2: Aggressive Trading

```json
{
    "bot_name": "Aggressive SOL Bot",
    "symbol": "SOLUSDT",
    "leverage": 20,
    "position_margin": 5.0,
    "tp_enabled": true,
    "sl_enabled": true
}
```

- Margin per trade: 5 USDC
- Effective position size: 100 USDC (5 × 20)
- Risk: Fixed at 5 USDC regardless of SOL price

### Example 3: Multiple Bots Portfolio

```json
[
    {
        "bot_name": "BTC Bot",
        "symbol": "BTCUSDT",
        "leverage": 10,
        "position_margin": 10.0
    },
    {
        "bot_name": "ETH Bot",
        "symbol": "ETHUSDT",
        "leverage": 10,
        "position_margin": 10.0
    },
    {
        "bot_name": "SOL Bot",
        "symbol": "SOLUSDT",
        "leverage": 10,
        "position_margin": 10.0
    }
]
```

- Total margin if all bots open: 30 USDC
- Easy to calculate total exposure
- Consistent risk across all bots

## Technical Details

### Quantity Calculation Formula

```python
quantity = (position_margin × leverage) / current_price
```

### Precision Handling

The calculated quantity is rounded to the exchange's step size:

```python
step_size = 0.001  # Example for SOL
quantity_decimal = Decimal(str(raw_quantity))
step_decimal = Decimal(str(step_size))
rounded_quantity = float((quantity_decimal // step_decimal) * step_decimal)
```

### Caching Mechanism

- Quantity is calculated once when opening a position
- Cached for the entire position lifetime
- Ensures TP/SL orders use the exact same quantity
- Cleared when position is closed

## Troubleshooting

### Issue: "Either 'quantity' or 'position_margin' must be provided"

**Solution:** Add one of these fields to your config:
```json
"position_margin": 5.0
```
or
```json
"quantity": 0.5
```

### Issue: Quantity too small or too large

**Solution:** Adjust your `position_margin` or `leverage`:
- Too small: Increase `position_margin` or `leverage`
- Too large: Decrease `position_margin` or `leverage`

### Issue: Position margin doesn't match expected value

**Cause:** Price volatility between calculation and execution

**Solution:** This is normal. The bot calculates quantity at the moment of order placement. Small differences are expected due to:
- Price movement between calculation and execution
- Rounding to exchange step size
- Maker/taker price differences

## Best Practices

1. **Start Small:** Begin with small `position_margin` values (2-5 USDC)
2. **Test First:** Use backtest mode to verify calculations
3. **Monitor Closely:** Watch first few trades to ensure expected behavior
4. **Consistent Leverage:** Use same leverage across similar strategies
5. **Account for Fees:** Remember trading fees reduce effective margin

## API Reference

### BotConfig

```python
@dataclass
class BotConfig:
    position_margin: Optional[float] = None  # Fixed margin per position
    quantity: Optional[float] = None         # Fixed quantity per position
    leverage: int                            # Leverage multiplier
    
    def uses_fixed_margin(self) -> bool:
        """Check if using fixed margin mode"""
        return self.position_margin is not None
```

### TradeHandler

```python
def calculate_quantity_from_margin(self, current_price: float) -> float:
    """Calculate position quantity from fixed margin amount"""
    
def get_trade_quantity(self) -> float:
    """Get quantity for trading (calculated or fixed)"""
    
def clear_cached_quantity(self) -> None:
    """Clear cached quantity when position is closed"""
```

## Version History

- **v1.0.0** (2026-04-30): Initial implementation of fixed margin sizing
  - Added `position_margin` field to BotConfig
  - Implemented dynamic quantity calculation
  - Added quantity caching mechanism
  - Updated all order placement methods
  - Backward compatible with fixed quantity mode

## Support

For questions or issues:
1. Check this documentation
2. Review example configs in `config/_example_bots_config.json`
3. Test in backtest mode first
4. Check logs for calculation details

---

**Note:** This feature is production-ready and recommended for all new bot configurations. Legacy fixed quantity mode remains supported for backward compatibility.