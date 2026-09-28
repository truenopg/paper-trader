import csv
import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research.fetch_data import write_csv


class TestWriteCsv(unittest.TestCase):
    def test_engine_loader_format(self):
        bars = [
            (1609459200, 29000.0, 29600.0, 28800.0, 29400.0, 123.4),
            (1609545600, 29400.0, 29800.0, 29100.0, 29750.0, 100.0),
        ]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "out.csv"
            write_csv(bars, path)
            rows = list(csv.reader(open(path)))
        self.assertEqual(rows[0], ["ts", "open", "high", "low", "close", "volume"])
        self.assertEqual(rows[1][0], "2021-01-01T00:00:00")
        self.assertEqual(rows[1][1:5], ["29000.00", "29600.00", "28800.00", "29400.00"])
        self.assertEqual(len(rows), 3)


if __name__ == "__main__":
    unittest.main()

class TestResample(unittest.TestCase):
    def test_1h_to_4h_alignment(self):
        from research.fetch_data import resample
        base = 1609459200  # 2021-01-01 00:00 UTC, already 4h aligned
        bars = [(base + i * 3600, 100 + i, 105 + i, 95 - i, 102 + i, 10.0)
                for i in range(8)]
        out = resample(bars, 4 * 3600)
        self.assertEqual(len(out), 2)
        t, o, h, l, c, v = out[0]
        self.assertEqual(t, base)
        self.assertEqual(o, 100)          # first open
        self.assertEqual(h, 108)          # max of highs 105..108
        self.assertEqual(l, 92)           # min of lows 95..92
        self.assertEqual(c, 105)          # last close of the group (i=3)
        self.assertEqual(v, 40.0)         # summed volume
