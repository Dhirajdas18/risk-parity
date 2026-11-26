import numpy as np

from rp import weights as W


def _cov(seed=0, n=4):
    rng = np.random.default_rng(seed)
    a = rng.normal(size=(n, n))
    return a @ a.T / n + np.diag(rng.uniform(0.01, 0.1, n))


def test_erc_equalises_risk_shares_and_respects_a_budget():
    S = _cov()
    w = W.erc(S)
    assert np.isclose(w.sum(), 1) and (w > 0).all()
    assert np.allclose(W.risk_contributions(w, S), 0.25, atol=1e-8)
    b = np.array([0.4, 0.3, 0.2, 0.1])
    assert np.allclose(W.risk_contributions(W.erc(S, b), S), b, atol=1e-8)


def test_erc_is_inverse_vol_when_assets_are_uncorrelated():
    S = np.diag([0.04, 0.01, 0.09])
    assert np.allclose(W.erc(S), W.inverse_vol(S))


def test_min_variance_and_max_sharpe_on_simple_cases():
    S = np.diag([0.04, 0.01])
    assert np.allclose(W.min_variance(S), [0.2, 0.8], atol=1e-6)
    w = W.max_sharpe(S, np.array([0.04, 0.01]))  # unconstrained answer ∝ S^-1 mu = [1, 1]
    assert np.allclose(w, [0.5, 0.5], atol=0.02)


def test_ewma_cov_long_half_life_is_sample_cov():
    rng = np.random.default_rng(1)
    p = rng.normal(size=(40, 3))
    assert np.allclose(W.ewma_cov(p, 1e9), np.cov(p, rowvar=False))
    q = p.copy()
    q[:20] *= 10  # old months noisy: a short half-life should mostly ignore them
    assert W.ewma_cov(q, 2)[0, 0] < np.cov(q, rowvar=False)[0, 0] / 5
