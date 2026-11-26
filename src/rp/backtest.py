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
            "sharpe": float(e.mean() / e.std() * np.sqrt(12)),
            "dd": float((wealth / wealth.cummax() - 1).min())}
