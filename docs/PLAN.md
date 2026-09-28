# PLAN — v1: deployable US housing analytics + ML forecast

## Goal & scope
Build the first complete, deployable version from an empty repo (only CLAUDE.md, LICENSE exist):
a Streamlit app with 4 pages (Market overview, Regional explorer, ML forecast, Findings), offline tests,
and Streamlit Community Cloud deploy files. No accounts/API keys. Out of scope: county/ZIP data, metro
lat/lon maps, rentals, user auth.

## Data sources (all verified 2026-09-28, no key needed)
| Name | URL | Notes |
|---|---|---|
| ZHVI metro | `https://files.zillowstatic.com/research/public_csvs/zhvi/Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv` | ~4.5 MB, 895 rows. Cols `RegionID,SizeRank,RegionName,RegionType,StateName`, then monthly date cols `2000-01-31`…(latest `2026-08-31`). Row `RegionType=="country"` is "United States"; metros are `msa`, `StateName` = 2-letter abbr. |
| ZHVI state | `https://files.zillowstatic.com/research/public_csvs/zhvi/State_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv` | Same layout; `RegionName` = full state name. |
| 30-yr mortgage | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US` | Cols `observation_date,MORTGAGE30US`, weekly → resample to month-end mean. |
| Case-Shiller US | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=CSUSHPINSA` | Cols `observation_date,CSUSHPINSA`, monthly (lags ~3 months). |

Caching: `@st.cache_data(ttl=86400, show_spinner=...)` wrappers in `app.py`-side helpers around pure loaders;
trained model via `@st.cache_resource` keyed on the latest data date. FRED values may be `"."` → coerce to NaN.
Failure handling: Zillow down → `st.error("Zillow data unavailable: …")` and `st.stop()` on that page;
FRED down → show warning, macro charts hidden, model runs with macro features as NaN (HGB handles NaN).
Offline mode: if env var `MICHIGANMEN_DATA_DIR` is set, loaders read `<dir>/zhvi_metro.csv`, `zhvi_state.csv`,
`MORTGAGE30US.csv`, `CSUSHPINSA.csv` instead of URLs (used by tests and AppTest).

## Files
- `app.py` — entry point. `st.set_page_config(page_title="michiganmen — US Housing", layout="wide")`, sidebar
  `st.radio` over 4 pages, calls `render_*` functions from `housing/pages.py`. Footer disclaimer on every page.
- `housing/__init__.py` — empty.
- `housing/data.py` — pure I/O + tidy transforms (no streamlit import).
  - `URLS: dict[str, str]`; `STATE_ABBR: dict[str, str]` (50 states + DC full name → abbr).
  - `source(name: str) -> str` returns URL or offline path per `MICHIGANMEN_DATA_DIR`.
  - `load_zhvi(kind: Literal["metro","state"]) -> pd.DataFrame` → long df `[region_id, region, region_type, state, size_rank, date(datetime64 month-end), value]`, NaN values dropped.
  - `load_fred(series_id: str) -> pd.Series` indexed by month-end date, monthly mean.
  - `parse_zhvi(buf) -> pd.DataFrame` and `parse_fred(buf, series_id) -> pd.Series` (what the loaders call; tests use these directly).
  - `to_wide(long_df) -> pd.DataFrame` (index date, columns region).
- `housing/analysis.py` — descriptive stats.
  - `yoy(series: pd.Series) -> pd.Series` (pct change vs 12 months earlier).
  - `appreciation_table(long_df) -> pd.DataFrame` one row per region at latest date: `region, state, size_rank, value, chg_1y, chg_5y, chg_10y` (fractions; NaN if history too short).
  - `national_series(long_df) -> pd.Series` (the `country` row).
- `housing/model.py` — ML (no streamlit import).
  - `build_features(long_df, mortgage: pd.Series | None) -> pd.DataFrame` panel keyed `(region, date)`.
  - `build_target(long_df, horizon=12) -> pd.Series` = `log(P[t+12]/P[t])`.
  - `time_split(df, test_months=24, horizon=12) -> (train, test)` (see Validation).
  - `train_and_evaluate(long_df, mortgage) -> ForecastResult` dataclass: `metrics: pd.DataFrame` (rows model / naive_momentum / zero; cols MAE, direction_acc, n_test), `predictions: pd.DataFrame` (`region, state, value, pred_12m` as simple % = `exp(logpred)-1`, latest date), `national_pred: float`, `as_of: pd.Timestamp`, `feature_importance: pd.Series | None` (skip if costly).
- `housing/pages.py` — streamlit rendering: `render_overview`, `render_explorer`, `render_forecast`, `render_findings`, plus cached wrappers `cached_zhvi(kind)`, `cached_fred(sid)`, `cached_forecast(as_of_key)`. Plotly charts.
- `tests/make_fixtures.py` — deterministic (np.random.default_rng(0)) generator writing the 4 fixture CSVs in the exact source formats: US + 10 metros (SizeRank 0..10, varied trends, one metro with leading NaNs until 2010), 5 states, months 2000-01-31..2026-08-31; FRED weekly mortgage from 2000 and monthly CS index. Commit the generated CSVs in `tests/fixtures/` (each < 200 KB).
- `tests/test_data.py`, `tests/test_analysis.py`, `tests/test_model.py`, `tests/test_app.py` (AppTest with `MICHIGANMEN_DATA_DIR=tests/fixtures`, each page renders with no exception).
- `tests/conftest.py` — sets `MICHIGANMEN_DATA_DIR` fixture path; autouse fixture that makes `urllib`/`requests`/socket connect raise (guard: no network).
- `requirements.txt` — `streamlit>=1.36`, `pandas>=2.0`, `numpy>=1.24`, `scikit-learn>=1.3`, `plotly>=5.18`. `requirements-dev.txt` — `-r requirements.txt`, `pytest>=7`.
- `.gitignore` — `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.streamlit/secrets.toml`, `.DS_Store`.
- `.streamlit/config.toml` — theme only (optional), `[server] headless = true`.
- `README.md` — what it is, data sources, local run (`python -m venv .venv && pip install -r requirements-dev.txt && streamlit run app.py`, `pytest`), deploy steps (push to `gserfaty/michiganmen`, share.streamlit.io → New app → repo/branch `main`/file `app.py`, Python 3.11), model description, disclaimer.

## Pages
1. **Market overview**: KPI row (US typical value, YoY %, 30-yr rate latest + 12m change, Case-Shiller YoY);
   line chart US ZHVI since 2000; line chart of ZHVI YoY % with mortgage rate on secondary axis; Case-Shiller line. Latest data dates shown.
2. **Regional explorer**: toggle Metro/State; filters: state multiselect (metro), min size-rank slider (top N metros by SizeRank, default 200), value range; sort by 1/5/10-yr change or value; `st.dataframe` with % formatting; bar chart top 20 by chosen metric; State mode: plotly choropleth (`locationmode="USA-states"`) colored by chosen metric; select a region → its ZHVI history line vs US.
3. **ML forecast**: metrics table (model vs baselines), text stating whether model beats naive MAE; national call ("Up/Down, +x.x% predicted next 12 mo"); histogram of metro predictions; searchable table of per-metro predictions; short methodology expander.
4. **Findings**: Top 15 gainers (1-yr and 5-yr, metros with SizeRank ≤ 200), Top 15 predicted gainers (+ bottom 10 predicted), Top 15 most valuable metros by typical value; prominent `st.warning` disclaimer: "Forecasts are statistical estimates, not financial advice."

## ML approach
- Panel: one row per (metro incl. US row, month t), origins t ≥ 2003-01 (need 36m history).
- Features at t (only data ≤ t): log returns `r1, r3, r6, r12, r24, r36`; `vol12` = std of monthly log returns over 12m;
  `accel` = r3(t) − r3(t−3); `drawdown36` = log(P/max P over 36m); `rel_us` = log(P) − log(P_US); `us_r12`;
  `log_size_rank` = log1p(SizeRank); macro (if available): `mort` (month mean rate), `mort_chg12` = mort(t) − mort(t−12). Rows with NaN core returns (r12) dropped.
- Target: `y = log(P[t+12]/P[t])`.
- Model: `sklearn.ensemble.HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=50, l2_regularization=1.0, random_state=0)`.
- Validation (time-based, no leakage): let `L` = last origin with a known target (latest date − 12 months).
  Test origins = `(L−23 months … L]`. Train origins ≤ `L − 24 months − 12 months` so every train target window ends before the first test origin. Report on test: MAE (in pct points on simple returns), direction accuracy (sign of pred vs actual), n. Baselines: `naive_momentum` (pred = r12, i.e. last year repeats) and `zero` (no change; direction acc = share of positives).
- Final fit: retrain on all labeled rows; predict at latest date for every metro + US. `national_pred` = US-row prediction; also show median metro prediction.
- Speed: ~900 regions × ~270 origins ≈ 240k rows; HGB fits in a few seconds. Budget: full `train_and_evaluate` < 30 s locally on real data; cache with `st.cache_resource`.

## Acceptance criteria
1. `ls app.py requirements.txt .gitignore README.md housing/data.py housing/analysis.py housing/model.py housing/pages.py tests/fixtures/zhvi_metro.csv` all exist.
2. `grep -E "streamlit|pandas|scikit-learn|plotly" requirements.txt | wc -l` ≥ 4; `.gitignore` contains `.venv/`.
3. `pytest -q` passes with network disabled by the conftest guard (0 failures, ≥ 12 tests).
4. `tests/test_data.py`: `parse_zhvi` on fixture returns required long columns, datetime `date`, a `country` row; `parse_fred` handles `"."` values and resamples weekly to monthly.
5. `tests/test_analysis.py`: `appreciation_table` on a hand-built series (100 → 110 over 12 months) gives `chg_1y == 0.10` (±1e-9) and NaN `chg_10y` for short history; `yoy` correct.
6. `tests/test_model.py`: (a) features at date t are unchanged when all data after t is altered (no leakage); (b) `time_split` max train origin + 12 months < min test origin; (c) `train_and_evaluate` on fixtures returns metrics rows `model`, `naive_momentum`, `zero` with MAE ≥ 0 and 0 ≤ direction_acc ≤ 1, predictions for every metro, finite `national_pred`; (d) works when `mortgage=None`.
7. `tests/test_app.py`: `streamlit.testing.v1.AppTest.from_file("app.py")` with `MICHIGANMEN_DATA_DIR=tests/fixtures` runs each of the 4 pages (set sidebar radio) with `at.exception` empty.
8. Every page contains the not-financial-advice disclaimer text (checked in AppTest: markdown/warning/caption contains "not financial advice").
9. With `MICHIGANMEN_DATA_DIR` pointing to a non-existent dir, the overview page shows an `st.error` rather than an uncaught exception (AppTest).
10. Real-data timing: `python -c "import time;from housing import data,model;t=time.time();r=model.train_and_evaluate(data.load_zhvi('metro'),data.load_fred('MORTGAGE30US'));print(r.metrics);print(time.time()-t)"` completes in < 60 s and prints the 3-row metrics table (network allowed for this check only).
11. `streamlit run app.py --server.headless true --server.port 8599` starts and `curl -s localhost:8599/_stcore/health` returns `ok`.
12. README contains a "Deploy to Streamlit Community Cloud" section naming `app.py` as main file and the repo `gserfaty/michiganmen`.
13. No streamlit import in `housing/data.py`, `housing/analysis.py`, `housing/model.py` (`grep -L streamlit` lists all three).
