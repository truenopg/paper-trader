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
most consistent and cuts drawdown a lot. A one-page [manual playbook](research/PLAYBOOK.md) turns the Donchian rules into
something tradable by hand. The live paper broker below turns it into a
daily-running bot.

## Live paper trading

`live/` runs the research winner - S1 Donchian breakout, 3R variant - one new
daily bar at a time, on paper, with the same engine and cost model as the
backtests. It is the backtest continued forward, not a new strategy.

- **Account**: two independent sleeves of 10,000 USD virtual each (BTC and
  gold), 1% risk per trade. The account is denominated in USD because both
  data series are USD; no FX conversion is applied anywhere. Paper money
  only - no exchange account, no real orders, ever.
- **Flat start**: live from 2026-11-07. The full price history is replayed
  so indicators warm up, but orders before that date are suppressed: no
  positions inherited from the backtest, no fabricated live history. The
  equity curve starts at 20,000 USD.
- **Costs** (modeling assumptions from the research protocol, not a claim
  about any real venue): BTC 25 bps per side, gold 3 bps per side, split
  between commission and slippage. Fills at the next bar's open.
- **Data**: Coinbase BTC-USD spot daily candles and Yahoo GC=F front-month
  gold futures (XAUUSD proxy, same caveat as the research). Both public, no
  keys. Only closed bars are used; the still-forming bar of the current day
  is never read. Stale-feed checks warn in the state file.
- **Schedule**: a GitHub Actions cron runs it daily after both markets'
  daily bars are final, then commits the new state. The repository itself
  is the dashboard:
  - `state/paper_state.json` - current positions, stops, equity, warnings
  - `report/equity.csv` - the daily equity curve, one row per day
  - `report/SIGNAL_LOG.md` - one line per paper fill

## Roadmap

- [x] `research/` rule-based strategies for XAUUSD/BTC with honest backtests
- [x] Live data feeds (no paid vendors): Coinbase candles, Yahoo
- [x] Paper broker: virtual cash, realistic spreads, persisted state
- [x] Daily P&L report and signal log
