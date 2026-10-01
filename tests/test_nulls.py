import random
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import research  # noqa: F401
from research.nulls import shuffled_path
from bt.data import synthetic_gbm


def test_shuffle_keeps_length_and_bar_validity():
    bars = synthetic_gbm(days=200, seed=3)
    out = shuffled_path(bars, random.Random(1))
    assert len(out) == len(bars)
    assert [b.ts for b in out] == [b.ts for b in bars]
    assert all(b.low <= min(b.open, b.close) and b.high >= max(b.open, b.close) for b in out)


def test_shuffle_is_reproducible_and_changes_path():
    bars = synthetic_gbm(days=100, seed=5)
    a = shuffled_path(bars, random.Random(7))
    b = shuffled_path(bars, random.Random(7))
    assert [x.close for x in a] == [x.close for x in b]
    assert [x.close for x in a] != [x.close for x in bars]
