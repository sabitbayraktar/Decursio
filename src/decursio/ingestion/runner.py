"""CLI entrypoint: stream quotes into DuckDB with imbalance."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

from decursio.config import Settings
from decursio.ingestion.polygon_stream import PolygonQuoteClient, PolygonStreamError
from decursio.ingestion.synthetic_l2 import SyntheticL2Client
from decursio.ingestion.tick import QuoteTick
from decursio.signals.imbalance import top_of_book_imbalance
from decursio.storage.duckdb_store import DuckDBStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


def _persist_quote(store: DuckDBStore, tick: QuoteTick) -> None:
    imb = top_of_book_imbalance(tick.bid_size, tick.ask_size)
    store.insert_quote(
        symbol=tick.symbol,
        bid_price=tick.bid_price,
        ask_price=tick.ask_price,
        bid_size=tick.bid_size,
        ask_size=tick.ask_size,
        imbalance=imb,
        raw_json=json.dumps(tick.raw),
    )
    logger.debug("%s imbalance=%.4f", tick.symbol, imb)


async def _on_quote(store: DuckDBStore, tick: QuoteTick) -> None:
    _persist_quote(store, tick)


def main() -> None:
    settings = Settings.from_env()

    if settings.ingest_source == "polygon" and not settings.polygon_api_key:
        print(
            "POLYGON_API_KEY is not set. Set the key or use DECURSIO_INGEST_SOURCE=synthetic.",
            file=sys.stderr,
        )
        sys.exit(1)

    Path(settings.duckdb_path).parent.mkdir(parents=True, exist_ok=True)
    store = DuckDBStore(settings.duckdb_path)
    store.ensure_schema()

    async def handle_quote(tick: QuoteTick) -> None:
        await _on_quote(store, tick)

    symbols_label = ", ".join(settings.symbols)

    if settings.ingest_source == "synthetic":
        logger.info("ingesting symbols (synthetic L2): %s", symbols_label)
        client = SyntheticL2Client(
            symbols=settings.symbols,
            on_quote=handle_quote,
            interval_sec=settings.synthetic_interval_sec,
            depth=settings.synthetic_depth,
            seed=settings.synthetic_seed,
        )
        asyncio.run(client.run_forever())
        return

    logger.info("ingesting symbols (Polygon): %s", symbols_label)
    client = PolygonQuoteClient(
        api_key=settings.polygon_api_key or "",
        ws_url=settings.polygon_ws_url,
        symbols=settings.symbols,
        on_quote=handle_quote,
    )
    try:
        asyncio.run(client.run_forever())
    except PolygonStreamError as exc:
        print(f"Polygon WebSocket error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
