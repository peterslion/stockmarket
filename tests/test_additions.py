"""Tests for S&P 500 addition-year counts."""

from __future__ import annotations

import pandas as pd

from earnings_reaction.additions import additions_since, peak_year, yearly_additions


def test_additions_since_keeps_2020_onward_and_counts_peak_year():
    constituents = pd.DataFrame(
        {
            "Symbol": ["OLD", "AAPL", "TSLA", "ABNB", "XYZ"],
            "Security": ["Old Co", "Apple", "Tesla", "Airbnb", "New Co"],
            "Date added": ["2015-01-01", "1980-01-01", "2020-12-21", "2023-09-18", "2023-03-01"],
        }
    )
    added = additions_since(constituents, since_year=2020)
    assert list(added["ticker"]) == ["TSLA", "ABNB", "XYZ"]
    yearly = yearly_additions(added)
    assert list(yearly["year"]) == [2020, 2023]
    assert list(yearly["n_added"]) == [1, 2]
    assert peak_year(yearly) == {"year": 2023, "n_added": 2}


def test_peak_year_none_when_empty():
    assert peak_year(pd.DataFrame(columns=["year", "n_added"])) is None
