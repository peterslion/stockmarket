# Earnings surprise 2-day returns

Compute the **2-day percentage change** in a stock around earnings, then ask two questions:

1. Does **surprise magnitude** line up with the stock’s 2-day reaction?
2. Does that reaction differ in **S&P 500 bull vs bear markets**?

The default ticker is **AMZN**. The dashboard can load any Yahoo Finance symbol.

## What it measures

For every three consecutive trading days (Day 1, Day 2, Day 3):

```text
2-day return = Close_Day3 / Close_Day1 - 1
```

Day 2 is the earnings announcement session. Correlation uses **every reported print** (beats and misses). `Surprise(%)` comes from Yahoo Finance.

Bull and bear markets are dated on **SPY** with a 20% peak-to-trough reversal: a bear runs from the peak before a 20% drop to the trough before a 20% rally. A second cut flags prints while SPY is below its 200-day moving average.

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

S&P 500 5%+ corrections between all-time highs (Question 3):

```bash
python3 question3_sp500_corrections.py
```

Index year-to-date returns as of 21 August 2026 (Question 2):

```bash
python3 question2_indexes_ytd.py
```

Open [http://127.0.0.1:43147/indexes-ytd](http://127.0.0.1:43147/indexes-ytd) for the ranking table.

S&P 500 constituents added since 2020 (Question 1):

```bash
python3 question1_sp500_additions.py
```

Open [http://127.0.0.1:43147/additions](http://127.0.0.1:43147/additions) for the yearly counts.

Open [http://127.0.0.1:43147/corrections](http://127.0.0.1:43147/corrections) for the same table in the browser.

## Tests

```bash
python3 -m pytest -q
```

## Data

- Earnings: `yfinance.Ticker.get_earnings_dates()`
- Stock and SPY prices: `yfinance.Ticker.history(period="max", auto_adjust=True)`

Requires network access to Yahoo Finance. If a request is rate-limited, wait and use **Refresh**.
