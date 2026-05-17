"""Dash UI: recent imbalance time series and quote table."""

from __future__ import annotations

import logging
from pathlib import Path

import dash
import plotly.graph_objects as go
from dash import Input, Output, dcc, html
from dash.dash_table import DataTable

from decursio.config import Settings
from decursio.storage.duckdb_store import DuckDBStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _build_app(store: DuckDBStore, default_symbol: str | None) -> dash.Dash:
    app = dash.Dash(__name__)
    app.title = "Decursio — imbalance"

    app.layout = html.Div(
        className="container",
        style={"maxWidth": "1100px", "margin": "24px auto", "fontFamily": "system-ui"},
        children=[
            html.H1("Order book imbalance"),
            html.P(
                "Reads persisted quotes from DuckDB. Run `decursio-ingest` in another terminal "
                "(synthetic L2 by default, or Polygon when configured)."
            ),
            html.Label("Symbol filter (optional)"),
            dcc.Input(
                id="symbol-input",
                type="text",
                placeholder="e.g. AAPL (leave empty for all)",
                value=default_symbol or "",
                debounce=True,
                style={"width": "220px", "marginLeft": "8px"},
            ),
            dcc.Graph(id="imbalance-chart", style={"height": "420px"}),
            html.H3("Recent rows"),
            DataTable(
                id="quotes-table",
                page_size=15,
                style_table={"overflowX": "auto"},
                style_cell={"fontSize": "13px", "padding": "6px"},
            ),
            dcc.Interval(id="refresh", interval=2_000, n_intervals=0),
        ],
    )

    @app.callback(
        Output("imbalance-chart", "figure"),
        Output("quotes-table", "data"),
        Output("quotes-table", "columns"),
        Input("refresh", "n_intervals"),
        Input("symbol-input", "value"),
    )
    def refresh(_n: int, symbol_value: str | None) -> tuple[go.Figure, list, list]:
        sym = (symbol_value or "").strip().upper() or None
        series = store.imbalance_series(sym, limit=1500)
        fig = go.Figure()
        if series:
            fig.add_trace(
                go.Scatter(
                    x=[r["ts"] for r in series],
                    y=[r["imbalance"] for r in series],
                    mode="lines",
                    name="imbalance",
                    line=dict(width=1.2),
                )
            )
        fig.update_layout(
            margin=dict(l=40, r=20, t=30, b=40),
            yaxis=dict(range=[-1.05, 1.05], title="imbalance"),
            xaxis=dict(title="time"),
            template="plotly_white",
        )
        rows = store.recent_quotes(limit=200)
        if sym:
            rows = [r for r in rows if r["symbol"] == sym]
        cols = [{"name": c, "id": c} for c in rows[0]] if rows else []
        return fig, rows[:50], cols

    return app


def main() -> None:
    settings = Settings.from_env()

    Path(settings.duckdb_path).parent.mkdir(parents=True, exist_ok=True)
    store = DuckDBStore(settings.duckdb_path)
    store.ensure_schema()

    default_sym = settings.symbols[0] if len(settings.symbols) == 1 else None
    app = _build_app(store, default_sym)
    logger.info("starting Dash on http://%s:%s/", settings.dash_host, settings.dash_port)
    app.run(host=settings.dash_host, port=settings.dash_port, debug=False)


if __name__ == "__main__":
    main()
