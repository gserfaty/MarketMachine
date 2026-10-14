# Design Review: Phase 5 - Data surfaces (charts and tables)

## Rendered Evidence (Step 0)
- Screenshot: none. Spec-only phase. Surface reviewed: `## Data surfaces` in `/Users/gabriel/code/michiganmen/DESIGN.md` (lines 363 to 550, end of file), with source values from `## Color tokens`. JOURNEY.md is the page contract at the same root and was not needed for the DW-5.1/5.2 checks.
- Coverage gap: no rendered pixels. Every contrast ratio and CVD distance below was computed from the hex values with a stdlib Python script (WCAG 2.x relative luminance; Machado et al. 2009 severity 1.0 matrices applied in linear RGB; CIE76 in CIELAB, D65 white). Script: `/private/tmp/claude-501/-Users-gabriel-code-michiganmen/e5fe1d20-0d95-41bb-9fd6-d8d2270b706d/scratchpad/viz_check.py` (palette, text, gridline, band) and `map_check.py` (choropleth label stops).
- Doctrine: `docs/pillar-taxonomy.md §5` maps `data-viz` to `skills/data-viz/SKILL.md` (under the design-for-ai 4.2.0 plugin). Read in full before review.

## Assessment B — Deterministic Detector
- Command: `node /Users/gabriel/.claude/plugins/cache/rtd/design-for-ai/4.2.0/scripts/detect.mjs` (no HTML path supplied)
- Exit: 3 (N/A, no rendered artifact). Confirmed by running it: `"status": "na"`, `"naReason": "no html artifact supplied"`.
- Findings: N/A — no rendered artifact.
- Opened only after Assessment A findings were frozen: YES.

## Triage
- Baseline: visual color and contrast checks, plus the data-viz doctrine as dispatched.
- Dispatched: `data-viz`. Signals present: Plotly line, bar, histogram, and choropleth charts; `st.dataframe` tables; an 80% range band; a rank-IC chart.
- Not applicable: content-design (no microcopy in scope), behavioral, deceptive-patterns, journey.
- Not loaded: `usability` and the `design-dna`/`checklists` baselines. Dispatch scoped this review to data-viz, so they were not applied. Outside DW-5.1, DW-5.2 and the listed edge cases.
- Deferred: none.

## Cross-Pillar Findings (ONE ranked report)
| Severity | Pillar | Problem | Principle | Fix |
|----------|--------|---------|-----------|-----|
| Minor | data-viz | The Equity chart puts a 2-series comparison (focus ink line plus `--viz-cat-3` amber dashed "Net equity") in one chart. The co-occurrence rule 3 says violet and amber appear "only in charts with 3 or 4 compared series." The color check still passes (ink/amber min 53.3), so this is a rule-consistency defect. | Internal consistency of the spec's own co-occurrence rules | Either drop amber from Equity (use ink plus grey context) or amend rule 3 to cover the 2-series case. |
| Minor | data-viz | In Financing, the amber `--viz-cat-3` ARM scenario and the grey `--viz-context` 30-year fixed line are both dashed. The "Redundant encoding" rule says `cat-3 dashed` and `grey context dashed`, so dash does not separate these two series. Direct labels carry the identity. | Knaflic 2015: redundant channel must separate the series it is meant to | Give one of the two a different dash or marker, or state that labels alone carry identity for that chart. |
| Minor | data-viz | Dash carries two meanings. Range bands use dashed for "projected", but Financing (30-year fixed grey dashed) and Equity (net equity amber dashed) also use dashed for series identity. A reader cannot tell a projected line from a non-projected series by dash alone. | Knaflic 2015: one channel per meaning | Reserve dash for projection; use solid, dotted or markers for series identity. |
| Minor | data-viz | The table `NumberColumn(format="%+.1f%%")` option emits an ASCII hyphen for negatives. The spec's True-minus rule requires U+2212 in chart tick text and in `fmt_pct` strings. Numeric change columns therefore show "-" where the rest of the surface shows "−". | Consistency (Nielsen 4); the spec's own True-minus rule | Route signed change columns through `fmt_pct`, or use the numeric column only for sorting with a hidden field. |
| Note | data-viz | Choropleth colorscale rationale is overstated. The spec says a plain gradient "would pass through mid-tones where neither ink nor white reaches 4.5:1", but its own scale uses gradients between stops (0.2 to 0.5 blue-3 to neutral-5; 0.5 to 0.8 neutral-5 to green-3), and I computed every stop plus the no-data fill at 5.56 or higher. The stepped stops at 0.2, 0.4 and 0.8 are still a valid design choice; the stated reason is not what keeps the labels legible. | Truthful documentation of encoding (Cairo 2019) | Reword the rationale, or leave as is; no contrast failure results. |
| Note | data-viz | Choropleth scale clips at p5/p95 (`M = max(|p5|,|p95|)`). States beyond the clip share the end color. Each state is labeled with its true value, so the loss is in color only. | Truthful encoding (Cairo 2019) | Acceptable. State in the caption that the color scale is clipped. |
| Note | data-viz | Up/down under tritan is 12.9 (floor 10). It passes, and direction never relies on hue (▲/▼ and signs in text). The margin is thin for the map, where labels are the carrier. | WCAG 1.4.1 | None required. |
| Note | data-viz | Gridlines `--neutral-4` (1.20:1) and axis `--neutral-7` (1.72:1) are declared decorative. The spec's wording that WCAG 1.4.11 "exempts" them is loose, but gridlines are not required to understand the chart, so the substance holds. | WCAG 1.4.11 scope | None required. |

## Requirement Fulfillment

### DW-5.1
PREMISE:  "Chart palette passes colorblind check and up/down is redundantly encoded (sign/arrow + color)."
EVIDENCE:
- Palette CVD, my own computation (CIE76 in CIELAB; Machado 2009 severity 1.0 for protan, deutan, tritan; normal shown too). Recomputed from the locked hexes: ink #312d2c, teal #007a87, amber #b7791f, violet #7a5cb8, grey #948584, up #35742f, down #41629f, background #fdfcfc. All 15 co-occurring pairs, min dE:
  - ink/teal 32.3, ink/amber 53.3, ink/violet 30.4, teal/amber 67.3, teal/violet 26.5, amber/violet 45.1
  - ink/grey 37.6, teal/grey 14.9, amber/grey 33.3, violet/grey 17.0
  - up/down 12.9, up/ink 36.0, down/ink 37.4, up/grey 29.5, down/grey 37.1
  - All at or above the floor of 10. Worst pair: up/down under tritan at 12.9.
- Excluded pairs reproduce the spec's values (violet/down 7.9 deutan, teal/up 10.4 tritan, teal/down 10.3 tritan). Co-occurrence rule 1 keeps them off a shared chart, so the exclusion holds.
- Redundant encoding, bars of change: "▲ +4.2%" / "▼ −1.8%" data labels at the bar end, plus a visible zero baseline (`--viz-zero`). Color is not the sole carrier. PASS.
- Redundant encoding, forecast endpoints: "▼ −2.1%" / "▲ +1.3%" in `--viz-text`; direction color only on the end marker and segment. PASS.
- Redundant encoding, choropleth: every state carries a signed label "TX ▲ +4.2%" from a text layer. PASS.
- Redundant encoding, tables: signed strings with ▲/▼ where direction must be explicit; numeric change columns carry the sign. PASS.
VERDICT:  PASS

### DW-5.2
PREMISE:  "Chart text and gridline colors resolve to DESIGN.md tokens; chart text passes AA."
EVIDENCE:
- Token resolution, quoted from the spec: `--viz-text: var(--text)` (→ `--neutral-12` #312d2c), `--viz-text-muted: var(--text-secondary)` (→ `--neutral-11` #696160), `--viz-bg: var(--background)`, `--viz-grid: var(--neutral-4)`, `--viz-axis: var(--neutral-7)`, `--viz-zero: var(--neutral-9)`, `--viz-up: var(--positive)`, `--viz-down: var(--negative)`. Gridline and axis colors resolve to locked tokens. PASS.
- Text ratios on `--background` #fdfcfc, recomputed: `--viz-text` 13.30; `--viz-text-muted` 5.89; `--positive` #35742f 5.56; `--negative` #41629f 5.91. All ≥ 4.5. PASS.
- Band labels: `--viz-text-muted` on the 80% band composite #e5e3e3 = 4.72. PASS.
- Forecast endpoint text `--viz-text` on the band composite: 10.65. PASS. (Direction color is on the marker and line only, not on text.)
- Choropleth state labels: every stop of both ramps plus the no-data fill, with the label color the spec assigns per fill (`--viz-text` or `--background`). Minimum 5.56 (at the green and blue ends, white on #35742f and on #41629f 5.91). I recomputed all 21 stop pairs: all PASS. The spec forbids `--viz-text-muted` on map fills, and I found no use of it there. PASS.
- Gridline `--viz-grid` = `--neutral-4` (1.20:1) and axis `--viz-axis` = `--neutral-7` (1.72:1) are decorative per the spec; see Note row. Token resolution PASS.
VERDICT:  PASS

## Edge cases

### Many-series charts (cap highlighted series, grey the rest)
- Handled by construction, not by "grey the rest." The spec hard-caps named series at 4 per chart (one ink focus, at most three comparison series in teal, amber, violet, or grey context), and says "the build never draws 5 or more lines in one panel." Above the cap it routes to small multiples or a table. Every listed page is at or under the cap (Per-page chart and table list).
- Quote: "Hard cap: at most 4 named series per chart."
- Reviewer note: the spec does not say to grey the rest of a many-series chart. It prevents the case. No page as listed can produce that chart.
VERDICT:  PASS

### Negative-only datasets
- Bars: handled explicitly. All bars `--viz-down` with ▼ and −, extending from a visible zero line in the down direction, with 0 kept in range and no flipped axis (Up/down encoding, "Negative-only dataset"). PASS.
- Choropleth (change metric): symmetric scale, `zmin=-M`, `zmax=+M`, zero at the exact center, so all-negative data sits on the down half and no state takes the green end (Choropleth). The spec states this directly. PASS.
VERDICT:  PASS

## Issues (if FAIL)
None. No DW item fails, no listed edge case is unhandled, and no Critical or Major finding remains against the current spec text.

**Verdict: PASS**

## Notes (non-blocking)
- No pixel evidence. Every ratio is computed from the spec's hex values. Once rendered, check the choropleth labels and the Financing dash-only series in pixels.
- Superseded findings: the previous review at this path (before this run) recorded a Critical (choropleth labels at 1.00 to 2.59:1) and a Major (forecast endpoint label at 4.45:1 on the band). Those rows describe spec text that no longer exists. The current `## Data surfaces` assigns per-state label colors (ink or background, never muted on map fills) and sets the endpoint text to `--viz-text`, and my recomputation of both passes. The old FAIL is not carried forward.
- Previously noted Minor items that still apply: dash double meaning; ASCII hyphen in `%+.1f%%` numeric columns; `--viz-band` written as a literal `rgb()` rather than a token reference, and the categorical hexes defined outside the locked blocks (the spec declares both as exceptions, so not re-filed here).
- Doctrine coverage: `data-viz` applied. `usability` and the visual baselines were not loaded (outside the dispatched scope). Distinctiveness (ai-tells CHECKER) was not evaluated: it applies to a rendered surface, and no rendered surface exists in this phase.

**All requirements met:** YES (DW-5.1 PASS, DW-5.2 PASS, edge cases PASS)

**Verdict: PASS (with Minor notes; no blockers)**
