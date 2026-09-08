"""Question 2. [Macro] Index year-to-date returns as of 21 August 2026."""

from __future__ import annotations

import pandas as pd
import yfinance as yf

START = "2026-01-01"
END = "2026-08-21"
DOWNLOAD_END = "2026-08-22"

INDEXES = [
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


def close_frame(raw: pd.DataFrame | pd.Series) -> pd.DataFrame:
    """Normalize yfinance Close output to a ticker-column DataFrame."""
    data = raw
    if isinstance(raw, pd.DataFrame) and isinstance(raw.columns, pd.MultiIndex):
        if "Close" in raw.columns.get_level_values(0):
            data = raw["Close"]
    elif isinstance(raw, pd.DataFrame) and "Close" in raw.columns:
        data = raw["Close"]
    if isinstance(data, pd.Series):
        data = data.to_frame()
    frame = data.copy()
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = [str(col[-1]) for col in frame.columns]
    else:
        frame.columns = [str(col) for col in frame.columns]
    return frame


def index_ytd_returns(
    close: pd.DataFrame,
    end: str = END,
    indexes: list[tuple[str, str, str]] | None = None,
) -> pd.DataFrame:
    """First-to-last close return through END for each index."""
    universe = indexes or INDEXES
    frame = close.copy()
    frame.columns = [str(col) for col in frame.columns]
    cutoff = pd.Timestamp(end)
    rows = []
    for country, name, ticker in universe:
        series = frame[ticker].dropna() if ticker in frame.columns else pd.Series(dtype="float64")
        series = series.loc[:cutoff]
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
        rows.append(
            {
                "country": country,
                "index": name,
                "ticker": ticker,
                "start_date": pd.Timestamp(start_date).date(),
                "start_close": start_close,
                "end_date": pd.Timestamp(end_date).date(),
                "end_close": end_close,
                "return": end_close / start_close - 1,
            }
        )
    return pd.DataFrame(rows)


def load_index_closes(start: str = START, end: str = DOWNLOAD_END) -> pd.DataFrame:
    tickers = [ticker for _, _, ticker in INDEXES]
    raw = yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    return close_frame(raw)


def _json_value(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return str(value)
    if isinstance(value, str):
        return value
    return float(value)


def run_index_ytd() -> dict:
    table = index_ytd_returns(load_index_closes())
    ranked = table.dropna(subset=["return"]).sort_values("return", ascending=False)
    rows = []
    for _, row in table.iterrows():
        rows.append(
            {
                "country": row["country"],
                "index": row["index"],
                "ticker": row["ticker"],
                "start_date": _json_value(row["start_date"]),
                "start_close": _json_value(row["start_close"]),
                "end_date": _json_value(row["end_date"]),
                "end_close": _json_value(row["end_close"]),
                "return": _json_value(row["return"]),
            }
        )
    return {
        "start": START,
        "end": END,
        "as_of": END,
        "index_count": int(len(table)),
        "available_count": int(table["return"].notna().sum()),
        "leader": None
        if ranked.empty
        else {
            "country": ranked.iloc[0]["country"],
            "index": ranked.iloc[0]["index"],
            "return": float(ranked.iloc[0]["return"]),
        },
        "laggard": None
        if ranked.empty
        else {
            "country": ranked.iloc[-1]["country"],
            "index": ranked.iloc[-1]["index"],
            "return": float(ranked.iloc[-1]["return"]),
        },
        "rows": rows,
    }
