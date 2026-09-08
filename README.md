# Market questions

Runnable scripts and a small dashboard for four questions.

## Question 1. [Index] S&P 500 stocks added since 2020

```bash
python3 question1_sp500_additions.py
```

Open [http://127.0.0.1:43147/additions](http://127.0.0.1:43147/additions).

## Question 2. [Macro] Indexes YTD as of 21 August 2026

```bash
python3 question2_indexes_ytd.py
```

Open [http://127.0.0.1:43147/indexes-ytd](http://127.0.0.1:43147/indexes-ytd).

## Question 3. [Index] S&P 500 market corrections

```bash
python3 question3_sp500_corrections.py
```

Open [http://127.0.0.1:43147/corrections](http://127.0.0.1:43147/corrections).

## Question 4. [Stock] AMZN 2-day returns around earnings surprises, including S&P 500 bull/bear splits

```bash
python3 question4_amzn_earnings.py
```

Open [http://127.0.0.1:43147](http://127.0.0.1:43147).

For every three consecutive trading days (Day 1, Day 2, Day 3):

```text
2-day return = Close_Day3 / Close_Day1 - 1
```

Day 2 is the earnings session. Correlation uses every reported print (beats and misses). Bull and bear markets are dated on SPY with a 20% peak-to-trough reversal.

## Run the dashboard

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 43147
```

```bash
python3 -m pytest -q
```

Requires network access to Yahoo Finance and Wikipedia.
