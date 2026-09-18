# Bot 90: reducing losses when price keeps trending

Analysis date: 2026-09-19. All example times below are Asia/Bangkok (UTC+7).

**Recommendation: trial a directional efficiency filter over six completed 4-hour candles. Skip a mean-reversion entry when price has moved efficiently against the proposed trade over the preceding 24 hours.** Start with efficiency ≥ 0.60 as a research setting. This was more useful than ADX in the supplied trades. It cannot prevent every loss, and the improvement below is retrospective, not a validated future return.

**What the supplied data shows**

- 84 closed trades, opened September 1–18, with the last exit September 19 at 02:50:53.
- Recorded realized PnL: **+14.9384 USDC**; 58 profitable trades and 26 losing trades, a 69.0% win rate.
- Gross profits: 129.0956; gross losses: 114.1572; profit factor: 1.131.
- 51 take-profit exits earned +124.9166; six stops lost −51.1662; 27 countdown exits summed to −58.8120.
- Average TP exit: +2.4493; average stop exit: −8.5277. One stop consumes approximately **3.48 average TP wins**. Considering only these two exit types, break-even requires about 77.7% TP wins; countdown exits change the actual break-even calculation.
- Maximum drawdown of cumulative **closed-trade** PnL: 19.9766 USDC. This is not account-equity or intratrade drawdown.

Your observation is supported by several loss clusters, but not every loss is a trend loss. The bot buys after a red candle and sells after a green candle. A persistent move repeatedly invites entries against it. Both wick filters are disabled, the maximum preceding body is a permissive 3.5%, and there is no configured post-stop cooldown. A wick bounce target can be small compared with the 1.05% stop.

**Inputs and alignment**

I inspected `config/bot_90.json`, `strategies/entry/entry_wick_mean_reversion.py`, the pasted trade table, and `BTCUSDC_4h_1500_20260112T070000+0700_20260919T065959+0700.csv`.

The CSV contains 1,500 consecutive 4-hour candles, January 12 at 07:00 through September 19 at 06:59:59.999, with no duplicate starts, missing 4-hour intervals, or invalid OHLC relationships. Trade timestamps have no timezone suffix; I treated them as Bangkok time. All 84 trade directions match the preceding CSV candle's color, and all logged preceding-body percentages match within rounding (maximum difference 0.00049 percentage points). This supports the timezone and candle alignment.

For each entry, I used the latest candle whose close timestamp was strictly earlier than entry. Indicator history includes earlier months for warm-up. I did not use the entry candle's eventual high, low, or close to decide whether to skip it. The table's `date` sometimes differs from the calendar date of `open time`; calculations use `open time`.

**Comparison of entry filters**

These results remove flagged trades from the actual record and retain each remaining trade's recorded realized PnL and position size. They are **trade-exclusion scenarios**, not a fresh execution backtest. Skipping trades could change later sizing, account state, fills, and eligibility in a real run. Recorded fees are already included in realized PnL; I did not subtract them again. Funding or other unrecorded costs cannot be inferred.

| Rule for skipping an entry | Kept trades | Kept PnL, USDC | Profit factor | Closed-trade max drawdown | Stops retained |
|---|---:|---:|---:|---:|---:|
| No additional filter | 84 | 14.9384 | 1.131 | 19.9766 | 6 |
| ADX(14) ≥ 25, either direction | 62 | 2.9731 | 1.032 | 19.2712 | 6 |
| ADX(14) ≥ 25 and opposing DI direction | 76 | 12.7812 | 1.123 | 18.4250 | 6 |
| Opposing EMA20/EMA50 alignment | 55 | 12.4868 | 1.171 | 19.9766 | 3 |
| Three consecutive same-color candles | 65 | 8.1747 | 1.095 | 20.1514 | 4 |
| Existing support wick: require last wick > 0.20% | 59 | 22.3459 | 1.305 | 17.9706 | 4 |
| Existing counter-trend wick: require last wick > 0.10% | 64 | -6.0507 | 0.938 | 19.9766 | 6 |
| Opposing 24-hour net movement ≥ 1 ATR(14) | 52 | 32.3437 | 1.666 | 11.4070 | 1 |
| **Opposing 24-hour efficiency ≥ 0.60** | **65** | **47.4746** | **1.826** | **16.2900** | **1** |

EMA alignment means close > EMA20 > EMA50 for an uptrend, or close < EMA20 < EMA50 for a downtrend. Only entries against that direction are skipped. DI direction is the sign of +DI minus −DI. ATR and ADX use Wilder smoothing with a 14-observation arithmetic seed; EMA uses alpha = 2/(period+1).

The efficiency rule skips 19 trades: **nine losses totaling 56.6623 and ten wins totaling 24.1261**. The net retrospective improvement is 32.5362 USDC. It retains 48 wins and 17 losses. Losing trade count falls partly because fewer trades are taken; the retained win rate is 73.8%.

**Why ADX alone is insufficient here**

ADX measures trend strength and needs a separate direction measure. Above 25 is a common convention, not a universal threshold. See [Fidelity's DMI explanation](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/DMI).

The six stop-loss entries had ADX readings of **12.58, 17.03, 23.81, 19.48, 18.28, and 24.00**. A ≥25 gate misses all six. Lowering the threshold to 20 and filtering opposing DI direction retained PnL of 13.3460 and still retained five stops. Here the short recent directional move is a better warning than a slower smoothed trend-strength reading. This does not establish that ADX is ineffective in other periods.

**The recommended calculation**

Let `t` be the latest fully closed candle. Use **seven closes to measure six close-to-close changes**, covering 24 hours:

```text
net_move = close[t] - close[t-6]
path_length = sum(abs(close[j] - close[j-1]), j=t-5 ... t)
ER6 = abs(net_move) / path_length
```

Set ER6 to zero if path length is zero. ER6 near one means closes moved mostly in one direction; near zero means much of the movement reversed. It measures directional consistency, not absolute volatility.

```text
skip LONG  if ER6 >= 0.60 and net_move < 0
skip SHORT if ER6 >= 0.60 and net_move > 0
otherwise continue through the existing entry checks
```

Do not block a trade merely because efficiency is high when its direction agrees with the 24-hour move. Recompute on each newly closed candle; the basic rule has no additional cooldown or hysteresis.

Manual example: before the **September 18, 19:00 SHORT**, the relevant seven closes were:

```text
76,385.9 → 76,690.6 → 76,509.9 → 76,334.3
         → 77,295.6 → 77,720.0 → 77,968.9
net_move    = +1,583.0
path_length = 2,295.6
ER6         = 1,583.0 / 2,295.6 = 0.68958
```

The proposed SHORT opposed an efficient upward move, so the rule skips it. That trade actually lost 8.5052 USDC. At entry, ADX was only 24.00. ATR(14) was 856.53, making the 24-hour move 1.848 ATR.

On September 18, the SHORT entries at 11:00, 15:00, 19:00, and 23:00 collectively lost 19.9766. ER6 would skip the last three, avoiding 16.0066 of those losses, but retain the first loss of 3.9700. The September 1, 23:00 LONG stop also remains: its ER6 was only 0.443. A pre-entry filter cannot reliably anticipate every newly developing move.

**Sensitivity and the limits of this evidence**

At a six-change lookback, nearby thresholds produce:

| ER threshold | Kept trades | Kept PnL | Max drawdown | Stops retained |
|---|---:|---:|---:|---:|
| 0.50 | 59 | 49.2606 | 11.3080 | 1 |
| 0.60 | 65 | 47.4746 | 16.2900 | 1 |
| 0.70 | 69 | 42.2274 | 14.4812 | 2 |

The benefit is not isolated to a single threshold. However, the lookback matters: ER4 ≥0.60 retained 29.2034, while ER8 ≥0.60 retained 29.3854. ER8 ≥0.70 retained only 13.7187, below baseline. Six changes is a candidate, not an established optimum.

Using a calendar split at September 10, 00:00 Bangkok:

| Entry period | Baseline PnL | ER6 ≥0.60 opposing filter PnL |
|---|---:|---:|
| September 1–9 | 27.6180 | 38.3946 |
| September 10–18 | -12.6796 | 9.0800 |

Both segments improve, but **neither is a clean holdout**: I inspected the full sample while comparing rules. There were 26 initial rule/baseline scenarios, followed by nine ER lookback/threshold checks and three combinations, with some overlap. Selection bias remains substantial, and neighboring trades share market conditions.

The earlier CSV history supplies market regimes, not realized bot results. After discarding the first 180 rows for warm-up, January–August had 994 candles satisfying the current color/body/wick-override conditions; ER6 would flag 197 of them (19.8%). That is a signal-frequency check only, excluding execution and bot-state constraints. It does not demonstrate historical profitability.

**A second candidate: movement relative to ATR**

Calculate `signed_move = (close[t] - close[t-6]) / ATR14[t]`. Skip SHORT when this is ≥1 and LONG when it is ≤−1. This rule had lower closed-trade drawdown than ER6 alone, but removed 32 trades and retained less total PnL. It is worth comparing in forward testing if drawdown reduction is the priority.

True range is `max(high-low, abs(high-previous_close), abs(low-previous_close))`. ATR14 is Wilder's smoothed true range. ATR measures volatility, not direction; the signed close change provides direction. See [Fidelity's ATR explanation](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/atr).

An additional magnitude requirement, `ER6 >=0.60 AND abs(signed_move)>=1`, retained 66 trades and 49.7536 USDC here. It differed from the basic ER rule by just one profitable trade. That is too little evidence to justify presenting the combination as a proven improvement.

**What can be done with existing configuration**

The simplest candidate requiring no new indicator code is:

```json
{
  "support_position_wick_lookback": 1,
  "min_support_position_wick_pct": 0.002,
  "counter_trend_wick_lookback": 0
}
```

These are proposed values inside `dynamic_config`, not a complete bot configuration. The support filter requires a **lower wick for LONG** or **upper wick for SHORT**, measured excluding the body and divided by candle open. This asks for some prior rejection in the desired reversal direction. It still misses several trend losses.

Do not enable both filters merely because their names sound protective. The existing counter-trend filter checks the other wick: upper for LONG, lower for SHORT. Its one-candle 0.10% version worsened results here. Requiring two support wicks above 0.20% also worsened retained PnL to −13.7971.

Combining ER6 with the one-candle support filter retained 45 trades, 40.6840 PnL, and an 8.5473 drawdown. This is another exploratory result with substantially fewer trades; validate the individual rules before stacking them.

**Implementation and validation plan**

1. Add the ER gate after determining the proposed side in `EntryWickMeanReversion.should_open`, before permitting an entry. Use only completed candles. The current method treats `klines_df.iloc[-1]` as the live candle, so calculate ER from `klines_df.iloc[:-1]`. At least seven completed candles are required; skip with an explicit reason when history is insufficient.
2. Log ER6, net move, proposed side, latest closed-candle time, and the pass/skip decision. These calculations can be automated; no recurring manual judgment is needed. In a trial, retain shadow signals for blocked trades so missed winners can also be measured.
3. Freeze the candidate rule before collecting a new evaluation period. Compare baseline, ER6, and the ATR-movement alternative in paper/shadow testing. Evaluate net PnL after actual costs, loss frequency, drawdown, missed profits, retained trade count, and separate market episodes. The same September sample cannot establish future performance.
4. For an execution replay, obtain 1-minute data or finer trades/order records. A 4-hour bar cannot tell which of TP and SL occurred first, whether a maker order filled, or the price at the 230-minute countdown exit. Do not label a full-candle OHLC simulation as a faithful reproduction of this bot.
5. Keep exit and sizing changes separate initially. Tightening stops, adding break-even exits, or changing TP cannot be validated from this trade table: it lacks the price path. Two rows even report final PnL above recorded `max pnl`, indicating sampled extrema are incomplete. No conclusion about an optimal tighter stop follows from those columns.

Separately, the current `_process_data` computes TP percentiles from the last 180 rows including the live candle. At live entry that candle is only partially formed; a historical replay using its completed OHLC would introduce look-ahead. Preserve the actual information available at entry in a reproduction, or deliberately change TP estimation to completed candles and evaluate that as a separate strategy change.

The configured 32× leverage does not improve the signal; it increases exposure relative to margin. Trend filtering should be evaluated at controlled position sizes. This report does not change the live configuration or recommend increasing leverage.

**Minimal reproduction of the recommended trade-exclusion calculation**

This snippet uses pandas and the supplied files; it reproduces the primary count and PnL comparison without requiring a trading client or network access.

```python
from pathlib import Path
import pandas as pd

root = Path('.')  # run from repository root
k = pd.read_csv(next(root.glob('BTCUSDC_4h_1500*.csv')))
k['close_time'] = pd.to_datetime(k['close_time'], utc=True)
k = k.sort_values('close_time')
k['net_move'] = k['close'].diff(6)
path = k['close'].diff().abs().rolling(6).sum()
k['er6'] = (k['net_move'].abs() / path).where(path.ne(0), 0)

trades = pd.read_csv(
    '/home/ntpk/.codex/attachments/'
    '28b8c1ca-e9ca-4cd3-bc16-1b506675c39d/pasted-text.txt',
    sep='\t',
)
trades['entry_time'] = (
    pd.to_datetime(trades['open time'])
      .dt.tz_localize('Asia/Bangkok').dt.tz_convert('UTC')
)
m = pd.merge_asof(
    trades.sort_values('entry_time'),
    k[['close_time', 'net_move', 'er6']],
    left_on='entry_time', right_on='close_time',
    direction='backward', allow_exact_matches=False,
)
assert m[['net_move', 'er6']].notna().all().all()
side = m['position side'].map({'LONG': 1, 'SHORT': -1})
assert side.notna().all()
skip = m['er6'].ge(0.60) & (side * m['net_move']).lt(0)
print(len(m), round(m['realized pnl'].sum(), 4))  # 84, 14.9384
print((~skip).sum(), round(m.loc[~skip, 'realized pnl'].sum(), 4))
# 65, 47.4746
```
