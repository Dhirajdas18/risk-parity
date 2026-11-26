"""IIM Ahmedabad's Indian Fama-French-momentum data library (Agarwalla, Jacob and Varma):
the latest release's survivorship-bias adjusted files, fetched into data/iima/ (not committed).

Factor columns, in percent a period: SMB (small minus big), HML (high minus low book-to-market),
WML (winners minus losers, momentum), MF (the market premium: market return minus risk-free,
which matches the library's own published "market premium") and RF (risk-free).
"""

import os
import re
import time
import urllib.request
from pathlib import Path

import pandas as pd

LIBRARY = "https://faculty.iima.ac.in/iffm/Indian-Fama-French-Momentum/"
CITATION = ("Agarwalla, S. K., Jacob, J. and Varma, J. R. (2013), Four factor model in Indian "
            "equities market, Working Paper W.P. No. 2013-09-05, Indian Institute of Management, "
            "Ahmedabad")
FILES = {
    "factors_monthly": "FourFactors_and_Market_Returns_Monthly",
    "factors_daily": "FourFactors_and_Market_Returns_Daily",
    "size_value": "Size_Value_Portfolio_Returns_Monthly",
    "size_momentum": "Size_Momentum_Portfolio_Returns_Monthly",
}
FACTORS = ["MKT", "SMB", "HML", "WML"]
NAMES = {"MKT": "Market", "SMB": "Size", "HML": "Value", "WML": "Momentum"}


def data_dir() -> Path:
    return Path(os.environ.get("RP_DATA_DIR", "data")) / "iima"


def _get(url: str, tries: int = 4) -> bytes:
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except OSError:
            if i == tries - 1:
                raise
            time.sleep(5 * (i + 1))
    raise RuntimeError("unreachable")


def latest_release(html: str) -> str:
    """The newest 'YYYY-MM' release named in the library page's survivorship-adjusted links."""
    found = re.findall(r"DATA/(\d{4}-\d{2})_FourFactors_and_Market_Returns_Monthly_"
                       r"SurvivorshipBiasAdjusted\.csv", html)
    if not found:
        raise ValueError("no release found on the library page")
    return max(found)


def fetch() -> str:
    """Download the latest release's files; returns the release."""
    release = latest_release(_get(LIBRARY).decode("utf-8", "replace"))
    out = data_dir()
    out.mkdir(parents=True, exist_ok=True)
    for key, stem in FILES.items():
        body = _get(f"{LIBRARY}DATA/{release}_{stem}_SurvivorshipBiasAdjusted.csv")
        if not body.startswith(b"Date,"):
            raise ValueError(f"{key}: not a CSV")
        (out / f"{key}.csv").write_bytes(body)
    (out / "release.txt").write_text(release)
    return release


def release() -> str:
    return (data_dir() / "release.txt").read_text().strip()


def _read(key: str) -> pd.DataFrame:
    d = pd.read_csv(data_dir() / f"{key}.csv", na_values=["NA"])
    d["Date"] = pd.to_datetime(d["Date"], format="mixed")
    return d.set_index("Date").sort_index()


def factors(freq: str = "monthly") -> pd.DataFrame:
    """Factor returns in decimals, indexed by month-end (monthly) or day: MKT (the market
    premium, the file's MF), SMB, HML, WML, RF and MARKET (the market's own return, MF + RF).
    Periods missing any of them are dropped (the source has
    no market return for its first month and no long-short returns for November 1994)."""
    d = _read(f"factors_{freq}") / 100
    d = d.dropna(subset=["MF", "RF", "SMB", "HML", "WML"])
    d["MKT"] = d["MF"]
    d["MARKET"] = d["MF"] + d["RF"]
    if freq == "monthly":
        d.index = d.index + pd.offsets.MonthEnd(0)
    return d[FACTORS + ["RF", "MARKET"]]


def portfolios(key: str) -> pd.DataFrame:
    """Size-value (BV, BN, BG, SV, SN, SG) or size-momentum (WB, WS, LB, LS) portfolio returns,
    decimals, month-end index."""
    d = _read(key) / 100
    d.columns = [re.search(r"Portfolios? (\w+) returns", c).group(1) for c in d.columns]
    d.index = d.index + pd.offsets.MonthEnd(0)
    return d
