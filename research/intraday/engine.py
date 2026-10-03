"""Fast intraday backtest core (numba). Entry at the open of the bar AFTER the
signal bar; SL/TP checked on bar high/low (SL first if both touched, i.e. the
pessimistic assumption); optional time exit; per-day loss halt; costs in bps
per side charged in R units. One position at a time.
"""
from __future__ import annotations
import numpy as np
from numba import njit


@njit(cache=True)
def simulate(o, h, l, c, day, sig, sl_dist, rr, max_hold, cost_bps, day_stop_r, flat_hour_mask, hour):
    """sig[i] in {-1,0,1}: signal on closed bar i -> fill at o[i+1].
    Returns arrays: entry_idx, exit_idx, pnl_r, direction."""
    n = len(c)
    ei = np.empty(n, np.int64); xi = np.empty(n, np.int64)
    pr = np.empty(n, np.float64); di = np.empty(n, np.int8)
    k = 0
    i = 0
    cur_day = -1
    day_pnl = 0.0
    while i < n - 2:
        if day[i] != cur_day:
            cur_day = day[i]
            day_pnl = 0.0
        d = sig[i]
        if d == 0 or day_pnl <= -day_stop_r or sl_dist[i] <= 0:
            i += 1
            continue
        e = i + 1
        entry = o[e]
        sd = sl_dist[i]
        sl = entry - d * sd
        tp = entry + d * sd * rr
        cost_r = 2.0 * cost_bps * 1e-4 * entry / sd
        exit_p = c[min(e + max_hold, n - 1)]
        j_exit = min(e + max_hold, n - 1)
        for j in range(e, min(e + max_hold, n - 1) + 1):
            # SL first
            if d == 1:
                if l[j] <= sl:
                    exit_p = min(sl, o[j]) if j > e else sl
                    j_exit = j
                    break
                if h[j] >= tp:
                    exit_p = tp
                    j_exit = j
                    break
            else:
                if h[j] >= sl:
                    exit_p = max(sl, o[j]) if j > e else sl
                    j_exit = j
                    break
                if l[j] <= tp:
                    exit_p = tp
                    j_exit = j
                    break
            if flat_hour_mask[hour[j]] == 1 and j > e:
                exit_p = c[j]
                j_exit = j
                break
            exit_p = c[j]
            j_exit = j
        pnl = d * (exit_p - entry) / sd - cost_r
        ei[k] = e; xi[k] = j_exit; pr[k] = pnl; di[k] = d
        k += 1
        if day[j_exit] == cur_day:
            day_pnl += pnl
        i = j_exit + 1
    return ei[:k], xi[:k], pr[:k], di[:k]


def metrics(pnl_r, ts_entry, risk, start, end, days_total=None):
    """Equity from trade sequence with fixed fractional risk (compounded).
    Daily loss measured on UTC days of trade exit."""
    import pandas as pd
    m = (ts_entry >= start) & (ts_entry < end)
    p = pnl_r[m]
    t = ts_entry[m]
    if len(p) == 0:
        return None
    eq = np.cumprod(1 + risk * p)
    peak = np.maximum.accumulate(np.concatenate([[1.0], eq]))[1:]
    dd = eq / peak - 1
    days = pd.Series(1 + risk * p, index=pd.DatetimeIndex(t)).groupby(pd.DatetimeIndex(t).floor("D")).prod() - 1
    yrs = (pd.Timestamp(end) - pd.Timestamp(start)).days / 365.25
    wins = p[p > 0].sum(); loss = -p[p < 0].sum()
    dr = days.values
    return dict(trades=len(p), ret=eq[-1] - 1, cagr=eq[-1] ** (1 / yrs) - 1,
                maxdd=dd.min(), worst_day=dr.min() if len(dr) else 0.0,
                pf=wins / loss if loss > 0 else np.inf, win=(p > 0).mean(),
                exp_r=p.mean(), sharpe=(dr.mean() / dr.std() * np.sqrt(365)) if dr.std() > 0 else 0.0)
