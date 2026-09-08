"""Tests for year-to-date index return math."""

from __future__ import annotations

import pandas as pd
import pytest

from earnings_reaction.indexes_ytd import index_ytd_returns


def test_index_ytd_returns_uses_first_and_last_close_through_end():
    close = pd.DataFrame(
        {
            "^GSPC": [100.0, 110.0, 120.0],
            "^HSI": [200.0, 180.0, 190.0],
        },
        index=pd.to_datetime(["2026-01-02", "2026-08-21", "2026-08-24"]),
    )
    indexes = [
        ("United States", "S&P 500", "^GSPC"),
        ("Hong Kong", "HANG SENG INDEX", "^HSI"),
    ]
    table = index_ytd_returns(close, end="2026-08-21", indexes=indexes)
    assert len(table) == 2
    us = table.iloc[0]
    assert us["return"] == pytest.approx(0.10)
    assert str(us["start_date"]) == "2026-01-02"
    assert str(us["end_date"]) == "2026-08-21"
    hk = table.iloc[1]
    assert hk["return"] == pytest.approx(-0.10)


def test_index_ytd_returns_keeps_missing_ticker_row():
    close = pd.DataFrame({"^GSPC": [100.0, 105.0]}, index=pd.to_datetime(["2026-01-02", "2026-08-21"]))
    indexes = [
        ("United States", "S&P 500", "^GSPC"),
        ("China", "Shanghai Composite", "000001.SS"),
    ]
    table = index_ytd_returns(close, end="2026-08-21", indexes=indexes)
    assert pd.isna(table.iloc[1]["return"])
    assert table.iloc[0]["return"] == pytest.approx(0.05)
