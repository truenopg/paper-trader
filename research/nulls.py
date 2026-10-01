#!/usr/bin/env python3
"""Null-hypothesis test: does a strategy beat shuffled history?

    python research/nulls.py [n_shuffles]

Each bar is turned into (gap, high/low/close relative to open). The bars are
shuffled in random order and re-chained into a price path, so volatility and
bar shape are kept but trend and serial structure are destroyed. A trend or
breakout rule that "works" only because of real autocorrelation should score
near the null median; one that is just lucky should sit inside the null band.
The result is the percentile of the real full-sample Sharpe in the null set.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import research  # noqa: F401
from research.run_backtests import ASSETS, CASH, STRATEGIES, TS_FORMAT
from bt.broker import Broker
from bt.core import Bar
from bt.data import load_csv
from bt.engine import Backtest
from bt.stats import summary


def shuffled_path(bars, rng):
    """Re-chain bars in random order, keeping each bar's shape and gap."""
    shapes = []
    prev_close = bars[0].open
    for b in bars:
        shapes.append((b.open / prev_close, b.high / b.open, b.low / b.open,
                       b.close / b.open, b.volume))
        prev_close = b.close
    rng.shuffle(shapes)
    out, price = [], bars[0].open
    for b, (gap, hi, lo, cl, vol) in zip(bars, shapes):
        o = price * gap
        out.append(Bar(b.ts, o, o * hi, o * lo, o * cl, vol))
        price = o * cl
    return out


def sharpe(strategy, bars, costs):
    bt = Backtest(strategy, Broker(CASH, costs))
    bt.run(bars)
    return summary(bt.equity_curve)["sharpe"]


def main(n: int = 100) -> None:
    rng = random.Random(42)
    for asset, (path, costs) in ASSETS.items():
        bars = load_csv(path, ts_format=TS_FORMAT)
        print(f"\n== {asset}: {len(bars)} bars, {n} shuffles ==")
        for name, make in STRATEGIES:
            real = sharpe(make(), bars, costs)
            null = sorted(sharpe(make(), shuffled_path(bars, rng), costs) for _ in range(n))
            pct = sum(x < real for x in null) / n
            print(f"  {name:17}: real sharpe {real:5.2f}  null median {null[n // 2]:5.2f}  "
                  f"null p95 {null[int(n * .95)]:5.2f}  real beats {pct:4.0%} of nulls")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 100)
