"""Tests for synthetic L2 book generation."""

from decursio.config import Settings, _parse_ingest_source
from decursio.ingestion.l2_book import (
    BookLevel,
    L2Snapshot,
    snapshot_to_quote_tick,
    snapshot_to_raw,
)
from decursio.ingestion.synthetic_l2 import SyntheticL2Client
from decursio.signals.imbalance import top_of_book_imbalance


def test_snapshot_to_quote_tick_top_of_book() -> None:
    snap = L2Snapshot(
        symbol="AAPL",
        bids=(BookLevel(100.0, 500), BookLevel(99.99, 200)),
        asks=(BookLevel(100.01, 300), BookLevel(100.02, 150)),
    )
    tick = snapshot_to_quote_tick(snap, source="synthetic_l2")
    assert tick.bid_price == 100.0
    assert tick.ask_price == 100.01
    assert tick.bid_size == 500
    assert tick.ask_size == 300
    raw = snapshot_to_raw(snap, source="synthetic_l2")
    assert raw["source"] == "synthetic_l2"
    assert len(raw["bids"]) == 2


def test_synthetic_imbalance_oscillates() -> None:
    async def noop(_tick: object) -> None:
        pass

    client = SyntheticL2Client(["AAPL"], on_quote=noop, seed=1, depth=3)
    imbalances = []
    for _ in range(30):
        snap = client.next_snapshot("AAPL")
        tick = snapshot_to_quote_tick(snap, source="synthetic_l2")
        imbalances.append(top_of_book_imbalance(tick.bid_size, tick.ask_size))
    assert max(imbalances) > 0.1
    assert min(imbalances) < -0.1


def test_parse_ingest_source_auto() -> None:
    assert _parse_ingest_source("auto", None) == "synthetic"
    assert _parse_ingest_source("auto", "key") == "polygon"
    assert _parse_ingest_source("synthetic", None) == "synthetic"


def test_settings_defaults_to_synthetic_without_key(monkeypatch) -> None:
    monkeypatch.delenv("POLYGON_API_KEY", raising=False)
    monkeypatch.setenv("DECURSIO_INGEST_SOURCE", "auto")
    settings = Settings.from_env()
    assert settings.ingest_source == "synthetic"
