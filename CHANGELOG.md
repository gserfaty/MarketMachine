# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
