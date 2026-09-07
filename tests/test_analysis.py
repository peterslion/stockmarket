"""Unit tests for 2-day return math, filtering, and correlation."""

from __future__ import annotations

import pandas as pd
import pytest

from earnings_reaction.analysis import (
    align_earnings_to_returns,
    filter_lookback,
    pearson_corr,
    prepare_earnings,
    summarize_positive_surprises,
    two_day_returns,
)


def test_two_day_returns_uses_close_day3_over_day1():
    index = pd.bdate_range("2024-01-02", periods=5)
    close = pd.Series([100.0, 101.0, 110.0, 90.0, 99.0], index=index)
    result = two_day_returns(close)
    assert list(result.index) == list(index[1:-1])
    assert result.iloc[0] == pytest.approx(110.0 / 100.0 - 1.0)
    assert result.iloc[1] == pytest.approx(90.0 / 101.0 - 1.0)
    assert result.iloc[2] == pytest.approx(99.0 / 110.0 - 1.0)


def test_two_day_returns_empty_when_too_short():
    close = pd.Series([10.0, 11.0], index=pd.bdate_range("2024-01-02", periods=2))
    result = two_day_returns(close)
    assert result.empty


def test_prepare_earnings_drops_unreported_and_duplicates():
    idx = pd.to_datetime(
        ["2024-02-01 16:00:00-05:00", "2024-02-01 16:00:00-05:00", "2024-04-30 16:00:00-04:00"],
        utc=True,
    )
    earnings = pd.DataFrame(
        {
            "EPS Estimate": [0.80, 0.80, 0.83],
            "Reported EPS": [1.00, 1.00, float("nan")],
            "Surprise(%)": [24.38, 24.38, 17.67],
        },
        index=idx,
    )
    prepared = prepare_earnings(earnings)
    assert len(prepared) == 1
    assert prepared.iloc[0]["earnings_date"] == pd.Timestamp("2024-02-01")
    assert prepared.iloc[0]["Surprise(%)"] == pytest.approx(24.38)


def test_align_maps_non_trading_earnings_date_to_next_session():
    close = pd.Series(
        [100.0, 102.0, 105.0],
        index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
    )
    earnings = pd.DataFrame(
        {
            "EPS Estimate": [1.0],
            "Reported EPS": [1.2],
            "Surprise(%)": [20.0],
        },
        index=pd.to_datetime(["2024-01-03"]),
    )
    aligned = align_earnings_to_returns(earnings, close)
    assert aligned.iloc[0]["day2"] == pd.Timestamp("2024-01-03")
    assert aligned.iloc[0]["two_day_return"] == pytest.approx(105.0 / 100.0 - 1.0)


def test_summarize_positive_surprises_median_and_correlation():
    aligned = pd.DataFrame(
        {
            "earnings_date": pd.to_datetime(["2024-01-02", "2024-04-02", "2024-07-02", "2024-10-02"]),
            "day2": pd.to_datetime(["2024-01-02", "2024-04-02", "2024-07-02", "2024-10-02"]),
            "EPS Estimate": [1.0, 1.0, 1.0, 1.0],
            "Reported EPS": [1.1, 0.9, 1.2, 1.3],
            "Surprise(%)": [10.0, -10.0, 20.0, 30.0],
            "two_day_return": [0.02, -0.05, 0.04, 0.06],
        }
    )
    summary = summarize_positive_surprises(aligned)
    assert summary["event_count"] == 3
    assert summary["median_2day_return"] == pytest.approx(0.04)
    assert summary["pearson_correlation"] == pytest.approx(1.0)
    assert summary["spearman_correlation"] == pytest.approx(1.0)
    assert summary["positive_return_share"] == pytest.approx(1.0)


def test_filter_lookback_keeps_recent_events_only():
    events = pd.DataFrame(
        {
            "earnings_date": pd.to_datetime(["2020-01-15", "2024-01-15", "2025-01-15"]),
            "Surprise(%)": [5.0, 5.0, 5.0],
            "two_day_return": [0.01, 0.02, 0.03],
        }
    )
    filtered = filter_lookback(events, years=3, as_of=pd.Timestamp("2026-09-07"))
    assert list(filtered["earnings_date"].dt.strftime("%Y-%m-%d")) == ["2024-01-15", "2025-01-15"]


def test_pearson_undefined_when_constant():
    x = pd.Series([1.0, 1.0, 1.0])
    y = pd.Series([0.1, 0.2, 0.3])
    assert pearson_corr(x, y) is None
