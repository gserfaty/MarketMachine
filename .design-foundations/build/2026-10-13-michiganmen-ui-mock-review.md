# Design Review: Phase MOCK - michiganmen UI mock (Market overview, ML forecast / Austin)

## Rendered Evidence (Step 0)
- Screenshots: `.design-foundations/mocks/market-overview.jpg`, `.design-foundations/mocks/ml-forecast-austin.jpg` (read and critiqued as pixels)
- Source: `market-overview.html`, `ml-forecast-austin.html` (read for structure, tokens, contrast math)
- Surface: two pages, wireframe fidelity. Both self-declare "Wireframe — no DESIGN.md locked; greyscale defaults. Colour/type pending Phase 2." No DESIGN.md / JOURNEY.md exist, so the DW-MOCK.2 "wireframe structure is sound" branch applies.
- Screenshots are desktop-width only; the lower part of each page (forecast table end, footer/disclaimer) is below the captured fold and was verified from source.

## Assessment B — Deterministic Detector
- Command: `node .../design-for-ai/4.2.0/scripts/detect.mjs market-overview.html ml-forecast-austin.html > .design-foundations/build/detect.json`
- Exit: 0 (ran)
- Findings: 2, both `hero-eyebrow-chip` (one per page)
- Opened only after Assessment A findings were frozen: YES

## Triage
- Baseline (always on): visual + usability
- Dispatched: data-viz (KPI tiles, a driver table, and two chart placeholders that encode forecasts and intervals); content-design (real headline and microcopy: answer-first H1s, reliability copy, the disclaimer); journey (overview -> pick metro -> forecast -> financing handoff)
- Not applicable: behavioral / deceptive-patterns (no pricing, signup, or conversion mechanics)
- Deferred: none

## Cross-Pillar Findings (ONE ranked report)
| Severity | Pillar | Problem (in the rendered pixels) | Principle | Fix |
|----------|--------|----------------------------------|-----------|-----|
| Major | usability | Layout has no breakpoints. It uses a fixed `260px 1fr` grid, a 4-column KPI row, `select{min-width:320px}` and 64px main padding. At phone width it will scroll horizontally or crush the KPIs. Streamlit stacks the sidebar on mobile, so the mock does not show that state. | Responsive / medium-form fit (ch03); Nielsen #7 flexibility | Add a narrow breakpoint: collapse nav, use 2x2 then 1-column KPIs, and drop the select min-width |
| Major | content / data-viz | The overview H1 range "(0% to +3.6%)" has no interval label. The forecast page explains its "80% range", but the overview range has no confidence level or explanation. | Nielsen #4 consistency; honest uncertainty encoding (data-viz: label every interval) | Add "80% range" to the overview H1/sub, matching the forecast page |
| Minor | detector + visual | `hero-eyebrow-chip`, evidence: `eyebrow "United States · Zillow ZHVI, updated mon" above <h1> "US home values: up 1.2% over the past year; foreca"` and `eyebrow "ML forecast · Austin, TX (carried from M" above <h1> "Austin, TX home values: forecast −2.1% over the ne"`. **Register justification:** the line carries data provenance, update cadence and the carried-over metro, which is functional and not a decorative kicker. The uppercase, tracked styling is still the generic AI pattern. | ai-tells.md (eyebrow-over-hero tell) | Keep the content. Restyle it as a sentence-case source/meta line, or move provenance under the H1 and into the KPI captions |
| Minor | usability | The overview sidebar says "Selected metro: None yet — pick below" while the select already shows Austin, TX, so the state readout disagrees with the control | Nielsen #1 visibility of system status | Default the select to a "Choose a metro…" placeholder, or show Austin as the pre-selected metro |
| Minor | usability | The forecast-page "change" link inline-overrides `padding:0;min-height:0`, making the 13px link the only metro switcher (about 20px tall) | Fitts's law; WCAG 2.2 SC 2.5.8 target size (24px) | Give it a 24–44px target or add a metro select in the forecast header |
| Minor | data-viz | The "What drives this forecast" table lists three factors, all "Pulls forecast down", with no magnitude. Readers cannot tell which factor matters most. | Data-ink / encode the quantity that answers the question (Tufte); Nielsen #2 | Add a contribution column in points, or sort with a small bar |
| Minor | content | The KPI row shows ZHVI YoY +1.2% next to Case-Shiller YoY +1.9% with no note on why two "YoY" figures differ. "Latest month" also gives no actual month. | Nielsen #1 (data freshness), #2 match with real world | Caption the difference ("different index method") and print the as-of month |
| Minor | content | Nav label casing is inconsistent: "Market Profile" uses title case while every other item uses sentence case | Nielsen #4 consistency | Change it to "Market profile" |
| Minor | content | "vs. simple guess: Better" has no number behind it, while the other two reliability tiles are quantified | Nielsen #2; quantified claims (content-design) | Give the error reduction, e.g. "2.4 vs 3.1 pts error" |

## Requirement Fulfillment
### DW-MOCK.1
PREMISE:  the mock renders a viewable surface for the named page(s).
EVIDENCE: Both JPGs show fully rendered pages, each with a sidebar nav, an answer-first H1, KPI or reliability cards, a chart placeholder, and a next-step CTA. Nav links cross-link the two pages (`aria-current` is set correctly per page). The overview form's action targets the forecast page.
VERDICT:  PASS

### DW-MOCK.2
PREMISE:  text/interactive contrast and applied tokens hold on the rendered pixels (styled), or wireframe structure is sound (wireframe).
EVIDENCE: This is a wireframe, declared in the on-page flag.
- Structure: semantic `nav[aria-label]`, `main`, `header`, `h1`→`h2` hierarchy, labelled `select`, `table` with `th`, sections with `aria-labelledby`, `prefers-reduced-motion` guard.
- Tokens: a greyscale token set is defined on `:root` and used throughout. The only exceptions are two inline style overrides.
- Contrast is AA throughout:
  - text #212121 on #fff ≈ 16:1
  - secondary #616161 on #fff ≈ 6.2:1, on #f5f5f5 ≈ 5.7:1, on #ebebeb ≈ 5.2:1
  - active nav and button: #fff on #424242 ≈ 10:1
- Interactive targets are 44px min-height, except the inline "change" link (Minor finding above).
- The required "not financial advice" disclaimer is present in both footers.
VERDICT:  PASS

**All requirements met:** YES

## Notes (non-blocking)
- Distinctiveness (ai-tells.md CHECKER): the surface has no nameable aesthetic direction yet. It is deliberately greyscale and the flag defers colour and type to Phase 2. DW-MOCK.2 explicitly allows the wireframe branch, so this is recorded as a carried-forward gate and not a FAIL here. The styled Phase 2 mock must pass CHECKER mode, or it fails.
- Chart placeholders are bracketed text, so chart encoding (axes, band styling, forecast/history distinction) is unreviewed. Review it at styled fidelity.
- The visible placeholder copy "[One-line plain-language takeaway…]" and "[Placeholder figures.]" is acceptable for a wireframe and must not ship.
- "Regional explorer", "Findings", "Market Profile" and "Financing estimator" are `href="#"` stubs, which is expected for a two-page mock.
- The disclaimer is 13px grey at the page foot, below the fold. It meets the CLAUDE.md requirement, but consider placing it near the forecast H1 as well.
- Only desktop screenshots were supplied, so the phone-width behaviour is inferred from CSS and not captured in pixels.

**Verdict: PASS** (wireframe; 2 Major + 7 Minor to address in the styled pass)
