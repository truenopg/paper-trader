#!/usr/bin/env python3
"""Run the candidate strategies on real data with the honest protocol.

    python research/run_backtests.py

Protocol (from STRATEGIES.md): in-sample to 2023-12-31, out-of-sample
2024-01-01 on; costs XAUUSD 3 bps/side, BTC 25 bps/side (split between
commission and slippage); every strategy sized at 1% risk per trade.
Buy & hold on the same window is the benchmark that matters: a strategy
that loses to it after costs has no reason to exist.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import research  # noqa: F401 - wires the vendored engine path
from research.strategies import DonchianBreakout, RsiMeanReversion, SmaTrendCross
from bt.broker import Broker, CostModel
from bt.data import load_csv
from bt.engine import Backtest
from bt.stats import summary, trade_stats
from bt.strategies import BuyAndHold

OOS_START = datetime(2024, 1, 1)
TS_FORMAT = "%Y-%m-%dT%H:%M:%S"

ASSETS = {
    "BTC": ("research/data/btc_1d.csv", CostModel(commission_bps=12.5, slippage_bps=12.5)),
    "XAUUSD": ("research/data/xauusd_1d.csv", CostModel(commission_bps=1.5, slippage_bps=1.5)),
}

STRATEGIES = [
    ("S1 donchian trail", lambda: DonchianBreakout()),
    ("S1 donchian 3R", lambda: DonchianBreakout(target_r=3.0)),
    ("S2 rsi mean-rev", lambda: RsiMeanReversion()),
    ("S3 sma cross trail", lambda: SmaTrendCross()),
    ("S3 sma cross 3R", lambda: SmaTrendCross(target_r=3.0)),
]

CASH = 10_000.0


def run(strategy, bars, costs) -> str:
    bt = Backtest(strategy, Broker(CASH, costs))
    bt.run(bars)
    s = summary(bt.equity_curve)
    t = trade_stats(bt.broker.fills)
    return (f"ret {s['total_return']:+7.1%}  sharpe {s['sharpe']:5.2f}  "
            f"maxDD {s['max_drawdown']:6.1%} ({s['max_drawdown_duration']:3} bars)  "
            f"trades {t['trades']:3}  win {t['win_rate']:3.0%}  PF {t['profit_factor']:5.2f}")


def main() -> None:
    for asset, (path, costs) in ASSETS.items():
        bars = load_csv(path, ts_format=TS_FORMAT)
        in_sample = [b for b in bars if b.ts < OOS_START]
        oos = [b for b in bars if b.ts >= OOS_START]
        print(f"\n== {asset} daily: {len(in_sample)} IS bars "
              f"({in_sample[0].ts.date()}..{in_sample[-1].ts.date()}), "
              f"{len(oos)} OOS bars ({oos[0].ts.date()}..{oos[-1].ts.date()}) ==")
        for period, subset in [("IS ", in_sample), ("OOS", oos)]:
            print(f"  {period} buy&hold       : {run(BuyAndHold(), subset, costs)}")
            for name, make in STRATEGIES:
                print(f"  {period} {name:17}: {run(make(), subset, costs)}")


if __name__ == "__main__":
    main()
