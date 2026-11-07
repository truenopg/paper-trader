"""Persistence and rendering for the daily run.

state/paper_state.json  - latest account snapshot (auditable, committed)
report/equity.csv       - full daily equity series, one row per bar date
report/SIGNAL_LOG.md    - human log, one line per fill event
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

STATE_PATH = Path("state/paper_state.json")
EQUITY_PATH = Path("report/equity.csv")
LOG_PATH = Path("report/SIGNAL_LOG.md")


def load_state(path: Path = STATE_PATH) -> Optional[dict]:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def write_state(state: dict, path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def write_equity(rows: List[dict], path: Path = EQUITY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "BTC", "XAUUSD", "TOTAL"])
        for r in rows:
            w.writerow([r["date"], f"{r['BTC']:.2f}", f"{r['XAUUSD']:.2f}",
                        f"{r['TOTAL']:.2f}"])


def append_log(events: List[str], path: Path = LOG_PATH) -> None:
    if not events:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("# Signal and fill log\n\n"
                        "One line per paper fill. Fills happen at the open of the\n"
                        "bar after the signal, with the cost model applied.\n\n")
    with open(path, "a") as f:
        for e in events:
            f.write(e + "\n")


def fmt_money(x: float) -> str:
    return f"{x:,.2f} USD"
