"""Synthetic L2 order-book snapshots for local development without Polygon."""

from __future__ import annotations

import asyncio
import math
import random
from dataclasses import dataclass
from typing import Any

from decursio.ingestion.tick import QuoteHandler, QuoteTick

# Default mids when no per-symbol override is configured.
_DEFAULT_MIDS: dict[str, float] = {
    "AAPL": 190.0,
    "MSFT": 420.0,
    "GOOG": 175.0,
    "AMZN": 185.0,
}


@dataclass(frozen=True)
class BookLevel:
    price: float
    size: int


@dataclass(frozen=True)
class L2Snapshot:
    """Multi-level book snapshot; bids/asks are best-first."""

    symbol: str
    bids: tuple[BookLevel, ...]
    asks: tuple[BookLevel, ...]


def snapshot_to_raw(snapshot: L2Snapshot) -> dict[str, Any]:
    return {
        "source": "synthetic_l2",
        "symbol": snapshot.symbol,
        "bids": [{"price": lvl.price, "size": lvl.size} for lvl in snapshot.bids],
        "asks": [{"price": lvl.price, "size": lvl.size} for lvl in snapshot.asks],
    }


def snapshot_to_quote_tick(snapshot: L2Snapshot) -> QuoteTick:
    """Collapse an L2 snapshot to top-of-book for storage and imbalance."""
    best_bid = snapshot.bids[0]
    best_ask = snapshot.asks[0]
    return QuoteTick(
        symbol=snapshot.symbol,
        bid_price=best_bid.price,
        ask_price=best_ask.price,
        bid_size=best_bid.size,
        ask_size=best_ask.size,
        exchange_bid=None,
        exchange_ask=None,
        raw=snapshot_to_raw(snapshot),
    )


class SyntheticL2Client:
    """Emits quote ticks derived from a drifting synthetic L2 book."""

    def __init__(
        self,
        symbols: list[str],
        on_quote: QuoteHandler,
        *,
        interval_sec: float = 0.5,
        depth: int = 5,
        tick_size: float = 0.01,
        spread_ticks: int = 1,
        seed: int | None = None,
        mid_prices: dict[str, float] | None = None,
    ) -> None:
        if depth < 1:
            raise ValueError("depth must be >= 1")
        self._symbols = [s.upper() for s in symbols]
        self._on_quote = on_quote
        self._interval_sec = interval_sec
        self._depth = depth
        self._tick_size = tick_size
        self._spread_ticks = spread_ticks
        self._rng = random.Random(seed)
        self._phase = 0.0
        merged = dict(_DEFAULT_MIDS)
        if mid_prices:
            merged.update({k.upper(): v for k, v in mid_prices.items()})
        self._mid: dict[str, float] = {
            sym: merged.get(sym, 100.0 + self._rng.uniform(-5, 5)) for sym in self._symbols
        }

    def next_snapshot(self, symbol: str) -> L2Snapshot:
        """Advance internal state and return the next book for *symbol*."""
        sym = symbol.upper()
        mid = self._mid[sym]
        mid += self._rng.gauss(0, 0.02)
        self._mid[sym] = mid

        half_spread = self._spread_ticks * self._tick_size
        best_bid = mid - half_spread
        best_ask = mid + half_spread

        # Oscillating depth skew produces a visible imbalance time series.
        skew = math.sin(self._phase) * 0.45 + self._rng.uniform(-0.05, 0.05)
        base = 400
        bid_scale = max(0.15, 1.0 + skew)
        ask_scale = max(0.15, 1.0 - skew)

        bids: list[BookLevel] = []
        asks: list[BookLevel] = []
        for level in range(self._depth):
            decay = 1.0 / (1 + level * 0.35)
            bids.append(
                BookLevel(
                    price=round(best_bid - level * self._tick_size, 2),
                    size=max(1, int(base * bid_scale * decay)),
                )
            )
            asks.append(
                BookLevel(
                    price=round(best_ask + level * self._tick_size, 2),
                    size=max(1, int(base * ask_scale * decay)),
                )
            )

        self._phase += 0.12
        return L2Snapshot(symbol=sym, bids=tuple(bids), asks=tuple(asks))

    async def run_forever(self) -> None:
        while True:
            for symbol in self._symbols:
                snapshot = self.next_snapshot(symbol)
                await self._on_quote(snapshot_to_quote_tick(snapshot))
            await asyncio.sleep(self._interval_sec)
