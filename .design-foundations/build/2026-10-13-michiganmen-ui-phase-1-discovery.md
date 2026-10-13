# Discovery + Design: Phase 1 - Journey & page specs

Doctrine loaded: `journey` (references/journey/journey.md), `usability` (skills/usability/SKILL.md).

## Artifacts Found / Current State
- No DESIGN.md, no JOURNEY.md. Mocks (wireframe, approved) + mock review exist.
- App today (`app.py`, `housing/pages.py`): sidebar `st.radio("Page")` with 6 options in order Market overview, Regional explorer, ML forecast, Findings, Market Profile, Financing estimator. Per-page behavior read in full:
  - Market overview: 4 `st.metric` (US value, YoY, 30y rate w/ 12m delta, Case-Shiller YoY), 3 charts (value, YoY vs rate dual-axis, Case-Shiller), as-of caption, footer disclaimer. Does NOT call the forecast model.
  - Regional explorer: Metro/State radio, state multiselect, size-rank slider, value slider, sort select, full table, top-20 bar, state choropleth, "Region history" select vs US.
  - ML forecast: opens with backtest tables (metrics, per-year), rank-IC chart, bullets, blend info, THEN the national 12-month call metric, histogram, per-metro table with text search, methodology expander. No metro selector.
  - Findings: five tables (top 15 1-yr, 5-yr, predicted gainers, bottom 10 predicted, most valuable), `st.warning` disclaimer.
  - Market Profile (collaborator): "Select a market" selectbox, 4 metrics, history, compare-with selectbox + table + chart, KNN similar markets, warning disclaimer. Header reads "Market Profiles".
  - Financing: top warning, price source radio (metro / manual), own metro selectbox (defaults to biggest metro), loan inputs, then results tables, ARM block, amortization, equity projection (own region fallback), sources expander.
- Metro state today: NONE shared. Three separate selectors (Explorer "Region history", Profile "Select a market", Financing "Metro") plus Equity "Appreciation series". Forecast has none.

## Gaps (design vs. code)
1. No cross-page metro state; query param and session state must be introduced (Phase build, not this phase).
2. Overview headline in the mock ("forecast +1.3% next 12 months (0% to +3.6%)") needs the trained model, which Overview does not load today. Cost: first-load training spinner. Spec degrades to trailing YoY if forecast is unavailable/slow.
3. Forecast reliability (MAE, direction accuracy, vs-baseline) is market-wide backtest data, not per-metro. The mock's "How reliable is this?" must be worded as the model's overall track record, not Austin's.
4. Mock's "What drives this forecast" (per-factor "pulls down") needs per-metro attribution that does not exist. New analytics are out of scope. Spec: show the latest input values only; attribution deferred.
5. Forecast page crashes uncaught if model training raises (no try/except). Needs an error state.
6. Explorer empty-filter result shows an empty table with no message.
7. Mock nav order equals today's order, which breaks the stated flow (Findings sits between Forecast and Profile). Spec reorders; flagged for user.
8. Mock review findings to fold in: "80% range" label on overview; sidebar readout must equal picker; change-metro target >= 24px; data month named; "Market profile" sentence case.

## Gate Status
DESIGN.md absent (Phase 2 produces it); JOURNEY.md is this phase's output. Prerequisite met: research brief + plan + approved mock. No visual tokens needed here.

## DW Verification
| DW-ID | Done-When Item | Status | Evidence |
|-------|---------------|--------|----------|
| DW-1.1 | 6 page specs, each with purpose, entry points, headline answer, prioritized blocks, states, exits | COVERED | JOURNEY.md `## Page specs`: grep count of `### ` spec headings = 6; each has the 6 labeled fields (checked by script) |
| DW-1.2 | Metro persistence flow (select, carry, change, invalid/missing) | COVERED | JOURNEY.md `## Flows` "Metro persistence" with 4 branches + state table |
| DW-1.3 | Every page lists empty/error states | COVERED | Each spec has a `States` field naming data-source-down case; script checks all 6 |
| DW-1.4 | <=4 headline KPIs per page; sidebar <=6 options | COVERED | Each spec lists `Headline KPIs (above the fold)` with count <=4; IA lists 6 nav items; script counts both |
**All items COVERED:** YES (count 4/4 equals prompt)

## Design Decisions
- JTBD school: Moesta (Switch forces), per plan. Single job story, three-beat journey (Market -> Metro -> Money). Loyalty loop not forced: this is a research tool, so the repeat loop is "re-check each month when new Zillow data lands". Theater flag: map is based on the owner's stated flow, not interviews; owner Gabriel, update at each phase gate.
- IA (Rosenfeld/Morville): task-organized, hub-and-spoke with a global metro as the contextual spine. 6 flat sidebar items grouped by three non-interactive captions (Market / Metro / Money); six is the Hick cap, grouping eases scanning. New order: Market overview, Findings, Regional explorer, Market profile, ML forecast, Financing estimator.
- Metro state: one source of truth (`st.session_state["metro"]` mirrored to `?metro=`), all pickers are views; the sidebar readout renders from state so it cannot disagree with a picker (mock-review finding). Invalid or missing metro never blocks a page.
- Headline answer per page = one sentence with a number and, for forecasts, the "80% range". Disclaimer shown on every page.
- Cowan cap: <=4 KPIs per page; Forecast uses 3 reliability tiles + the headline sentence.
- Market Profile: spec binds its first selector to the shared metro and renames the nav label; its logic (compare, KNN) is untouched.

## Recommendation
BUILD
