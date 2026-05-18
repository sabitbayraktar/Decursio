"""Replay L2 snapshots from JSON or JSONL files."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from decursio.ingestion.l2_book import L2Snapshot, parse_l2_snapshot, snapshot_to_quote_tick
from decursio.ingestion.tick import QuoteHandler, QuoteTick


def load_snapshots_from_path(path: Path) -> list[L2Snapshot]:
    """Load snapshots from a .jsonl file (one object per line) or .json array/file."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"empty snapshot file: {path}")

    if path.suffix.lower() == ".jsonl":
        snapshots: list[L2Snapshot] = []
        for line_no, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON") from exc
            if not isinstance(data, dict):
                raise ValueError(f"{path}:{line_no}: expected a JSON object")
            snapshots.append(parse_l2_snapshot(data))
        if not snapshots:
            raise ValueError(f"no snapshots in {path}")
        return snapshots

    data = json.loads(text)
    if isinstance(data, dict):
        return [parse_l2_snapshot(data)]
    if isinstance(data, list):
        return [parse_l2_snapshot(item) for item in data]
    raise ValueError(f"{path}: expected a JSON object or array")


class L2ReplayClient:
    """Replays pre-recorded L2 snapshots into the quote pipeline."""

    def __init__(
        self,
        snapshots: list[L2Snapshot],
        on_quote: QuoteHandler,
        *,
        symbols: list[str] | None = None,
        interval_sec: float = 0.5,
        loop: bool = True,
    ) -> None:
        if not snapshots:
            raise ValueError("snapshots must not be empty")
        allowed = {s.upper() for s in symbols} if symbols else None
        filtered = [
            s for s in snapshots if allowed is None or s.symbol.upper() in allowed
        ]
        if not filtered:
            label = ", ".join(symbols or [])
            raise ValueError(f"no snapshots match symbols: {label}")
        self._snapshots = filtered
        self._on_quote = on_quote
        self._interval_sec = interval_sec
        self._loop = loop

    async def run_forever(self) -> None:
        while True:
            await self.run_once()
            if not self._loop:
                return

    async def run_once(self) -> None:
        for snapshot in self._snapshots:
            tick: QuoteTick = snapshot_to_quote_tick(snapshot, source="replay")
            await self._on_quote(tick)
            await asyncio.sleep(self._interval_sec)
