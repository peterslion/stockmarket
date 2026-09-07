"""End-to-end AMZN (or other ticker) earnings-surprise reaction analysis."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from earnings_reaction.analysis import (
    SURPRISE_COL,
    align_earnings_to_returns,
    attach_market_context,
    filter_lookback,
    summarize_positive_surprises,
    summarize_reactions,
    summarize_regime_split,
    two_day_returns,
)
from earnings_reaction.fetch import DEFAULT_TICKER, MARKET_INDEX, load_earnings, load_index, load_prices

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


def _bool(value) -> bool | None:
    if value is None or pd.isna(value):
        return None
    return bool(value)


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
        "regime": None if pd.isna(row.get("regime")) else str(row.get("regime")),
        "below_200dma": _bool(row.get("below_200dma")),
    }


def _naive_ts(value) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is not None:
        ts = ts.tz_localize(None)
    return ts


def run_analysis(ticker: str = DEFAULT_TICKER) -> dict:
    ticker = ticker.strip().upper() or DEFAULT_TICKER
    earnings = load_earnings(ticker)
    prices = load_prices(ticker)
    index_prices = load_index(MARKET_INDEX)
    if prices.empty or "Close" not in prices.columns:
        raise RuntimeError(f"No price history returned for {ticker}.")
    if index_prices.empty or "Close" not in index_prices.columns:
        raise RuntimeError(f"No price history returned for {MARKET_INDEX}.")

    close = prices["Close"]
    aligned = attach_market_context(
        align_earnings_to_returns(earnings, close),
        index_prices["Close"],
    )
    returns = two_day_returns(close)
    as_of = _naive_ts(close.index.max()).normalize()

    windows = []
    for key, years, label in LOOKBACKS:
        subset = filter_lookback(aligned, years, as_of=as_of)
        positive = subset.loc[
            (subset[SURPRISE_COL] > 0) & subset["two_day_return"].notna()
        ].sort_values("earnings_date", ascending=False)
        reported = subset.dropna(subset=[SURPRISE_COL, "two_day_return"]).sort_values(
            "earnings_date", ascending=False
        )
        windows.append(
            {
                "key": key,
                "years": years,
                "label": label,
                **summarize_positive_surprises(subset),
                "all_surprises": summarize_reactions(subset),
                "regimes": summarize_regime_split(subset),
                "events": [_row_to_record(row) for _, row in positive.iterrows()],
                "all_events": [_row_to_record(row) for _, row in reported.iterrows()],
            }
        )

    all_events = [
        _row_to_record(row)
        for _, row in aligned.sort_values("earnings_date", ascending=False).iterrows()
    ]
    price_start = _naive_ts(close.index.min())
    price_end = _naive_ts(close.index.max())

    return {
        "ticker": ticker,
        "market_index": MARKET_INDEX,
        "as_of": _iso_date(as_of),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "price_start": _iso_date(price_start),
        "price_end": _iso_date(price_end),
        "price_sessions": int(len(close.dropna())),
        "earnings_rows_loaded": int(len(earnings)) if earnings is not None else 0,
        "reported_earnings": int(len(aligned.dropna(subset=[SURPRISE_COL, "two_day_return"]))),
        "baseline_median_2day_return": _float(returns.median()) if len(returns) else None,
        "windows": windows,
        "all_reported_events": all_events,
        "methodology": {
            "earnings_source": "yfinance.Ticker.get_earnings_dates()",
            "price_source": "yfinance.Ticker.history(period='max', auto_adjust=True)",
            "two_day_return": "Close_Day3 / Close_Day1 - 1, indexed on Day 2 (earnings session)",
            "positive_surprise": "Surprise(%) > 0 with a reported EPS and a mapped 2-day return",
            "correlation": (
                "Pearson, 5/95 winsorized Pearson, and Spearman between 2-day return and Surprise(%), "
                "using every reported print (beats and misses)."
            ),
            "market_regime": (
                f"Bull/bear markets dated on {MARKET_INDEX} with a 20% peak-to-trough reversal. "
                "Robustness cut: print occurs while the index is below its 200-day moving average."
            ),
        },
    }
