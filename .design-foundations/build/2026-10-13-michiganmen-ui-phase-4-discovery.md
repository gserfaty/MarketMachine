# Discovery + Design: Phase 4 - Words

## Artifacts Found / Current State
- JOURNEY.md has 6 page specs with draft headline answers and state names, but no final labels, button copy, or error strings.
- Code strings inventoried from app.py and housing/pages.py: page titles ("Market Profiles", "Market Profile" nav), metric labels (YoY change, Case-Shiller YoY, 1Y Appreciation, Size Rank), jargon (rank IC, MAE, bias, coverage80, width80, top_decile_lift, ZHVI, PITI-style table rows, SOFR, DTI), widget labels (Region type, Top N metros by size rank, Value range ($), Sort by, Choropleth metric with raw keys chg_1y, Region history, Search region, Select a market, Compare with, Price source, Metro, Down payment as %/$, Credit score band, Lender fees, ARM chart, Appreciation series, Loan for projection), alerts (Zillow data unavailable: {e}; FRED mortgage data unavailable; listings unavailable; SOFR unavailable; blend no longer beats model; ARM conventional-only; equity needs Zillow history; long-horizon uncertainty; jumbo; DTI messages; raw str(e) from estimator), spinners (Loading Zillow home value data...; Loading FRED series...; Loading Zillow listings data...; Training forecast model...), disclaimers (DISCLAIMER constant, Findings "Ranges ... not guarantees", financing "Estimate only ..." warning).
## Gaps
- Raw exception text is shown to users (st.error(f"... {e}"), st.error(str(e))): needs cause + fix wording.
- Jargon with no plain term; technical terms are in column headers and bullets, not tooltips.
- Inconsistent casing (Title Case vs sentence case), mixed "YoY"/"1-yr"/"1Y".
- Loading copy is fine in intent but ends in "..." and is not consistent.
## Gate Status
DESIGN.md locked (Open House); error form = "Error:"/"Couldn't ..." with check-X icon; data-down = warning "Heads up:". JOURNEY.md present. Prerequisites met.
## DW Verification
| DW-ID | Done-When Item | Status | Evidence |
|-------|---------------|--------|----------|
| DW-4.1 | Every page spec has headline template, labels, error/empty copy | COVERED | `**Copy**` block in each of 6 specs; grep count = 6 |
| DW-4.2 | Disclaimers on every forecast/financing page | COVERED | Each Copy block has a Disclaimer line (forecast: Overview, Findings, ML forecast, Profile footer; financing: notice + equity warning); grep |
**All items COVERED:** YES (2 of 2)
## Design Decisions
- Voice: direct, plain, calm (Podmajersky: voice stable, tone contextual). Sentence case everywhere (Redish scannability; matches nav spec).
- Answer sentence front-loads the number (Redish front-load). Placeholders in <angle brackets>; data month named in an as-of line.
- Jargon rule: plain term as label, technical term in help tooltip (Redish plain language; Yifrah microcopy).
- Errors: what happened, why, fix; never blame (Yifrah). Data-down = warning "Heads up:", real failures = "Error:"/"Couldn't ..." per DESIGN.md.
- Disclaimers: wording kept; only shortened where JOURNEY already allowed ("kept, shortened").
## Recommendation
BUILD
