"""Tests for L2 snapshot file replay."""

from pathlib import Path

import pytest

from decursio.ingestion.l2_book import BookLevel, L2Snapshot, parse_l2_snapshot
from decursio.ingestion.l2_replay import L2ReplayClient, load_snapshots_from_path


def test_parse_l2_snapshot() -> None:
    snap = parse_l2_snapshot(
        {
            "symbol": "AAPL",
            "bids": [{"price": 100.0, "size": 50}],
            "asks": [{"price": 100.01, "size": 40}],
        }
    )
    assert snap.symbol == "AAPL"
    assert snap.bids[0].size == 50


def test_load_demo_fixture() -> None:
    path = Path(__file__).resolve().parents[1] / "fixtures" / "demo_aapl.jsonl"
    snaps = load_snapshots_from_path(path)
    assert len(snaps) == 10
    assert all(s.symbol == "AAPL" for s in snaps)


def test_replay_client_filters_symbols() -> None:
    snaps = [
        L2Snapshot("AAPL", (BookLevel(1.0, 1),), (BookLevel(1.01, 1),)),
        L2Snapshot("MSFT", (BookLevel(2.0, 1),), (BookLevel(2.01, 1),)),
    ]

    async def noop(_tick: object) -> None:
        pass

    client = L2ReplayClient(snaps, on_quote=noop, symbols=["AAPL"], loop=False)
    assert len(client._snapshots) == 1


def test_replay_client_requires_matching_symbol() -> None:
    snaps = [L2Snapshot("MSFT", (BookLevel(1.0, 1),), (BookLevel(1.01, 1),))]

    async def noop(_tick: object) -> None:
        pass

    with pytest.raises(ValueError, match="no snapshots match"):
        L2ReplayClient(snaps, on_quote=noop, symbols=["AAPL"], loop=False)
