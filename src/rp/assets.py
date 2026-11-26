"""Monthly returns of the four asset classes, in decimals, by month-end:
- equity: IIMA's market return (market premium + risk-free), survivorship-bias adjusted;
- gilt10 and gilt5: a 10- and a 5-year par Government of India bond bought each month-end at the
  RBI yield and repriced a month later at the interpolated yield for its shorter life;
- gold: COMEX gold times the rupee rate, month-end to month-end;
- cash: IIMA's risk-free rate.
"""

import numpy as np
import pandas as pd


def par_price(c: np.ndarray, y: np.ndarray, years: np.ndarray) -> np.ndarray:
    """Price per 100 of a bond paying coupon c (% a year, half-yearly) at yield y (%), `years`
    to maturity (fractional periods allowed); a par bond (c = y) prices at 100."""
    h = y / 200
    n = 2 * years
    return (c / 2) / h * (1 - (1 + h) ** -n) + 100 * (1 + h) ** -n


def bond_returns(w: pd.DataFrame, n: int) -> pd.Series:
    """One month's return of an n-year par bond bought at month-end t-1: coupon accrued for a
    month plus the price change at month-end t, at the yield for n - 1/12 years (linear between
    the n-1 and n-year yields)."""
    y0 = w[n].shift(1)
    y1 = w[n] + (w[n - 1] - w[n]) / 12
    p1 = par_price(y0.to_numpy(), y1.to_numpy(), np.full(len(w), n - 1 / 12))
    return pd.Series(p1 / 100 - 1 + y0.to_numpy() / 1200, index=w.index).dropna()


def table() -> pd.DataFrame:
    from rp import gold, iima, rbi

    f = iima.factors("monthly")
    w = rbi.yields()
    g = gold.monthly()
    out = pd.DataFrame({
        "equity": f["MARKET"],
        "gilt10": bond_returns(w, 10),
        "gilt5": bond_returns(w, 5),
        "gold": g["gold_inr"].pct_change(fill_method=None),
        "cash": f["RF"],
    })
    return out.dropna()
