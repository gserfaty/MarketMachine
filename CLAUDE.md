# michiganmen

Streamlit web app that analyzes the US housing market with historical and current public data and uses machine learning to forecast market direction, find appreciating areas, and rank the most valuable markets.

- Stack: Python 3.11+, Streamlit, pandas, scikit-learn, Plotly. Entry point: `app.py`.
- Deploy target: Streamlit Community Cloud from the GitHub repo `gserfaty/michiganmen` (`app.py` at repo root, `requirements.txt` pinned loosely). Must also run with `streamlit run app.py` locally.
- Data: free public sources that need no API key (e.g. Zillow Research CSVs, FRED `fredgraph.csv`). Download at runtime with `st.cache_data`, and fall back gracefully with a clear message if a source is down.
- Local env: `.venv/` (gitignored). Tests: `pytest` in `tests/`, must not hit the network (use small fixtures).
- Agent workflow: `planner` (Opus) → `developer` (Sonnet) → `evaluator` (Haiku), coordinated by the `orchestrate` skill. Handoffs live in `docs/PLAN.md` and `docs/EVAL.md`.
- Forecasts are statistical estimates, not financial advice; the UI must say so.
