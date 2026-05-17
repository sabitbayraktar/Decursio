"""DuckDB file-backed storage for quote ticks and derived imbalance."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, Iterator

import duckdb


class DuckDBStore:
    def __init__(self, path: str) -> None:
        self._path = path

    @contextmanager
    def _conn(self) -> Iterator[duckdb.DuckDBPyConnection]:
        conn = duckdb.connect(self._path)
        try:
            yield conn
        finally:
            conn.close()

    def ensure_schema(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS quotes (
                    ts TIMESTAMPTZ NOT NULL,
                    symbol VARCHAR NOT NULL,
                    bid_price DOUBLE NOT NULL,
                    ask_price DOUBLE NOT NULL,
                    bid_size BIGINT NOT NULL,
                    ask_size BIGINT NOT NULL,
                    imbalance DOUBLE NOT NULL,
                    raw_json VARCHAR
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_quotes_symbol_ts ON quotes (symbol, ts);"
            )

    def insert_quote(
        self,
        *,
        symbol: str,
        bid_price: float,
        ask_price: float,
        bid_size: int,
        ask_size: int,
        imbalance: float,
        raw_json: str | None = None,
    ) -> None:
        ts = datetime.now(UTC)
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO quotes
                (ts, symbol, bid_price, ask_price, bid_size, ask_size, imbalance, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                [ts, symbol, bid_price, ask_price, bid_size, ask_size, imbalance, raw_json],
            )

    def recent_quotes(self, limit: int = 500) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT ts, symbol, bid_price, ask_price, bid_size, ask_size, imbalance
                FROM quotes
                ORDER BY ts DESC
                LIMIT ?;
                """,
                [limit],
            ).fetchall()
            cols = [
                "ts",
                "symbol",
                "bid_price",
                "ask_price",
                "bid_size",
                "ask_size",
                "imbalance",
            ]
            return [dict(zip(cols, r, strict=True)) for r in rows]

    def imbalance_series(self, symbol: str | None, limit: int = 2000) -> list[dict[str, Any]]:
        with self._conn() as conn:
            if symbol:
                rows = conn.execute(
                    """
                    SELECT ts, imbalance
                    FROM quotes
                    WHERE symbol = ?
                    ORDER BY ts DESC
                    LIMIT ?;
                    """,
                    [symbol.upper(), limit],
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT ts, imbalance
                    FROM quotes
                    ORDER BY ts DESC
                    LIMIT ?;
                    """,
                    [limit],
                ).fetchall()
            # chronological for plotting
            series = [{"ts": r[0], "imbalance": r[1]} for r in reversed(rows)]
            return series
