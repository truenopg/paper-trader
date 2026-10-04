# Intraday strategy search (5m-4h) - results so far

Question: is there an intraday rule-based strategy on crypto or gold that keeps
daily drawdown under 5% and total under 10%, and survives out-of-sample with
realistic costs? Short answer so far: **no robust winner. Small edges exist,
none that survives honest selection.**

## Setup
- Data (free): Binance public archive 5m for BTC, ETH, SOL, BNB, XRP, ADA, PAXG
  (2021-01 to 2026-08); real XAUUSD spot ticks from Dukascopy rebuilt into 5m bars
  (06-18 UTC, weekdays; `fetch_dukascopy.py`).
- Engine (`engine.py`): signal on a closed bar, fill at next open, stop checked
  before target within a bar (pessimistic), time exit, per-day loss halt, costs in bps/side.
- Families (`signals.py`): Donchian breakout, EMA cross, RSI reversion, Bollinger fade, opening-range breakout,
  with trend/session filters, ATR stops, RR 1-4, 5m/15m/1h/4h. ~35,000 configs in total.
- Split: train 2021-01..2023-06, out-of-sample 2023-07..2026-08. Risk 0.5% per trade, 2% daily halt.
  Survivor = positive and PF>1.15 in both periods, >=100 trades each, DD inside 5% daily / 10% total.

## Results
| Test | Outcome |
|---|---|
| BTC, gold token, 5m-1h, realistic costs (7.5 bps/side crypto) | 0 of ~8,000 configs profitable in both periods |
| Crypto basket (6 coins) 15m-4h, 7.5-10 bps/side | 73 survivors, almost all 4h Donchian |
| Same family, honest walk-forward (one param set chosen per year from past data) | PF 1.02, +0.012R/trade, maxDD -13% pooled: edge gone, DD limit broken |
| Real XAUUSD, 1 bp/side | 4 survivors, all 1h RSI(2) reversion vs EMA200; OOS PF 1.17-1.26, ~2-4% CAGR, maxDD -5% to -7% |
| Real XAUUSD, 2 bps/side | 1 survivor of 3,984 |

## Read
Picking the best of thousands of configs finds lucky ones; walk-forward removes most of the luck.
The only idea that repeats on real data is a very small gold mean-reversion edge (~0.05-0.1R per
trade). Treat it as a hypothesis to test forward on a demo account, not as a system.

## Not tested yet
FX and index CFDs, volatility-regime and multi-timeframe families, ensembles of weak uncorrelated edges.
