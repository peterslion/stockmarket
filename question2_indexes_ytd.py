# Question 2. [Macro] Indexes YTD (as of 21 August 2026)
import pandas as pd
import yfinance as yf

START = "2026-01-01"
END = "2026-08-21"

indexes = [
    ("United States", "S&P 500", "^GSPC"),
    ("China", "Shanghai Composite", "000001.SS"),
    ("Hong Kong", "HANG SENG INDEX", "^HSI"),
    ("Australia", "S&P/ASX 200", "^AXJO"),
    ("India", "Nifty 50", "^NSEI"),
    ("Canada", "S&P/TSX Composite", "^GSPTSE"),
    ("Germany", "DAX", "^GDAXI"),
    ("United Kingdom", "FTSE 100", "^FTSE"),
    ("Japan", "Nikkei 225", "^N225"),
    ("Mexico", "IPC Mexico", "^MXX"),
    ("Brazil", "Ibovespa", "^BVSP"),
]

tickers = [ticker for _, _, ticker in indexes]

raw = yf.download(
    tickers,
    start=START,
    end="2026-08-22",
    auto_adjust=True,
    progress=False,
    threads=True,
)

close = raw["Close"]

rows = []
for country, name, ticker in indexes:
    series = close[ticker].dropna() if ticker in close.columns else pd.Series(dtype="float64")
    series = series.loc[:END]

    if series.empty:
        rows.append(
            {
                "country": country,
                "index": name,
                "ticker": ticker,
                "start_date": pd.NaT,
                "start_close": pd.NA,
                "end_date": pd.NaT,
                "end_close": pd.NA,
                "return": pd.NA,
            }
        )
        continue

    start_date, start_close = series.index[0], float(series.iloc[0])
    end_date, end_close = series.index[-1], float(series.iloc[-1])
    growth = end_close / start_close - 1

    rows.append(
        {
            "country": country,
            "index": name,
            "ticker": ticker,
            "start_date": start_date.date(),
            "start_close": start_close,
            "end_date": end_date.date(),
            "end_close": end_close,
            "return": growth,
        }
    )

returns = pd.DataFrame(rows)
print(returns.to_string(index=False, formatters={"return": "{:.2%}".format}))
