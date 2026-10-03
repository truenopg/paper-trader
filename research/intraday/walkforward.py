"""Walk-forward for the 4h Donchian breakout family on a crypto basket.
Each test year: pick ONE parameter set (shared by all coins) using only prior data
(expanding window from 2021-01), trade it on the test year, chain the results.
Portfolio = all coins' trades pooled, 0.5% risk per trade, 2% daily halt per coin."""
from __future__ import annotations
import itertools, sys
import numpy as np, pandas as pd
from engine import simulate, metrics
import signals as S

COINS = {"BTCUSDT": 7.5, "ETHUSDT": 7.5, "SOLUSDT": 10.0, "BNBUSDT": 10.0, "XRPUSDT": 10.0, "ADAUSDT": 10.0}
RISK, DAY_STOP = 0.005, 0.02
GRID = list(itertools.product([10, 20, 30, 50, 80], [1.0, 2.0, 3.0], [0, 100, 200], [1.5, 2.0, 3.0, 4.0], [3, 6]))
HM = np.zeros(24, np.int8)

def trades_for(cost_scale=1.0, tf="4h"):
    out = {}
    for sym, bps in COINS.items():
        d = S.load(sym, tf)
        o, h, l, c = d.o.values, d.h.values, d.l.values, d.c.values
        day = (d.index.floor("D").astype("int64") // 86_400_000_000_000).values
        hour = d.index.hour.values; tsa = d.index.values
        cache = {}
        for n, k, tr, rr, mh in GRID:
            key = (n, k, tr)
            if key not in cache:
                sig, sl = S.donchian(d, n, k, tr, 0, 24)
                cache[key] = (np.nan_to_num(sig).astype(np.int64), np.nan_to_num(sl))
            sig, sl = cache[key]
            ei, xi, pr, di = simulate(o, h, l, c, day, sig, sl, rr, mh, bps * cost_scale, DAY_STOP / RISK, HM, hour)
            out[(sym, n, k, tr, rr, mh)] = (tsa[ei], pr)
    return out

def pooled(tr, params, start, end):
    ts, pn = [], []
    for sym in COINS:
        t, p = tr[(sym,) + params]
        m = (t >= np.datetime64(start)) & (t < np.datetime64(end))
        ts.append(t[m]); pn.append(p[m])
    t = np.concatenate(ts); p = np.concatenate(pn)
    o = np.argsort(t); return t[o], p[o]

def score(tr, params, start, end):
    t, p = pooled(tr, params, start, end)
    if len(p) < 60: return -9
    w, l = p[p > 0].sum(), -p[p < 0].sum()
    return p.mean() if (l > 0 and w / l > 1.1) else -9

def main(cost_scale=1.0):
    tr = trades_for(cost_scale)
    chain_t, chain_p = [], []
    for ty, tend in [(2023, 2024), (2024, 2025), (2025, 2026), (2026, 2027)]:
        ts_, te_ = f"{ty}-01-01", f"{tend}-01-01"
        best = max(GRID, key=lambda g: score(tr, g, "2021-01-01", ts_) if ty > 2021 else -9)
        t, p = pooled(tr, best, ts_, te_)
        print(f"test {ty}: chosen n={best[0]} k_sl={best[1]} trend={best[2]} rr={best[3]} hold={best[4]*4}h -> trades {len(p)} exp {p.mean():+.3f}R")
        chain_t.append(t); chain_p.append(p)
    t = np.concatenate(chain_t); p = np.concatenate(chain_p)
    for risk in (0.0025, 0.005):
        m = metrics(p, t, risk, pd.Timestamp("2023-01-01"), pd.Timestamp("2027-01-01"))
        print(f"WALK-FORWARD 2023-01..2026-08 risk {risk:.2%}/trade:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items()})
    # fixed-param reference: all coins, one fixed round-number set, whole 5.7y
    for g in [(20, 2.0, 200, 3.0, 3), (50, 2.0, 200, 3.0, 3), (20, 2.0, 0, 3.0, 3)]:
        t, p = pooled(tr, g, "2021-01-01", "2027-01-01")
        m = metrics(p, t, 0.005, pd.Timestamp("2021-01-01"), pd.Timestamp("2027-01-01"))
        print("fixed", g, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items()})

if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 1.0)
