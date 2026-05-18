"""Run local demo ingest with synthetic L2 defaults (no API key)."""

from __future__ import annotations

import os
import sys


def main() -> None:
    os.environ.setdefault("DECURSIO_INGEST_SOURCE", "synthetic")
    os.environ.setdefault("DECURSIO_SYMBOLS", "AAPL")
    os.environ.setdefault("DECURSIO_SYNTHETIC_INTERVAL_SEC", "0.5")
    os.environ.setdefault("DECURSIO_SYNTHETIC_DEPTH", "5")
    os.environ.setdefault("DECURSIO_SYNTHETIC_SEED", "42")
    os.environ.setdefault("DUCKDB_PATH", "data/market.duckdb")

    print(
        "Decursio demo ingest (synthetic L2). "
        "In another terminal run: decursio-dashboard",
        file=sys.stderr,
    )
    from decursio.ingestion.runner import main as ingest_main

    ingest_main()


if __name__ == "__main__":
    main()
