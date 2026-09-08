# Question 3. [Index] S&P 500 Market Corrections Analysis
import pandas as pd
import yfinance as yf

raw = yf.download("^GSPC", start="1950-01-01", auto_adjust=True, progress=False)
close = raw["Close"]
if isinstance(close, pd.DataFrame):
    close = close.iloc[:, 0]
close = close.dropna().sort_index()

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
    if dd < 5:
        continue
    rows.append({
        "peak_date": peak_date.date(),
        "trough_date": trough_date.date(),
        "recovery_date": recovery_date.date(),
        "drawdown_pct": dd,
        "days_peak_to_trough": (trough_date - peak_date).days,
        "days_peak_to_new_ath": (recovery_date - peak_date).days,
    })

c = pd.DataFrame(rows)
print(c[["drawdown_pct", "days_peak_to_trough", "days_peak_to_new_ath"]].quantile([0.25, 0.50, 0.75]))
print("median drawdown %:", c["drawdown_pct"].median())
