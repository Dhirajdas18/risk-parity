"""The risk parity lab: one static Plotly page carrying monthly asset returns (rp.js runs the
portfolios in the browser)."""

import datetime
import json
import re
from pathlib import Path
from string import Template

import pandas as pd

from rp import iima, plots

FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
ICON = (
    "data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 16 16%22%3E"
    "%3Cpath d=%22M1 8h3l1-4 2 8 2-6 1 2h5%22 fill=%22none%22"
    " stroke=%22%232a78d6%22 stroke-width=%221.8%22 stroke-linejoin=%22round%22/%3E"
    "%3C/svg%3E"
)
HERE = Path(__file__).parent
JS = (HERE / "rp.js").read_text(encoding="utf-8")
LAB = (HERE / "lab.html").read_text(encoding="utf-8")
PAGE = Template((HERE / "page.html").read_text(encoding="utf-8"))
REPO = "https://github.com/Dhirajdas18/risk-parity"


def lab_data(t: pd.DataFrame) -> dict:
    """Months as 'YYYY-MM-DD' and each asset's monthly return (6 decimals)."""
    out = {"months": list(t.index.strftime("%Y-%m-%d"))}
    for c in t:
        out[c] = [round(float(v), 6) for v in t[c]]
    return out


def lab_section(d: dict) -> str:
    from rp.reports import COL

    return (LAB.replace("$js", JS).replace("$data", json.dumps(d, separators=(",", ":")))
            .replace("$colors", json.dumps(COL)))


def method_section(_: dict) -> str:
    return """<ul class="plain">
<li>Returns: monthly, in rupees. Stocks are IIMA’s broad market including dividends, not NIFTY.
Gilts are a par bond of 5 or 10 years bought at each month-end at RBI’s yield and repriced a month
later at the yield for its shorter life, plus a month’s coupon; RBI’s yields are computed from
settled trades. Gold is COMEX gold times the rupee rate at month-ends; Indian prices also carry
import duty, which changed over the years.</li>
<li>Risk parity: each month the covariance of the chosen assets over the previous 12, 36 or 60
months gives weights whose risk contributions (weight times the covariance-weighted exposure) are
equal, solved exactly by cyclical coordinate descent. The weights are held for the month without
rebalancing costs.</li>
<li>Sharpe ratios are measured above IIMA’s risk-free rate; growth is compounded over calendar
time. Research only, not investment advice.</li>
</ul>"""


SECTIONS = [
    ("Risk parity lab", "Pick the assets, the years and the estimation window. Research only, not "
     "investment advice.", lab_section),
    ("Method and caveats", "How the returns and weights are built, and what the page leaves out.",
     method_section),
]


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def build_html(t: pd.DataFrame, release: str) -> str:
    d = lab_data(t)
    parts, nav = [], []
    for title, blurb, make in SECTIONS:
        sid = _slug(title)
        nav.append(f'<li><a href="#{sid}">{title}</a></li>')
        parts.append(f'<section id="{sid}">\n<h2>{title}</h2>\n<p>{blurb}</p>\n{make(d)}\n'
                     "</section>")
    dk, s = plots.DARK, plots.SERIES
    return PAGE.substitute(
        updated=datetime.date.today().strftime("%d %b %Y").lstrip("0"),
        release=release, first=f"{t.index[0]:%b %Y}", last=f"{t.index[-1]:%b %Y}",
        citation=iima.CITATION, icon=ICON, font=FONT, repo=REPO,
        surface=plots.SURFACE, text=plots.TEXT, text2=plots.TEXT_2, grid=plots.GRID,
        accent=s[0], accent2=s[1], green=s[2], violet=s[6], muted=plots.MUTED,
        d_surface=dk[plots.SURFACE], d_text=dk[plots.TEXT], d_text2=dk[plots.TEXT_2],
        d_grid=dk[plots.GRID], d_accent=dk[s[0]], d_accent2=dk[s[1]], d_green=dk[s[2]],
        d_violet=dk[s[6]], d_muted="#6b6a64",
        nav="\n".join(nav), sections="\n".join(parts),
    )

