"""Signal families. Each returns (sig, sl_dist) arrays on closed bars."""
from __future__ import annotations
import numpy as np
import pandas as pd


def load(symbol: str, tf: str) -> pd.DataFrame:
    d = pd.read_pickle(f"/tmp/d/{symbol}_5m.pkl")
    if tf != "5min":
        d = d.resample(tf).agg({"o": "first", "h": "max", "l": "min", "c": "last", "v": "sum"}).dropna()
    return d


def ema(x, n): return pd.Series(x).ewm(span=n, adjust=False).mean().values
def sma(x, n): return pd.Series(x).rolling(n).mean().values


def rsi(c, n):
    s = pd.Series(c); dlt = s.diff()
    up = dlt.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-dlt.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).values


def atr(h, l, c, n):
    pc = np.roll(c, 1); pc[0] = c[0]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    return pd.Series(tr).rolling(n).mean().values


def in_hours(idx, h0, h1):
    hr = idx.hour.values
    return (hr >= h0) & (hr < h1) if h0 < h1 else (hr >= h0) | (hr < h1)


def donchian(d, n, k_sl, trend_n, h0, h1):
    h, l, c = d.h.values, d.l.values, d.c.values
    hi = pd.Series(h).rolling(n).max().shift(1).values
    lo = pd.Series(l).rolling(n).min().shift(1).values
    a = atr(h, l, c, 14)
    tr = ema(c, trend_n) if trend_n else None
    long_ = (c > hi); short_ = (c < lo)
    if tr is not None:
        long_ &= c > tr; short_ &= c < tr
    ok = in_hours(d.index, h0, h1)
    sig = np.where(long_ & ok, 1, np.where(short_ & ok, -1, 0))
    return sig, a * k_sl


def ema_cross(d, f, s, k_sl, trend_n, h0, h1):
    c, h, l = d.c.values, d.h.values, d.l.values
    ef, es = ema(c, f), ema(c, s)
    up = (ef > es) & (np.roll(ef, 1) <= np.roll(es, 1))
    dn = (ef < es) & (np.roll(ef, 1) >= np.roll(es, 1))
    if trend_n:
        t = ema(c, trend_n); up &= c > t; dn &= c < t
    ok = in_hours(d.index, h0, h1)
    return np.where(up & ok, 1, np.where(dn & ok, -1, 0)), atr(h, l, c, 14) * k_sl


def rsi_rev(d, n, lo, k_sl, trend_n, h0, h1):
    c, h, l = d.c.values, d.h.values, d.l.values
    r = rsi(c, n)
    long_ = r < lo; short_ = r > 100 - lo
    if trend_n:
        t = ema(c, trend_n); long_ &= c > t; short_ &= c < t
    ok = in_hours(d.index, h0, h1)
    return np.where(long_ & ok, 1, np.where(short_ & ok, -1, 0)), atr(h, l, c, 14) * k_sl


def boll_fade(d, n, nstd, k_sl, h0, h1):
    c, h, l = d.c.values, d.h.values, d.l.values
    m = sma(c, n); s = pd.Series(c).rolling(n).std().values
    long_ = c < m - nstd * s; short_ = c > m + nstd * s
    ok = in_hours(d.index, h0, h1)
    return np.where(long_ & ok, 1, np.where(short_ & ok, -1, 0)), atr(h, l, c, 14) * k_sl


def orb(d, start_h, range_bars, k_sl, h_end):
    """Opening-range breakout: range of first `range_bars` bars from start_h (UTC);
    first close beyond it (until h_end) signals; one per day."""
    c, h, l = d.c.values, d.h.values, d.l.values
    idx = d.index
    sig = np.zeros(len(d), int)
    day = idx.floor("D")
    hr = idx.hour.values
    a = atr(h, l, c, 14) * k_sl
    start_pos = {}
    for dday, grp in pd.Series(np.arange(len(d)), index=idx).groupby(day):
        pos = grp.values
        hh = hr[pos]
        s = np.where(hh == start_h)[0]
        if len(s) == 0: continue
        s0 = pos[s[0]]
        r_end = s0 + range_bars
        if r_end >= pos[-1]: continue
        rh, rl = h[s0:r_end].max(), l[s0:r_end].min()
        for i in range(r_end, pos[-1] + 1):
            if hr[i] >= h_end and h_end > start_h: break
            if c[i] > rh: sig[i] = 1; break
            if c[i] < rl: sig[i] = -1; break
    return sig, a
