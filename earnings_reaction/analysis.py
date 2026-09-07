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


def reported_events(aligned: pd.DataFrame) -> pd.DataFrame:
    if aligned.empty:
        return aligned.copy()
    return aligned.dropna(subset=[SURPRISE_COL, "two_day_return"]).copy()


def winsorize(series: pd.Series, lower: float = 0.05, upper: float = 0.95) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    lo, hi = numeric.quantile([lower, upper])
    return numeric.clip(lo, hi)


def market_regimes(close: pd.Series, threshold: float = 0.20) -> pd.Series:
    """Label each session bull or bear with a 20% peak–trough reversal on an index.

    A bear starts at the peak that precedes a 20% drop and continues until the
    trough that precedes a 20% rally. That is the usual dating of S&P 500
    bull and bear markets (dot-com, GFC, COVID crash, 2022).
    """
    prices = _normalize_close(close)
    if prices.empty:
        return pd.Series(dtype=object, name="regime")

    values = prices.to_numpy(dtype=float)
    n = len(values)
    labels = np.full(n, "bull", dtype=object)
    peak = values[0]
    trough = values[0]
    peak_i = 0
    trough_i = 0
    state = "bull"
    for i, price in enumerate(values):
        if state == "bull":
            if price >= peak:
                peak = price
                peak_i = i
            elif price <= peak * (1.0 - threshold):
                labels[peak_i : i + 1] = "bear"
                state = "bear"
                trough = price
                trough_i = i
        else:
            if price <= trough:
                trough = price
                trough_i = i
            elif price >= trough * (1.0 + threshold):
                labels[trough_i : i + 1] = "bull"
                state = "bull"
                peak = price
                peak_i = i
        labels[i] = state
    return pd.Series(labels, index=prices.index, name="regime")


def below_moving_average(close: pd.Series, window: int = 200) -> pd.Series:
    prices = _normalize_close(close)
    average = prices.rolling(window, min_periods=window).mean()
    return (prices < average).rename("below_ma")


def map_series_asof(dates: pd.Series, values: pd.Series) -> pd.Series:
    """Map event dates onto a daily series, using the latest session on or before."""
    series = values.copy()
    series.index = pd.DatetimeIndex([as_naive_day(idx) for idx in series.index])
    series = series[~series.index.duplicated(keep="last")].sort_index()
    mapped = []
    for value in dates:
        day = as_naive_day(value)
        if pd.isna(day) or series.empty:
            mapped.append(pd.NA)
            continue
        if day in series.index:
            mapped.append(series.loc[day])
            continue
        prior = series.index[series.index <= day]
        mapped.append(series.loc[prior[-1]] if len(prior) else pd.NA)
    return pd.Series(mapped, index=dates.index)


def attach_market_context(aligned: pd.DataFrame, index_close: pd.Series) -> pd.DataFrame:
    """Stamp each earnings print with the S&P regime on Day 2."""
    out = aligned.copy()
    if out.empty:
        out["regime"] = pd.Series(dtype=object)
        out["below_200dma"] = pd.Series(dtype=object)
        return out
    regimes = market_regimes(index_close)
    weak_tape = below_moving_average(index_close, window=200)
    out["regime"] = map_series_asof(out["day2"], regimes)
    out["below_200dma"] = map_series_asof(out["day2"], weak_tape)
    return out


def _side_summary(events: pd.DataFrame) -> dict:
    n = int(len(events))
    if n == 0:
        return {
            "event_count": 0,
            "median_2day_return": None,
            "mean_2day_return": None,
            "positive_return_share": None,
        }
    return {
        "event_count": n,
        "median_2day_return": float(events["two_day_return"].median()),
        "mean_2day_return": float(events["two_day_return"].mean()),
        "positive_return_share": float((events["two_day_return"] > 0).mean()),
    }


def summarize_reactions(events: pd.DataFrame) -> dict:
    """Correlation and median reactions for all reported surprises, not just beats."""
    sample = reported_events(events)
    n = int(len(sample))
    beats = sample.loc[sample[SURPRISE_COL] > 0]
    misses = sample.loc[sample[SURPRISE_COL] < 0]
    surprise = sample[SURPRISE_COL] if n else pd.Series(dtype=float)
    ret = sample["two_day_return"] if n else pd.Series(dtype=float)
    winsor_surprise = winsorize(surprise) if n else surprise
    return {
        "event_count": n,
        "median_2day_return": float(ret.median()) if n else None,
        "mean_2day_return": float(ret.mean()) if n else None,
        "pearson_correlation": pearson_corr(ret, surprise) if n else None,
        "spearman_correlation": spearman_corr(ret, surprise) if n else None,
        "winsorized_pearson_correlation": pearson_corr(ret, winsor_surprise) if n else None,
        "abs_pearson_correlation": pearson_corr(ret.abs(), surprise.abs()) if n else None,
        "abs_spearman_correlation": spearman_corr(ret.abs(), surprise.abs()) if n else None,
        "beats": _side_summary(beats),
        "misses": _side_summary(misses),
        "terciles": surprise_terciles(sample),
    }


def surprise_terciles(events: pd.DataFrame) -> list[dict]:
    sample = reported_events(events)
    if len(sample) < 3:
        return []
    try:
        bins = pd.qcut(sample[SURPRISE_COL], 3, duplicates="drop")
    except ValueError:
        return []
    rows = []
    labels = ["Lowest surprise third", "Middle third", "Highest surprise third"]
    ordered = list(bins.cat.categories)
    for idx, category in enumerate(ordered):
        slice_ = sample.loc[bins == category]
        name = labels[idx] if idx < len(labels) and len(ordered) == 3 else f"Surprise bin {idx + 1}"
        rows.append(
            {
                "label": name,
                "event_count": int(len(slice_)),
                "median_surprise": float(slice_[SURPRISE_COL].median()),
                "median_2day_return": float(slice_["two_day_return"].median()),
                "mean_2day_return": float(slice_["two_day_return"].mean()),
            }
        )
    return rows


def summarize_regime_split(events: pd.DataFrame) -> dict:
    sample = reported_events(events)
    if "regime" not in sample.columns:
        bull = sample.iloc[0:0]
        bear = sample.iloc[0:0]
    else:
        bull = sample.loc[sample["regime"] == "bull"]
        bear = sample.loc[sample["regime"] == "bear"]
    if "below_200dma" in sample.columns:
        weak = sample.loc[sample["below_200dma"] == True]  # noqa: E712
        strong = sample.loc[sample["below_200dma"] == False]  # noqa: E712
    else:
        weak = sample.iloc[0:0]
        strong = sample.iloc[0:0]
    return {
        "definition": (
            "S&P 500 bull/bear markets dated with a 20% peak-to-trough reversal on SPY. "
            "A bear runs from the peak before a 20% drop to the trough before a 20% rally."
        ),
        "bull": summarize_reactions(bull),
        "bear": summarize_reactions(bear),
        "above_200dma": summarize_reactions(strong),
        "below_200dma": summarize_reactions(weak),
    }
