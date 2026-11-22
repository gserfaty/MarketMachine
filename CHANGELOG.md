# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Monthly precomputed forecasts (2026-11-22)
- `python -m housing.precompute OUT_DIR` trains the 3/12/24m forecasts on live data and writes `<h>m.json` (every `ForecastResult` field except the fitted model, plus the `as_of_key`). The new `precompute` workflow runs it monthly (22nd) and publishes the files to the orphan `forecasts` branch.
- The app (`cached_forecast`, 6 h `st.cache_data` fetch) and the API load these first and use them only when their `as_of_key` equals the current one (same data month and `CODE_VERSION`); otherwise, or on any fetch error, they train on demand as before. API `model.source` can now be `precomputed`.
- `model.result_to_json` / `result_from_json` (generic over dataclass fields) replace the hand-written Redis codec, which also fixes `blend_weight` and the backtest not round-tripping through Redis.

### Stale forecast cache after deploy fixed (2026-11-22)
- After PR #7 deployed, the live forecast page raised `AttributeError` on `blend_weight`: Streamlit Cloud reloads code without restarting, so `st.cache_resource` kept a `ForecastResult` built by the old model code.
- `model.as_of_key` now includes `CODE_VERSION`, a hash of `housing/model.py`, so the Streamlit, in-process API and Redis caches all drop results from older model code.
- PR: [#8](https://github.com/gserfaty/MarketMachine/pull/8), 1 review round (approved), 2 commits.

### Learned blend weight (2026-11-22)
- The served `blend` is now `w*model + (1-w)*naive_momentum` with a learned w (`model.fit_blend_weight`, `ForecastResult.blend_weight`) instead of a fixed 50/50. The forecast page caption and README show the weight. `housing.benchmark` now backtests from 2010 so each year's weight has history.
- Method: replace the fixed 50/50 `blend` with `w*model + (1-w)*naive_momentum`, w on a 0-1 grid (step 0.05) minimizing MAE. Variant (a) learns w only; variant (b) also learns an intercept (median residual). Expanding window: for each test year, w is fit only on backtest rows resolved before that year's first origin (w=0.5 with fewer than 2 resolved years), so scores and intervals are out-of-sample (`model.apply_blend_weights`). The served w is fit on all backtest rows. Live data, rolling backtest from 2010, intervals recomputed (24m also calibrated).
- Served w (all rows): 0.95 at 3m, 0.8 at 12m, 0.65 at 24m. Per-year backtest weights, excluding the 0.5 fallback years: 3m 0.9-1.0, 12m 0.75-1.0, 24m 0.2-0.85.
- Results, full period / 2020-2025 holdout (MAE pp, bias pp, rank IC, cov80):

  | h | Predictor | Full MAE | Full bias | Full IC | Full cov80 | Holdout MAE | Holdout bias | Holdout IC | Holdout cov80 |
  |---|---|---|---|---|---|---|---|---|---|
  | 3m | 50/50 blend | 0.926 | -0.10 | 0.606 | 0.80 | 1.128 | -0.01 | 0.596 | 0.80 |
  | 3m | (a) learned w, shipped | 0.869 | -0.14 | 0.669 | 0.81 | 1.042 | -0.10 | 0.673 | 0.81 |
  | 3m | (b) w + intercept | 0.866 | -0.01 | 0.669 | 0.81 | 1.042 | +0.04 | 0.673 | 0.81 |
  | 3m | model only | 0.859 | -0.13 | 0.674 | - | 1.039 | -0.11 | 0.671 | - |
  | 12m | 50/50 blend | 3.422 | -0.79 | 0.478 | 0.78 | 4.198 | -0.41 | 0.491 | 0.77 |
  | 12m | (a) learned w, shipped | 3.326 | -1.10 | 0.492 | 0.80 | 3.924 | -1.21 | 0.528 | 0.81 |
  | 12m | (b) w + intercept | 3.324 | -0.23 | 0.490 | 0.78 | 3.882 | -0.19 | 0.524 | 0.82 |
  | 12m | model only | 3.366 | -1.25 | 0.485 | - | 4.093 | -1.62 | 0.512 | - |
  | 24m | 50/50 blend | 8.401 | -1.17 | 0.414 | 0.72 | 11.482 | +4.36 | 0.435 | 0.64 |
  | 24m | (a) learned w, shipped | 8.392 | -1.41 | 0.422 | 0.71 | 11.299 | +4.06 | 0.464 | 0.62 |
  | 24m | (b) w + intercept | 8.975 | +1.59 | 0.422 | 0.74 | 12.779 | +7.01 | 0.463 | 0.84 |
  | 24m | model only | 8.670 | -1.41 | 0.401 | - | 11.966 | +3.87 | 0.464 | - |

- Pre-set keep bar: 12m MAE at least 0.03 pp lower on both periods, rank IC not worse, |bias| no more than 0.3 pp worse, cov80 in 0.70-0.90, no horizon's MAE worse.
  - (a) passed MAE (every horizon, both periods) and rank IC. It failed |bias| at 12m: -0.79 to -1.10 pp full (+0.31 worse) and -0.41 to -1.21 pp holdout (+0.80 worse). Its 24m holdout cov80 of 0.62 is also below 0.70, but the 50/50 baseline was already 0.64 there.
  - (b) failed 24m MAE (+0.57 pp full, +1.30 pp holdout) and 24m |bias| (+0.42 full, +2.65 holdout), likely because the intercept learned in the 2010s overshoots later years. It was not used.
  - The repo owner chose to ship (a) at all horizons for the lower MAE and better ranking, accepting the more pessimistic bias.
- Zillow head-to-head (`housing.benchmark`, 23 snapshots at 3m, 19 at 12m, ~890 metros), MAE / bias / rank IC: 3m Zillow 1.000 / -0.42 / 0.56, 50/50 blend 0.996 / +0.04 / 0.58, (a, shipped) 0.904 / -0.09 / 0.67, (b) 0.904 / +0.05 / 0.67, model 0.899 / -0.10 / 0.67. 12m Zillow 3.510 / -1.47 / 0.18, 50/50 blend 2.973 / +0.47 / 0.50, (a, shipped) 2.770 / -0.29 / 0.52, (b) 2.822 / +0.74 / 0.51, model 2.953 / -0.72 / 0.49.
- Possible follow-up for the bias: (b) at 3m and 12m only, or a capped intercept. Choosing that now would use the holdout to pick the rule, so it would need a fresh out-of-sample check first.
- PR: [#7](https://github.com/gserfaty/MarketMachine/pull/7), 3 review rounds (changes requested on the docs-only version; approved after converting to the model change), 7 commits.

### Observability: JSON logs, Prometheus metrics, Grafana dashboard (2026-11-22)
- New `api/obs.py`: JSON access logs with request id (`X-Request-ID` honored and echoed), Prometheus metrics at `/metrics` (requests, latency, forecast compute time, cache hits/misses, data as-of gauge).
- `ops/prometheus.yml` and `ops/grafana/marketmachine-dashboard.json`; setup in README "Observability". Adds `prometheus-client` and `python-json-logger` to `requirements-api.txt` only.
- PR: [#6](https://github.com/gserfaty/MarketMachine/pull/6), 2 review rounds (changes requested, then approved), 5 commits.

### Redis caching and rate limiting (2026-11-22)
- API only: optional `REDIS_URL` shares computed forecasts across workers (JSON, 6 h TTL, keyed by the data as-of key) and enables a per-IP fixed-window rate limit (`RATE_LIMIT_PER_MIN`, default 60) returning 429 with `Retry-After`; `/v1/health` and `/v1/ready` are exempt.
- Fails open: no Redis or a Redis error keeps the in-process cache and no limit. Streamlit app and `requirements.txt` unchanged; `redis` added to `requirements-api.txt`.
- PR: [#4](https://github.com/gserfaty/MarketMachine/pull/4), 1 review round (approved), 4 commits.

### Forecast ledger and drift monitoring (2026-11-22)
- Optional Postgres ledger for the API (`DATABASE_URL`, `api/ledger.py`, Alembic migration for table `forecasts`): all metros' predictions recorded once per as-of, horizon and model version; disabled when unset, write errors never fail a request.
- New `GET /v1/monitoring/drift?horizon=`: realized MAE and bias of matured forecasts versus the backtest MAE, and PSI plus mean shift between the latest and previous batch.
- `psycopg[binary]` added to `requirements-api.txt`; `requirements.txt` unchanged.
- PR: [#5](https://github.com/gserfaty/MarketMachine/pull/5), 1 review round (approved), 5 commits.

### Head-to-head with Zillow's forecasts (2026-11-03)
- New `housing/benchmark.py` CLI scores our rolling backtest against Zillow's published metro forecasts per snapshot (MAE, bias, direction, rank IC, snapshots won).
- Recovered 23 Zillow forecast snapshots (BaseDate 2022-07 to 2026-03) from the Wayback Machine and added them to the `snapshots` branch.
- Result, ~890 metros: 12m (18 snapshots) MAE 2.97 vs Zillow 3.56, rank IC 0.49 vs 0.17, won 15/18; 3m (23 snapshots) MAE 1.01 vs 1.00, rank IC 0.58 vs 0.56, won 15/23. Model-only is better at 3m (MAE 0.92).
- Caveat: our side uses today's revised ZHVI; Zillow forecast on real-time data. No model change.
- PR: [#3](https://github.com/gserfaty/MarketMachine/pull/3), 1 review round (approved; minor doc notes applied), 3 commits.

### Loss and hyperparameter tuning rejected (2026-11-02)
- Protocol: configs chosen on test years 2010-2019, confirmed on a 2020-2025 holdout untouched during tuning; live data with mortgage, supply and MSACSR. 19 configs logged to MLflow experiment `marketmachine-tuning-2026-10-30` (nothing registered).
- 12m served blend, holdout MAE / bias / rank IC / cov80: current 4.252 / -0.480 / 0.485 / 0.772.
  - Tuning-period winners (2010-2019 MAE 2.869 vs current 2.895) did not hold up on the holdout: l2=5 4.253 (+0.001 pp), half-life 5y 4.315 (+0.063 pp).
  - Largest holdout gains (picked in hindsight, still under the bar): early stopping 4.236 (-0.016 pp, bias worse at -0.581), target clipped 1%/99% 4.238 (-0.014 pp).
  - absolute_error loss: tuning 2.976 vs 2.895 and holdout 4.310 vs 4.252, worse in both periods.
  - Keep bar was -0.03 pp holdout MAE with |bias| and rank IC not worse; none passed, so the model is unchanged.
- Blend check: model-only beats the 50/50 blend on holdout MAE (4.202) and rank IC (0.507) but has bias -1.78 pp, so the 50/50 blend stays; input for a later learned-stacking step.
- Full-period 12m blend MAE is now 3.404 (was 3.374 on 2026-10-22) with the model settings and features unchanged; attributed to one more month of data and Zillow revisions (the 2026-10-26/30 code changes added optional parameters with unchanged defaults).
- PR: [#2](https://github.com/gserfaty/MarketMachine/pull/2), 2 review rounds (changes requested, then approved), 3 commits.

### Versioned REST API (2026-10-30)
- New `api/` FastAPI app (`uvicorn api.main:app`): `/v1` health, ready, metros, per-metro forecast, forecast summary, affordability, financing estimate.
- Forecasts computed on demand and cached in-process; optional `MARKETMACHINE_WARM=1`; uses the registry champion when present.
- Uniform JSON error schema; data failures return 503.
- `data.load_forecast_inputs` and `model.as_of_key` shared with the app; `train_and_evaluate(final_model=...)`; `track.champion_version`.
- Review fixes: guarded per-key cache locks, generic 503 text (details logged), concurrency test.
- PR: [#1](https://github.com/gserfaty/MarketMachine/pull/1), 2 review rounds (approved, then re-approved after hardening), 6 commits.

### Experiment tracking and model registry (2026-10-26)
- New `housing/track.py` CLI: logs params, metrics and backtest per horizon to a local MLflow sqlite store.
- Registers `marketmachine-{h}m` with `champion`/`challenger` aliases and a MAE/coverage promotion rule; `load_champion(h)` for the API.
- `model.train_and_evaluate` takes `feature_cols` and returns the fitted model; app behaviour unchanged.
- New `requirements-api.txt` (mlflow-skinny); the app and `requirements.txt` do not use mlflow.

### Data contracts with Pandera (2026-10-26)
- New `housing/schemas.py`: one Pandera contract per data source (columns, ranges, month-end/unique dates).
- All loaders go through `data._parsed`, which raises `DataValidationError` on bad data; the UI degrades as before.
- Live downloads also check minimum region counts and freshness.
- Added `pandera>=0.20` to requirements and `tests/test_schemas.py`.

### Design polish and 6-item navigation (2026-10-22)
- Headline deltas use `fmt_pct` ("▲ +4.2%") colored by `ui.color_deltas`; `--positive`/`--negative` are now defined.
- KPI cards go through `ui.kpi` everywhere: equal height, delta and notes inside the card (arrows in text, gray for notes).
- Chart legends get fixed-width entry slots so they cannot overlap.
- History/forecast chart x-axis ends 2 months past the forecast end.
- "(from Market overview)" caption on ML forecast shows only when the metro was picked on Overview (`metro_src`).
- Findings merged into Market overview ("Top markets"); `/findings` is a hidden redirect.
- Sidebar is back to 6 items.

### Zillow forecast benchmark (2026-10-22)
- Added a loader for Zillow's own metro forecast (ZHVF, 1/3/12 months, found by month offset from BaseDate), shown on the ML forecast page at 3m and 12m as a "We vs Zillow" line plus a "Zillow's forecast" table column. No 24m comparison (Zillow has none). It is a comparison only, not a model feature.
- Added `.github/workflows/zillow-snapshot.yml`: monthly (day 20) copy of the Zillow forecast CSV to the `snapshots` branch.
- Real data, 2026-10-22: 12m n=894, same direction 771 (86%), median difference -0.1 points (ours minus Zillow); 3m 660 of 894, -0.4 points.
- No historical accuracy is claimed; that needs the forecasts to come due.

### National months' supply feature (2026-10-22)
- Shipped: FRED `MSACSR` (months' supply of new houses) as `msacsr` and `msacsr_chg12`, lagged 1 month (point in time), merged by date like mortgage. NaN (old model) when the series is down.
- Before -> after (blend; MAE pp / bias pp / rank IC / coverage80 / width80 pp / 2019+ MAE / 2019+ bias):
  3m 0.937 / -0.108 / 0.607 / 0.801 / 3.45 -> 0.932 / -0.109 / 0.604 / 0.798 / 3.40;
  12m 3.602 / -0.954 / 0.473 / 0.777 / 14.01 / 4.198 / -0.692 -> 3.374 / -0.719 / 0.481 / 0.788 / 13.12 / 3.986 / -0.621;
  24m 8.590 / -1.590 / 0.404 / 0.719 / 36.58 / 11.339 / 1.595 -> 8.450 / -1.089 / 0.412 / 0.714 / 34.46 / 11.749 / 1.848.
- Rejected (12m blend MAE vs 3.602): T10Y2Y curve 3.661, UNRATE chg12 3.643, HOUST YoY 3.615, PERMIT YoY 3.601 (flat), real mortgage rate 3.660 and DRSFRMACBS 3.714 all worse or flat. Combos add nothing: MSACSR + PERMIT 3.394, + HOUST 3.396, + DRSFRMACBS 3.548 (all worse than MSACSR alone, extra loaders).
- Lag sensitivity (12m): lag 2 gives 3.366, lag 3 gives 3.488; the gain is not a release-timing artifact. Lag 1 kept.
- Caveat: at 24m the 2019+ MAE is worse (11.339 -> 11.749) and the 80% range is 6% narrower. Series are revised data (no keyless vintages), so there is mild look-ahead.

### Bias correction rejected, 24m range calibration shipped (2026-10-22)
- Shipped: (b) at 24m only (`calibrate_intervals`, `ForecastResult.interval_k`); 3m and 12m untouched. Tested on the real-data quarterly backtest, mortgage on (FRED back), supply on. The 2026-10-21 horizon table below was measured with mortgage off; README now carries the mortgage-on numbers.
- Before (blend; MAE pp / bias pp / rank IC / coverage80 / width80 pp / 2019+ MAE / 2019+ bias):
  3m 0.937 / -0.108 / 0.607 / 0.801 / 3.45 / 1.083 / -0.026; 12m 3.602 / -0.954 / 0.473 / 0.777 / 14.01 / 4.198 / -0.692; 24m 8.590 / -1.590 / 0.404 / 0.647 / 31.66 / 11.339 / 1.595.
- (a) Intercept shift (out-of-sample pooled residual, gap 1+ceil(h/12)), mean / median: bias 3m +0.075 / +0.064, 12m +0.335 / +0.078, 24m +2.63 / +2.03 (MAE 24m 9.91 / 9.57 vs 8.59; 12m 3.74 / 3.65; 3m 0.947 / 0.944). Rank IC unchanged. Rejected: |bias| rises at 24m (1.59 to 2.03 median) and 24m MAE worsens by > 0.02 pp. The 24m shift overshoots because the early-year residuals do not predict later ones.
- (b) Conformal width multiplier on the uncorrected blend. Shipped at 24m: coverage80 0.647 to 0.719, width80 31.66 to 36.58 pp (+16%), MAE/bias/rank IC unchanged. Rejected at 3m (0.801 to 0.814, 0.013 off) and 12m (0.777 to 0.828, overshoots: 0.023 to 0.028 away); widths 3.61 / 16.52 pp. With (a) on, 24m width would grow 92% and coverage still only 0.75.

### Continuous integration (2026-10-22)
- GitHub Actions workflow `tests.yml` runs the offline test suite (`python -m pytest -q`, Python 3.13) on every pull request to `main` and every push to `main`.
- The `pytest` check is required on `main` (not strict); the code-owner review rule is unchanged.

### Data experiments (2026-10-21)
- No model change. New free metro features were tested with the real-data quarterly backtest (same pipeline as `train_and_evaluate`, 2010+, supply on). FRED was in maintenance, so `mortgage=None` for every run (baseline and candidates).
- Keep bar: at 12m, blend MAE must improve by >= 0.02 pp (the reproduction tolerance) or rank IC by >= 0.005, |bias| must not get worse, and 3m/24m must not get worse by more than the same margins.
- 12m blend MAE (pp): baseline 3.787; + sales_yoy 3.792; + inc_yoy 3.793; + pti 3.789; + sales_yoy + pti 3.784; + FHFA gap 3.795; + FHFA 12m growth 3.800.
- 3m / 24m MAE: baseline 0.933 / 9.171; sales + pti 0.933 / 9.144; FHFA gap 0.932 / 9.199.
- Rejected: sales_yoy, inc_yoy, pti (12m MAE worse, IC flat); sales + pti (best combo, but 0.003 MAE gain is noise, 2019+ MAE worse, two loaders; its bias gain of 0.07 is a lead for bias work); FHFA gap / 12m growth (IC +0.004 but MAE and coverage worse, 24m worse on MAE, bias and coverage); Census BPS permits (2024+ CBSA files omit the largest metros, join not clean); BLS LAUS (403 Access Denied with a project User-Agent).

### Affordability page (2026-10-21)
- New Money page: enter income, down payment and other debts; every metro is ranked by estimated monthly payment (`finance.estimate`, PMMS rate, state tax and insurance) against the 30% rule.
- Zillow context columns (payment, income needed, share, 20% down) from three new Zillow affordability files; `cached_affordability` caches them.
- Fallbacks: manual 30-year rate when FRED is down, all metros ranked when the Zillow files are down, forecast column n/a when the forecast fails.

### Forecast horizons (2026-10-21)
- ML forecast page has a 3 / 12 / 24 month selector (default 12). 3m and 24m are trained lazily and cached per horizon; other pages stay on 12m.
- Interval gap = 1 + ceil(h/12) (3 years at 24m, so no leakage); the naive trend baseline is scaled by h/12.
- Real-data quarterly backtest 2010+, mortgage unavailable (FRED was down), supply data on:

| Horizon | Blend MAE (pp) | Bias (pp) | Rank IC | Coverage80 | Interval gap |
|---|---|---|---|---|---|
| 3 months | 0.93 | -0.06 | 0.61 | 0.80 | 2 yrs |
| 12 months | 3.79 | -0.62 | 0.47 | 0.75 | 2 yrs |
| 24 months | 9.17 | -1.78 | 0.39 | 0.63 | 3 yrs |

### Refactor (2026-10-21)
- `housing/pages.py` split into `housing/shared.py` and six file-based pages in `housing/pages/`; no behavior change; tests use `AppTest.switch_page` instead of the private `_page_hash`.

### Renamed
- Project renamed from michiganmen to **MarketMachine** (GitHub repo `gserfaty/MarketMachine`; the old URL redirects). The offline-fixtures env var is now `MARKETMACHINE_DATA_DIR` and the Plotly template is `marketmachine`.

### UI redesign (in progress, branch feature/ui-redesign)
- Phase 1: `JOURNEY.md` — job story, market → metro → money journey, sidebar IA (Market / Metro / Money), metro persistence (session + `?metro=`), and page specs for all 6 pages with answer-first headlines and data-down states.
- Phase 2: `DESIGN.md` locked — "Open House": brand red #c74248 on white (white-on-red 4.88:1), Newsreader headlines over Public Sans body, slate-blue down / green up (never red), airy spacing, all text pairs WCAG AA.
- Phase 3: Streamlit design system in `DESIGN.md ## Components` — theme-first mapping to `.streamlit/config.toml` (fonts, colors, radius, borders), a minimal CSS layer only for what the theme can't do (Roofline, button states, focus rings, picker list), component tokens, and a contrast ledger (all interactive pairs ≥3:1).
- Phase 4: final copy in `JOURNEY.md` — plain-language headlines, jargon swaps (typical miss, ranking skill, range hit rate, combined forecast), cause-and-fix error copy, "Heads up:" for data-down, disclaimers on every forecast/financing page.
- Phase 5: chart and table spec in `DESIGN.md ## Data surfaces` — one Plotly template from tokens, no brand red in data, colorblind-checked series palette, up/down always ▲/▼ + sign (green / slate blue), symmetric diverging map with per-state labels, ≤4 series per chart, dual-axis charts retired, numeric tables via `st.column_config`.
- App implementation: `.streamlit/config.toml` theme from the Components mapping, new `housing/ui.py` (CSS block with Roofline/button/focus/picker rules, headline and KPI helpers, ▲/▼ percent formatter, shared-metro picker synced to `?metro=`, data-down warning with Try again, `michiganmen` Plotly template), `st.navigation` with Market / Metro / Money sections, all six pages rewritten to the JOURNEY.md copy with answer-first headlines, dual-axis charts replaced, numeric `column_config` tables, classed symmetric state map with per-state labels; Market profile is presentation and metro binding only.

### Repository
- Repo is now public. `main` requires a pull request approved by the owner (@gserfaty) via `.github/CODEOWNERS`; see `CONTRIBUTING.md`.

### Step 8
- Added: equity projection on the Financing estimator (home value, remaining balance, equity, net equity if sold; years 1/5/10/30
  table plus a yearly chart) for the selected fixed or ARM (index flat) loan.
- Year 1 uses the served ML blend with its 80% range (historical-trend fallback if the forecast is unavailable). Years 2+ use the
  metro's historical log growth with a sqrt-time 80% range from its 5-year returns (120-month minimum, else United States).
- Selling costs default to ~6% of sale price (editable). Shared `_forecast` helper so pages hit one forecast cache key.
- Verified on live Zillow metros: median-metro 10y value change +5% / +46% / +97% (lo / mid / hi).

### Step 7
- Added: 5/6 and 10/6 SOFR ARMs on the Financing estimator (conventional only) with four constant-index scenarios
  (flat, +2 pp, -1 pp, caps worst case): P&I after first reset, max P&I, total interest, and a payment chart vs the 30y fixed.
- Terms: index = 30-day Average SOFR (new FRED series `SOFR30DAYAVG`); caps 2/1/5 for 5/6 and 5/1/5 for 10/6 (not 2/1/5), 6-month
  resets, per the ARRC 2019 white paper; floor = margin; margin default 2.75; rate rounded to 0.125 (unverified).
- Initial rate is an approximation: adjusted 30y fixed minus 0.50 (5/6) or 0.25 (10/6).

### Step 6
- Added: "Financing estimator" page comparing 30/20/15/10-year fixed loans (rate, APR, P&I, tax, insurance, PMI/MIP, PITI,
  total interest) with an amortization chart, plus an optional DTI check. Math lives in pure `housing/finance.py`.
- Rates: new FRED series `MORTGAGE15US`; 30y and 15y PMMS monthly averages, 20y interpolated and 10y extrapolated linearly.
  Conventional terms over 15y are adjusted by approximate Fannie Mae LLPA (2023-05-01) at 0.25% rate per point; FHA/VA use a rule of thumb.
- APR: rate at which the PV of P&I plus MI equals the loan less lender fees (upfront FHA/VA fees are financed).
- Hardcoded tables with as-of dates: FHFA conforming limit $832,750 (2025-11-25), Tax Foundation property tax (2024 ACS),
  NAIC 2022 insurance, HUD Mortgagee Letter 2023-05 (2023-03-20), VA funding fee (2023-04-07); PMI card is illustrative.

### Step 5
- Added: 80% prediction intervals on the served blend. Method: empirical quantiles (10%/90%) of past blend backtest
  residuals scaled by the metro's 12-month volatility (vol12); year Y uses only years <= Y-2 (no leakage). No extra fits.
- Real-data backtest (2012+): coverage 77.6% overall, 78.7% for 2019+; average width 14.0 pp overall, 16.4 pp for 2019+.
  Point metrics unchanged (blend MAE 3.588, rank IC 0.474). New metrics `coverage80`, `width80`.
- Rejected: quantile HGB (2 extra fits per year); constant-width residual quantiles (73% coverage).

### Step 4
- Added: metro supply features from two Zillow sources (for-sale inventory, share of listings with a price cut):
  `inv_yoy`, `pc`, `pc_chg12`. NaN-tolerant (history starts 2018); folds drop all-NaN columns.
- Before/after, real-data backtest averages: blend MAE 3.631 -> 3.588, blend rank IC 0.469 -> 0.474,
  blend bias -0.94 -> -0.91; 2019+ blend MAE 4.257 -> 4.159, 2019+ rank IC 0.464 -> 0.476.
- Tried and rejected: ZORI price-to-rent and rent growth (hurt MAE); new listings and days to pending (added nothing).
  BLS metro unemployment skipped (download returns 403).
- The model (MAE 3.581) now edges out the blend (3.588); serving stays `blend`.

### Step 3
- Changed: the model fit uses exponential recency sample weights (half-life 3 years, measured from the first
  test origin in the backtest and from as_of in the served fit).
- Before/after, real-data backtest averages: blend MAE 3.66 -> 3.63, blend rank IC 0.468 -> 0.469,
  blend bias -0.94 -> -0.94; model MAE 3.72 -> 3.68, model rank IC 0.478 -> 0.471.
- Tried and rejected: predicting the metro return relative to the US plus a US momentum forecast (blend
  MAE 4.26, bias +0.39). The pessimistic bias is not fixed.

### Step 2
- Added: `blend` predictor (average of model and naive momentum) in the backtest; served-forecast statement on the ML forecast page.
- Changed: `pred_12m` and `national_pred` are now the blend; `ForecastResult.metrics` has a `blend` row.

### Added
- Yearly rolling-origin backtest (expanding window, 2010 onward) with per-year and average scorecards.
- Metrics: bias (mean pred - actual, pp), rank IC (mean per-date Spearman across metros),
  top-decile lift (top-10% predicted metros' mean outcome minus all-metro mean, pp).
- Plain-English interpretation and rank IC chart on the ML forecast page.
- This CHANGELOG.

### Changed
- Replaced the single 24-month holdout. `ForecastResult.metrics` is now the backtest average with
  columns MAE, bias, direction_acc, rank_ic, top_decile_lift, years; per-year scores are in `ForecastResult.backtest`.

### Removed
- `housing.model.time_split`.
