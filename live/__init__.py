"""Live paper-trading: the research strategies, run one new daily bar at a time.

Everything here reuses the vendored backtest-engine (bt) and the research
strategy classes, so the live bot is literally the backtest continued
forward: same fills-at-next-open rule, same cost model, same sizing.
"""
