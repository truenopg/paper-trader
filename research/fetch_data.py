#!/usr/bin/env python3
"""Download real OHLCV data for the strategy research, no API keys.

    python research/fetch_data.py btc_1d     # BTC-USD daily, Coinbase, since 2015
    python research/fetch_data.py btc_4h     # BTC-USD 4h, Coinbase, since 2020
    python research/fetch_data.py xauusd_1d  # gold daily, Yahoo GC=F futures (XAUUSD proxy)
    python research/fetch_data.py all

Sources (all public, no vendor account):
- Coinbase Exchange candles API: 300 candles per request, paginated.
  Candles come as [time, low, high, open, close, volume], newest first.
  (BTC daily and 1h; Binance klines would be first choice but geo-blocks
  this network, Coinbase spot BTC-USD is the honest substitute. Kraken
  also works but clamps history to the newest 720 candles when `since`
  is far in the past, so it cannot page deep history forward.)
  Coinbase has no 4h granularity, so btc_4h is 1h bars resampled to 4h,
  aligned to 00/04/08/12/16/20 UTC like standard charting platforms.
- Yahoo Finance chart API: GC=F front-month gold futures as the XAUUSD
  spot proxy. Futures track spot closely on the daily scale; the basis
  is noise next to CFD spreads. Documented so nobody mistakes it for
  actual spot ticks.

Output: CSV with the bt engine's loader format (ts,open,high,low,close,volume),
one row per bar, oldest first, UTC timestamps.
"""
from __future__ import annotations

import csv
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
UA = {"User-Agent": "Mozilla/5.0 (research data fetch)"}


def _get_json(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_coinbase(symbol: str, granularity: int, start: datetime, end: datetime):
    """Paginate Coinbase candles (max 300/request) from start to end (UTC)."""
    bars = []
    page_end = end
    while page_end > start:
        page_start = max(start, page_end - timedelta(seconds=granularity * 299))
        url = (f"https://api.exchange.coinbase.com/products/{symbol}/candles"
               f"?granularity={granularity}"
               f"&start={page_start.isoformat()}&end={page_end.isoformat()}")
        chunk = _get_json(url)
        if not chunk:
            break
        for t, low, high, open_, close, vol in chunk:
            bars.append((int(t), open_, high, low, close, vol))
        oldest = min(c[0] for c in chunk)
        new_end = datetime.fromtimestamp(oldest, tz=timezone.utc)
        if new_end >= page_end:
            break  # hit the earliest data the exchange has
        page_end = new_end
        if page_end <= start:
            break
        time.sleep(0.15)  # polite pacing
    return sorted(set(bars))


def fetch_yahoo_daily(symbol: str, start: datetime, end: datetime):
    """Daily bars from the Yahoo chart API."""
    p1, p2 = int(start.timestamp()), int(end.timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.parse.quote(symbol)}?period1={p1}&period2={p2}&interval=1d")
    result = _get_json(url)["chart"]["result"][0]
    ts = result["timestamp"]
    q = result["indicators"]["quote"][0]
    bars = []
    for i, t in enumerate(ts):
        if q["open"][i] is None:  # holidays / gaps
            continue
        bars.append((int(t), q["open"][i], q["high"][i], q["low"][i],
                     q["close"][i], q["volume"][i] or 0.0))
    return sorted(bars)


def resample(bars, seconds: int):
    """Aggregate 1h-style bars into larger aligned candles (o/h/l/c/v)."""
    out = {}
    for t, o, h, l, c, v in sorted(bars):
        bucket = t - t % seconds
        if bucket in out:
            b = out[bucket]
            out[bucket] = (bucket, b[1], max(b[2], h), min(b[3], l), c, b[5] + v)
        else:
            out[bucket] = (bucket, o, h, l, c, v)
    return [out[k] for k in sorted(out)]


def write_csv(bars, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts", "open", "high", "low", "close", "volume"])
        for t, o, h, l, c, v in bars:
            ts = datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
            w.writerow([ts, f"{o:.2f}", f"{h:.2f}", f"{l:.2f}", f"{c:.2f}", f"{v:.4f}"])
    return len(bars)


JOBS = {
    "btc_1d": ("BTC-USD daily (Coinbase, since 2015)", "btc_1d.csv",
               lambda: fetch_coinbase("BTC-USD", 86400,
                                      datetime(2015, 1, 1, tzinfo=timezone.utc),
                                      datetime.now(timezone.utc))),
    "btc_4h": ("BTC-USD 4h (Coinbase 1h resampled, since 2020)", "btc_4h.csv",
               lambda: resample(fetch_coinbase("BTC-USD", 3600,
                                               datetime(2020, 1, 1, tzinfo=timezone.utc),
                                               datetime.now(timezone.utc)), 4 * 3600)),
    "xauusd_1d": ("gold daily (Yahoo GC=F, XAUUSD proxy, since 2010)", "xauusd_1d.csv",
                  lambda: fetch_yahoo_daily("GC=F",
                                            datetime(2010, 1, 1, tzinfo=timezone.utc),
                                            datetime.now(timezone.utc))),
}


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for name in (JOBS if which == "all" else [which]):
        desc, filename, fetch = JOBS[name]
        n = write_csv(fetch(), DATA_DIR / filename)
        print(f"{filename}: {n} bars - {desc}")


if __name__ == "__main__":
    main()
