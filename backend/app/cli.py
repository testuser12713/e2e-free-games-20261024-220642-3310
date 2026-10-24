"""Command line interface: ``python -m app.cli refresh`` runs every source once."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from app.db import init_db
from app.runner import RunSummary, run_all


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Free games scraper - command line tools.",
    )
    commands = parser.add_subparsers(dest="command", metavar="COMMAND", required=True)
    commands.add_parser(
        "refresh",
        help="run every source adapter once, synchronously, and store the deals",
    )
    return parser


def print_summary(summary: RunSummary) -> None:
    if not summary.results:
        print("No source results.")
        return
    for result in summary.results:
        if result.ok:
            print(f"{result.name}: ok, {result.deal_count} deals")
        else:
            print(f"{result.name}: FAILED - {result.error}")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "refresh":
        init_db()
        print_summary(run_all())
    return 0


if __name__ == "__main__":
    sys.exit(main())
