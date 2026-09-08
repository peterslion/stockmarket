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


def _dump_reaction(title: str, block: dict, indent: str = "  ") -> None:
    print(f"{indent}{title}  n={block['event_count']}")
    print(f"{indent}  median 2-day return: {_pct(block['median_2day_return'])}")
    print(f"{indent}  Pearson: {_num(block['pearson_correlation'])}  winsorized: {_num(block['winsorized_pearson_correlation'])}  Spearman: {_num(block['spearman_correlation'])}")
    beats = block.get("beats") or {}
    misses = block.get("misses") or {}
    print(f"{indent}  beats n={beats.get('event_count', 0)} median {_pct(beats.get('median_2day_return'))}")
    print(f"{indent}  misses n={misses.get('event_count', 0)} median {_pct(misses.get('median_2day_return'))}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Question 4. [Stock] AMZN 2-day returns around earnings surprises, "
            "including S&P 500 bull/bear splits."
        )
    )
    parser.add_argument("--ticker", default=DEFAULT_TICKER, help="Yahoo Finance ticker (default: AMZN)")
    parser.add_argument("--json", action="store_true", help="Print the full JSON payload")
    args = parser.parse_args(argv)

    result = run_analysis(args.ticker)
    if args.json:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    print(f"Question 4. [Stock] {result['ticker']} 2-day returns around earnings surprises")
    print(f"Prices {result['price_start']} → {result['price_end']} ({result['price_sessions']} sessions)")
    print(f"Reported earnings rows: {result['reported_earnings']}")
    print(f"Market regime index: {result['market_index']}")
    print(f"Baseline median 2-day return (all sessions): {_pct(result['baseline_median_2day_return'])}")
    print()
    for window in result["windows"]:
        print(f"{window['label']}")
        all_s = window["all_surprises"]
        _dump_reaction("All reported prints", all_s, indent="")
        for tercile in all_s.get("terciles") or []:
            print(
                f"  {tercile['label']}: n={tercile['event_count']}  "
                f"median surprise {tercile['median_surprise']:.1f}%  "
                f"median 2-day {_pct(tercile['median_2day_return'])}"
            )
        regimes = window["regimes"]
        print("  S&P 500 regimes (20% peak-to-trough)")
        _dump_reaction("Bull", regimes["bull"], indent="  ")
        _dump_reaction("Bear", regimes["bear"], indent="  ")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
