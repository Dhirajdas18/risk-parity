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


def test_lever_and_exante_vol():
    idx = pd.date_range("2000-01-31", periods=60, freq="ME")
    rng = np.random.default_rng(0)
    r = pd.DataFrame(rng.normal(0.01, [0.05, 0.02], (60, 2)), index=idx, columns=["a", "b"])
    o = B.run(r, lambda p: np.array([0.5, 0.5]), 24)
    v = B.exante_vol(r, o, 24)
    S = np.cov(r.to_numpy()[:24], rowvar=False)
    assert np.isclose(v.iloc[0], np.sqrt(np.array([.5, .5]) @ S @ np.array([.5, .5]) * 12))
    rate = pd.Series(0.004, index=idx)
    out = B.lever(o["net"], 2.0, rate)
    assert np.allclose(out, 2 * o["net"] - 0.004)
    assert np.allclose(B.lever(o["net"], 1.0, rate), o["net"])


def test_sharpe_diff_identical_and_paired_mean():
    idx = pd.date_range("2000-01-31", periods=120, freq="ME")
    rng = np.random.default_rng(2)
    a = pd.Series(rng.normal(0.01, 0.03, 120), index=idx)
    cash = pd.Series(0.004, index=idx)
    d, se = B.sharpe_diff(a, a, cash)
    assert d == 0 and se < 1e-6  # same strategy: no difference, no uncertainty
    b = a + rng.normal(0, 0.001, 120)  # nearly identical: paired SE far below a single SE
    md, mse = B.mean_diff(a, b)
    assert mse < 0.03 * np.sqrt(12 / 120) / 5


def test_lever_charges_leverage_changes():
    idx = pd.date_range("2000-01-31", periods=3, freq="ME")
    r, rate = pd.Series(0.0, index=idx), pd.Series(0.0, index=idx)
    L = pd.Series([1.0, 2.0, 1.5], index=idx)
    assert np.allclose(B.lever(r, L, rate, cost=0.01), [0, -0.01, -0.005])
