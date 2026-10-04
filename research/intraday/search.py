"""Grid search over strategy families. Selection uses TRAIN only (2021-01..2023-06);
2023-07..2026-08 is out-of-sample. Prints compact results and saves a pickle."""
from __future__ import annotations
import itertools, pickle, sys, time
import numpy as np, pandas as pd
from engine import simulate, metrics
import signals as S

import os
SC = float(os.environ.get("COST_SCALE", "1"))
COSTS = {"BTCUSDT": 7.5 * SC, "PAXGUSDT": 3.0 * SC, "XAUUSD": 2.0 * SC, "ETHUSDT": 7.5 * SC, "SOLUSDT": 10.0 * SC, "BNBUSDT": 10.0 * SC, "XRPUSDT": 10.0 * SC, "ADAUSDT": 10.0 * SC}   # bps per side (x scale)
RISK = 0.005       # 0.5% per trade
DAY_STOP = 0.02    # halt new entries after -2% on the UTC day
T0, T1, T2 = pd.Timestamp("2021-01-01"), pd.Timestamp("2023-07-01"), pd.Timestamp("2026-09-01")
HOUR_MASK = np.zeros(24, np.int8)

def grids(tf):
    bars_per_h = {"5min": 12, "15min": 4, "1h": 1, "4h": 0.25}[tf]
    sessions = [(0, 24), (7, 17), (13, 21)]
    for n, k, tr, ses in itertools.product([20, 50, 100], [1.0, 2.0, 3.0], [0, 200], sessions):
        yield ("donchian", dict(n=n, k_sl=k, trend_n=tr, h0=ses[0], h1=ses[1]))
    for (f, s), k, tr, ses in itertools.product([(9, 21), (20, 50)], [1.0, 2.0, 3.0], [0, 200], sessions):
        yield ("ema_cross", dict(f=f, s=s, k_sl=k, trend_n=tr, h0=ses[0], h1=ses[1]))
    for n, lo, k, tr, ses in itertools.product([2, 3, 7, 14], [10, 20, 30], [1.0, 2.0, 3.0], [0, 200], sessions):
        yield ("rsi_rev", dict(n=n, lo=lo, k_sl=k, trend_n=tr, h0=ses[0], h1=ses[1]))
    for n, ns, k, ses in itertools.product([20, 50], [2.0, 2.5], [1.0, 2.0, 3.0], sessions):
        yield ("boll_fade", dict(n=n, nstd=ns, k_sl=k, h0=ses[0], h1=ses[1]))
    for sh, rb, k in itertools.product([0, 7, 8, 13, 14], [max(1, 12 // bars_per_h * 0 + {"5min": 6, "15min": 2, "1h": 1, "4h": 1}[tf]), {"5min": 12, "15min": 4, "1h": 2, "4h": 1}[tf]], [0.5, 1.0, 2.0]):
        yield ("orb", dict(start_h=sh, range_bars=rb, k_sl=k, h_end=min(24, sh + 8) if sh + 8 <= 24 else 24))

def main(symbols, tfs):
    rows = []
    t = time.time()
    for sym in symbols:
        for tf in tfs:
            d = S.load(sym, tf)
            o, h, l, c = d.o.values, d.h.values, d.l.values, d.c.values
            day = (d.index.floor("D").astype("int64") // 86_400_000_000_000).values
            hour = d.index.hour.values
            tsa = d.index.values
            mh_h = {"5min": 12 * 4, "15min": 4 * 6, "1h": 8, "4h": 3}[tf]  # max hold ~4h / 6h / 8h
            for fam, p in grids(tf):
                sig, sl = getattr(S, fam)(d, **p)
                sig = np.nan_to_num(sig).astype(np.int64)
                sl = np.nan_to_num(sl)
                for rr in (1.0, 1.5, 2.0, 3.0):
                    ei, xi, pr, di = simulate(o, h, l, c, day, sig, sl, rr, mh_h, COSTS[sym], DAY_STOP / RISK, HOUR_MASK, hour)
                    if len(pr) < 30: continue
                    te = tsa[ei]
                    tr_ = metrics(pr, te, RISK, T0, T1)
                    oo = metrics(pr, te, RISK, T1, T2)
                    if tr_ is None or oo is None: continue
                    rows.append(dict(sym=sym, tf=tf, fam=fam, rr=rr, **{f"p_{k}": v for k, v in p.items()},
                                     **{f"tr_{k}": v for k, v in tr_.items()}, **{f"oo_{k}": v for k, v in oo.items()}))
            print(sym, tf, len(rows), f"{time.time()-t:.0f}s", flush=True)
    df = pd.DataFrame(rows)
    df.to_pickle(os.environ.get("OUT","/tmp/search_results.pkl"))
    print("total configs:", len(df))

if __name__ == "__main__":
    main(sys.argv[1].split(","), sys.argv[2].split(","))
