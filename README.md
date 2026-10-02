# paper-trader

A live paper-trading bot: rule-based strategies connected to real market
data, trading virtual money with realistic costs, state persisted between
runs, and a daily P&L curve you can watch grow (or shrink) honestly.

Built on top of [backtest-engine](https://github.com/truenopg/backtest-engine):
the same event-driven engine that backtests a strategy runs it live, one new
bar at a time. If a strategy cannot survive the backtest honestly, it does
not get to trade paper money.

## Status

Research phase done: three rule-based strategies for XAUUSD and BTC are
specified, backtested on real data with realistic costs and an
in-sample / out-of-sample split, and tested against shuffled-price nulls.
Results, including the failures, are in [research/README.md](research/README.md).
Short version: nothing beats buy & hold on return; the Donchian breakout is the
most consistent and cuts drawdown a lot. Next: the live paper broker.

## Roadmap

- [x] `research/` rule-based strategies for XAUUSD/BTC with honest backtests
- Live data feeds (no paid vendors): Coinbase candles, Yahoo
- Paper broker: virtual cash, realistic spreads, persisted state
- Daily P&L report and signal log
