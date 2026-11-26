"""Walk-forward portfolios on monthly returns: at each month-end, weights from the previous
`window` months only, held over the next month; trading from the drifted weights costs `cost`
per rupee traded (one way)."""

from collections.abc import Callable

import numpy as np
import pandas as pd

Rule = Callable[[np.ndarray], np.ndarray]  # past returns (T x N) -> weights (N)


def run(r: pd.DataFrame, rule: Rule, window: int = 36, cost: float = 0.0, every: int = 1,
        start: str | None = None) -> pd.DataFrame:
    """Monthly net return, weights held, turnover and cost. Rebalances every `every` months."""
    X = r.to_numpy()
    cols = list(r.columns)
    held = None
    rows, wts = [], []
    first = window if start is None else max(window, int(np.searchsorted(r.index, start)))
    for k, t in enumerate(range(first, len(r))):
        if held is None or k % every == 0:
            target = rule(X[t - window:t])
            trade = np.abs(target - (held if held is not None else 0.0)).sum()
            if held is None:
                trade = 0.0  # the first purchase is not charged
            w = target
        else:
            trade, w = 0.0, held
        gross = float(w @ X[t])
        c = trade * cost
        grown = w * (1 + X[t])
        held = grown / grown.sum()
        rows.append((r.index[t], gross - c, gross, trade / 2, c))
        wts.append(w)
    out = pd.DataFrame(rows, columns=["date", "net", "gross", "turnover", "cost"]).set_index("date")
    return out.join(pd.DataFrame(wts, index=out.index, columns=cols))


def stats(ret: pd.Series, cash: pd.Series) -> dict:
    """Compounded growth over calendar time, volatility and Sharpe above cash (12 months a year),
    worst fall."""
    cash = cash.reindex(ret.index)
    wealth = (1 + ret).cumprod()
    years = (ret.index[-1] - ret.index[0]).days / 365.25 + 1 / 12
    e = ret - cash
    return {"cagr": float(wealth.iloc[-1] ** (1 / years) - 1),
            "vol": float(ret.std() * np.sqrt(12)),
            "sharpe": float(e.mean() / e.std() * np.sqrt(12)) if e.std() > 0 else float("nan"),
            "dd": float((wealth / wealth.cummax() - 1).min())}


def exante_vol(r: pd.DataFrame, o: pd.DataFrame, window: int = 36) -> pd.Series:
    """Each month's volatility forecast (a year) for the weights held in `o`, from the same past
    `window` months the weights were set from."""
    pos = r.index.get_indexer(o.index)
    X, W = r.to_numpy(), o[list(r.columns)].to_numpy()
    v = [np.sqrt(w @ np.cov(X[t - window:t], rowvar=False) @ w * 12) for t, w in zip(pos, W,
                                                                                  strict=True)]
    return pd.Series(v, index=o.index)


def lever(ret: pd.Series, L: pd.Series | float, rate: pd.Series, cost: float = 0.0) -> pd.Series:
    """Return on L rupees of the portfolio per rupee of capital, borrowing L - 1 at `rate`
    (monthly); changing L trades |L_t - L_t-1| rupees at `cost` each (the first month is free)."""
    out = L * ret - (L - 1) * rate.reindex(ret.index)
    if cost and isinstance(L, pd.Series):
        out = out - cost * L.diff().abs().fillna(0)
    return out


def sharpe_diff(a: pd.Series, b: pd.Series, cash: pd.Series) -> tuple[float, float]:
    """Difference of two strategies' Sharpe ratios above cash (a minus b, a year) and its standard
    error from the paired monthly returns (Jobson-Korkie with Memmel's correction)."""
    ea, eb = a - cash.reindex(a.index), b - cash.reindex(b.index)
    sa, sb = ea.mean() / ea.std(), eb.mean() / eb.std()
    rho = ea.corr(eb)
    var = (2 - 2 * rho + 0.5 * (sa**2 + sb**2 - 2 * sa * sb * rho**2)) / len(ea)
    return float((sa - sb) * np.sqrt(12)), float(np.sqrt(var * 12))


def mean_diff(a: pd.Series, b: pd.Series) -> tuple[float, float]:
    """Difference of two strategies' average returns (a minus b, a year) and its standard error
    from the paired monthly differences."""
    d = a - b
    return float(d.mean() * 12), float(d.std() * np.sqrt(12 / len(d)))
