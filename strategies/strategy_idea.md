

## MACDHIST
monitor histogram of macd -> look for stange chage
hist negative -> position : close short, open long
hist positive -> negative : close long, open short

### ✅ Strength
- high velocity

### ❌ Weaknesses
![alt text](../assets/strategies/macdhist/macd_result_live_trading.png)

- Sideways Market : false entries, frequent position flipping

### Potential Improvements
- add conditions only open position only stange aling with macd

    * hist negative -> position
    * macd < 0
    * marked_price under EMA 200
    * all 3 conditions: open short
    * 2 con


    * hist positive -> negative and macd >= 0 : close long, open short

- 