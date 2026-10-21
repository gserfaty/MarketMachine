# Architecture

## Module map
- `app.py` - entry point: page config, `st.navigation`, sidebar, metro selection.
- `housing/data.py` - downloads Zillow Research CSVs and FRED `fredgraph.csv`; `MARKETMACHINE_DATA_DIR` points it at local files (offline).
- `housing/analysis.py` - growth, rankings and market-profile calculations.
- `housing/model.py` - feature builder and `HistGradientBoostingRegressor` forecast with backtest.
- `housing/finance.py` - mortgage, ARM and equity-projection math (no Streamlit).
- `housing/ui.py` - theme, CSS, sidebar, shared widgets, disclaimer text.
- `housing/shared.py` - cached loaders and helpers used by several pages.
- `housing/pages/` - one script per page: overview, findings, explorer, profile, forecast, financing.
  Streamlit runs these files; they are not imported. Each ends with a call to its render function.

## Data flow
download (`data.py`: Zillow CSVs, FRED) -> features / analysis (`analysis.py`, `model.py` feature builder)
-> model (`cached_forecast` trains once per data as-of date) -> pages render tables and charts.

## Caching
All in `housing/shared.py`, so every page shares the same caches:
- `st.cache_data` (ttl 24h) for Zillow, FRED and supply loaders, keyed by the data directory.
- `st.cache_resource` for the trained model, keyed by `as_of_key` (latest data date plus supply flag) plus `horizon`. 12m is shared by all pages; 3m/24m are trained only when picked on the forecast page.

## Navigation
`app.py` registers `st.Page("housing/pages/<name>.py", ...)` entries and runs `st.navigation`.
The selected metro lives in session state and the `?metro=` query parameter. `st.session_state["_nav"]`
holds the `st.Page` objects for `ui.nav_button`.

## Tests
`pytest` in `tests/`, fully offline: `tests/conftest.py` points `MARKETMACHINE_DATA_DIR` at
`tests/fixtures/` (built by `tests/make_fixtures.py`) and blocks sockets. `tests/test_app.py` uses
`AppTest` and `switch_page` to render each page file.
