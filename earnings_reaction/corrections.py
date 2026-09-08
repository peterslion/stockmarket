"""Question 3. [Index] S&P 500 Market Corrections Analysis."""

from __future__ import annotations

import pandas as pd
import yfinance as yf

INDEX = "^GSPC"
START = "1950-01-01"
MIN_DRAWDOWN_PCT = 5.0


def load_sp500_close(start: str = START) -> pd.Series:
    raw = yf.download(INDEX, start=start, auto_adjust=True, progress=False)
    close = raw["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    return close.dropna().sort_index()


def find_corrections(close: pd.Series, min_drawdown_pct: float = MIN_DRAWDOWN_PCT) -> pd.DataFrame:
    """List 5%+ peak-to-trough corrections between consecutive all-time highs."""
    close = close.dropna().sort_index()
    if close.empty:
        return pd.DataFrame(
            columns=[
                "peak_date",
                "trough_date",
                "recovery_date",
                "drawdown_pct",
                "days_peak_to_trough",
                "days_peak_to_new_ath",
            ]
        )

    prev_max = close.shift(1).cummax()
    is_ath = close > prev_max
    is_ath.iloc[0] = True
    ath = close.index[is_ath]

    rows = []
    for peak_date, recovery_date in zip(ath[:-1], ath[1:]):
        between = close.loc[peak_date:recovery_date].iloc[1:-1]
        if between.empty:
            continue
        peak = float(close.loc[peak_date])
        trough_date = between.idxmin()
        trough = float(between.min())
        dd = (peak - trough) / peak * 100
        if dd < min_drawdown_pct:
            continue
        rows.append(
            {
                "peak_date": pd.Timestamp(peak_date).date(),
                "trough_date": pd.Timestamp(trough_date).date(),
                "recovery_date": pd.Timestamp(recovery_date).date(),
                "drawdown_pct": dd,
                "days_peak_to_trough": int((trough_date - peak_date).days),
                "days_peak_to_new_ath": int((recovery_date - peak_date).days),
            }
        )
    return pd.DataFrame(rows)


def summarize_corrections(corrections: pd.DataFrame) -> pd.DataFrame:
    cols = ["drawdown_pct", "days_peak_to_trough", "days_peak_to_new_ath"]
    if corrections.empty:
        return pd.DataFrame(index=[0.25, 0.50, 0.75], columns=cols)
    return corrections[cols].quantile([0.25, 0.50, 0.75])


def run_corrections() -> dict:
    close = load_sp500_close()
    table = find_corrections(close)
    quantiles = summarize_corrections(table)
    median_dd = float(table["drawdown_pct"].median()) if not table.empty else None
    return {
        "index": INDEX,
        "start": START,
        "min_drawdown_pct": MIN_DRAWDOWN_PCT,
        "sessions": int(len(close)),
        "price_start": str(pd.Timestamp(close.index.min()).date()),
        "price_end": str(pd.Timestamp(close.index.max()).date()),
        "correction_count": int(len(table)),
        "median_drawdown_pct": median_dd,
        "quantiles": {
            str(idx): {col: float(quantiles.loc[idx, col]) for col in quantiles.columns}
            for idx in quantiles.index
        },
        "corrections": [
            {
                "peak_date": str(row.peak_date),
                "trough_date": str(row.trough_date),
                "recovery_date": str(row.recovery_date),
                "drawdown_pct": float(row.drawdown_pct),
                "days_peak_to_trough": int(row.days_peak_to_trough),
                "days_peak_to_new_ath": int(row.days_peak_to_new_ath),
            }
            for row in table.itertuples(index=False)
        ],
    }


if __name__ == "__main__":
    # Question 3. [Index] S&P 500 Market Corrections Analysis
    close = load_sp500_close()
    c = find_corrections(close)
    print(c[["drawdown_pct", "days_peak_to_trough", "days_peak_to_new_ath"]].quantile([0.25, 0.50, 0.75]))
    print("median drawdown %:", c["drawdown_pct"].median())
