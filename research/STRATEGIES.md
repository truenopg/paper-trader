# Candidate strategies - XAUUSD & BTC

Three rule-based systems, specified so a human can execute them manually
with zero discretion left: entries, exits, filters, sizing and costs are
all mechanical. No parameter was tuned on the data below - they are round
numbers with a rationale, chosen *before* seeing results. That is the only
honest way to keep the out-of-sample split meaningful.

Conventions:
- Timeframe: daily bars unless stated. Signals computed on closed bars
  only; orders fill at the next bar's open (the engine forbids look-ahead).
- Sizing: fixed fractional risk - every trade risks 1% of current equity
  from entry price to stop distance. No trade if the stop cannot be placed.
- Costs: XAUUSD 3 bps/side, BTC 25 bps/side (retail CFD spread + slippage,
  round numbers on the pessimistic side).
- Evaluation: in-sample = data to 2023-12-31, out-of-sample = 2024-01-01 on.
  A strategy only "passes" if it holds up OOS with these costs.

## S1 - Trend breakout (Donchian 55/20 + regime filter)

The systematized version of "trade structure with 1:3 RR".

- Regime filter: only long when close > SMA(200); only short when close < SMA(200).
- Entry: close breaks the 55-day Donchian extreme in the regime direction
  (highest high for longs, lowest low for shorts).
- Stop: entry -/+ 2 x ATR(20).
- Exit: Donchian 20-day extreme in the opposite direction, or stop hit.
  A variant takes profit at 3R instead of trailing; both are reported.
- Rationale: 55/20 is the classic Turtle window; ATR(20) and 1% risk are
  the most standard sizing choices in the literature.

## S2 - Mean reversion with trend filter (RSI 3)

- Filter: only longs, and only when close > SMA(200) (buy dips in uptrends;
  catching falling knives in downtrends is where mean reversion dies).
- Entry: RSI(3) < 10.
- Exit: close > SMA(20) or RSI(3) > 70; stop at entry - 2 x ATR(20).
- Rationale: RSI(3)<10 in an uptrend is the most replicated short-term
  mean-reversion setup; SMA(200) is the standard regime line.

## S3 - Dual moving-average trend (20/50 + 200)

- Filter: long only above SMA(200), short only below.
- Entry: SMA(20) crosses SMA(50) in the regime direction.
- Stop: 2 x ATR(20) from entry.
- Exit: opposite cross, stop, or 3R target (both variants reported).
- Rationale: 20/50 is the slowest cross that still trades a few times a
  year; anything faster is a costs donation at CFD spreads.

## Null hypothesis

Every strategy is also run on shuffled-return synthetic series with the
same length and volatility. If the real-data edge does not beat the null
distribution, the honest conclusion is that there is no edge - that gets
reported too.
