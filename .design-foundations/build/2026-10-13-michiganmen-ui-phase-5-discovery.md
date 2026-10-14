# Discovery + Design: Phase 5 - Charts & tables

## Artifacts Found / Current State
No chart template exists. `housing/pages.py` builds Plotly figures inline with Plotly defaults (blue/red/green default colorway, legends, dual axes on Overview and Financing amortization, a hard-coded `rgba(31,119,180,0.2)` equity band), two `st.line_chart` calls on Market profile, and 14 `st.dataframe` calls that mostly pass pre-formatted strings (misaligned, mis-sorted). Charts: Overview 3 (line, dual-axis, Case-Shiller), Explorer 3 (bar top20, choropleth, history), Profile 2, Forecast 2 (rank-IC line, histogram), Financing 3 (ARM lines, amortization+balance dual axis, equity band).

## Gaps
Default Plotly colors incl. red; no up/down encoding; dual axes; string-formatted numbers; Streamlit `theme="streamlit"` would override any template; `chart*Colors` theme keys unset (confirmed present in streamlit/config.py 1.64.0).

## Gate Status
DESIGN.md locked (Phases 2-3); JOURNEY.md present. Prerequisites met. Locked blocks and `## Components` untouched; only `## Data surfaces` appended.

## DW Verification
| DW-ID | Done-When Item | Status | Evidence |
|-------|---------------|--------|----------|
| DW-5.1 | Palette passes colorblind check; up/down redundantly encoded | COVERED | CVD simulation (Machado 2009 full severity, CIELAB): min pair 25.8 deutan across ink/teal/amber/violet; ink vs grey >=37; all series >=3:1 on white; up/down = green+▲+"+" / slate-blue+▼+"−" plus zero-line position and data labels. Note: green vs blue is only 12.9 under tritan, so direction never relies on hue |
| DW-5.2 | Chart text and gridline colors resolve to DESIGN.md tokens; text passes AA | COVERED | `--viz-text`/`--viz-text-muted`/`--viz-grid`/`--viz-axis`/`--viz-zero` alias locked tokens; text 13.30 and 5.89 (4.72 on band) all >=4.5; gridlines 1.20 decorative by design |
**All items COVERED:** YES (2/2)

## Design Decisions
- Data highlight is ink (neutral-12), not brand red: red stays action-only; one preattentive attribute (Knaflic 2015).
- Direction colors only on change charts; level charts stay ink so a falling price is never colored (Never list).
- Dual axes retired for small multiples (Cairo 2019, Tufte 1983). Streamlit native charts replaced by Plotly for one renderer.
- Three categorical hues (teal, amber, violet) hand-picked and validated with a script (palette.mjs makes ramps, not categorical sets; no palette.mjs run needed this phase because no new ramp is generated).
- Tables: numeric columns + `st.column_config` instead of strings; no new dependencies.

## Recommendation
BUILD (complete: spec appended to DESIGN.md `## Data surfaces`).
