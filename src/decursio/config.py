"""Runtime configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _split_symbols(raw: str) -> list[str]:
    parts = [p.strip().upper() for p in raw.split(",") if p.strip()]
    return parts or ["AAPL"]


def _parse_ingest_source(raw: str, api_key: str | None) -> str:
    """Resolve ingest source: synthetic, replay, polygon, or auto (default)."""
    value = (raw or "auto").strip().lower()
    if value == "auto":
        return "polygon" if api_key else "synthetic"
    if value in ("synthetic", "replay", "polygon"):
        return value
    raise ValueError(
        f"DECURSIO_INGEST_SOURCE must be synthetic, replay, polygon, or auto; got {raw!r}"
    )


def _parse_bool(raw: str, *, default: bool) -> bool:
    text = raw.strip().lower()
    if not text:
        return default
    if text in ("1", "true", "yes", "on"):
        return True
    if text in ("0", "false", "no", "off"):
        return False
    raise ValueError(f"expected a boolean env value; got {raw!r}")


def _parse_optional_int(raw: str) -> int | None:
    text = raw.strip()
    if not text:
        return None
    return int(text)


@dataclass(frozen=True)
class Settings:
    polygon_api_key: str | None
    polygon_ws_url: str
    ingest_source: str
    symbols: list[str]
    duckdb_path: str
    dash_host: str
    dash_port: int
    synthetic_interval_sec: float
    synthetic_seed: int | None
    synthetic_depth: int
    replay_path: str | None
    replay_interval_sec: float
    replay_loop: bool

    @classmethod
    def from_env(cls) -> Settings:
        key = os.environ.get("POLYGON_API_KEY", "").strip() or None
        symbols = _split_symbols(os.environ.get("DECURSIO_SYMBOLS", "AAPL"))
        ingest_source = _parse_ingest_source(
            os.environ.get("DECURSIO_INGEST_SOURCE", "auto"),
            key,
        )
        return cls(
            polygon_api_key=key,
            polygon_ws_url=os.environ.get(
                "POLYGON_WS_URL", "wss://socket.polygon.io/stocks"
            ).strip(),
            ingest_source=ingest_source,
            symbols=symbols,
            duckdb_path=os.environ.get("DUCKDB_PATH", "data/market.duckdb").strip(),
            dash_host=os.environ.get("DASH_HOST", "127.0.0.1").strip(),
            dash_port=int(os.environ.get("DASH_PORT", "8050")),
            synthetic_interval_sec=float(os.environ.get("DECURSIO_SYNTHETIC_INTERVAL_SEC", "0.5")),
            synthetic_seed=_parse_optional_int(os.environ.get("DECURSIO_SYNTHETIC_SEED", "")),
            synthetic_depth=int(os.environ.get("DECURSIO_SYNTHETIC_DEPTH", "5")),
            replay_path=os.environ.get("DECURSIO_L2_REPLAY_PATH", "").strip() or None,
            replay_interval_sec=float(os.environ.get("DECURSIO_REPLAY_INTERVAL_SEC", "0.5")),
            replay_loop=_parse_bool(os.environ.get("DECURSIO_REPLAY_LOOP", ""), default=True),
        )
