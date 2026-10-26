# Architecture

## Module map
- `app.py` - entry point: page config, `st.navigation`, sidebar, metro selection.
- `housing/schemas.py` - Pandera contracts per source and `DataValidationError`.
- `housing/data.py` - downloads Zillow Research CSVs and FRED `fredgraph.csv` (mortgage, months' supply) plus Zillow's own forecast (`load_zillow_forecast`, comparison only); `MARKETMACHINE_DATA_DIR` points it at local files (offline).
- `housing/analysis.py` - growth, rankings and market-profile calculations.
- `housing/track.py` - CLI (`python -m housing.track`) logging each horizon's run to a local MLflow sqlite store, registering `marketmachine-{h}m` with `champion`/`challenger` aliases; `load_champion(h)` is the hook for the API. Never imported by the app.
- `housing/model.py` - feature builder (national macro features merged by date, lagged per release) and `HistGradientBoostingRegressor` forecast with backtest; `calibrate_intervals` (out-of-sample conformal width multiplier, 24m only).
- `housing/finance.py` - mortgage, ARM and equity-projection math (no Streamlit).
- `housing/ui.py` - theme, CSS, sidebar, shared widgets, disclaimer text.
- `housing/shared.py` - cached loaders and helpers used by several pages.
- `housing/pages/` - one script per page: overview, findings (hidden redirect to overview), explorer, profile, forecast, financing, affordability.
  Streamlit runs these files; they are not imported. Each ends with a call to its render function.

## Data flow
download (`data.py`: Zillow CSVs, FRED) -> parse -> validate (`schemas.validate` via `data._parsed`) -> features / analysis (`analysis.py`, `model.py` feature builder)
-> model (`cached_forecast` trains once per data as-of date) -> pages render tables and charts.
Candidate feature sources are evaluated offline with `model.rolling_backtest` before a loader is added (see `docs/RESEARCH.md` results).

Validation also runs live-only freshness and minimum-count checks (off when `MARKETMACHINE_DATA_DIR` is set). A failure raises `DataValidationError`, which `shared.py` turns into `None`, so the UI shows the "Heads up" warning or its degraded mode.

## Caching
All in `housing/shared.py`, so every page shares the same caches:
- `st.cache_data` (ttl 24h) for Zillow, FRED, supply and affordability (`cached_affordability`, `cached_zillow_forecast`) loaders, keyed by the data directory.
- `st.cache_resource` for the trained model, keyed by `as_of_key` (latest data date plus supply flag) plus `horizon`. 12m is shared by all pages; 3m/24m are trained only when picked on the forecast page.

## Navigation
`app.py` registers `st.Page("housing/pages/<name>.py", ...)` entries and runs `st.navigation`. `findings` is registered with `visibility="hidden"` as an alias for old /findings links (6 visible items).
The selected metro lives in session state and the `?metro=` query parameter. `st.session_state["_nav"]`
holds the `st.Page` objects for `ui.nav_button`.

## Tracking and registry
Store: `mlruns.db` (sqlite) and `mlartifacts/` in the repo root (gitignored), or `MLFLOW_TRACKING_URI`. Each run logs params,
metrics, the backtest table and the fitted HGB model (registered as `marketmachine-{h}m`). With `--promote`, the new version
becomes `champion` if blend coverage80 is in 0.70-0.90 and blend MAE <= the horizon's champion MAE + 0.02 pp (or no champion
yet); otherwise it is `challenger`. mlflow lives in `requirements-api.txt`; the Streamlit app never imports it.

## Tests
`pytest` in `tests/`, fully offline: `tests/conftest.py` points `MARKETMACHINE_DATA_DIR` at
`tests/fixtures/` (built by `tests/make_fixtures.py`) and blocks sockets. `tests/test_app.py` uses
`AppTest` and `switch_page` to render each page file. `tests/test_track.py` runs one fixture training against a tmp sqlite MLflow store.
CI: `.github/workflows/tests.yml` runs `python -m pytest -q` on Python 3.13 for PRs to and pushes on `main`; its `pytest` job is a required status check.
`.github/workflows/zillow-snapshot.yml` is the monthly snapshot job (not a test).

## Snapshots and future track record
- The `snapshots` branch holds `zillow_forecast/<BaseDate>.csv`, one file per month.
- A future page lists them and, for each BaseDate b and h in {3,12} with b+h <= the latest ZHVI month, computes realized = ZHVI(b+h)/ZHVI(b) - 1 per metro.
- It reports Zillow's MAE and direction accuracy, and ours from either our own snapshots (to be added) or a point-in-time retrain on ZHVI truncated to b (caveat: revised data).
- First 3m results arrive about Jan 2027; first 12m about Oct 2027.
