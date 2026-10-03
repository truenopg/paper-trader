# Manual playbook - S1 Donchian breakout (daily chart)

The one strategy that held up in both periods and both assets (see
[README](README.md)). Written so it can be traded by hand, no EA. Past
results do not guarantee anything; the OOS edge rests on 6-12 trades per asset.

Check once per day, after the daily candle closes. Never intraday.

## Long setup (mirror for shorts)
1. **Regime**: daily close above the 200-day SMA. Below it, no longs.
2. **Trigger**: daily close is above the highest high of the previous 55 days.
3. **Entry**: market order at the next day's open.
4. **Stop**: entry minus 2 x ATR(20) (ATR of the last 20 daily candles). Place it immediately.
5. **Size**: risk 1% of account. Lots = (account x 1%) / (entry - stop) in price units x contract value. No stop, no trade.
6. **Exit, variant A (trail)**: close below the lowest low of the previous 20 days, exit at next open.
   **Variant B (3R)**: take profit at entry + 3 x (entry - stop).
7. One position per asset. No adding, no moving the stop away, no override because "it looks weak".

## Shorts
Same, with close below SMA(200), close below the lowest low of 55 days, stop entry + 2 x ATR(20), exit above the highest high of 20 days or at 3R.

## Expect
- Win rate 33-67% depending on variant; few trades (a handful per year per asset).
- Long flat stretches and drawdowns of months. Losses are normal; the stop is the rule.
- Costs matter: use the tightest spread you can; avoid entries around news spikes.

## Prop-firm notes
Check your firm's daily-loss and max-drawdown rules against 1% risk per trade
(two losing trades on two assets in a day is 2%). Rules are mechanical, so
they are allowed as manual trading, but confirm the firm's own terms.
