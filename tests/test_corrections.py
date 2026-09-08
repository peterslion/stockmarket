"""Tests for S&P 500 peak-to-trough correction dating."""

from __future__ import annotations

import pandas as pd
import pytest

from earnings_reaction.corrections import find_corrections, summarize_corrections


def test_find_corrections_measures_drawdown_between_aths():
    index = pd.bdate_range("2020-01-01", periods=10)
    # Peak 100, drop to 90 (10%), recover to 101.
    close = pd.Series([100, 99, 95, 90, 92, 96, 98, 99, 100.5, 101], index=index)
    table = find_corrections(close, min_drawdown_pct=5.0)
    assert len(table) == 1
    assert table.iloc[0]["drawdown_pct"] == pytest.approx(10.0)
    assert table.iloc[0]["peak_date"] == index[0].date()
    assert table.iloc[0]["trough_date"] == index[3].date()
    assert table.iloc[0]["recovery_date"] == index[-2].date()


def test_find_corrections_skips_sub_5_percent_dips():
    index = pd.bdate_range("2020-01-01", periods=6)
    close = pd.Series([100, 99, 98, 97, 99, 101], index=index)
    table = find_corrections(close, min_drawdown_pct=5.0)
    assert table.empty


def test_summarize_corrections_quantiles():
    table = pd.DataFrame(
        {
            "drawdown_pct": [6.0, 10.0, 20.0],
            "days_peak_to_trough": [10, 20, 40],
            "days_peak_to_new_ath": [20, 40, 80],
        }
    )
    quantiles = summarize_corrections(table)
    assert quantiles.loc[0.50, "drawdown_pct"] == pytest.approx(10.0)
