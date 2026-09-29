"""Technical indicators over bar series, computed without look-ahead.

All functions return lists aligned to the input: positions where the
window is not yet complete hold None. Donchian channels are shifted by
one bar - the channel a breakout is measured against never includes the
bar being tested, or the breakout would reference itself.
"""
from __future__ import annotations

from typing import List, Optional, Sequence


def sma(values: Sequence[float], window: int) -> List[Optional[float]]:
    out: List[Optional[float]] = [None] * len(values)
    acc = 0.0
    for i, v in enumerate(values):
        acc += v
        if i >= window:
            acc -= values[i - window]
        if i >= window - 1:
            out[i] = acc / window
    return out


def rsi(closes: Sequence[float], period: int) -> List[Optional[float]]:
    """Wilder's RSI. Needs `period` gains/losses to seed, then smooths."""
    out: List[Optional[float]] = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains, losses = 0.0, 0.0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        gains += max(d, 0.0)
        losses += max(-d, 0.0)
    avg_gain, avg_loss = gains / period, losses / period
    out[period] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(d, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-d, 0.0)) / period
        out[i] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    return out


def atr(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float],
        period: int) -> List[Optional[float]]:
    """Wilder's ATR (true range smoothed)."""
    out: List[Optional[float]] = [None] * len(closes)
    if len(closes) <= period:
        return out
    trs = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        trs.append(max(highs[i] - lows[i],
                       abs(highs[i] - closes[i - 1]),
                       abs(lows[i] - closes[i - 1])))
    value = sum(trs[1:period + 1]) / period
    out[period] = value
    for i in range(period + 1, len(closes)):
        value = (value * (period - 1) + trs[i]) / period
        out[i] = value
    return out


def donchian(highs: Sequence[float], lows: Sequence[float], window: int):
    """Previous `window`-bar extremes, excluding the current bar."""
    upper: List[Optional[float]] = [None] * len(highs)
    lower: List[Optional[float]] = [None] * len(highs)
    for i in range(window, len(highs)):
        upper[i] = max(highs[i - window:i])
        lower[i] = min(lows[i - window:i])
    return upper, lower
