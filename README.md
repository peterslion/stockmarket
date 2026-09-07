# Earnings surprise 2-day returns

Compute the **median 2-day percentage change** in a stock after **positive earnings surprises**, plus the **correlation** between that 2-day return and the surprise magnitude.

The default ticker is **AMZN**. The dashboard can load any Yahoo Finance symbol.

## What it measures

For every three consecutive trading days (Day 1, Day 2, Day 3):

```text
2-day return = Close_Day3 / Close_Day1 - 1
```

Day 2 is treated as the earnings announcement session. A print is a positive surprise when Yahoo’s `Surprise(%)` is greater than zero and a reported EPS is present.

The headline window is the last **five years** of reported prints. The app also shows 3-year, 10-year, and full-history cuts.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 43147
```

Open [http://127.0.0.1:43147](http://127.0.0.1:43147).

Print the same numbers in the terminal:

```bash
python3 -m earnings_reaction.cli --ticker AMZN
```

## Tests

```bash
python3 -m pytest -q
```

## Data

- Earnings: `yfinance.Ticker.get_earnings_dates()`
- Prices: `yfinance.Ticker.history(period="max", auto_adjust=True)`

Requires network access to Yahoo Finance. If a request is rate-limited, wait and use **Refresh**.
