# Design Review 2: michiganmen UI redesign (live app, 1280x800)
Assessment B: N/A (Streamlit serves a JS shell; no static .html). Pages reviewed live: /, /findings, /explorer, /profile, /forecast, /financing, with and without ?metro=Austin, TX. Computed-contrast scan of all text on /profile: lowest pair 5.70:1 (14px disclaimer), all >= AA. Focus ring visible (2px red outline on sidebar nav, Tab).

## Findings (ranked)
| Sev | Page | Problem | Principle | Fix |
|-----|------|---------|-----------|-----|
| Major | /forecast, /findings, / (headline) | Headline answer states deltas as prose with sign only ("forecast -2.7%", "+9.2%", "down 4.7%"); no ▲/▼. DESIGN.md: arrow and sign always present, direction never by one cue. | Redundant coding (WCAG 1.4.1); DESIGN.md Usage rules | Prefix headline deltas with ▲/▼ in --positive/--negative, or confirm in DESIGN.md that prose "up/down" words count |
| Minor | /financing, /forecast | KPI cards uneven height (wrapped labels / "7.34% / 7.44%" wraps), ragged bottom edge | Alignment / proximity (Gestalt) | Set min-height on KPI cards or shorten labels ("Rate / APR") |
| Minor | /explorer, /findings | Delta caption ("▲ +8.7%") sits outside its card, left-misaligned under the third card; reads orphaned | Proximity | Put the delta inside the card |
| Minor | /forecast, / charts | Legend swatches collide ("United States" runs into "80% range" swatch); x-axis runs to 2030 leaving ~25% empty plot, squeezing the forecast fan to a tiny wedge | Data-ink ratio; legibility (Tufte) | Add legend spacing; cap x-axis at forecast end + small pad; widen/label band |
| Minor | /forecast | "Using Austin, TX (from Market overview)" shown when metro arrived via URL | Copy accuracy / Nielsen #1 | Show the source only when it is true, else drop |
| Minor | /findings | Disclaimer only below tables, not near headline forecast (sidebar copy is present) | Proximity of caveat to claim | Move short disclaimer under headline, as on / and /forecast |

## Requirements
- R1 PASS: text pairs 5.70-13.30:1; controls have visible borders; focus ring visible.
- R2 PARTIAL (passes on tokens): red only on Roofline/nav/CTA/focus; negatives blue with ▼ and sign in KPIs and chart label (▼ -2.7%); Public Sans/Newsreader, white bg. Gap: headline prose deltas lack arrows (Major above). Not a blocker given the headline is a sentence with explicit direction wording.
- R3 PASS: headline and all KPI values fully visible above fold on all six pages; no truncation (Rate and APR wraps but is complete).
- R4 PASS: with ?metro=Austin, TX the sidebar ("Austin, TX", Change) and the page pickers on /findings, /profile, /forecast, /financing all show Austin, TX; unselected shows "No metro selected / Choose a metro".
- R5 PASS: disclaimer on /, /forecast, /financing (estimate, not quote), /findings and in sidebar on all pages.
- R6 PASS with Minor notes: axes readable, 1 line + band + forecast (<=4 series), range band labeled in legend and headline, not clipped; empty x-range and legend collision noted.
- R7 PASS: page titles, serif answer sentence with Roofline, KPI rows, disclaimers, CTAs ("See forecast for Austin", "Estimate financing") match page specs as far as sampled.

## Distinctiveness
Nameable direction: "airy red-and-white real-estate section with a serif answer sentence and Roofline". Distinct enough; not generic.

**Verdict: PASS (no Critical findings; 1 Major, 5 Minor).**
