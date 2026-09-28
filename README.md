# michiganmen

A Streamlit web app that analyzes the US housing market with historical and current public
data and uses machine learning to forecast market direction, find appreciating areas, and rank
the most valuable markets.

**Forecasts are statistical estimates, not financial advice.**

## Data sources

All free, public, and require no API key:

- [Zillow Home Value Index (ZHVI)](https://www.zillow.com/research/data/) — metro and state, smoothed/seasonally adjusted, all-homes tier.
- [FRED `MORTGAGE30US`](https://fred.stlouisfed.org/series/MORTGAGE30US) — weekly 30-year fixed mortgage rate.
- [FRED `CSUSHPINSA`](https://fred.stlouisfed.org/series/CSUSHPINSA) — Case-Shiller US National Home Price Index.

Data is downloaded at runtime and cached (`st.cache_data`, 24h TTL). If a source is unavailable,
the app shows a clear error/warning instead of crashing.

## Pages

1. **Market overview** — KPIs (US typical value, YoY change, mortgage rate, Case-Shiller YoY) and trend charts.
2. **Regional explorer** — filter/sort metros or states, bar chart of top movers, state choropleth, per-region history.
3. **ML forecast** — model vs. baseline metrics, national 12-month call, per-metro predictions.
4. **Findings** — top gainers, top/bottom predicted movers, most valuable metros.

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

## ML model

A `HistGradientBoostingRegressor` predicts each metro's 12-month log return from point-in-time
price-momentum, volatility, and macro (mortgage rate) features — no data from after the
prediction date is used. It's validated on a chronologically later, held-out window against a
naive momentum baseline and a zero-change baseline, reporting MAE and directional accuracy.

## Deploy to Streamlit Community Cloud

1. Push this repo to `gserfaty/michiganmen` on GitHub (`app.py` at the repo root).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Select the `gserfaty/michiganmen` repo, branch `main`, main file `app.py`, Python 3.11.
4. Deploy. No secrets or API keys are required.
