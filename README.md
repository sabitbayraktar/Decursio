# Decursio

Python toolkit for **order-book imbalance** signals: ingest top-of-book quotes (from a **synthetic L2** feed or [Polygon.io](https://polygon.io/)), persist rows in **DuckDB**, and explore activity in a **Plotly Dash** dashboard.

## What you get

- **Ingestion** — Default **synthetic L2** snapshots (no API key), **JSONL replay** from fixtures, or Polygon WebSocket when configured.
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

- `DECURSIO_INGEST_SOURCE` — `auto` (default), `synthetic`, `replay`, or `polygon`
- `DECURSIO_L2_REPLAY_PATH` — `.json` / `.jsonl` snapshot file when source is `replay`
- `POLYGON_API_KEY` — required only for `polygon` (or `auto` when set)
- `DECURSIO_SYNTHETIC_INTERVAL_SEC` — seconds between synthetic ticks (default `0.5`)
- `DECURSIO_SYNTHETIC_DEPTH` — L2 levels per side (default `5`)
- `DECURSIO_SYMBOLS` — comma-separated tickers (default `AAPL`)
- `DUCKDB_PATH` — database file path (default `data/market.duckdb`)

## Run

### Quick demo (recommended for local testing)

**Terminal 1 — synthetic ingest (seeded, no config file required)**

```bash
decursio-demo
```

**Terminal 2 — dashboard**

```bash
decursio-dashboard
```

Open `http://127.0.0.1:8050`. The imbalance chart should update every ~0.5s.

### Replay a fixture file

**Terminal 1**

```bash
export DECURSIO_INGEST_SOURCE=replay
export DECURSIO_L2_REPLAY_PATH=fixtures/demo_aapl.jsonl
export DECURSIO_REPLAY_LOOP=true
decursio-ingest
```

Each line in the JSONL file is one L2 snapshot:

```json
{"symbol": "AAPL", "bids": [{"price": 190.0, "size": 500}], "asks": [{"price": 190.01, "size": 300}]}
```

### Standard ingest

```bash
decursio-ingest
```

Without `POLYGON_API_KEY`, `auto` uses **synthetic L2**. Set `DECURSIO_INGEST_SOURCE=polygon` and `POLYGON_API_KEY` for live Polygon quotes.

## Layout

| Path | Role |
|------|------|
| `src/decursio/ingestion/` | L2 book types, synthetic feed, file replay, Polygon client |
| `fixtures/` | Sample JSONL L2 snapshots for replay testing |
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
