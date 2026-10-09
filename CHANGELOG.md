# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
