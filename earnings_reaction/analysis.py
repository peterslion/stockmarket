"""Pure calculations for 2-day earnings-reaction returns."""

from __future__ import annotations

import numpy as np
import pandas as pd

SURPRISE_COL = "Surprise(%)"
REPORTED_COL = "Reported EPS"
ESTIMATE_COL = "EPS Estimate"


def _normalize_close(close: pd.Series) -> pd.Series:
    series = close.copy()
    index = pd.to_datetime(series.index)
    if getattr(index, "tz", None) is not None:
        index = index.tz_convert(None)
    series.index = index.normalize()
    series = pd.to_numeric(series, errors="coerce")
    series = series[~series.index.duplicated(keep="last")].sort_index().dropna()
    return series


def two_day_returns(close: pd.Series) -> pd.Series:
    """Return Close[Day3] / Close[Day1] - 1 for every 3 consecutive trading days.

    The result is indexed by Day 2, the middle session. That is the session
    assumed to be the earnings announcement date.
    """
    prices = _normalize_close(close)
    if len(prices) < 3:
        return pd.Series(dtype=float, name="two_day_return")

    values = prices.to_numpy(dtype=float)
    day2_index = prices.index[1:-1]
    returns = (values[2:] / values[:-2]) - 1.0
    return pd.Series(returns, index=day2_index, name="two_day_return")


def as_naive_day(value) -> pd.Timestamp:
    """Calendar date, keeping the original wall-clock timezone."""
    if value is None or pd.isna(value):
        return pd.NaT
    ts = pd.Timestamp(value)
    if ts.tzinfo is not None:
        ts = ts.replace(tzinfo=None)
    return ts.normalize()


def _naive_dates(values) -> pd.Series:
    """Calendar dates in the original timezone, with tz info stripped."""
    return pd.Series([as_naive_day(value) for value in values], dtype="datetime64[ns]")


def prepare_earnings(earnings: pd.DataFrame) -> pd.DataFrame:
    """Normalize Yahoo earnings dates and keep reported surprises only."""
    empty = pd.DataFrame(
        columns=["earnings_date", ESTIMATE_COL, REPORTED_COL, SURPRISE_COL]
    )
    if earnings is None or earnings.empty:
        return empty

    frame = earnings.copy()
    if "Earnings Date" not in frame.columns:
        frame = frame.reset_index()
        if "Earnings Date" not in frame.columns:
            frame = frame.rename(columns={frame.columns[0]: "Earnings Date"})

    out = pd.DataFrame(
        {
            "earnings_date": _naive_dates(frame["Earnings Date"]),
            ESTIMATE_COL: pd.to_numeric(frame.get(ESTIMATE_COL), errors="coerce"),
            REPORTED_COL: pd.to_numeric(frame.get(REPORTED_COL), errors="coerce"),
            SURPRISE_COL: pd.to_numeric(frame.get(SURPRISE_COL), errors="coerce"),
        }
    )
    out = out.dropna(subset=[REPORTED_COL, SURPRISE_COL])
    out = out.drop_duplicates(subset=["earnings_date"], keep="first")
    return out.sort_values("earnings_date").reset_index(drop=True)


def map_to_trading_day(dates: pd.Series, trading_days: pd.DatetimeIndex) -> pd.Series:
    """Map a calendar date to that session, or the next trading day if needed."""
    days = pd.DatetimeIndex([as_naive_day(day) for day in trading_days]).unique().sort_values()
    mapped = []
    for value in dates:
        day = as_naive_day(value)
        if pd.isna(day):
            mapped.append(pd.NaT)
            continue
        if day in days:
            mapped.append(day)
            continue
        later = days[days >= day]
        mapped.append(later[0] if len(later) else pd.NaT)
    return pd.Series(mapped, index=dates.index, name="day2")


def align_earnings_to_returns(
    earnings: pd.DataFrame,
    close: pd.Series,
) -> pd.DataFrame:
    """Attach the Day-2 2-day return to each reported earnings date."""
    prepared = prepare_earnings(earnings)
    returns = two_day_returns(close)
    if prepared.empty or returns.empty:
        prepared["day2"] = pd.Series(dtype="datetime64[ns]")
        prepared["two_day_return"] = pd.Series(dtype=float)
        return prepared

    prepared["day2"] = map_to_trading_day(prepared["earnings_date"], returns.index)
    prepared["two_day_return"] = prepared["day2"].map(returns)
    return prepared


def pearson_corr(x: pd.Series, y: pd.Series) -> float | None:
    """Pearson correlation that returns None when it is undefined."""
    paired = pd.DataFrame({"x": pd.to_numeric(x, errors="coerce"), "y": pd.to_numeric(y, errors="coerce")})
    paired = paired.dropna()
    if len(paired) < 2:
        return None
    xv = paired["x"].to_numpy(dtype=float)
    yv = paired["y"].to_numpy(dtype=float)
    xv = xv - xv.mean()
    yv = yv - yv.mean()
    denom = float(np.sqrt(np.dot(xv, xv) * np.dot(yv, yv)))
    if denom == 0.0:
        return None
    return float(np.dot(xv, yv) / denom)


def spearman_corr(x: pd.Series, y: pd.Series) -> float | None:
    ranks_x = pd.Series(x).rank()
    ranks_y = pd.Series(y).rank()
    return pearson_corr(ranks_x, ranks_y)


def positive_surprise_events(aligned: pd.DataFrame) -> pd.DataFrame:
    if aligned.empty:
        return aligned.copy()
    mask = (aligned[SURPRISE_COL] > 0) & aligned["two_day_return"].notna()
    return aligned.loc[mask].copy()


def filter_lookback(events: pd.DataFrame, years: int | None, as_of: pd.Timestamp | None = None) -> pd.DataFrame:
    if years is None or events.empty:
        return events.copy()
    cutoff_anchor = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp.now(tz=None)
    cutoff = cutoff_anchor.normalize() - pd.DateOffset(years=years)
    return events.loc[events["earnings_date"] >= cutoff].copy()


def summarize_positive_surprises(events: pd.DataFrame) -> dict:
    pos = positive_surprise_events(events)
    n = int(len(pos))
    median = float(pos["two_day_return"].median()) if n else None
    mean = float(pos["two_day_return"].mean()) if n else None
    return {
        "event_count": n,
        "median_2day_return": median,
        "mean_2day_return": mean,
        "pearson_correlation": pearson_corr(pos["two_day_return"], pos[SURPRISE_COL]) if n else None,
        "spearman_correlation": spearman_corr(pos["two_day_return"], pos[SURPRISE_COL]) if n else None,
        "positive_return_share": float((pos["two_day_return"] > 0).mean()) if n else None,
    }
