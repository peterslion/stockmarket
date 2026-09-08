"""Question 1. [Index] S&P 500 stocks added since 2020."""

from __future__ import annotations

import io

import pandas as pd
import requests

URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; sp500-additions/1.0; "
        "+https://en.wikipedia.org/wiki/List_of_S%26P_500_companies)"
    )
}
SINCE_YEAR = 2020


def load_sp500_constituents() -> pd.DataFrame:
    html = requests.get(URL, headers=HEADERS, timeout=30)
    html.raise_for_status()
    tables = pd.read_html(io.StringIO(html.text))
    return tables[0][["Symbol", "Security", "Date added"]].copy()


def additions_since(constituents: pd.DataFrame, since_year: int = SINCE_YEAR) -> pd.DataFrame:
    frame = constituents.copy()
    frame["Date added"] = pd.to_datetime(frame["Date added"], errors="coerce")
    frame["year"] = frame["Date added"].dt.year
    return (
        frame.loc[frame["year"] >= since_year]
        .rename(columns={"Symbol": "ticker", "Security": "name"})
        [["ticker", "name", "year"]]
        .reset_index(drop=True)
    )


def yearly_additions(additions: pd.DataFrame) -> pd.DataFrame:
    if additions.empty:
        return pd.DataFrame(columns=["year", "n_added"])
    return (
        additions.groupby("year")
        .size()
        .reset_index(name="n_added")
        .sort_values("year")
        .reset_index(drop=True)
    )


def peak_year(yearly: pd.DataFrame) -> dict | None:
    if yearly.empty:
        return None
    peak = yearly.loc[yearly["n_added"].idxmax()]
    return {"year": int(peak["year"]), "n_added": int(peak["n_added"])}


def run_sp500_additions() -> dict:
    constituents = load_sp500_constituents()
    added = additions_since(constituents)
    yearly = yearly_additions(added)
    peak = peak_year(yearly)
    return {
        "source": URL,
        "since_year": SINCE_YEAR,
        "addition_count": int(len(added)),
        "peak": peak,
        "yearly": [
            {"year": int(row.year), "n_added": int(row.n_added)}
            for row in yearly.itertuples(index=False)
        ],
        "additions": [
            {"ticker": row.ticker, "name": row.name, "year": int(row.year)}
            for row in added.sort_values(["year", "ticker"]).itertuples(index=False)
        ],
    }
