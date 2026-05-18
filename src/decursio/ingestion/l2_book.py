"""L2 order-book snapshot types and conversions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from decursio.ingestion.tick import QuoteTick


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


def _levels_from_list(raw: list[Any], label: str) -> tuple[BookLevel, ...]:
    if not raw:
        raise ValueError(f"{label} must contain at least one level")
    levels: list[BookLevel] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"{label}[{i}] must be an object with price and size")
        try:
            levels.append(
                BookLevel(price=float(item["price"]), size=int(item["size"]))
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"{label}[{i}] needs numeric price and size") from exc
    return tuple(levels)


def parse_l2_snapshot(data: dict[str, Any]) -> L2Snapshot:
    """Parse a JSON object into an L2Snapshot."""
    symbol = data.get("symbol") or data.get("sym")
    if not symbol:
        raise ValueError("snapshot missing symbol")
    bids_raw = data.get("bids")
    asks_raw = data.get("asks")
    if not isinstance(bids_raw, list) or not isinstance(asks_raw, list):
        raise ValueError("snapshot must include bids and asks arrays")
    return L2Snapshot(
        symbol=str(symbol).upper(),
        bids=_levels_from_list(bids_raw, "bids"),
        asks=_levels_from_list(asks_raw, "asks"),
    )


def snapshot_to_raw(snapshot: L2Snapshot, *, source: str = "l2") -> dict[str, Any]:
    return {
        "source": source,
        "symbol": snapshot.symbol,
        "bids": [{"price": lvl.price, "size": lvl.size} for lvl in snapshot.bids],
        "asks": [{"price": lvl.price, "size": lvl.size} for lvl in snapshot.asks],
    }


def snapshot_to_quote_tick(snapshot: L2Snapshot, *, source: str = "l2") -> QuoteTick:
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
        raw=snapshot_to_raw(snapshot, source=source),
    )
