"""Download Dukascopy XAUUSD tick files (free, hourly .bi5), build 5m bid OHLC.
Usage: python fetch_dukascopy.py 2021-01-01 2026-08-31 out.pkl
Format: LZMA-compressed records of 20 bytes big-endian: ms offset, ask, bid (int, /1000 for XAUUSD), ask vol, bid vol (float).
Note: month index in the URL is 0-based."""
import sys, lzma, struct, urllib.request, datetime as dt
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

SYMBOL = "XAUUSD"; PT = 1000.0

def fetch_hour(t):
    url = f"https://datafeed.dukascopy.com/datafeed/{SYMBOL}/{t.year}/{t.month-1:02d}/{t.day:02d}/{t.hour:02d}h_ticks.bi5"
    for _ in range(4):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read()
            break
        except Exception:
            raw = None
    if not raw: return t, []
    try: data = lzma.decompress(raw)
    except Exception: return t, []
    out = []
    for off in range(0, len(data) - 19, 20):
        ms, ask, bid, av, bv = struct.unpack(">IIIff", data[off:off+20])
        out.append((t + dt.timedelta(milliseconds=ms), bid / PT, (ask - bid) / PT))
    return t, out

def month_hours(y, m):
    t = dt.datetime(y, m, 1); out = []
    while t.month == m:
        if t.weekday() < 5 and 6 <= t.hour < 18:   # London+NY daytime only (UTC)
            out.append(t)
        t += dt.timedelta(hours=1)
    return out

def build_month(y, m, ex, cache):
    import os
    f = f"{cache}/{y}-{m:02d}.pkl"
    if os.path.exists(f): return
    bars = []
    for t, ticks in ex.map(fetch_hour, month_hours(y, m)):
        if ticks:
            s = pd.DataFrame(ticks, columns=["ts", "bid", "spr"]).set_index("ts")
            o = s.bid.resample("5min").ohlc(); o["spr"] = s.spr.resample("5min").mean()
            bars.append(o.dropna())
    if bars:
        pd.concat(bars).to_pickle(f); print("done", y, m, flush=True)

def main(cache="/tmp/duka", workers=200):
    import glob
    with ThreadPoolExecutor(workers) as ex:
        for y in range(2021, 2027):
            for m in range(1, 13):
                if (y, m) > (2026, 8): break
                build_month(y, m, ex, cache)
    parts = [pd.read_pickle(f) for f in sorted(glob.glob(f"{cache}/*.pkl"))]
    d = pd.concat(parts).sort_index(); d = d[~d.index.duplicated()]
    d.columns = ["o", "h", "l", "c", "spr"]; d["v"] = 0.0
    d.to_pickle("/tmp/d/XAUUSD_5m.pkl"); print(len(d), d.index[0], d.index[-1], "median spread", d.spr.median())

if __name__ == "__main__":
    main()
