# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
