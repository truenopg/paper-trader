import unittest
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import research  # noqa: F401
from research.strategies import DonchianBreakout
from bt.broker import Broker, CostModel
from bt.core import Bar
from bt.engine import Backtest


def make_bars(closes, spread=1.0):
    ts = datetime(2020, 1, 1)
    bars = []
    for c in closes:
        bars.append(Bar(ts, c, c + spread / 2, c - spread / 2, c, 100.0))
        ts += timedelta(days=1)
    return bars


def uptrend_then_breakout(n_trend=220, breakout_close=130.0):
    closes = [100.0 + 0.1 * i for i in range(n_trend)]
    return closes + [breakout_close]


class TestDonchianBreakout(unittest.TestCase):
    def test_no_entry_below_trend_sma(self):
        # falling series: any "breakout" happens below SMA(200)
        closes = [300.0 - 0.5 * i for i in range(240)]
        closes.append(max(closes[-55:]) + 5.0)  # pop above the 55-bar high
        bt = Backtest(DonchianBreakout(), Broker(10_000.0, CostModel(0, 0)))
        bt.run(make_bars(closes))
        self.assertEqual(len(bt.broker.fills), 0)

    def test_entry_sizes_to_one_percent_risk(self):
        bt = Backtest(DonchianBreakout(), Broker(10_000.0, CostModel(0, 0)))
        # one bar after the signal: the engine fills at the NEXT bar's open
        bt.run(make_bars(uptrend_then_breakout() + [130.5]))
        buys = [f for f in bt.broker.fills if f.side.value == "buy"]
        self.assertEqual(len(buys), 1)
        # qty x stop distance (2 x ATR ~ 2 x 1.0) risks about 1% of 10k
        self.assertAlmostEqual(buys[0].qty * 2.0, 100.0, delta=15.0)

    def test_stop_exit_closes_position(self):
        closes = uptrend_then_breakout()
        closes += [129.0, 128.0]  # entry fills at next open after signal
        bt = Backtest(DonchianBreakout(), Broker(10_000.0, CostModel(0, 0)))
        bt.run(make_bars(closes))
        self.assertGreater(bt.broker.position, 0)
        # crash bar: low far below the stop (~128)
        crash = make_bars([100.0], spread=60.0)
        crash[0] = Bar(crash[0].ts, 128.0, 129.0, 100.0, 105.0, 100.0)
        bt.run(crash + make_bars([104.0]))
        self.assertEqual(bt.broker.position, 0)

    def test_target_variant_exits_at_3r(self):
        closes = uptrend_then_breakout() + [129.5]
        bt = Backtest(DonchianBreakout(target_r=3.0), Broker(10_000.0, CostModel(0, 0)))
        bt.run(make_bars(closes))
        self.assertGreater(bt.broker.position, 0)
        moon = make_bars([150.0], spread=20.0)  # high clears the 3R target
        bt.run(moon + make_bars([151.0]))
        self.assertEqual(bt.broker.position, 0)


if __name__ == "__main__":
    unittest.main()
