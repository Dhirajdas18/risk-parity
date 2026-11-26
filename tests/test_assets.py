import numpy as np
import pandas as pd

from rp import assets


def test_par_bond_returns_its_coupon_when_yields_stay_put():
    idx = pd.date_range("2020-01-31", periods=4, freq="ME")
    w = pd.DataFrame({9: 7.0, 10: 7.0}, index=idx)
    r = assets.bond_returns(w, 10)
    assert np.allclose(r, 0.07 / 12)


def test_bond_loses_about_duration_times_the_yield_rise():
    idx = pd.date_range("2020-01-31", periods=2, freq="ME")
    w = pd.DataFrame({9: [7.0, 8.0], 10: [7.0, 8.0]}, index=idx)
    r = assets.bond_returns(w, 10).iloc[0]
    dur = (1 - 1.035 ** -20) / 0.07  # modified duration of a 10-year 7% par bond, half-yearly
    assert abs(r - (0.07 / 12 - dur * 0.01)) < 0.004  # convexity makes it a little better
    assert r > 0.07 / 12 - dur * 0.01


def test_par_price_is_100_at_any_maturity():
    assert np.allclose(assets.par_price(np.array([6.5]), np.array([6.5]), np.array([3.7])), 100)
