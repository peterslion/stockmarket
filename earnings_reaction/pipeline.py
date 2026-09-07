"""End-to-end AMZN (or other ticker) earnings-surprise reaction analysis."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from earnings_reaction.analysis import (
    SURPRISE_COL,
    align_earnings_to_returns,
    filter_lookback,
    summarize_positive_surprises,
    two_day_returns,
)
from earnings_reaction.fetch import DEFAULT_TICKER, load_earnings, load_prices

LOOKBACKS = (
    ("3y", 3, "Last 3 years"),
    ("5y", 5, "Last 5 years"),
    ("10y", 10, "Last 10 years"),
    ("all", None, "All reported history"),
)


def _iso_date(value) -> str | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def _float(value) -> float | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return None
    return float(value)


def _row_to_record(row: pd.Series) -> dict:
    surprise = _float(row.get(SURPRISE_COL))
    return {
        "earnings_date": _iso_date(row["earnings_date"]),
        "day2": _iso_date(row["day2"]),
        "eps_estimate": _float(row.get("EPS Estimate")),
        "reported_eps": _float(row.get("Reported EPS")),
        "surprise_pct": surprise,
        "two_day_return": _float(row.get("two_day_return")),
        "is_positive_surprise": bool(surprise is not None and surprise > 0),
    }


def run_analysis(ticker: str = DEFAULT_TICKER) -> dict:
    ticker = ticker.strip().upper() or DEFAULT_TICKER
    earnings = load_earnings(ticker)
    prices = load_prices(ticker)
    if prices.empty or "Close" not in prices.columns:
        raise RuntimeError(f"No price history returned for {ticker}.")

    close = prices["Close"]
    aligned = align_earnings_to_returns(earnings, close)
    returns = two_day_returns(close)
    as_of = pd.Timestamp(close.index.max())
    if as_of.tzinfo is not None:
        as_of = as_of.tz_localize(None)
    as_of = as_of.normalize()

    windows = []
    for key, years, label in LOOKBACKS:
        subset = filter_lookback(aligned, years, as_of=as_of)
        summary = summarize_positive_surprises(subset)
        positive = subset.loc[
            (subset[SURPRISE_COL] > 0) & subset["two_day_return"].notna()
        ].sort_values("earnings_date", ascending=False)
        windows.append(
            {
                "key": key,
                "years": years,
                "label": label,
                **summary,
                "events": [_row_to_record(row) for _, row in positive.iterrows()],
            }
        )

    all_events = [
        _row_to_record(row)
        for _, row in aligned.sort_values("earnings_date", ascending=False).iterrows()
    ]

    def _naive_ts(value) -> pd.Timestamp:
        ts = pd.Timestamp(value)
        if ts.tzinfo is not None:
            ts = ts.tz_localize(None)
        return ts

    price_start = _naive_ts(close.index.min())
    price_end = _naive_ts(close.index.max())

    return {
        "ticker": ticker,
        "as_of": _iso_date(as_of),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "price_start": _iso_date(price_start),
        "price_end": _iso_date(price_end),
        "price_sessions": int(len(close.dropna())),
        "earnings_rows_loaded": int(len(earnings)) if earnings is not None else 0,
        "reported_earnings": int(len(aligned)),
        "baseline_median_2day_return": _float(returns.median()) if len(returns) else None,
        "windows": windows,
        "all_reported_events": all_events,
        "methodology": {
            "earnings_source": "yfinance.Ticker.get_earnings_dates()",
            "price_source": "yfinance.Ticker.history(period='max', auto_adjust=True)",
            "two_day_return": "Close_Day3 / Close_Day1 - 1, indexed on Day 2 (earnings session)",
            "positive_surprise": "Surprise(%) > 0 with a reported EPS and a mapped 2-day return",
            "correlation": "Pearson and Spearman between 2-day return and Surprise(%)",
        },
    }
