# paper-trader

A live paper-trading bot: rule-based strategies connected to real market
data, trading virtual money with realistic costs, state persisted between
runs, and a daily P&L curve you can watch grow (or shrink) honestly.

Built on top of [backtest-engine](https://github.com/truenopg/backtest-engine):
the same event-driven engine that backtests a strategy runs it live, one new
bar at a time. If a strategy cannot survive the backtest honestly, it does
not get to trade paper money.

## Status

Week 1 of the project: strategy research. The `research/` folder holds fully
specified rule-based strategies for XAUUSD and BTC - objective entries,
exits, filters and sizing, written so a human can execute them manually with
discipline (no EA required) - plus their honest backtest results, including
the failures. Only validated strategies get wired into the live bot.

## Roadmap

- `research/` rule-based strategies for XAUUSD/BTC with honest backtests
- Live data feeds (no paid vendors): Binance klines, stooq
- Paper broker: virtual cash, realistic spreads, persisted state
- Daily P&L report and signal log
