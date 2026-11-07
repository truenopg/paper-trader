#!/usr/bin/env python3
"""One daily step of the paper bot: refresh data, replay, snapshot, report.

    python live/run_daily.py              # fetch new bars, then run
    python live/run_daily.py --no-fetch   # replay only (tests, offline)

The replay IS the backtest: the same DonchianBreakout class and bt engine
that produced the research results run over the full updated history, so
the live account state is the honest continuation of the backtest. Paper
money only. Two independent sleeves of 10,000 USD each, one per asset,
matching the research sizing (1% risk per trade).

Cost model (modeling assumptions, inherited from the research protocol in
research/run_backtests.py, NOT a claim about any real venue): BTC 25 bps
per side (12.5 commission + 12.5 slippage), gold 3 bps per side
(1.5 + 1.5). The paper account is denominated in USD because both data
series are USD; no FX conversion is applied anywhere.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import research  # noqa: F401 - wires the vendored engine path
from research.strategies import DonchianBreakout
from bt.broker import Broker, CostModel
from bt.data import load_csv
from bt.engine import Backtest

from live.fetch import check_stale, trim_csv, update_feed
from live import report

CASH_USD = 10_000.0

# The paper account starts flat on this date (UTC). Backtest signals before
# it are ignored: no inherited positions, no fabricated live history. The
# full price history is still replayed so the strategy's indicators
# (SMA200, 55/20 channels, ATR) are correctly warmed up.
LIVE_START = datetime(2026, 11, 7)  # naive UTC, matching bt.data.load_csv

ASSETS = {
    "BTC": {
        "csv": Path("live/data/btc_1d.csv"),
        "source": "coinbase",
        "costs": CostModel(commission_bps=12.5, slippage_bps=12.5),
        "max_gap_days": 2,
    },
    "XAUUSD": {
        "csv": Path("live/data/xauusd_1d.csv"),
        "source": "yahoo",
        "costs": CostModel(commission_bps=1.5, slippage_bps=1.5),
        "max_gap_days": 5,
    },
}


class LiveGate:
    """Suppresses strategy orders before the live start date."""

    def __init__(self, inner, start):
        self._inner = inner
        self._start = start

    def on_bar(self, bar, broker):
        order = self._inner.on_bar(bar, broker)
        if bar.ts < self._start:
            return None
        return order


def run_asset(name: str, cfg: dict) -> dict:
    bars = load_csv(str(cfg["csv"]), ts_format="%Y-%m-%dT%H:%M:%S")
    strategy = DonchianBreakout(target_r=3.0)
    gated = LiveGate(strategy, LIVE_START)
    bt = Backtest(gated, Broker(CASH_USD, cfg["costs"]))
    bt.run(bars)
    broker = bt.broker
    last = bars[-1]
    open_entry = None
    if broker.position != 0 and broker.fills:
        f = broker.fills[-1]
        open_entry = {
            "side": "long" if broker.position > 0 else "short",
            "qty": round(abs(broker.position), 8),
            "entry_price": round(f.price, 4),
            "entry_date": f.ts.strftime("%Y-%m-%d"),
            "unrealized_usd": round(broker.position * (last.close - f.price), 2),
            "stop": getattr(strategy, "_stop", None),
        }
    return {
        "asset": name,
        "last_bar_date": last.ts.strftime("%Y-%m-%d"),
        "close": round(last.close, 4),
        "equity_usd": round(broker.equity(last.close), 2),
        "cash_usd": round(broker.cash, 2),
        "return_pct": round((broker.equity(last.close) / CASH_USD - 1) * 100, 2),
        "fills": len(broker.fills),
        "open": open_entry,
        "_bt": bt,  # in-process only, stripped before writing state
    }


def diff_events(prev: Optional[dict], results: List[dict]) -> List[str]:
    """Human-readable log lines for fills that are new since the last run."""
    events = []
    for r in results:
        bt = r["_bt"]
        old_n = (prev or {}).get("assets", {}).get(r["asset"], {}).get("fills", 0)
        for f in bt.broker.fills[old_n:]:
            events.append(
                f"- {f.ts.strftime('%Y-%m-%d')} {r['asset']} {f.side.value} "
                f"{f.qty:.8f} @ {f.price:,.2f} (commission {f.commission:.2f})")
    return events


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-fetch", action="store_true")
    args = ap.parse_args()

    warnings = []
    if not args.no_fetch:
        for name, cfg in ASSETS.items():
            added = update_feed(cfg["csv"], cfg["source"])
            trim_csv(cfg["csv"])
            print(f"[feed] {name}: {added} new bar(s)")
    for name, cfg in ASSETS.items():
        w = check_stale(cfg["csv"], cfg["max_gap_days"])
        if w:
            warnings.append(w)

    results = [run_asset(name, cfg) for name, cfg in ASSETS.items()]
    prev = report.load_state()
    events = diff_events(prev, results)
    report.append_log(events)

    now = datetime.now(timezone.utc)
    state = {
        "updated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "currency": "USD",
        "note": "Paper money only. Two 10,000 USD sleeves, S1 Donchian 3R, "
                "fills at next open, costs per research protocol. Live from "
                + LIVE_START.strftime("%Y-%m-%d")
                + ": flat start, no positions inherited from the backtest.",
        "warnings": warnings,
        "assets": {r["asset"]: {k: v for k, v in r.items() if k != "_bt"}
                   for r in results},
    }
    report.write_state(state)

    # equity curve, aligned by date (outer join on date)
    curves = {}
    dates = set()
    for r in results:
        bt = r["_bt"]
        curves[r["asset"]] = {t.strftime("%Y-%m-%d"): e
                              for t, e in zip(bt.timestamps, bt.equity_curve)}
        dates |= set(curves[r["asset"]].keys())
    rows = []
    last_known = {a: CASH_USD for a in ASSETS}
    start_d = LIVE_START.strftime("%Y-%m-%d")
    for d in sorted(x for x in dates if x >= start_d):
        for a in ASSETS:
            last_known[a] = curves[a].get(d, last_known[a])
        rows.append({"date": d, "BTC": last_known["BTC"],
                     "XAUUSD": last_known["XAUUSD"],
                     "TOTAL": last_known["BTC"] + last_known["XAUUSD"]})
    if not rows:
        # No closed bar on/after LIVE_START yet: one snapshot of the flat
        # account, dated with the run date. The first closed bar replaces it.
        tot = sum(r["equity_usd"] for r in results)
        rows.append({"date": now.strftime("%Y-%m-%d"),
                     "BTC": results[0]["equity_usd"],
                     "XAUUSD": results[1]["equity_usd"],
                     "TOTAL": tot})
    report.write_equity(rows)

    total = sum(r["equity_usd"] for r in results)
    print(f"[paper] total equity {total:,.2f} USD "
          f"(start {2 * CASH_USD:,.2f})")
    for r in results:
        print(f"[paper] {r['asset']}: equity {r['equity_usd']:,.2f} "
              f"({r['return_pct']:+.2f}%), fills {r['fills']}, "
              f"open {r['open']}")
    for e in events:
        print(f"[event] {e}")
    for w in warnings:
        print(f"[warn] {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
