# Data research: features for turning points + Affordability page

Verified with curl on 2026-10-21 (all times are single-request latency from this Mac). "Keyless" = works with no API key.
Zillow file base: `https://files.zillowstatic.com/research/public_csvs/` (abbrev. `Z/`). Zillow metro files have
RegionID, SizeRank, RegionName ("Detroit, MI"), RegionType (`msa`; row 0 = United States), StateName; wide by month-end date.

## Headline findings
- **FRED is down today**: every `fredgraph.csv?id=...` (even MORTGAGE30US, which the app uses) returns HTTP 200 with a
  "Site Maintenance" HTML page (not CSV). The app must detect non-CSV bodies and fall back (check `data.py` handles
  this; a 200 + HTML will break `read_csv` naive parsing). All FRED candidates below are therefore UNVERIFIED today.
- **BLS bulk**: returned 200 with a contact email in the User-Agent earlier, but on 2026-10-21 a project User-Agent (`MarketMachine/1.0 (+repo URL)`) got **403 Access Denied**; not used.
- **Census API now needs a key** ("Missing Key" HTML even for `for=us:*`), so keyless ACS income is NOT available.
- **Zillow publishes affordability by metro** (payment, income needed, payment-to-income share): best fit for the
  Affordability page, zero join cost.

## Zillow Research (keyless, join on RegionID/RegionName, same file layout as current loaders)
| File (under `Z/`) | Rows (metros) | History | Latest | Latency | Notes |
|---|---|---|---|---|---|
| `new_homeowner_affordability/Metro_new_homeowner_affordability_downpayment_0.20_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv` | 390 | 2012-01 | 2026-09 | 0.6s | share of median income spent on mortgage payment (US 0.22 -> 0.34; SF 0.37 -> 0.60) |
| `new_homeowner_income_needed/Metro_new_homeowner_income_needed_downpayment_0.20_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv` | 390 | 2012-01 | 2026-09 | 0.6s | $ income to afford at 30% rule (US 37k -> 101k) |
| `total_monthly_payment/Metro_total_monthly_payment_downpayment_0.20_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv` | 390 | 2012-01 | 2026-09 | 0.6s | $/month PITI-style payment (US 930 -> 2,523) |
| `sales_count_now/Metro_sales_count_now_uc_sfrcondo_month.csv` | 301 | **2008-02** | 2026-09 | 0.6s | closed sales count; longest Zillow activity series |
| `median_sale_price/Metro_median_sale_price_uc_sfrcondo_sm_month.csv` | 794 | 2008-04 | 2026-08 | 0.8s | |
| `median_sale_to_list/Metro_median_sale_to_list_uc_sfrcondo_sm_month.csv` | 668 | 2018-03 | 2026-08 | ~0.7s | (the `_ratio_` name 404s) |
| `pct_sold_above_list/...` and `pct_sold_below_list/Metro_pct_sold_below_list_uc_sfrcondo_sm_month.csv` | 668 | 2018-03 | 2026-08 | 0.8s | competition gauge |
| `market_temp_index/Metro_market_temp_index_uc_sfrcondo_month.csv` | 928 | 2019-01 | 2026-09 | 0.7s | Zillow "heat" index, bounded 0-100 |
| `new_con_sales_count_raw/...`, `new_con_median_sale_price/...` (`_uc_sfrcondo_month.csv`) | 421 / 214 | 2018-01 | 2026-08 | 0.6s | new-construction share/price; sparse metros |
| `mean_days_to_close/Metro_mean_days_to_close_uc_sfrcondo_sm_month.csv` | 668 | 2018-03 | 2026-08 | 0.6s | |
| `zhvf_growth/Metro_zhvf_growth_uc_sfrcondo_tier_0.33_0.67_month.csv` | 895 | none (BaseDate + 3 horizons to 2027-09) | now | 0.5s | Zillow's own forecast: no history, so not a feature; snapshot it monthly as a benchmark to beat |
Gotchas: affordability/income files are 2012+ only (13y; no 2008 crash), so using them as features shrinks the training
window like inventory did (2018+). Implied income = payment*12/affordability: US 51k (2012) -> 88k (2026), Detroit 50k -> 82k,
SF 74k -> 146k, i.e. plausible and time-varying; Zillow does not document the income source in the file (confirm on its methodology page).
Short-history (2018+) files (sale-to-list, above-list, heat, close time) will likely repeat the inventory problem
(few turning points in-sample). Tried-and-rejected files (ZORI, new_listings, days to pending) still return 200.

## BLS LAUS metro labor market (keyless with email in User-Agent)
- URL: `https://download.bls.gov/pub/time.series/la/la.data.60.Metro` (+ `la.area` for names). 41 MB, 752,777 rows,
  tab-separated `series_id year period value footnote`. Needs `User-Agent: <contact email>`; without it 403.
- Series id: `LAUMT` (NSA, 747,868 rows) / `LASMT` (SA, 4,908 rows, few metros) + 2-digit state FIPS + 5-digit CBSA + `0000000` + measure (`03`
  unemployment rate, `04` unemployed, `05` employed, `06` labor force). Example `LAUMT261982000000003` = Detroit unemployment rate.
- History 1990-01 -> 2026-08/09 (M08 2026 = latest, flagged `P`); monthly; ~1 month lag. Oct 2025 values are "-" (shutdown gap), handle.
- Join: BLS gives CBSA code in id; Zillow metro file has NO CBSA code. Needs a name crosswalk ("Detroit, MI" vs
  "Detroit-Warren-Dearborn, MI Metropolitan Statistical Area": match on first principal city + state), or use the CBSA
  in Realtor.com / FHFA / Census BPS files to bridge. Expect ~95% auto-match; list the rest.
- Also keyless: `POST https://api.bls.gov/publicAPI/v1/timeseries/data/` (verified 200; v1 limits 25 series/query, 10 years, 25 queries/day) - too small for a panel, fine for a spot check.
- Why: unemployment change and employment growth lead price changes at turning points (2012 recovery, 2020 shock). Employment (`05`) YoY is the cleanest feature. 90% of cost is one 41 MB download (filter to measure 03/05, cache).

## Census Building Permits Survey, metro (keyless, bulk text)
- `https://www2.census.gov/econ/bps/CBSA%20(beginning%20Jan%202024)/cbsa2608c.txt` (Aug 2026, monthly `c`; `y` = YTD) and
  `.../Metro%20(ending%202023)/ma2312c.txt`, `ma9912c.txt` (back to 1999 at least; `ma1990a.txt` annual exists). 0.17s each, CSV-ish, columns: survey date, CSA, CBSA code, name, then bldgs/units/value for 1-, 2-, 3-4-, 5+-unit.
- Correction (2026-10-21): the 2024+ CBSA annual files (`cbsa2512y.txt`) leave out the largest metros (no rows for Detroit 19820, New York 35620, Los Angeles 31080, Chicago), so the join is not clean.
- History 1990s -> now; latency ~1 month; two regimes (2023 vs 2024 CBSA delineations - codes shift, Detroit etc.).
- Panel cost: one request per month (~300 for 2000-2026) or use Dec `y` files for 27 annual points. Practical only if
  cached to a committed parquet/CSV refreshed monthly, or limited to `y` files of the latest 5 years.
- Why: units permitted / housing stock = supply pipeline; supply is the standard fundamental behind Sun Belt cooling. Join: CBSA code -> same crosswalk as BLS.

## FHFA House Price Index (keyless; needs a browser User-Agent)
- Metro quarterly: `https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_metro.csv`: 4.2 MB, 84,460 rows, no header
  (name, CBSA, yr, qtr, index, yoy-text with parentheses for negatives, '-' for missing), from 1975 Q1 to **2026 Q2**; 0.6s. Includes MSADs (Detroit-Dearborn-Livonia 19804) so mapping is messier.
- Richer: `https://www.fhfa.gov/hpi/download/monthly/hpi_master.csv` (17 MB, header; hpi_type/flavor/frequency/level/place_name/place_id/yr/period/index_nsa/index_sa).
  Metro rows are quarterly (traditional all-transactions 71k rows; purchase-only 14k; distress-free 2k); monthly series are US/Census-division only.
- Why: independent methodology (repeat sales on conforming loans) and a 1975+ history lets us validate the model on 1990s/2007 turns, but ZHVI-derived targets start 2000, so gain is limited to extra *features* (e.g. FHFA-vs-ZHVI gap = overshoot signal).
- Conforming loan limits: the 2026 xlsx URLs guessed return 404 and `huduser.gov` returns an anti-bot 202 with an empty body, so these are NOT verified. Needed for Affordability only if modelling jumbo cutoffs.

## Realtor.com inventory (keyless S3)
- `https://econdata.s3-us-west-2.amazonaws.com/Reports/Core/RDC_Inventory_Core_Metrics_Metro_History.csv`: 33 MB, 113,775 rows, 925 CBSAs
  (has `cbsa_code`, which solves the crosswalk), monthly 2016-07 -> 2026-09, 2.0s. Columns incl. active/new/pending listing counts with mm & yy
  changes, price_reduced_share, median_days_on_market, median_listing_price, pending_ratio. Overlaps Zillow inventory/price cuts (history 2016+, 1.5y longer) - also the CBSA bridge for BLS/BPS.
- Redfin metro tracker `https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/redfin_metro_market_tracker.tsv000.gz`: 200, 111 MB, Last-Modified 2026-06-02 (stale); not worth it.

## FRED (keyless in principle; DOWN today, so none verified)
Per the page maintenance notice all return HTML. Series that are national and would only add regime context, not cross-section:
HOUST, PERMIT, MSACSR (months' supply), RHVRUSQ156N (homeowner vacancy), UNRATE, DGS10 / T10Y2Y, CUSR0000SAH1 (CPI shelter),
UMCSENT, DRSFRMACBS (delinquency), MEHOINUSA672N (national income, annual). Retry later with
`curl -sL "https://fred.stlouisfed.org/graph/fredgraph.csv?id=HOUST" | head -2` (must start with `observation_date`).
Metro-level FRED panels (e.g. per-CBSA unemployment `...URN`, permits `...BPPRIV`, Case-Shiller metro `ATNHPI...`) would be 1 request
per metro (multi-id `id=A,B,C` per request is supported by fredgraph but untested today): ~400 requests = impractical at runtime; BLS bulk and Census BPS files above cover the same ground in few downloads.

## Ranking
### (a) Model features (expected turning-point value x ease)
1. **BLS LAUS employment YoY and unemployment-rate change** (1990+, monthly, one 41 MB file; needs UA email + CBSA crosswalk). Best leading fundamental, long history.
2. **Zillow sales_count YoY** (2008+; 301 metros, same loader pattern) - volume turns before price at 2012/2020; 2008 start includes the crash and 2012 recovery.
3. **Census BPS permits per 1000 housing units** (monthly 1999+, CBSA join; heavy unless cached) - supply pipeline.
4. **Zillow affordability share / income-needed change** (2012+, 390 metros, trivially joined) - price-to-income stretch; collinear with price & rate, so test only the income-implied part (implied income YoY).
5. **FRED national regime vars** (10y-2y, UNRATE, MSACSR) once FRED is up, as interactions; or FHFA-vs-ZHVI gap (quarterly 1975+).
Low priority: market heat, sale-to-list, above-list (2018-19+ only; same short-window problem that capped inventory features).
Backtest tip: gate each by dropping rows without the feature only if it starts <=2012, else rely on HistGB native NaN handling.
Also add Zillow `zhvf_growth` snapshots to a log as a free benchmark.

### (b) Affordability page
1. Zillow `total_monthly_payment` (390 metros, 2012+).
2. Zillow `new_homeowner_income_needed` (same).
3. Zillow `new_homeowner_affordability` (payment-to-income share; implied income = payment*12/share).
4. Own calc: ZHVI x FRED MORTGAGE30US (rate slider what-if) divided by implied income (already in app data; supports rate scenarios).
5. Census ACS median household income B19013 (needs a free key; api now says "Missing Key") - only as an optional check of the implied income.
Not found keyless: official metro median income (BLS gives wages by QCEW at bls.gov/cew, untested; HUD blocked).

## Results (2026-10-21 experiments)
Pipeline identical to `model.train_and_evaluate` (`build_features`, candidate columns left-merged on region/date, `rolling_backtest` 2010+ quarterly origins, blend row). FRED was down, so `mortgage=None` for baseline and candidates; supply on.
Keep bar: at 12m, blend MAE must improve by >= 0.02 pp (the reproduction tolerance) or rank IC by >= 0.005, |bias| must not get worse, and 3m/24m must not get worse by more than the same margins. A smaller gain is below what the evaluator can reproduce.

Features:
- `sales_yoy`: Zillow metro `sales_count_now` (sfrcondo, monthly, 301 metros, 2008+); 3-month rolling mean, log(s / s.shift(12)), inf to NaN.
- `inc_yoy`: implied income = `afford_payment`*12 / `afford_share`, log YoY. `pti`: the `afford_share` level.
- `fhfa_gap`: FHFA `hpi_at_metro.csv` (needs a browser User-Agent), joined on first city + first state (first MSAD if the MSA is missing): 376 of 894 Zillow metros, 97% of the top 300. Quarterly ffilled to monthly, lagged 2 months. Feature = FHFA 12m log growth minus ZHVI 12m log growth. `fhfa_r12` = FHFA 12m log growth alone.
- Census BPS and BLS LAUS: not tested (see corrections above).

Blend results (MAE and bias in pp):
| Run | 3m MAE / bias / IC / cov80 | 12m MAE / bias / IC / cov80 | 24m MAE / bias / IC / cov80 | 12m 2019+ MAE |
|---|---|---|---|---|
| baseline (current model) | 0.933 / -0.063 / 0.609 / 0.797 | 3.787 / -0.618 / 0.474 / 0.753 | 9.171 / -1.780 / 0.387 / 0.631 | 4.489 |
| + sales_yoy | 0.932 / -0.061 / 0.607 / 0.796 | 3.792 / -0.564 / 0.473 / 0.753 | 9.152 / -1.754 / 0.391 / 0.628 | 4.510 |
| + inc_yoy | 0.934 / -0.062 / 0.608 / 0.797 | 3.793 / -0.604 / 0.473 / 0.752 | 9.170 / -1.716 / 0.389 / 0.630 | 4.501 |
| + pti | 0.933 / -0.059 / 0.608 / 0.797 | 3.789 / -0.557 / 0.474 / 0.752 | 9.137 / -1.568 / 0.391 / 0.625 | 4.514 |
| + sales_yoy + pti | 0.933 / -0.058 / 0.607 / 0.796 | 3.784 / -0.548 / 0.474 / 0.754 | 9.144 / -1.608 / 0.393 / 0.625 | 4.502 |
| + fhfa_gap | 0.932 / -0.063 / 0.610 / 0.796 | 3.795 / -0.600 / 0.478 / 0.744 | 9.199 / -1.834 / 0.393 / 0.614 | 4.534 |
| + fhfa_r12 | 0.932 / -0.062 / 0.609 / 0.797 | 3.800 / -0.583 / 0.478 / 0.744 | 9.243 / -1.780 / 0.392 / 0.610 | 4.548 |

Verdict: none kept; no model change. sales+pti is the best combination (12m MAE -0.003, bias +0.07, IC flat, 2019+ MAE worse), noise-level. FHFA: 12m IC +0.004 but MAE and coverage worse and 24m worse on MAE, bias and coverage.

## 2026-10-22 results: national regime features
12m blend, real data, mortgage + supply on (MAE pp / bias pp / rank IC / coverage80 / width80 pp):
baseline 3.602 / -0.954 / 0.473 / 0.777 / 14.01; curve (T10Y2Y) 3.661 / -0.975 / 0.474 / 0.777 / 14.21; UNRATE chg12 3.643 / -1.017 / 0.475 / 0.779 / 14.32;
**MSACSR lvl + chg12 3.374 / -0.719 / 0.481 / 0.788 / 13.12 (kept)**; MSACSR lvl only 3.402; chg12 only 3.527; HOUST YoY 3.615; PERMIT YoY 3.601; real mortgage 3.660; DRSFRMACBS 3.714; MSACSR + PERMIT 3.394, + HOUST 3.396, + DRSFRMACBS 3.548.
Lag rules (point in time): daily series use the monthly mean with no lag; monthly series lag 1 month; quarterly DRSFRMACBS forward-filled and shifted 5 months from the quarter-start label; CPI YoY lagged 1 month.
Caveat: values are revised data (no keyless vintages), so there is mild look-ahead. Gains are at turning points (2011, 2012, 2022, 2023); small losses in 2019 and 2025.

## 2026-10-22 research
Verified with curl/gh on 2026-10-22.

### 1. FRED is back (keyless, no API key)
`https://fred.stlouisfed.org/graph/fredgraph.csv?id=<ID>` returns CSV again; header `observation_date,<ID>` (new column name, not `DATE`; check `housing/data.py` parser). First retry not needed.
| Series | Freq | Starts | Last obs seen | Note |
|---|---|---|---|---|
| MORTGAGE30US | weekly | 1971-04-02 | current | |
| T10Y2Y | daily | 1976-06-01 | 2026-10-21 (0.32) | blanks on holidays |
| DGS10 / DGS2 | daily | 1962-01-02 / 1976-06-01 | 2026-10-20 | 5.12 / 4.79 |
| UNRATE | monthly | 1948-01 | 2026-09 (4.2) | |
| MSACSR (months' supply) | monthly | 1963-01 | 2026-08 (8.5) | |
| HOUST | monthly | 1959-01 | 2026-09 | thousands, SAAR |
| PERMIT | monthly | 1960-01 | 2026-09 | thousands, SAAR |
| UMCSENT | monthly | 1952-11 | 2026-08 (51.7) | early rows have empty values; dropna |
| RHVRUSQ156N (rental vacancy) | quarterly | 1956-01 | 2026-04 (1.2) | NSA |
| DRSFRMACBS (SF mortgage delinquency, banks) | quarterly | 1991-01 | 2026-04 (1.86) | |
| CPIAUCSL | monthly | 1947-01 | 2026-09 | |
Mirrors: `alfred.stlouisfed.org/graph/fredgraph.csv` returns 404; no keyless mirror needed now. Publication lags differ (quarterly 1-2 quarters, monthly 1-2 months): lag features accordingly in a backtest (no vintages available keyless, so values are revised-data = mild look-ahead).

### 2. Zillow Home Value Forecast (zhvf_growth)
- URL: `https://files.zillowstatic.com/research/public_csvs/zhvf_growth/Metro_zhvf_growth_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv` (HTTP 200). Same product/tier/smoothing as our ZHVI file (`uc_sfrcondo_tier_0.33_0.67_sm_sa_month`): no series mismatch. `..._sfr_...` variant 404.
- Columns: `RegionID,SizeRank,RegionName,RegionType,StateName,BaseDate,<d1>,<d2>,<d3>`. Today: BaseDate 2026-09-30; horizon columns are dates 2026-10-31 (1 month), 2026-12-31 (3 month), 2027-09-30 (12 month). Only three horizons (no 24m); the date headers change each release, so identify horizons by position (cols 7-9) or by month offset from BaseDate.
- Units: percent growth vs the BaseDate ZHVI (e.g. NYC 0.3, 0.7, 2.8 means +2.8% over 12m). Range 12m: -4.2 to +7.4.
- Rows: 895 = 894 `msa` + 1 `country` (United States). 895/895 match our ZHVI file on both RegionID and RegionName (join on RegionID).
- Wayback: CDX lists 51 HTTP-200 captures of the sm_sa URL (with varying `?t=` params), 30 distinct content digests, 2022-09-04 to 2026-05-08, in 23 distinct months (2022-09..10, 2023-03..07, 2024-01..12 sporadic, 2025-02..12, 2026-01/04/05). Caveat: replay is unreliable. Fetching `.../web/<ts>id_/<url>` for the oldest and newest captures both returned a file with BaseDate 2023-05-31 (i.e. the same stale file), and `?t=` URLs returned empty, so snapshot contents were NOT verified as distinct. Note old 2022 captures also exist under the pre-`sm_sa` name `..._tier_0.33_0.67_month.csv` (4 captures, 2022-10 to 2023-05).
- No free historical archive found beyond Wayback; logging from 2026-10.
- Implication: a historical benchmark is possible only as roughly 20 sparse, irregular origins since 2022 (12m outcomes realized only for origins up to ~2025-09), and only if per-capture content checks pass. Cheaper and cleaner: start logging the live file monthly from now (as already suggested above).

### 3. GitHub protection (gserfaty/MarketMachine, main)
Current: `required_pull_request_reviews` = 1 approving review, `require_code_owner_reviews` true, `dismiss_stale_reviews` true, `require_last_push_approval` false; `enforce_admins` false (owner can merge past it); `required_status_checks` ABSENT; linear history, force pushes, deletions, conversation resolution, signatures all off/disabled.
To add a required check without touching reviews, PATCH the sub-resource (PUT on the branch would overwrite everything and requires re-sending all fields):
`gh api -X PATCH repos/gserfaty/MarketMachine/branches/main/protection/required_status_checks -F strict=false -f 'checks[][context]=test'`
Since no required_status_checks exists yet, PATCH will likely 404 (untested, to avoid changing protection); then use the full `PUT .../branches/main/protection` body (must resend `required_pull_request_reviews{required_approving_review_count:1,require_code_owner_reviews:true,dismiss_stale_reviews:true}`, `enforce_admins:false`, `restrictions:null`, `required_status_checks{strict:false,checks:[{context:"test"}]}`). The check name must match the Actions job name, and the workflow must have run once before the check can be selected. Actions minutes are free for public repos.
CI python: `.venv` is Python 3.13.1 (CLAUDE.md says 3.11+); pin the workflow to `python-version: "3.13"` and install `requirements.txt` + pytest. Tests must stay offline.

## 2026-10-26 platform stack
Verified in throwaway venvs (Python 3.13.1, macOS arm64) against PyPI JSON; all wheels `py3-none-any` unless noted; every package requires Python >=3.10 or lower. Ubuntu CI uses manylinux wheels for the same versions (psycopg-binary, sqlalchemy, numpy have cp313 wheels for macOS arm64/x86_64 and manylinux x86_64/aarch64).

| Package | Latest | Notes |
|---|---|---|
| pandera | 0.35.0 | import `pandera.pandas as pa` (the bare `import pandera as pa` pandas API is deprecated); deps: pydantic, typeguard, typing_inspect, packaging |
| mlflow-skinny | 3.17.2 | tracking + sqlite store + model registry verified working (see below) |
| mlflow (full) | 3.17.2 | adds flask, gunicorn, graphene, docker, matplotlib, scipy, pyarrow, cryptography; not needed |
| fastapi / starlette | 0.162.0 / 1.10.0 | needs pydantic v2 |
| uvicorn | 0.54.0 | plain `uvicorn` is enough (no `[standard]`) |
| pydantic | 2.14.1 | v2 only |
| httpx | 0.28.1 | required by starlette TestClient |
| redis (redis-py) | 8.1.0 | |
| fakeredis | 2.40.0 | in-memory Redis for tests (INCR/EXPIRE/TTL supported) |
| slowapi / fastapi-limiter | 0.1.10 / 0.2.0 | slowapi pulls `limits`; fastapi-limiter needs a live Redis (and pyrate-limiter) |
| sqlalchemy | 2.1.6 | requires Python >=3.11; 2.0.x also fine |
| alembic | 1.20.1 | |
| psycopg + psycopg-binary | 3.3.6 | URL scheme `postgresql+psycopg://`; binary has cp313 wheels (macOS + manylinux) |
| prometheus-client | 0.26.0 | zero deps; use `make_asgi_app()` mounted at `/metrics` |
| prometheus-fastapi-instrumentator | 8.1.0 | optional wrapper over prometheus-client |
| python-json-logger | 4.2.0 | stdlib `logging` formatter; structlog 26.1.0 is bigger/more API surface |

### Findings
- **Conflicts:** none. `pip check` clean after installing the whole stack on top of current requirements.txt. Note: unpinned `pandas>=2.0` now resolves to pandas 3.x (3.1.0 fresh, local .venv has 3.0.6) and numpy 2.5; pandera 0.35 imports fine with pandas 3. streamlit now 1.66.1 (local 1.64.0).
- **mlflow-skinny is viable.** Tested: `set_tracking_uri("sqlite:///.../m.db")`, `start_run`, `log_metric`, `mlflow.sklearn.log_model(..., registered_model_name=...)` -> "Created version 1". Gotchas: (1) mlflow 3 defaults sklearn serialization to `skops`, which is not installed; pass `serialization_format="cloudpickle"` (cloudpickle ships with skinny) or add `skops`; (2) skinny pulls sqlalchemy/alembic itself for the sqlite store; (3) no `mlflow ui` (needs full mlflow) - inspect via the sqlite file or pip-install full mlflow ad hoc locally. Use `sqlite:///` plus a local artifact root (default `./mlruns`; gitignore `mlruns/` and `*.db`).
- **Install weight** (on top of requirements.txt, site-packages: base 566 MB): skinny+sqlalchemy+alembic = +113 MB (679 MB total); full mlflow = +224 MB (790 MB). Base install ~1-2 min wheels-only; skinny adds roughly 10-20 s, full roughly 40-60 s (estimate; not timed precisely, pip cache hides it). Recommend skinny.
- **Rate limiting:** smallest = hand-rolled fixed window in ~10 lines: `n = r.incr(key)`; `if n == 1: r.expire(key, 60)`; 429 when `n > limit` (key = `rl:{client_ip}:{minute}`). No extra dependency, testable with fakeredis, fails open if Redis is down. slowapi adds `limits` and decorator plumbing; fastapi-limiter is async-Redis only. Recommend INCR/EXPIRE.
- **Logging:** python-json-logger (one handler line) over structlog.

### Homebrew (arm64, Sequoia bottles; none installed yet, `brew info` only)
| Formula | Version | Start | Port | Data/config |
|---|---|---|---|---|
| postgresql@17 | 17.11 (keg-only) | `brew services start postgresql@17` | 5432 | cluster in `/opt/homebrew/var/postgresql@17` (auto-initdb); `createdb marketmachine`; binaries need `/opt/homebrew/opt/postgresql@17/bin` on PATH (postgresql@18 is 18.6, also available) |
| redis | 8.10.3 | `brew services start redis` | 6379 | `/opt/homebrew/etc/redis.conf`; licence is RSAL/AGPL-tri for 8.x (fine locally) |
| prometheus | 3.15.1 | `brew services start prometheus` | 9090 | flags in `/opt/homebrew/etc/prometheus.args` (config `/opt/homebrew/etc/prometheus.yml`: add scrape job for `localhost:8000/metrics`) |
| grafana | 13.2.4 | `brew services start grafana` | 3000 | `/opt/homebrew/etc/grafana/grafana.ini`, data `/opt/homebrew/var/lib/grafana`; default login admin/admin; add Prometheus datasource `http://localhost:9090`; provisioning dir `/opt/homebrew/etc/grafana/provisioning` or import a dashboard JSON committed to the repo |
Without services: `redis-server` / `postgres -D <dir>` / `prometheus --config.file=...` run in the foreground. App/API: Streamlit 8501, uvicorn 8000, MLflow none (sqlite file).

### Recommended dependency split
- `requirements.txt` (Streamlit Cloud, unchanged): streamlit, pandas, numpy, scikit-learn, plotly. Add `pandera` here only if validation runs inside `housing/data.py` (it does for D: tiny, pure Python) -> add `pandera>=0.20`.
- `requirements-api.txt`: `-r requirements.txt`, mlflow-skinny>=3, fastapi, uvicorn, pydantic>=2, redis, sqlalchemy>=2, alembic, psycopg[binary]>=3, prometheus-client, python-json-logger.
- `requirements-dev.txt`: `-r requirements-api.txt`, pytest, httpx, fakeredis. (CI already installs `requirements.txt` + `requirements-dev.txt`, so the workflow needs no change; today dev does `-r requirements.txt`, change that one line, and update the cache-dependency-path to include requirements-api.txt.)
- Keep imports of mlflow/redis/sqlalchemy/prometheus lazy or confined to new modules (`housing/tracking.py`, `api/`) so the Streamlit app never imports them; tests for DB/Redis use sqlite in-memory and fakeredis (SQLAlchemy models must avoid Postgres-only types, or gate pg tests with a skip marker).
