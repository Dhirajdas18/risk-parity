import numpy as np
import pandas as pd

from rp import backtest as B


def _r(n=60):
    idx = pd.date_range("2010-01-31", periods=n, freq="ME")
    rng = np.random.default_rng(1)
    return pd.DataFrame(rng.normal(0.01, 0.04, (n, 2)), index=idx, columns=["a", "b"])


def test_weights_use_only_past_months_and_hold_next_month():
    r = _r()
    seen = []

    def rule(past):
        seen.append(past.copy())
        return np.array([0.5, 0.5])

    out = B.run(r, rule, window=12)
    assert np.allclose(seen[0], r.iloc[:12].to_numpy())
    assert out.index[0] == r.index[12]
    assert np.isclose(out["gross"].iloc[0], r.iloc[12].mean())


def test_costs_charged_on_the_trade_back_from_drifted_weights():
    r = _r()
    out = B.run(r, lambda p: np.array([0.5, 0.5]), window=12, cost=0.01)
    assert out["cost"].iloc[0] == 0  # first purchase free
    a, b = 1 + r.iloc[12]
    drift = np.array([0.5 * a, 0.5 * b]) / (0.5 * a + 0.5 * b)
    assert np.isclose(out["cost"].iloc[1], np.abs(0.5 - drift).sum() * 0.01)


def test_stats_compound_over_calendar_years():
    idx = pd.date_range("2020-01-31", periods=24, freq="ME")
    r = pd.Series((1.1 ** (1 / 12)) - 1, index=idx)
    s = B.stats(r, pd.Series(0.0, index=idx))
    assert abs(s["cagr"] - 0.10) < 0.002
