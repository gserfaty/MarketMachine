# Design Review: michiganmen UI redesign (app, 1280x800)

## Rendered Evidence
- Live app http://localhost:8597 rendered at 1280x800 in the browser pane; screenshots of Overview, Findings, Regional explorer, Market profile (Austin carried), ML forecast (no metro and Austin), Financing. DOM measured with JS (scrollWidth vs clientWidth, computed colors, focus outlines).

## Assessment B
- N/A: Streamlit serves a JS shell, no static rendered .html exists to feed detect.mjs. Coverage gap noted. (Prompt permits N/A in this case.)

## Triage
- Baseline visual + usability; data-viz (Plotly charts, tables); content-design (headline/microcopy). Not applicable: behavioral/deceptive (no conversion surface).

## Findings (ranked)
| Sev | Pillar | Page | Problem | Principle | Fix |
|-----|--------|------|---------|-----------|-----|
| Critical | usability/visual | Overview | KPI values truncated at 1280: "$368,697" renders "$368...", "▲ +1.2%" renders "▲ +1...." (x3); labels "Typical ho...", "Change ove...", "30-year mo..."; delta "+1.09 poin...". Content 156px in a 110px clip. | Nielsen #1/#6; R3 contract (no truncated values); Tufte: the number is the data | Metrics sit in 190px cards (main column only 969px: 300px sidebar + 4 cards). Drop value size to --text-xl for 4-up rows, cut card padding to --space-4, narrow sidebar to ~240px, or use 2x2 grid; add `text-overflow: clip/white-space: normal` fallback so no ellipsis ever |
| Critical | usability | Financing | Headline answer "$2,560" shows "$2,5...", cash down "$80,...", total interest "$472...", rate "7.34%..." (all 4 truncated); the key answer number is unreadable above the fold | same | same fix; also shorten the 4-line headline sentence (spec max 2 lines) or move the "tax and insurance..." sentence to the sub-line |
| Critical | usability | ML forecast | "Versus a no-change guess" value "3.6 vs 5.7 ..." and label "Versus a no-change g..." truncated | same | Render as "3.6 vs 5.7" with "points" in caption, or wrap |
| Major | usability | Findings, Market profile | "Vineyard ..." (metro name), label "Best performer, last 5 ye..."; Profile "$417...", "▼ −4....", "▼ −13...." and "Typical home v..." truncated (1-yr/5-yr values lose the number) | same | same |
| Major | visual/data-viz | ML forecast chart (and Profile chart) | Y axis title "Typical value ($)" collides with tick labels (450,000 to 400,000); plot area is tinted off-white (~surface) rather than --background; 80% range legend swatch nearly invisible (about 1.1:1); forecast tail and band tiny, no endpoint "▼ −2.7%" label as spec'd | Cleveland/McGill readability; Tufte data-ink; DESIGN.md Data surfaces (Range bands, template) | Increase left margin / `standoff` on axis title (or drop title, state unit in subhead), set plot_bgcolor=--background, add direct endpoint label, give band legend a visible swatch |
| Major | content/journey | Regional explorer | Region type / Sort by / Filters controls sit above the headline answer; JOURNEY says headline first, KPIs, then filters | Hick/progressive disclosure; JOURNEY block order | Move controls below KPI row (render headline from default state) |
| Major | journey | Overview with carried metro | Takeaway line still reads "Next, choose a metro to see its forecast." while Austin, TX is selected | Nielsen #1 visibility of status; JOURNEY: carried state copy | Swap takeaway to "Continue with Austin, TX" state (block below already does) |
| Minor | data-viz | Overview | YoY chart y tick "+0%" (should be "0%"); x axis starts 1980 so the YoY series leaves the left ~40% empty | Cairo truthful encoding; sign rules | Zero tick unsigned; share x range from the data start or trim rate series |
| Minor | content | Findings, Explorer | Value column "$1,068,543.13" shows cents; DESIGN.md table spec is `$1,234` | DESIGN.md Table spec | `format="$%d"` |
| Minor | usability | Findings/Explorer | KPI delta chips use Streamlit "↑" icon rather than "▲" (spec allows Streamlit arrow; ▲/▼ glyph in value text elsewhere) | Consistency (Nielsen #4) | Optional: standardize |
| Minor | usability | ML forecast | Expander headers expose Material icon ligature text "keyboard_arrow_right" in page text (visual renders icon; check icon font loads for assistive/offline) | Robustness | Verify, no action if icon font loads |
| Note | usability | Selectbox focus | Tab focus ring verified on buttons (2px solid rgb(199,66,72)); selectbox focus ring not demonstrated in this run; section-anchor links show Streamlit's 50% red glow instead of the token ring | WCAG 2.4.7 | Confirm selectbox ring; low risk |

Distinctiveness: PASS. Nameable direction (Open House: serif headline sentence + Roofline chevron + white/red), at least one non-generic choice (the Roofline, serif answer sentence). Not generic.

## Requirement Fulfillment
### R1
PREMISE: All text/background pairs on the rendered pages pass WCAG AA; interactive elements pass >=3:1 non-text with visible focus.
EVIDENCE: JS contrast scan over all text nodes on Forecast and Findings found 0 pairs under 4.6:1. Select border rgb(148,133,132) = neutral-9 (3.45:1). Buttons show 2px solid rgb(199,66,72) ring on keyboard focus. Selectbox focus ring not demonstrated; truncation (not contrast) is the problem. Overview/Financing/Profile not scanned individually (same tokens).
VERDICT: PASS

### R2
PREMISE: Colors, type and spacing match DESIGN.md tokens (red only for brand/action; down/negative never red; up/down carry arrows + sign).
EVIDENCE: Body bg rgb(253,252,252), h1 Newsreader 36px #312d2c, Public Sans body; Roofline present once per page; red only on CTA, nav active, Roofline, links; down values are "▼ −4.7%" with true minus, no red anywhere in charts. Deviations: chart plot area tinted, cents in table values, "+0%" tick, KPI values shrink/clip so spec size not usable.
VERDICT: PARTIAL

### R3
PREMISE: Each page's headline answer and key numbers fully visible above the fold at 1280x800 - no truncated values.
EVIDENCE: Headlines fully visible on all pages. KPI values truncated with ellipsis on Overview (3 of 4), Financing (4 of 4, including the monthly payment), ML forecast (1 of 3), Findings (1 of 3 + label), Profile (3 of 4). Measured: value content 156px vs 110px clip. Only Explorer fully intact.
VERDICT: FAIL

### R4
PREMISE: The selected metro is shown consistently in the sidebar and page pickers.
EVIDENCE: With ?metro=Austin, TX: sidebar readout "Austin, TX" + "Change"; Profile picker "Austin, TX"; Forecast picker "Austin, TX" with "Using Austin, TX (from Market overview)"; Overview "Continue with Austin, TX" with picker "Austin, TX". Empty state: "No metro selected" with empty pickers. (Overview takeaway line stays in no-metro wording, see findings.)
VERDICT: PASS

### R5
PREMISE: Disclaimers present on every page showing a forecast or financing figure.
EVIDENCE: Overview, Forecast, Findings: D1 callout under headline plus sidebar plus footer; Financing: D2 "not a loan quote or offer" notice under headline; Explorer/Profile: sidebar and footer D1.
VERDICT: PASS

### R6
PREMISE: Charts encode data truthfully per Data surfaces (axes readable, data not clipped, <=4 series, range bands labeled).
EVIDENCE: Dual axis retired (stacked small multiples), <=2 series per chart, ink line, no red, "80% range" and "Forecast" in legend plus as-of caption, "Today" divider. Defects: y-axis title overlaps tick labels on Forecast/Profile charts, off-spec plot tint, no endpoint label, YoY x axis wasted range.
VERDICT: PARTIAL

### R7
PREMISE: Page specs and copy in JOURNEY.md are reflected on the rendered pages.
EVIDENCE: Headlines, titles, KPI labels, section titles and nav groups match Phase 4 copy; sidebar readout/Change present; 6-item nav. Deviations: Explorer controls above headline; Overview takeaway not updated for carried metro; KPI labels cut so wording not readable.
VERDICT: PARTIAL

**All requirements met:** NO

## Notes
- Assessment B N/A (no static HTML). Pixel evidence obtained; no gaps otherwise.
- Not reviewed: Explorer expanded filters, State/choropleth, Financing below the fold, error/down states.

## Issues (blocking)
1. KPI value/label truncation on 5 of 6 pages (Critical, usability/R3, Nielsen #1): fix card width/type size/wrapping as above; re-measure scrollWidth <= clientWidth at 1280.

**Verdict: FAIL - R3 truncated key numbers (Critical); R2, R6, R7 partial.**
