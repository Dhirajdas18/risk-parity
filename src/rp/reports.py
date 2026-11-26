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


def report_estimation(out_dir: Path) -> dict:
    """Estimation choices for risk parity, all walk-forward from Jan 2009 (so a 60-month window
    has data): covariance from the past 12, 36 or 60 months, plain or with exponentially fading
    weights (half-life 12 months), rebalanced every 1, 3 or 12 months, paying 0.25% per rupee
    traded (one way). Net growth, volatility, Sharpe, worst fall, turnover and cost a year."""
    from rp import assets
    from rp import backtest as B
    from rp import weights as W

    t = assets.table()
    R, cash = t[RISKY], t["cash"]
    est = {"plain": lambda p: W.erc(cov(p)), "fading": lambda p: W.erc(W.ewma_cov(p, 12))}
    res, grid = {}, {}
    for win in (12, 36, 60):
        for e, f in est.items():
            for ev in (1, 3, 12):
                o = B.run(R, f, win, cost=0.0025, every=ev, start="2009-01-31")
                yrs = len(o) / 12
                s = B.stats(o["net"], cash)
                g = B.stats(o["gross"], cash)["cagr"]
                grid[win, e, ev] = (s["cagr"], o["cost"].sum() / yrs)
                res[f"  {win} months, {e}, every {ev}"] = (
                    fmt(s) + f"; before costs {g:+.1%}; turnover {o['turnover'].sum() / yrs:.0%}"
                    f" a year, cost {o['cost'].sum() / yrs:.2%} a year")
    o = B.run(R, rules()["60/40"], 60, cost=0.0025, start="2009-01-31")
    res["60/40, same months and costs"] = fmt(B.stats(o["net"], cash))
    res["months"] = f"{len(o)}, {o.index[0]:%b %Y}-{o.index[-1]:%b %Y}"
    c = [v[0] for v in grid.values()]
    res["range of net growth"] = f"{min(c):.1%} to {max(c):.1%}"

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    groups = [(w, e) for w in (12, 36, 60) for e in est]
    x = np.arange(len(groups))
    cl = {1: plots.SERIES[0], 3: plots.SERIES[3], 12: plots.SERIES[2]}
    for ax, i, lab, f in ((axes[0], 0, "compounded a year after costs", lambda v: f"{v:.1%}"),
                          (axes[1], 1, "trading cost a year", lambda v: f"{v:.2%}")):
        for j, ev in enumerate((1, 3, 12)):
            y = [grid[w, e, ev][i] for w, e in groups]
            ax.scatter(x + (j - 1) * 0.18, y, s=46, color=cl[ev], zorder=3,
                       label={1: "monthly", 3: "quarterly", 12: "yearly"}[ev])
        ax.set_xticks(x, [f"{w} months\n{e}" for w, e in groups], fontsize=8.5)
        ax.yaxis.set_major_formatter(lambda v, _, f=f: f(v))
        ax.set_title(lab, fontsize=10.5, loc="left")
    axes[0].set_yticks([0.10, 0.105, 0.11, 0.115, 0.12])
    axes[1].set_yticks([0, 0.0005, 0.001, 0.0015, 0.002, 0.0025])
    axes[0].legend(frameon=False, fontsize=8.5, title="rebalanced", title_fontsize=8.5,
                   loc="lower right")
    fig.suptitle("How risk parity was estimated barely mattered: 10.8% to 11.5% a year after "
                 "costs, 2009-2025", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    plots.save(fig, out_dir, "estimation")
    plt.close(fig)
    return res


CRISES = {"2008 crash": ("2008-01", "2009-02"), "2013 taper": ("2013-06", "2013-08"),
          "2020 Covid": ("2020-02", "2020-03"), "2022 rate rises": ("2022-01", "2022-06")}


def report_crises(out_dir: Path) -> dict:
    """Crises: each portfolio's return over four named stress windows (walk-forward, 36-month
    window, monthly, 0.25% per rupee traded), with each asset's return and gold split into its
    dollar price and the rupee; and average returns over every month stocks fell more than 5%,
    every month the 10-year gilt fell more than 2%, and every month both fell."""
    import pandas as pd

    from rp import assets, gold
    from rp import backtest as B

    t = assets.table()
    R, cash = t[RISKY], t["cash"]
    ru = rules()
    runs = {k: B.run(R, f, 36, cost=0.0025) for k, f in ru.items()}
    L = (B.exante_vol(R, runs["60/40"]) / B.exante_vol(R, runs["risk parity (ERC)"])).clip(upper=4)
    P = pd.DataFrame({k: o["net"] for k, o in runs.items()})
    P["risk parity 2x, borrow at cash + 3%"] = B.lever(P["risk parity (ERC)"], L, cash + 0.03 / 12)
    P = P.join(R)
    g = pd.read_parquet(gold.yahoo_dir() / "gold.parquet").resample("ME").last()
    res, tab = {}, {}
    for k, (a, b) in CRISES.items():
        x = (1 + P.loc[a:b]).prod() - 1
        tab[k] = x
        prev = g.index[g.index.get_indexer([pd.Timestamp(a)], method="bfill")[0] - 1]
        gd = g.loc[prev:b]
        usd, inr = (gd.iloc[-1] / gd.iloc[0] - 1)[["GC=F", "USDINR=X"]]
        res[f"{k} ({a} to {b})"] = "; ".join(f"{NAMES.get(c, c)} {v:+.1%}" for c, v in x.items())
        res[f"  {k}, gold"] = f"dollar price {usd:+.1%}, dollar in rupees {inr:+.1%}"
    for lab, m in (("stocks fell more than 5%", P["equity"] < -0.05),
                   ("10-year gilt fell more than 2%", P["gilt10"] < -0.02),
                   ("stocks and gilt both fell", (P["equity"] < 0) & (P["gilt10"] < 0))):
        res[f"months {lab}"] = f"{m.sum()} of {len(P)}: " + "; ".join(
            f"{NAMES.get(c, c)} {v:+.2%}" for c, v in P[m].mean().items())

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1.25, 1]})
    for ax, cols, cl, title in (
            (axes[0], ["60/40", "equal weight", "risk parity (ERC)",
                       "risk parity 2x, borrow at cash + 3%"],
             [plots.TEXT, plots.MUTED, plots.SERIES[0], plots.SERIES[1]], "Portfolios"),
            (axes[1], RISKY, [COL[c] for c in RISKY], "Assets (gold in rupees)")):
        x = np.arange(len(CRISES))
        wd = 0.8 / len(cols)
        for j, (c, col) in enumerate(zip(cols, cl, strict=True)):
            ax.bar(x + (j - (len(cols) - 1) / 2) * wd, [tab[k][c] * 100 for k in CRISES],
                   width=wd * 0.92, color=col, label=NAMES.get(c, c))
        ax.axhline(0, color=plots.TEXT_2, lw=0.8)
        ax.set_xticks(x, list(CRISES), fontsize=9)
        ax.yaxis.set_major_formatter(
            lambda v, _: "0%" if round(v) == 0 else f"{v:+.0f}%".replace("-", "−"))
        ax.legend(frameon=False, fontsize=8, loc="lower right")
        ax.set_title(title, fontsize=10.5, loc="left")
    axes[0].set_ylabel("return over the window")
    fig.suptitle("Risk parity rose 11% through the 2008 crash while 60/40 lost 36%; gilts and "
                 "gold both rose", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    plots.save(fig, out_dir, "crises")
    plt.close(fig)
    return res


REPORTS: dict[str, Callable[[Path], dict]] = {
    "basics": report_basics,
    "leverage": report_leverage,
    "estimation": report_estimation,
    "crises": report_crises,
}
