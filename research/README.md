# Research results - XAUUSD & BTC rule-based strategies

Three mechanical strategies ([specs](STRATEGIES.md)), fixed before looking at
results, run through [backtest-engine](https://github.com/truenopg/backtest-engine)
with next-bar fills, costs on every fill (BTC 25 bps/side, XAUUSD 3 bps/side),
1% risk per trade. In-sample (IS) to 2023-12-31, out-of-sample (OOS) from
2024-01-01. Reproduce: `python3 research/run_backtests.py`, `python3 research/nulls.py 200`.

Data: BTC daily from Coinbase (2015-07 on), gold daily from Yahoo GC=F futures
(2010 on) as a proxy for XAUUSD spot. See `data/` and `fetch_data.py`.

## Out-of-sample results (2024-01 to 2026-09)

| Strategy | BTC ret | BTC Sharpe | BTC maxDD | BTC trades | Gold ret | Gold Sharpe | Gold maxDD | Gold trades |
|---|---|---|---|---|---|---|---|---|
| Buy & hold | +83.7% | 0.59 | -52.1% | - | +95.5% | 1.25 | -24.4% | - |
| S1 Donchian, trailing exit | +8.5% | 0.52 | -5.0% | 9 | +13.1% | 0.67 | -7.9% | 6 |
| S1 Donchian, 3R target | +9.4% | 0.80 | -4.2% | 11 | +10.9% | 1.18 | -2.6% | 12 |
| S2 RSI(3) mean reversion | +3.8% | 0.91 | -0.9% | 6 | +0.8% | 0.27 | -1.4% | 7 |
| S3 SMA 20/50 cross, trailing | +0.3% | 0.04 | -4.1% | 10 | +16.1% | 0.85 | -7.3% | 2 |
| S3 SMA 20/50 cross, 3R | +6.0% | 0.67 | -3.0% | 6 | +6.2% | 1.52 | -1.2% | 2 |

## In-sample results (BTC from 2015, gold from 2010 to 2023)

| Strategy | BTC ret | BTC PF | Gold ret | Gold PF |
|---|---|---|---|---|
| Buy & hold | +14252% | - | +81.0% | - |
| S1 trailing | +146.2% | 4.90 | -9.2% | 0.78 |
| S1 3R | +60.4% | 2.54 | +2.3% | 1.04 |
| S2 RSI | +3.5% | 1.57 | +5.0% | 2.07 |
| S3 trailing | +139.4% | 5.63 | -8.5% | 0.66 |
| S3 3R | +11.9% | 1.72 | -11.0% | 0.56 |

## Null test: shuffled bars (200 shuffles, full sample)

Bars are re-ordered randomly (volatility and bar shape kept, trend and serial
structure destroyed). Column = share of shuffled series the real result beats.

| Strategy | BTC | Gold |
|---|---|---|
| S1 trailing | 90% | 66% |
| S1 3R | 100% | 88% |
| S2 RSI | 85% | 80% |
| S3 trailing | 98% | 64% |
| S3 3R | 99% | 48% |

## What this says, honestly

- **Nothing here beats buy & hold on return.** Both assets rose strongly in the
  OOS window. The strategies trade return for much smaller drawdowns
  (BTC: -4% to -5% vs -52%). Whether that is worth it is a risk preference, not a win.
- **S1 (Donchian breakout) is the most consistent.** Positive in both periods on
  BTC and OOS on gold, in both exit variants. On gold IS it is roughly flat
  (-9% to +2%): the edge is not stable across regimes.
- **S3 trailing fails on BTC OOS** (+0.3%, PF 1.06). Its IS result (+139%) did not carry over.
  Gold S3 looks good OOS but is 2 trades: meaningless.
- **S2 is thin.** Positive but 6-7 trades per period; Sharpe 0.91 on BTC is noise-level evidence.
- **Null test is supportive on BTC, weak on gold.** On BTC most variants beat 85-100%
  of shuffled series; on gold only S1 3R passes 85%, so for gold there is no
  statistical evidence of edge beyond luck. Passing 95% is the usual bar and only
  S1 3R and S3 on BTC clear it.

## Caveats

- Trade counts are low (2-12 per OOS cell). Treat OOS numbers as consistent-or-not, not as precise estimates.
- Gold uses GC=F futures, not XAUUSD spot at a prop firm; costs are flat bps.
- Stops are checked on daily bars and filled at the next open, so intrabar order is unknown.
- One IS/OOS split, no walk-forward. The OOS window was bull-trending for both assets.
- Not investment advice; this is research on past data.
