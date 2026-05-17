# Decursio

Python toolkit for **order-book imbalance** signals: ingest top-of-book quotes (from a **synthetic L2** feed or [Polygon.io](https://polygon.io/)), persist rows in **DuckDB**, and explore activity in a **Plotly Dash** dashboard.

## What you get

- **Ingestion** — Default **synthetic L2** snapshots (no API key). Optional Polygon WebSocket `Q` (quotes) feed when you set `POLYGON_API_KEY`.
- **Signals** — Top-of-book imbalance: \((\text{bid\_size} - \text{ask\_size}) / (\text{bid\_size} + \text{ask\_size})\) when depth is positive, else neutral.
- **Storage** — DuckDB file with a typed `quotes` table and helpers for inserts and recent reads.
- **Dashboard** — Dash app with a live-updating imbalance time series and a small recent-rows table.

## Prerequisites

- Python 3.11+
- For live Polygon data: API key with **stocks** WebSocket and **Q** channel access.

## Setup

```bash
cd Decursio
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

Copy `.env.example` to `.env` if you want to tune paths or switch to Polygon.

Optional variables (see `.env.example`):

- `DECURSIO_INGEST_SOURCE` — `auto` (default), `synthetic`, or `polygon`
- `POLYGON_API_KEY` — required only for `polygon` (or `auto` when set)
- `DECURSIO_SYNTHETIC_INTERVAL_SEC` — seconds between synthetic ticks (default `0.5`)
- `DECURSIO_SYNTHETIC_DEPTH` — L2 levels per side (default `5`)
- `DECURSIO_SYMBOLS` — comma-separated tickers (default `AAPL`)
- `DUCKDB_PATH` — database file path (default `data/market.duckdb`)

## Run

**Terminal 1 — ingest and persist**

```bash
decursio-ingest
```

Without `POLYGON_API_KEY`, this streams **synthetic L2** into DuckDB. Set `DECURSIO_INGEST_SOURCE=polygon` and `POLYGON_API_KEY` for live Polygon quotes.

**Terminal 2 — dashboard**

```bash
decursio-dashboard
```

Open the URL printed in the log (typically `http://127.0.0.1:8050`).

## Layout

| Path | Role |
|------|------|
| `src/decursio/ingestion/` | Synthetic L2 feed, Polygon WebSocket client, `runner` entrypoint |
| `src/decursio/signals/` | Imbalance and related signal helpers |
| `src/decursio/storage/` | DuckDB schema, inserts, reads |
| `src/decursio/dashboard/` | Dash application |

## Development

```bash
pip install -e ".[dev]"
ruff check src
pytest
```

## License

MIT
