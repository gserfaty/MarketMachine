# michiganmen

A Streamlit web app that analyzes the US housing market with historical and current public
data and uses machine learning to forecast market direction, find appreciating areas, and rank
the most valuable markets.

**Forecasts are statistical estimates, not financial advice.**

## Data sources

All free, public, and require no API key:

- [Zillow Home Value Index (ZHVI)](https://www.zillow.com/research/data/) — metro and state, smoothed/seasonally adjusted, all-homes tier.
- Zillow for-sale inventory (metro, from 2018) — count of listings; used as year-over-year change.
- Zillow share of listings with a price cut (metro, from 2018).
- [FRED `MORTGAGE30US`](https://fred.stlouisfed.org/series/MORTGAGE30US) — weekly 30-year fixed mortgage rate.
- [FRED `MORTGAGE15US`](https://fred.stlouisfed.org/series/MORTGAGE15US) — weekly 15-year fixed mortgage rate.
- [FRED `SOFR30DAYAVG`](https://fred.stlouisfed.org/series/SOFR30DAYAVG) — 30-day average SOFR (ARM index). ARM terms:
  [ARRC white paper](https://www.newyorkfed.org/medialibrary/Microsites/arrc/files/2019/ARRC-SOFR-indexed-ARM-Whitepaper.pdf),
  [Freddie Mac SOFR ARMs fact sheet](https://sf.freddiemac.com/docs/pdf/fact-sheet/sofr_arms_fact_sheet.pdf), Fannie Mae Selling Guide B2-1.4-02.
- Hardcoded reference tables (sources and as-of dates in `housing/finance.py` and the page): FHFA conforming limit,
  Tax Foundation property tax rates, NAIC/III 2022 insurance premiums, approximate Fannie Mae LLPA, HUD FHA MIP, VA funding fee.
- [FRED `CSUSHPINSA`](https://fred.stlouisfed.org/series/CSUSHPINSA) — Case-Shiller US National Home Price Index.

Data is downloaded at runtime and cached (`st.cache_data`, 24h TTL). If a source is unavailable,
the app shows a clear error/warning instead of crashing.

## Pages

1. **Market overview** — KPIs (US typical value, YoY change, mortgage rate, Case-Shiller YoY) and trend charts.
2. **Regional explorer** — filter/sort metros or states, bar chart of top movers, state choropleth, per-region history.
3. **ML forecast** — backtest scorecard vs. baselines, served blend forecast (national 12-month call, per-metro predictions).
4. **Findings** — top gainers, top/bottom predicted movers, most valuable metros.
5. **Market Profile** — single-metro profile, comparison, and similar markets.
6. **Financing estimator** — 30/20/15/10-year fixed and 5/6, 10/6 SOFR ARM comparison and equity projection.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
streamlit run app.py
```

Run tests (fully offline, uses fixtures in `tests/fixtures/`):

```bash
pytest
```

## Model & evaluation

A `HistGradientBoostingRegressor` predicts each metro's 12-month log return from point-in-time
price-momentum, volatility, and macro (mortgage rate) features.
Training rows are weighted by recency (weight halves every 3 years
of origin age), so the model adapts faster after regime changes.
Supply features (metro for-sale inventory YoY, share of listings with a price cut and its 12-month change)
start in 2018 and are left NaN where missing; they enter the backtest from 2020/2021 and do not change earlier
years. Zillow revises these values, so history is the current vintage (same caveat as ZHVI).

**Backtest protocol.** Rolling-origin, expanding window, one refit per test year (2010 onward,
metros only). Test = all monthly origins in that year. Train = only rows whose 12-month outcome
window ended no later than the first test origin (the no-leakage rule). Backtest fits use
quarterly origins (Jan/Apr/Jul/Oct) only, about 3.5x faster since consecutive 12-month targets
overlap ~92%. The served forecast is fit on all rows. Final-year (2025) is partial.

**Metrics** (simple returns; averages are equal-weight over years):
- MAE (pp): mean absolute miss. Lower is better.
- bias (pp): mean(pred - actual). Negative = too pessimistic; near 0 is best.
- direction accuracy: share of calls with the right sign. Higher is better; 50% is a coin flip.
- rank IC: per origin date, Spearman correlation across metros of prediction vs outcome, averaged.
  0 = random ordering, 1 = perfect; above ~0.3 is useful.
- top-decile lift (pp): mean outcome of the top 10% predicted metros minus the all-metro mean.
  Higher is better; 0 = no skill.
- coverage80 / width80 (blend only): share of actual outcomes inside the 80% range, and its mean width (pp).

**Prediction intervals.** A forecast like "+3% (-1% to +6%)" means an 80% range: about 8 of 10 past forecasts
landed inside it. The range comes from past blend backtest residuals, scaled by the metro's 12-month volatility,
so volatile metros get wider ranges; for each year only earlier, already-resolved years are used. Backtest coverage
is about 78% (slightly under nominal) and drops sharply in market-wide shocks (2020, 2022). The range is not a guarantee.

**Served forecast.** The page and Findings serve `blend`, the equal-weight average of the model
and naive momentum (simple returns). Backtest average MAE is about 3.59 pp for the blend vs ~3.58 model
vs ~4.2 momentum; the page shows live numbers. The backtest still shows a pessimistic bias
(~-0.9 pp blend), largest at turning points (2012, 2020, 2023). `blend` is scored in the same backtest.

**Baselines and predictors.** `blend`, `model`, `naive_momentum` (predict the trailing 12-month return) and `zero` (no change;
rank IC and lift are n/a because it ranks nothing).

Past backtest performance does not guarantee future results.

## Financing estimator

Base rates are the latest monthly Freddie Mac PMMS averages (30y and 15y); 20y is interpolated linearly in term and 10y
extrapolated. For conventional loans over 15 years, an approximate Fannie Mae LLPA (credit band x LTV) moves the rate by 0.25%
per point relative to the PMMS reference borrower (740-759, 80% LTV). FHA/VA use a rule-of-thumb discount. Mortgage insurance:
illustrative PMI that drops at 78% of price, FHA upfront and annual MIP per HUD ML 2023-05, VA funding fee (financed, no MI).
APR is the rate at which the present value of P&I plus MI equals the loan less lender fees.
ARMs (conventional only): 5/6 and 10/6 indexed to 30-day Average SOFR, 6-month resets, caps 2/1/5 (5/6) and 5/1/5 (10/6) per the
ARRC model terms, rate floored at the margin (default 2.75) and rounded to 0.125 (unverified). The initial rate is an approximation
(adjusted 30y fixed minus 0.50 / 0.25). Scenarios hold the index constant (flat, +2 pp, -1 pp, caps worst case).
Equity projection: year 1 is the ML blend's 80% range for the metro (historical trend if unavailable); years 2+ compound the
region's average log growth (mu) with an 80% range of Z80 x sd5 x sqrt(h/5), where sd5 is the spread of its historical 5-year
returns. Needs 120 months of history, else United States is used. Selling costs default to ~6%; values are nominal. Highly
uncertain, not advice.
Limits: an estimate, not a loan quote; insurance data is from 2022 and likely below current premiums; LLPA and PMI tables are
approximate; no county loan limits, points, HOA or flood insurance.

## Deploy to Streamlit Community Cloud

1. Push this repo to `gserfaty/michiganmen` on GitHub (`app.py` at the repo root).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Select the `gserfaty/michiganmen` repo, branch `main`, main file `app.py`, Python 3.11.
4. Deploy. No secrets or API keys are required.
