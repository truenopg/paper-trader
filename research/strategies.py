"""The candidate rule-based strategies from STRATEGIES.md.

Each strategy keeps incremental indicator state (no O(n^2) recomputation)
and sizes positions with fixed fractional risk: every trade risks
`risk` x current equity between entry and stop.

Stops and targets are evaluated on the bar that breaches them, but the
exit order fills at the NEXT bar's open - the engine only fills market
orders that way. On a gap through the stop the fill can be worse than the
stop price; that conservatism is intentional and documented in the
results. No intrabar stop precision is claimed.
"""
from __future__ import annotations

from collections import deque
from typing import Optional

from bt.broker import Broker
from bt.core import Bar, Order, Side


class DonchianBreakout:
    """S1: 55-bar Donchian breakout in the direction of the 200-bar SMA.

    Long only above SMA(trend), short only below. Stop at 2 x ATR(20).
    Exit on the 20-bar opposite channel (target_r=None, trailing) or at
    target_r times the initial risk (e.g. 3.0 for a 1:3 RR), whichever
    comes first.
    """

    def __init__(self, entry: int = 55, exit: int = 20, trend: int = 200,
                 atr_period: int = 20, atr_mult: float = 2.0,
                 risk: float = 0.01, target_r: Optional[float] = None) -> None:
        if exit >= entry:
            raise ValueError("exit channel must be shorter than entry channel")
        self.entry, self.exit, self.trend = entry, exit, trend
        self.atr_period, self.atr_mult = atr_period, atr_mult
        self.risk, self.target_r = risk, target_r
        self._closes: deque = deque(maxlen=trend)
        self._highs_entry: deque = deque(maxlen=entry)
        self._lows_entry: deque = deque(maxlen=entry)
        self._highs_exit: deque = deque(maxlen=exit)
        self._lows_exit: deque = deque(maxlen=exit)
        self._trs: deque = deque(maxlen=atr_period)
        self._atr: Optional[float] = None
        self._prev_close: Optional[float] = None
        self._stop: Optional[float] = None
        self._entry_price: Optional[float] = None

    def _ready(self) -> bool:
        return (len(self._closes) == self.trend
                and len(self._highs_entry) == self.entry
                and self._atr is not None)

    def _update(self, bar: Bar) -> None:
        if self._prev_close is not None:
            tr = max(bar.high - bar.low,
                     abs(bar.high - self._prev_close),
                     abs(bar.low - self._prev_close))
            self._trs.append(tr)
            if len(self._trs) == self.atr_period:
                sm = sum(self._trs)
                self._atr = sm / self.atr_period if self._atr is None else (
                    (self._atr * (self.atr_period - 1) + tr) / self.atr_period)
        self._closes.append(bar.close)
        # channels look at CLOSED bars only - updated before the signal,
        # but a breakout compares this bar's close against prior extremes
        self._prev_close = bar.close

    def on_bar(self, bar: Bar, broker: Broker) -> Optional[Order]:
        upper = max(self._highs_entry) if len(self._highs_entry) == self.entry else None
        lower = min(self._lows_entry) if len(self._lows_entry) == self.entry else None
        trail_hi = max(self._highs_exit) if len(self._highs_exit) == self.exit else None
        trail_lo = min(self._lows_exit) if len(self._lows_exit) == self.exit else None
        sma200 = sum(self._closes) / self.trend if len(self._closes) == self.trend else None
        atr = self._atr
        self._highs_entry.append(bar.high)
        self._lows_entry.append(bar.low)
        self._highs_exit.append(bar.high)
        self._lows_exit.append(bar.low)
        self._update(bar)

        if not self._ready():
            return None

        pos = broker.position
        if pos > 0 and self._stop is not None:
            hit_stop = bar.low <= self._stop
            hit_target = (self.target_r is not None and self._entry_price is not None
                          and bar.high >= self._entry_price
                          + self.target_r * (self._entry_price - self._stop))
            hit_trail = trail_lo is not None and bar.close < trail_lo
            if hit_stop or hit_target or hit_trail:
                return Order(Side.SELL, pos)
        elif pos < 0 and self._stop is not None:
            hit_stop = bar.high >= self._stop
            hit_target = (self.target_r is not None and self._entry_price is not None
                          and bar.low <= self._entry_price
                          - self.target_r * (self._stop - self._entry_price))
            hit_trail = trail_hi is not None and bar.close > trail_hi
            if hit_stop or hit_target or hit_trail:
                return Order(Side.BUY, -pos)

        if pos == 0 and atr:
            if upper is not None and sma200 is not None and bar.close > upper and bar.close > sma200:
                qty = self.risk * broker.equity(bar.close) / (self.atr_mult * atr)
                self._entry_price = bar.close
                self._stop = bar.close - self.atr_mult * atr
                return Order(Side.BUY, qty)
            if lower is not None and sma200 is not None and bar.close < lower and bar.close < sma200:
                qty = self.risk * broker.equity(bar.close) / (self.atr_mult * atr)
                self._entry_price = bar.close
                self._stop = bar.close + self.atr_mult * atr
                return Order(Side.SELL, qty)
        return None


class RsiMeanReversion:
    """S2: buy RSI(3) < 10 dips, only above SMA(200). Long-only.

    Exit when close recovers above SMA(20) or RSI(3) > 70; hard stop at
    entry - 2 x ATR(20). Same fixed-risk sizing as S1.
    """

    def __init__(self, rsi_period: int = 3, rsi_entry: float = 10.0,
                 rsi_exit: float = 70.0, trend: int = 200, mean: int = 20,
                 atr_period: int = 20, atr_mult: float = 2.0,
                 risk: float = 0.01) -> None:
        self.rsi_period, self.rsi_entry, self.rsi_exit = rsi_period, rsi_entry, rsi_exit
        self.trend, self.mean = trend, mean
        self.atr_period, self.atr_mult, self.risk = atr_period, atr_mult, risk
        self._closes: deque = deque(maxlen=trend)
        self._trs: deque = deque(maxlen=atr_period)
        self._atr: Optional[float] = None
        self._prev_close: Optional[float] = None
        self._avg_gain: Optional[float] = None
        self._avg_loss: Optional[float] = None
        self._rsi: Optional[float] = None
        self._changes: deque = deque(maxlen=rsi_period)
        self._stop: Optional[float] = None

    def _ready(self) -> bool:
        return len(self._closes) == self.trend and self._rsi is not None and self._atr is not None

    def _update(self, bar: Bar) -> None:
        if self._prev_close is not None:
            tr = max(bar.high - bar.low,
                     abs(bar.high - self._prev_close),
                     abs(bar.low - self._prev_close))
            self._trs.append(tr)
            if len(self._trs) == self.atr_period:
                self._atr = (sum(self._trs) / self.atr_period if self._atr is None
                             else (self._atr * (self.atr_period - 1) + tr) / self.atr_period)
            d = bar.close - self._prev_close
            gain, loss = max(d, 0.0), max(-d, 0.0)
            if self._avg_gain is None:
                self._changes.append((gain, loss))
                if len(self._changes) == self.rsi_period:
                    self._avg_gain = sum(g for g, _ in self._changes) / self.rsi_period
                    self._avg_loss = sum(l for _, l in self._changes) / self.rsi_period
            else:
                self._avg_gain = (self._avg_gain * (self.rsi_period - 1) + gain) / self.rsi_period
                self._avg_loss = (self._avg_loss * (self.rsi_period - 1) + loss) / self.rsi_period
            if self._avg_gain is not None:
                self._rsi = 100.0 if self._avg_loss == 0 else (
                    100 - 100 / (1 + self._avg_gain / self._avg_loss))
        self._closes.append(bar.close)
        self._prev_close = bar.close

    def on_bar(self, bar: Bar, broker: Broker) -> Optional[Order]:
        rsi_now, atr_now = self._rsi, self._atr
        sma_trend = sum(self._closes) / self.trend if len(self._closes) == self.trend else None
        closes_mean = list(self._closes)[-self.mean:]
        sma_mean = sum(closes_mean) / len(closes_mean) if len(closes_mean) == self.mean else None
        self._update(bar)

        if not self._ready():
            return None

        pos = broker.position
        if pos > 0 and self._stop is not None:
            hit_stop = bar.low <= self._stop
            hit_mean = sma_mean is not None and bar.close > sma_mean
            hit_rsi = rsi_now is not None and rsi_now > self.rsi_exit
            if hit_stop or hit_mean or hit_rsi:
                return Order(Side.SELL, pos)

        if (pos == 0 and rsi_now is not None and rsi_now < self.rsi_entry
                and sma_trend is not None and bar.close > sma_trend and atr_now):
            qty = self.risk * broker.equity(bar.close) / (self.atr_mult * atr_now)
            self._stop = bar.close - self.atr_mult * atr_now
            return Order(Side.BUY, qty)
        return None
