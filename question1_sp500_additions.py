# Question 1: [Index] S&P 500 Stocks Added to the Index

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

html = requests.get(URL, headers=HEADERS, timeout=30)
html.raise_for_status()

tables = pd.read_html(io.StringIO(html.text))
sp500 = tables[0][["Symbol", "Security", "Date added"]].copy()

sp500["Date added"] = pd.to_datetime(sp500["Date added"], errors="coerce")
sp500["year"] = sp500["Date added"].dt.year

additions = (
    sp500.loc[sp500["year"] >= 2020]
    .rename(columns={"Symbol": "ticker", "Security": "name"})
    [["ticker", "name", "year"]]
    .reset_index(drop=True)
)

yearly = (
    additions.groupby("year")
    .size()
    .reset_index(name="n_added")
    .sort_values("year")
)

peak = yearly.loc[yearly["n_added"].idxmax()]

print(additions)
print()
print(yearly.to_string(index=False))
print()
print(
    f"Highest additions since 2020: {int(peak['year'])} "
    f"({int(peak['n_added'])} stocks)"
)
