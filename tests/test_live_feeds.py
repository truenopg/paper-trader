import csv
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from live.fetch import (append_bars, check_stale, closed_only, read_last_ts,
                        trim_csv)


def bar(days_ago: int, price: float = 100.0):
    dt = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0,
                                            microsecond=0) - timedelta(days=days_ago)
    return (int(dt.timestamp()), price, price + 1, price - 1, price, 1.0)


class TestClosedOnly(unittest.TestCase):
    def test_drops_todays_partial_bar(self):
        today = datetime.now(timezone.utc).replace(hour=10, minute=0,
                                                   second=0, microsecond=0)
        partial = (int(today.timestamp()), 1.0, 1.0, 1.0, 1.0, 1.0)
        self.assertEqual(closed_only([bar(1), partial]), [bar(1)])

    def test_keeps_yesterday(self):
        self.assertEqual(closed_only([bar(1)]), [bar(1)])


class TestCsvRoundTrip(unittest.TestCase):
    def test_append_and_read_last_ts(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "x.csv"
            append_bars(p, [bar(3), bar(2)])
            append_bars(p, [bar(1)])
            self.assertEqual(read_last_ts(p), bar(1)[0])
            with open(p) as f:
                rows = list(csv.reader(f))
            self.assertEqual(rows[0], ["ts", "open", "high", "low", "close", "volume"])
            self.assertEqual(len(rows), 4)
            datetime.strptime(rows[1][0], "%Y-%m-%dT%H:%M:%S")

    def test_trim_keeps_newest(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "x.csv"
            append_bars(p, [bar(i, 100 + i) for i in range(10, 0, -1)])
            trim_csv(p, keep=3)
            with open(p) as f:
                rows = list(csv.reader(f))
            self.assertEqual(len(rows), 4)
            self.assertEqual(read_last_ts(p), bar(1, 101)[0])


class TestCheckStale(unittest.TestCase):
    def test_missing_file(self):
        self.assertIn("no data", check_stale(Path("/nonexistent.csv"), 2))

    def test_fresh_ok(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "x.csv"
            append_bars(p, [bar(1)])
            self.assertIsNone(check_stale(p, 2))

    def test_stale_flagged(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "x.csv"
            append_bars(p, [bar(9)])
            self.assertIn("days old", check_stale(p, 2))


if __name__ == "__main__":
    unittest.main()
