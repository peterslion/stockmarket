"""Command-line runner for the earnings-reaction analysis."""

from __future__ import annotations

import argparse
import json
import sys

from earnings_reaction.fetch import DEFAULT_TICKER
from earnings_reaction.pipeline import run_analysis


def _pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.2f}%"


def _num(value: float | None, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Median 2-day return after positive earnings surprises."
    )
    parser.add_argument("--ticker", default=DEFAULT_TICKER, help="Yahoo Finance ticker (default: AMZN)")
    parser.add_argument("--json", action="store_true", help="Print the full JSON payload")
    args = parser.parse_args(argv)

    result = run_analysis(args.ticker)
    if args.json:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    print(f"{result['ticker']} earnings-surprise 2-day reaction")
    print(f"Prices {result['price_start']} → {result['price_end']} ({result['price_sessions']} sessions)")
    print(f"Reported earnings rows: {result['reported_earnings']}")
    print(f"Baseline median 2-day return (all sessions): {_pct(result['baseline_median_2day_return'])}")
    print()
    for window in result["windows"]:
        print(f"{window['label']}  (n={window['event_count']})")
        print(f"  median 2-day return: {_pct(window['median_2day_return'])}")
        print(f"  mean 2-day return:   {_pct(window['mean_2day_return'])}")
        print(f"  Pearson corr vs surprise: {_num(window['pearson_correlation'])}")
        print(f"  Spearman corr vs surprise: {_num(window['spearman_correlation'])}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
