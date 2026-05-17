"""Polygon.io stocks WebSocket client for quote (`Q`) events."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import websockets
from websockets.client import WebSocketClientProtocol

from decursio.ingestion.tick import QuoteHandler, QuoteTick

logger = logging.getLogger(__name__)

# Substrings in Polygon `status` messages that will not clear on reconnect.
_FATAL_STATUS_PHRASES = (
    "doesn't include websocket",
    "does not include websocket",
    "not entitled",
    "not authorized",
    "authentication failed",
    "invalid api key",
)

# `status` field values that indicate auth/plan failure (not transient outages).
_FATAL_STATUS_CODES = frozenset({"auth_failed"})


class PolygonStreamError(Exception):
    """Non-recoverable Polygon WebSocket error (plan, auth, etc.)."""


def _fatal_status_message(item: dict[str, Any]) -> str | None:
    """Return a user-facing reason if this status frame should stop ingestion."""
    if item.get("ev") != "status":
        return None
    status = str(item.get("status", "")).lower()
    message = item.get("message")
    if message is not None:
        text = str(message).lower()
        if any(phrase in text for phrase in _FATAL_STATUS_PHRASES):
            return str(message)
        if status in _FATAL_STATUS_CODES:
            return str(message)
    elif status in _FATAL_STATUS_CODES:
        return f"Polygon WebSocket status: {status}"
    return None


def _parse_quote_message(payload: dict[str, Any]) -> QuoteTick | None:
    if payload.get("ev") != "Q":
        return None
    sym = payload.get("sym")
    if not sym:
        return None
    try:
        bid = float(payload["bp"])
        ask = float(payload["ap"])
        bid_sz = int(payload["bs"])
        ask_sz = int(payload["as"])
    except (KeyError, TypeError, ValueError):
        return None
    bx = payload.get("bx")
    ax = payload.get("ax")
    return QuoteTick(
        symbol=str(sym).upper(),
        bid_price=bid,
        ask_price=ask,
        bid_size=bid_sz,
        ask_size=ask_sz,
        exchange_bid=int(bx) if bx is not None else None,
        exchange_ask=int(ax) if ax is not None else None,
        raw=dict(payload),
    )


class PolygonQuoteClient:
    """Connects to Polygon stocks WebSocket, authenticates, subscribes to `Q.*`."""

    def __init__(
        self,
        api_key: str,
        ws_url: str,
        symbols: list[str],
        on_quote: QuoteHandler,
    ) -> None:
        self._api_key = api_key
        self._ws_url = ws_url
        self._symbols = [s.upper() for s in symbols]
        self._on_quote = on_quote

    def _subscribe_params(self) -> str:
        return ",".join(f"Q.{s}" for s in self._symbols)

    async def _handle_connection(self, ws: WebSocketClientProtocol) -> None:
        await ws.send(json.dumps({"action": "auth", "params": self._api_key}))
        await ws.send(json.dumps({"action": "subscribe", "params": self._subscribe_params()}))

        async for message in ws:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                logger.debug("skip non-json frame: %s", message[:200])
                continue
            if not isinstance(data, list):
                data = [data]
            for item in data:
                if not isinstance(item, dict):
                    continue
                ev = item.get("ev")
                if ev == "status":
                    fatal = _fatal_status_message(item)
                    if fatal is not None:
                        logger.error("polygon fatal status: %s", fatal)
                        raise PolygonStreamError(fatal)
                    logger.info("polygon status: %s", item.get("message", item))
                    continue
                tick = _parse_quote_message(item)
                if tick is not None:
                    await self._on_quote(tick)

    async def run_forever(self) -> None:
        """Maintain a connection with simple exponential backoff on failures."""
        delay = 1.0
        max_delay = 60.0
        while True:
            try:
                async with websockets.connect(
                    self._ws_url,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=5,
                ) as ws:
                    logger.info("connected to %s", self._ws_url)
                    delay = 1.0
                    await self._handle_connection(ws)
            except asyncio.CancelledError:
                raise
            except PolygonStreamError:
                raise
            except Exception:
                logger.exception("websocket error; reconnecting in %.1fs", delay)
                await asyncio.sleep(delay)
                delay = min(max_delay, delay * 2)
