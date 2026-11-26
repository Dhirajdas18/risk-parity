"""README findings, one function per topic: `rp report <topic>` writes charts to out/."""

from collections.abc import Callable
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from rp import plots

RISKY = ["equity", "gilt10", "gold"]
NAMES = {"equity": "stocks", "gilt10": "10-year gilt", "gilt5": "5-year gilt", "gold": "gold",
         "cash": "cash"}
COL = {"equity": plots.SERIES[0], "gilt10": plots.SERIES[2], "gilt5": plots.SERIES[4],
       "gold": plots.SERIES[3], "cash": plots.MUTED}


def cov(p: np.ndarray) -> np.ndarray:
    return np.cov(p, rowvar=False)


def rules() -> dict:
    from rp import weights as W

    return {"equal weight": lambda p: np.full(p.shape[1], 1 / p.shape[1]),
            "60/40": lambda p: np.r_[0.6, 0.4, np.zeros(p.shape[1] - 2)],
            "inverse volatility": lambda p: W.inverse_vol(cov(p)),
            "risk parity (ERC)": lambda p: W.erc(cov(p))}


def fmt(s: dict) -> str:
    return (f"compounded {s['cagr']:+.1%} a year, volatility {s['vol']:.1%}, Sharpe "
            f"{s['sharpe']:.2f}, worst fall {s['dd']:.0%}")


def report_basics(out_dir: Path) -> dict:
    """What risk parity does on Indian stocks, the 10-year gilt and gold: each asset's return,
    volatility and correlations (Jan 2004 - Dec 2025); full-sample weights and each asset's share
    of portfolio risk for equal weight, 60/40, inverse volatility and equal risk contribution; and
    each rule run walk-forward (weights from the previous 36 months, monthly, no costs)."""
    from rp import assets
    from rp import backtest as B
    from rp import weights as W

    t = assets.table()
    R = t[RISKY]
    res = {"months": f"{len(t)}, {t.index[0]:%b %Y}-{t.index[-1]:%b %Y}"}
    for c in t:
        s = B.stats(t[c], t["cash"])
        res[f"  {NAMES[c]}"] = (f"compounded {s['cagr']:+.1%} a year, volatility {s['vol']:.1%}, "
                                f"worst fall {s['dd']:.0%}")
    C = R.corr()
    res["  correlations"] = "; ".join(f"{NAMES[a]}-{NAMES[b]} {C.at[a, b]:+.2f}"
                                      for i, a in enumerate(RISKY) for b in RISKY[i + 1:])
    S = cov(R.to_numpy())
    fixed = {"equal weight": np.full(3, 1 / 3), "60/40": np.array([0.6, 0.4, 0]),
             "inverse volatility": W.inverse_vol(S), "risk parity (ERC)": W.erc(S)}
    shares = {}
    for k, w in fixed.items():
        rc = W.risk_contributions(w, S)
        shares[k] = (w, rc)
        res[f"full sample, {k}"] = (
            "weights " + ", ".join(f"{NAMES[c]} {v:.0%}" for c, v in zip(RISKY, w, strict=True))
            + "; risk " + ", ".join(f"{NAMES[c]} {v:.0%}" for c, v in zip(RISKY, rc, strict=True))
            + f"; volatility {np.sqrt(w @ S @ w * 12):.1%}")
    curves = {}
    for k, f in rules().items():
        o = B.run(R, f, 36)
        curves[k] = (1 + o["net"]).cumprod()
        s = B.stats(o["net"], t["cash"])
        res[f"walk-forward {o.index[0]:%b %Y}-{o.index[-1]:%b %Y}, {k}"] = (
            fmt(s) + "; average weights " + ", ".join(
                f"{NAMES[c]} {o[c].mean():.0%}" for c in RISKY))

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1, 1.3]})
    ax = axes[0]
    keys = list(fixed)
    y = np.arange(len(keys))[::-1]
    left = np.zeros(len(keys))
    for j, c in enumerate(RISKY):
        v = np.array([shares[k][1][j] for k in keys]) * 100
        ax.barh(y, v, left=left, color=COL[c], height=0.6, label=NAMES[c])
        left += v
    ax.set_yticks(y, keys, fontsize=9)
    ax.set_xlim(0, 100)
    ax.set_xlabel("share of the portfolio's risk, %")
    ax.legend(frameon=False, fontsize=8.5, ncols=3, loc="lower left", bbox_to_anchor=(0, 1.0))
    ax.set_title("Where the risk comes from (2004-2025)", fontsize=10.5, loc="left", pad=22)
    ax = axes[1]
    cl = {"equal weight": plots.MUTED, "60/40": plots.TEXT, "inverse volatility": plots.SERIES[3],
          "risk parity (ERC)": plots.SERIES[0]}
    for k, w in curves.items():
        ax.plot(w.index, w, color=cl[k], lw=1.8 if "ERC" in k else 1.3, label=k)
    ax.yaxis.set_major_formatter(lambda v, _: f"₹{v:g}")
    ax.set_ylabel("₹1 from 2007, no costs")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("Walk-forward, weights from the past 36 months", fontsize=10.5, loc="left")
    fig.suptitle("In 60/40, stocks carried 96% of the risk; risk parity spread it evenly",
                 x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    plots.save(fig, out_dir, "basics")
    plt.close(fig)
    return res


def report_leverage(out_dir: Path) -> dict:
    """Leverage: risk parity scaled each month to 60/40's forecast volatility (both forecasts from
    the same past 36 months, leverage capped at 4), borrowing the extra at the cash rate plus a
    spread; against unlevered risk parity, 60/40 and all stocks (Jan 2007 - Dec 2025, no trading
    costs). Also the spread over cash at which levered risk parity only matches 60/40's growth."""
    from rp import assets
    from rp import backtest as B

    t = assets.table()
    R, cash = t[RISKY], t["cash"]
    ru = rules()
    erc, s64 = B.run(R, ru["risk parity (ERC)"]), B.run(R, ru["60/40"])
    stocks = B.run(R, lambda p: np.array([1.0, 0, 0]))
    L = (B.exante_vol(R, s64) / B.exante_vol(R, erc)).clip(upper=4)
    res = {"leverage": f"average {L.mean():.2f}x, range {L.min():.2f}-{L.max():.2f}x",
           "cash": f"compounded {B.stats(cash.loc[L.index], cash)['cagr']:.1%} a year"}
    curves = {"60/40": s64["net"], "all stocks": stocks["net"],
              "risk parity, no borrowing": erc["net"]}
    for sp in (0.0, 0.03, 0.08):
        curves[f"risk parity levered, borrowing at cash + {sp:.0%}"] = B.lever(
            erc["net"], L, cash + sp / 12)
    for k, v in curves.items():
        res[f"  {k}"] = fmt(B.stats(v, cash))
    target = B.stats(s64["net"], cash)["cagr"]
    lo, hi = 0.0, 0.2
    for _ in range(40):
        m = (lo + hi) / 2
        c = B.stats(B.lever(erc["net"], L, cash + m / 12), cash)["cagr"]
        lo, hi = (m, hi) if c > target else (lo, m)
    res["break-even spread over cash (levered risk parity grows like 60/40)"] = f"{m:.1%} a year"

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1.4, 1]})
    ax = axes[0]
    cl = {"60/40": plots.TEXT, "all stocks": plots.MUTED,
          "risk parity, no borrowing": plots.SERIES[2]}
    lev_col = [plots.SERIES[0], plots.SERIES[3], plots.SERIES[1]]
    for k, v in curves.items():
        w = (1 + v).cumprod()
        c = cl.get(k) or lev_col.pop(0)
        ax.plot(w.index, w, color=c, lw=1.8 if "levered" in k else 1.3,
                label=k.replace("risk parity levered, borrowing", "levered, borrow"))
    ax.set_yscale("log")
    ax.set_yticks([1, 2, 5, 10, 20], minor=False)
    ax.yaxis.set_minor_formatter(lambda v, _: "")
    ax.yaxis.set_major_formatter(lambda v, _: f"₹{v:g}")
    ax.set_ylabel("₹1 from 2007, no trading costs")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("Risk parity scaled to 60/40's risk", fontsize=10.5, loc="left")
    ax = axes[1]
    ax.plot(L.index, L, color=plots.SERIES[0], lw=1.5)
    ax.axhline(1, color=plots.MUTED, lw=0.8)
    ax.set_ylim(0, 3.5)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:g}x")
    ax.set_ylabel("rupees invested per rupee owned")
    ax.set_title("Leverage needed, from the past 36 months", fontsize=10.5, loc="left")
    fig.suptitle("Levered 2x at the cash rate, risk parity beat 60/40; at about 5% over cash, "
                 "the gain was gone", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    plots.save(fig, out_dir, "leverage")
    plt.close(fig)
    return res


REPORTS: dict[str, Callable[[Path], dict]] = {
    "basics": report_basics,
    "leverage": report_leverage,
}
