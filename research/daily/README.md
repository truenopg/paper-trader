# Daily multi-asset lab (free Yahoo data, 2005-2026)

18 markets: 7 FX majors, 6 equity indices, gold/silver/oil, BTC, ETH. Five families (Donchian, SMA cross,
time-series momentum, RSI(2) reversion, Bollinger reversion), 18 configs each, costs 1-3 bps/side, each sleeve
scaled to 10% vol. `python multi_asset.py` builds the data, `python wf.py` runs the evaluation.

Results, out of sample 2015-2026, no selection (equal-weight over all configs):

| Group | CAGR | Sharpe | Max DD |
|---|---|---|---|
| All families, all assets | 0.5% | 0.27 | -5.2% |
| Time-series momentum | 1.0% | 0.40 | -6.7% |
| Crypto only | 3.1% | 0.61 | -11.7% |
| FX only | -0.9% | -0.28 | -17.5% |
| Bollinger reversion | -1.0% | -0.27 | -21.4% |

Walk-forward (each year pick top 3 configs per asset by 5y Sharpe): Sharpe 0.26 over 20 years, max DD -11.5%.
Null (random 20-day positions on the same assets, 200 runs): 95th percentile Sharpe 0.42, so the walk-forward
result (0.32 since 2015) is not distinguishable from luck.

Conclusion: classic daily rules on free data show no edge that survives. FX trend is negative since 2015.
