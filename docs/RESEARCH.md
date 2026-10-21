# Data research: features for turning points + Affordability page

Verified with curl on 2026-10-21 (all times are single-request latency from this Mac). "Keyless" = works with no API key.
Zillow file base: `https://files.zillowstatic.com/research/public_csvs/` (abbrev. `Z/`). Zillow metro files have
RegionID, SizeRank, RegionName ("Detroit, MI"), RegionType (`msa`; row 0 = United States), StateName; wide by month-end date.

## Headline findings
- **FRED is down today**: every `fredgraph.csv?id=...` (even MORTGAGE30US, which the app uses) returns HTTP 200 with a
  "Site Maintenance" HTML page (not CSV). The app must detect non-CSV bodies and fall back (check `data.py` handles
  this; a 200 + HTML will break `read_csv` naive parsing). All FRED candidates below are therefore UNVERIFIED today.
- **BLS bulk now works**: `download.bls.gov` returns 200 when the User-Agent carries a contact email (403 without).
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
