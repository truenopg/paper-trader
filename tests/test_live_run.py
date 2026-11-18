import unittest
from datetime import datetime
from unittest.mock import MagicMock

from bt.core import Bar, Order, Side
from live.run_daily import LiveGate, run_asset, ASSETS, CASH_USD, LIVE_START


def make_bar(day: int) -> Bar:
    return Bar(datetime(2026, 11, day), 100.0, 101.0, 99.0, 100.0, 0.0)


class StubStrategy:
    """Always wants to buy 1 unit on every bar."""

    def on_bar(self, bar, broker):
        if broker.position == 0:
            return Order(Side.BUY, 1.0)
        return None


class TestLiveGate(unittest.TestCase):
    def test_suppresses_before_start_allows_after(self):
        gate = LiveGate(StubStrategy(), datetime(2026, 11, 7))
        broker = MagicMock()
        broker.position = 0
        self.assertIsNone(gate.on_bar(make_bar(6), broker))
        self.assertIsNotNone(gate.on_bar(make_bar(7), broker))

    def test_inner_still_sees_bars_for_warmup(self):
        inner = StubStrategy()
        gate = LiveGate(inner, datetime(2026, 11, 7))
        broker = MagicMock()
        broker.position = 0
        seen = []
        orig = inner.on_bar
        inner.on_bar = lambda b, br: (seen.append(b.ts), orig(b, br))[1]
        gate.on_bar(make_bar(1), broker)
        self.assertEqual(len(seen), 1)


class TestRunAssetOnRealData(unittest.TestCase):
    """The live account starts flat: no inherited backtest positions."""

    def test_no_fills_before_live_start(self):
        # The gate must suppress every pre-start signal on real data. Once
        # the strategy trades after LIVE_START, equity leaves 10k and this
        # is the assertion that keeps holding.
        r = run_asset("BTC", ASSETS["BTC"])
        for f in r["_bt"].broker.fills:
            self.assertGreaterEqual(f.ts, LIVE_START)
        self.assertGreaterEqual(r["last_bar_date"], "2026-11-06")

    def test_flat_until_first_live_signal(self):
        r = run_asset("BTC", ASSETS["BTC"])
        if r["fills"] == 0:
            self.assertEqual(r["equity_usd"], CASH_USD)
            self.assertIsNone(r["open"])


if __name__ == "__main__":
    unittest.main()
