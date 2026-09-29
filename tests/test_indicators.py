import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import research  # noqa: F401 - wires the vendored engine path
from research.indicators import atr, donchian, rsi, sma


class TestSma(unittest.TestCase):
    def test_window_padding_and_values(self):
        self.assertEqual(sma([1.0, 2.0, 3.0, 4.0], 2), [None, 1.5, 2.5, 3.5])

    def test_constant_series(self):
        self.assertEqual(sma([5.0] * 10, 5)[-1], 5.0)


class TestRsi(unittest.TestCase):
    def test_all_gains_is_100(self):
        self.assertEqual(rsi([1, 2, 3, 4, 5, 6], 3)[-1], 100.0)

    def test_all_losses_is_0(self):
        self.assertEqual(rsi([6, 5, 4, 3, 2, 1], 3)[-1], 0.0)

    def test_bounded(self):
        values = rsi([10, 11, 9, 10, 8, 12, 7, 11, 9, 10], 3)
        for v in values:
            if v is not None:
                self.assertTrue(0.0 <= v <= 100.0)


class TestAtr(unittest.TestCase):
    def test_constant_range(self):
        # every bar ranges 1.0 with no gaps: ATR = 1.0
        self.assertAlmostEqual(atr([2.0] * 6, [1.0] * 6, [1.5] * 6, 2)[-1], 1.0)

    def test_gap_counts_in_true_range(self):
        highs = [10.0, 13.0]
        lows = [9.0, 12.0]
        closes = [9.5, 12.5]
        # TR bar2 = max(1, |13-9.5|, |12-9.5|) = 3.5
        self.assertAlmostEqual(atr(highs, lows, closes, 1)[-1], 3.5)


class TestDonchian(unittest.TestCase):
    def test_excludes_current_bar(self):
        highs = [1.0, 2.0, 9.0, 3.0]
        lows = [0.5, 1.0, 0.1, 2.0]
        upper, lower = donchian(highs, lows, 2)
        # at i=2 the channel looks at bars 0-1: upper 2.0, lower 0.5
        self.assertEqual(upper[2], 2.0)
        self.assertEqual(lower[2], 0.5)
        # at i=3 it looks at bars 1-2: upper 9.0, lower 0.1
        self.assertEqual(upper[3], 9.0)
        self.assertEqual(lower[3], 0.1)


if __name__ == "__main__":
    unittest.main()
