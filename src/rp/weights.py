"""Portfolio weights from a covariance matrix, mirrored in rp.js.

Risk contribution of asset i: w_i (S w)_i, which sums to the portfolio variance w' S w. Equal
risk contribution (ERC) weights make every asset's contribution the same share; they come from
the convex problem min 1/2 y'Sy - sum b_i log y_i (y > 0), w = y / sum y, solved exactly by cyclical
coordinate descent (each step solves a quadratic in y_i).
"""

import numpy as np


def risk_contributions(w: np.ndarray, S: np.ndarray) -> np.ndarray:
    """Each asset's share of portfolio variance (sums to 1)."""
    w = np.asarray(w, float)
    rc = w * (S @ w)
    return rc / rc.sum()


def inverse_vol(S: np.ndarray) -> np.ndarray:
    v = 1 / np.sqrt(np.diag(S))
    return v / v.sum()


def erc(S: np.ndarray, budget: np.ndarray | None = None, tol: float = 1e-12,
        iters: int = 10000) -> np.ndarray:
    """Weights whose risk shares equal `budget` (equal shares by default)."""
    S = np.asarray(S, float)
    n = len(S)
    b = np.full(n, 1 / n) if budget is None else np.asarray(budget, float) / np.sum(budget)
    y = 1 / np.sqrt(np.diag(S))
    for _ in range(iters):
        prev = y.copy()
        for i in range(n):
            a = S[i, i]
            c = S[i] @ y - a * y[i]
            y[i] = (-c + np.sqrt(c * c + 4 * a * b[i])) / (2 * a)
        if np.max(np.abs(y - prev)) < tol * np.max(np.abs(y)):
            break
    return y / y.sum()


def _solve(f, n: int) -> np.ndarray:
    from scipy.optimize import minimize

    cons = ({"type": "eq", "fun": lambda w: w.sum() - 1},)
    res = minimize(f, np.full(n, 1 / n), method="SLSQP", bounds=[(0, 1)] * n, constraints=cons,
                   options={"ftol": 1e-14, "maxiter": 1000})
    w = np.clip(res.x, 0, None)
    return w / w.sum()


def min_variance(S: np.ndarray) -> np.ndarray:
    """Long-only, fully invested minimum variance."""
    return _solve(lambda w: w @ S @ w, len(S))


def max_sharpe(S: np.ndarray, mu: np.ndarray) -> np.ndarray:
    """Long-only, fully invested maximum Sharpe ratio (mu = expected returns above cash)."""
    return _solve(lambda w: -(w @ mu) / np.sqrt(w @ S @ w), len(S))
