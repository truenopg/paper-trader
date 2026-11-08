"""Incremental daily-bar feeds for the live bot. Public APIs, no keys.

Seeds: research/data CSVs (real downloads from the same sources, see
research/fetch_data.py). Each update appends only CLOSED daily bars: a
bar whose UTC day is today is still forming and is never written.

Staleness: crypto trades 24/7, gold futures do not (weekend + holiday
gaps are normal). check_stale flags only gaps beyond those norms.
"""
from __future__ import annotations

import csv
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

UA = {"User-Agent": "Mozilla/5.0 (paper-trader live feed)"}
TS_FORMAT = "%Y-%m-%dT%H:%M:%S"

Bar = Tuple[int, float, float, float, float, float]  # ts, o, h, l, c, v


def _get_json(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _today_utc() -> datetime:
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def read_last_ts(path: Path) -> Optional[int]:
    """Epoch seconds of the last row, or None. CSVs store ISO UTC strings."""
    if not path.exists():
        return None
    last = None
    with open(path) as f:
        for row in csv.reader(f):
            if row and row[0] != "ts":
                dt = datetime.strptime(row[0], TS_FORMAT).replace(tzinfo=timezone.utc)
                last = int(dt.timestamp())
    return last


def append_bars(path: Path, bars: List[Bar]) -> int:
    if not bars:
        return 0
    write_header = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["ts", "open", "high", "low", "close", "volume"])
        for b in bars:
            iso = datetime.fromtimestamp(b[0], tz=timezone.utc).strftime(TS_FORMAT)
            w.writerow([iso] + list(b[1:]))
    return len(bars)


def fetch_coinbase_daily(symbol: str, start: datetime, end: datetime) -> List[Bar]:
    """Coinbase Exchange daily candles from start to end (UTC), oldest first.

    Candles arrive [time, low, high, open, close, volume], newest first.
    """
    bars: List[Bar] = []
    page_end = end
    while page_end > start:
        page_start = max(start, page_end - timedelta(days=299))
        url = (f"https://api.exchange.coinbase.com/products/{symbol}/candles"
               f"?granularity=86400"
               f"&start={page_start.isoformat()}&end={page_end.isoformat()}")
        chunk = _get_json(url)
        if not chunk:
            break
        for t, low, high, open_, close, vol in chunk:
            bars.append((int(t), open_, high, low, close, vol))
        oldest = min(c[0] for c in chunk)
        page_end = datetime.fromtimestamp(oldest, tz=timezone.utc)
    bars.sort(key=lambda b: b[0])
    return bars


def fetch_yahoo_daily(symbol: str, start: datetime, end: datetime) -> List[Bar]:
    """Yahoo Finance chart API daily bars (GC=F front month as XAUUSD proxy)."""
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
           f"?interval=1d&period1={int(start.timestamp())}&period2={int(end.timestamp())}")
    payload = _get_json(url)
    result = payload["chart"]["result"][0]
    ts = result.get("timestamp", [])
    quote = result["indicators"]["quote"][0]
    bars: List[Bar] = []
    for i, t in enumerate(ts):
        o, h, l, c = quote["open"][i], quote["high"][i], quote["low"][i], quote["close"][i]
        if o is None or h is None or l is None or c is None:
            continue
        bars.append((int(t), float(o), float(h), float(l), float(c),
                     float(quote["volume"][i] or 0)))
    return bars


def closed_only(bars: List[Bar]) -> List[Bar]:
    """Drop the bar of the current UTC day: it is still forming."""
    today = int(_today_utc().timestamp())
    return [b for b in bars if b[0] < today]


def update_feed(path: Path, source: str) -> int:
    """Append new closed bars to a CSV. Returns the number added."""
    last = read_last_ts(path)
    start = (datetime.fromtimestamp(last, tz=timezone.utc) + timedelta(days=1)
             if last else datetime(2015, 1, 1, tzinfo=timezone.utc))
    end = _today_utc() + timedelta(days=1)
    if start >= _today_utc():
        return 0
    if source == "coinbase":
        new = fetch_coinbase_daily("BTC-USD", start, end)
    elif source == "yahoo":
        new = fetch_yahoo_daily("GC=F", start, end)
    else:
        raise ValueError(f"unknown source {source}")
    new = closed_only(new)
    # Dedup by UTC calendar day, not timestamp: Yahoo moves GC=F bar times
    # (05:00 vs 21:59:59 for the same day), which would otherwise append a
    # duplicate daily bar. On conflict the newest version of the day wins.
    by_day = {}
    for b in new:
        by_day[datetime.fromtimestamp(b[0], tz=timezone.utc).date()] = b
    if last:
        last_day = datetime.fromtimestamp(last, tz=timezone.utc).date()
        by_day = {d: b for d, b in by_day.items() if d > last_day}
    return append_bars(path, [by_day[d] for d in sorted(by_day)])


def check_stale(path: Path, max_gap_days: int) -> Optional[str]:
    """Warn if the newest bar is older than max_gap_days (feed problem)."""
    last = read_last_ts(path)
    if last is None:
        return f"{path.name}: no data at all"
    age = _today_utc() - datetime.fromtimestamp(last, tz=timezone.utc)
    if age.days > max_gap_days:
        return f"{path.name}: newest bar is {age.days} days old (limit {max_gap_days})"
    return None


def trim_csv(path: Path, keep: int = 500) -> None:
    """Keep only the newest `keep` bars: enough warmup for SMA(200) and the
    channels, without duplicating the research archive's full history."""
    if not path.exists():
        return
    with open(path) as f:
        rows = [r for r in csv.reader(f) if r]
    header, data = rows[0], rows[1:]
    if len(data) <= keep:
        return
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(data[-keep:])
