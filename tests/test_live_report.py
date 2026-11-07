import csv
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from live import report


class TestStateRoundTrip(unittest.TestCase):
    def test_write_and_load(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "state.json"
            report.write_state({"a": 1, "nested": {"b": [1, 2]}}, p)
            self.assertEqual(report.load_state(p)["nested"]["b"], [1, 2])
            json.loads(p.read_text())  # valid JSON

    def test_load_missing(self):
        self.assertIsNone(report.load_state(Path("/nonexistent.json")))


class TestEquityCsv(unittest.TestCase):
    def test_format(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "equity.csv"
            report.write_equity([{"date": "2026-11-07", "BTC": 10000.0,
                                  "XAUUSD": 10010.5, "TOTAL": 20010.5}], p)
            with open(p) as f:
                rows = list(csv.reader(f))
            self.assertEqual(rows[0], ["date", "BTC", "XAUUSD", "TOTAL"])
            self.assertEqual(rows[1], ["2026-11-07", "10000.00", "10010.50", "20010.50"])


class TestSignalLog(unittest.TestCase):
    def test_header_once_and_append(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "SIGNAL_LOG.md"
            report.append_log(["- 2026-11-08 BTC buy 0.1 @ 100.00 (commission 1.25)"], p)
            report.append_log(["- 2026-11-09 XAUUSD sell 0.5 @ 4000.00 (commission 0.60)"], p)
            text = p.read_text()
            self.assertEqual(text.count("# Signal and fill log"), 1)
            self.assertIn("BTC buy", text)
            self.assertIn("XAUUSD sell", text)

    def test_empty_events_no_file(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "SIGNAL_LOG.md"
            report.append_log([], p)
            self.assertFalse(p.exists())


if __name__ == "__main__":
    unittest.main()
