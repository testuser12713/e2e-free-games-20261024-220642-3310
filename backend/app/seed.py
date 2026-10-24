"""Demo seed: ``python -m app.seed`` fills the database from app/fixtures/demo_deals.json."""

from __future__ import annotations

import sys

from app.db import init_db


def main() -> int:
    """Create the schema and load the demo deals (idempotent)."""
    init_db()
    return 0


if __name__ == "__main__":
    sys.exit(main())
