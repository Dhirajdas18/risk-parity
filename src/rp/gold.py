"""Gold in rupees at month-ends: COMEX gold futures (GC=F, $ per troy ounce) times the rupee rate
(USDINR=X), and the GOLDBEES ETF (GOLDBEES.NS) as an Indian price check, from Yahoo Finance,
saved to data/yahoo/ (not committed)."""

import time
from pathlib import Path

import pandas as pd

from rp.iima import data_dir

TICKERS = ["GC=F", "USDINR=X", "GOLDBEES.NS"]


def yahoo_dir() -> Path:
    return data_dir().parent / "yahoo"


def fetch(tries: int = 5) -> pd.DataFrame:
    """Daily closes for TICKERS; retries until none is missing (threads=False: yfinance's cache
    is not safe to share across threads)."""
    import yfinance as yf

    missing = TICKERS
    for i in range(tries):
        df = yf.download(TICKERS, start="2000-01-01", auto_adjust=True, progress=False,
                         threads=False)["Close"]
        missing = [t for t in TICKERS if t not in df or df[t].notna().sum() < 100]
        if not missing:
            out = yahoo_dir()
            out.mkdir(parents=True, exist_ok=True)
            df.to_parquet(out / "gold.parquet")
            return df
        time.sleep(10 * (i + 1))
    raise RuntimeError(f"Yahoo returned no data for {missing} after {tries} tries")


def monthly() -> pd.DataFrame:
    """Month-end gold in rupees per troy ounce (GC=F x USDINR=X, both at their last close in the
    month) and GOLDBEES, from the saved daily closes."""
    d = pd.read_parquet(yahoo_dir() / "gold.parquet")
    m = d.resample("ME").last()
    out = pd.DataFrame({"gold_inr": m["GC=F"] * m["USDINR=X"], "goldbees": m["GOLDBEES.NS"]})
    return out.dropna(how="all")
