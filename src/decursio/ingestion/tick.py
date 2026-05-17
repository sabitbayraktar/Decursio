"""Shared quote tick types for ingestion sources."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

QuoteHandler = Callable[["QuoteTick"], Awaitable[None]]


@dataclass(frozen=True)
class QuoteTick:
    """Single NBBO-style quote update (best bid/ask with sizes)."""

    symbol: str
    bid_price: float
    ask_price: float
    bid_size: int
    ask_size: int
    exchange_bid: int | None
    exchange_ask: int | None
    raw: dict[str, Any]
