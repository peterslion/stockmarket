"""Yahoo Finance loaders used by the earnings-reaction pipeline."""

from __future__ import annotations

import pandas as pd
import yfinance as yf

DEFAULT_TICKER = "AMZN"
MARKET_INDEX = "SPY"
EARNINGS_LIMIT = 100


def load_earnings(ticker: str = DEFAULT_TICKER, limit: int = EARNINGS_LIMIT) -> pd.DataFrame:
    """Load earnings dates via yfinance Ticker.get_earnings_dates()."""
    frame = yf.Ticker(ticker).get_earnings_dates(limit=limit)
    if frame is None:
        return pd.DataFrame()
    return frame


def load_prices(ticker: str = DEFAULT_TICKER) -> pd.DataFrame:
    """Download the full daily price history for a ticker."""
    history = yf.Ticker(ticker).history(period="max", auto_adjust=True)
    if history is None:
        return pd.DataFrame()
    return history


def load_index(ticker: str = MARKET_INDEX) -> pd.DataFrame:
    """Download the market index used to date bull and bear regimes."""
    return load_prices(ticker)
