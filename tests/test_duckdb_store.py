"""Tests for DuckDB quote storage (including TIMESTAMPTZ reads)."""

from __future__ import annotations

from pathlib import Path

import pytest

from decursio.storage.duckdb_store import DuckDBStore

pytest.importorskip("pytz")


@pytest.fixture
def store(tmp_path: Path) -> DuckDBStore:
    db = DuckDBStore(str(tmp_path / "test.duckdb"))
    db.ensure_schema()
    return db


def test_insert_and_recent_quotes(store: DuckDBStore) -> None:
    store.insert_quote(
        symbol="AAPL",
        bid_price=190.0,
        ask_price=190.01,
        bid_size=500,
        ask_size=300,
        imbalance=0.25,
        raw_json='{"source": "test"}',
    )
    rows = store.recent_quotes(limit=10)
    assert len(rows) == 1
    row = rows[0]
    assert row["symbol"] == "AAPL"
    assert row["bid_price"] == 190.0
    assert row["imbalance"] == 0.25
    assert row["ts"] is not None


def test_imbalance_series_filtered(store: DuckDBStore) -> None:
    store.insert_quote(
        symbol="AAPL",
        bid_price=100.0,
        ask_price=100.01,
        bid_size=400,
        ask_size=100,
        imbalance=0.6,
    )
    store.insert_quote(
        symbol="MSFT",
        bid_price=200.0,
        ask_price=200.01,
        bid_size=100,
        ask_size=400,
        imbalance=-0.6,
    )
    series = store.imbalance_series("AAPL", limit=10)
    assert len(series) == 1
    assert series[0]["imbalance"] == 0.6
    assert series[0]["ts"] is not None


def test_imbalance_series_chronological(store: DuckDBStore) -> None:
    for imb in (0.1, 0.2, 0.3):
        store.insert_quote(
            symbol="AAPL",
            bid_price=100.0,
            ask_price=100.01,
            bid_size=100,
            ask_size=100,
            imbalance=imb,
        )
    series = store.imbalance_series("AAPL", limit=10)
    imbalances = [p["imbalance"] for p in series]
    assert imbalances == sorted(imbalances)
