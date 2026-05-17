"""Tests for Polygon WebSocket status handling."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import patch

import pytest

from decursio.ingestion.polygon_stream import (
    PolygonQuoteClient,
    PolygonStreamError,
    _fatal_status_message,
)


def test_fatal_status_websocket_plan() -> None:
    item = {
        "ev": "status",
        "message": (
            "Your plan doesn't include websocket access. "
            "Visit https://massive.com/pricing to upgrade."
        ),
    }
    assert _fatal_status_message(item) == item["message"]


def test_fatal_status_auth_failed() -> None:
    item = {"ev": "status", "status": "auth_failed", "message": "Invalid API Key"}
    assert _fatal_status_message(item) == "Invalid API Key"


def test_fatal_status_auth_failed_without_message() -> None:
    item = {"ev": "status", "status": "auth_failed"}
    assert _fatal_status_message(item) == "Polygon WebSocket status: auth_failed"


def test_non_fatal_generic_error_status() -> None:
    item = {
        "ev": "status",
        "status": "error",
        "message": "Service temporarily unavailable",
    }
    assert _fatal_status_message(item) is None


def test_non_fatal_connected() -> None:
    item = {"ev": "status", "message": "Connected Successfully"}
    assert _fatal_status_message(item) is None


def test_non_fatal_non_status_event() -> None:
    assert _fatal_status_message({"ev": "Q", "sym": "AAPL"}) is None


class _MockWebSocket:
    def __init__(self, frames: list[str]) -> None:
        self._frames = list(frames)
        self.sent: list[str] = []

    async def send(self, data: str) -> None:
        self.sent.append(data)

    def __aiter__(self) -> _MockWebSocket:
        return self

    async def __anext__(self) -> str:
        if not self._frames:
            raise StopAsyncIteration
        return self._frames.pop(0)


class _MockConnect:
    def __init__(self, frames: list[str], connect_calls: list[int]) -> None:
        self._frames = frames
        self._connect_calls = connect_calls

    async def __aenter__(self) -> _MockWebSocket:
        self._connect_calls.append(1)
        return _MockWebSocket(self._frames)

    async def __aexit__(self, *args: object) -> None:
        return None


def test_run_forever_no_reconnect_on_fatal_status() -> None:
    connect_calls: list[int] = []
    fatal_frame = json.dumps(
        [
            {
                "ev": "status",
                "message": "Your plan doesn't include websocket access.",
            }
        ]
    )

    def mock_connect(*args: object, **kwargs: object) -> _MockConnect:
        return _MockConnect([fatal_frame], connect_calls)

    async def noop_quote(_tick: object) -> None:
        pass

    client = PolygonQuoteClient(
        api_key="test-key",
        ws_url="wss://example.test/stocks",
        symbols=["AAPL"],
        on_quote=noop_quote,
    )

    async def run() -> None:
        with patch(
            "decursio.ingestion.polygon_stream.websockets.connect",
            mock_connect,
        ):
            with pytest.raises(PolygonStreamError, match="websocket access"):
                await client.run_forever()

    asyncio.run(run())
    assert len(connect_calls) == 1


def test_run_forever_logs_fatal_status(caplog: pytest.LogCaptureFixture) -> None:
    connect_calls: list[int] = []
    fatal_frame = json.dumps(
        [{"ev": "status", "status": "auth_failed", "message": "Invalid API Key"}]
    )

    def mock_connect(*args: object, **kwargs: object) -> _MockConnect:
        return _MockConnect([fatal_frame], connect_calls)

    async def noop_quote(_tick: object) -> None:
        pass

    client = PolygonQuoteClient(
        api_key="test-key",
        ws_url="wss://example.test/stocks",
        symbols=["AAPL"],
        on_quote=noop_quote,
    )

    async def run() -> None:
        with patch(
            "decursio.ingestion.polygon_stream.websockets.connect",
            mock_connect,
        ):
            with pytest.raises(PolygonStreamError):
                await client.run_forever()

    with caplog.at_level("ERROR"):
        asyncio.run(run())

    assert any("polygon fatal status" in r.message for r in caplog.records)
    assert any("Invalid API Key" in r.message for r in caplog.records)
