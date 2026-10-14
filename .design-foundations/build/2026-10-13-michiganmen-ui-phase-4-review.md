# Design Review: Phase 4 - Content (page copy and voice)

## Rendered Evidence (Step 0)
- Screenshot: none — spec-only phase. Structure-level critique of `JOURNEY.md` (`## Page specs` Copy blocks, `## Voice & tone`) and `DESIGN.md` (visual contract, read for context only). No pixel-level evidence; nothing in the DW items depends on pixels.
- Surface: JOURNEY.md, six page specs (Market overview, Findings, Regional explorer, Market profile, ML forecast, Financing estimator), Voice & tone, shared strings D1/D2/D3.

## Assessment B — Deterministic Detector
- Command: `node /Users/gabriel/.claude/plugins/cache/rtd/design-for-ai/4.2.0/scripts/detect.mjs` (no artifact supplied)
- Exit: 3 (N/A — no rendered artifact). Stdout: `"status": "na"`, `"naReason": "no html artifact supplied — nothing rendered yet"`.
- Findings: N/A — no rendered artifact
- Opened only after Assessment A findings were frozen: YES. (A pre-existing `detect.json` in `.design-foundations/build/` was not read.)
- Note: a first attempt used the repo-relative path `scripts/detect.mjs`, which does not exist in this repo; it failed with a module-not-found error (exit 1). The re-run from the plugin path returned the valid N/A exit 3. This is a path error, not a detector failure.

## Triage
- Baseline (always-on): visual + usability. Visual/usability doctrine not loaded as findings are scoped to the two DW items (content). Distinctiveness criterion not applicable to a spec-only copy phase.
- Dispatched: `content-design` (signal present: real product copy — headlines, empty/error states, button and label microcopy, voice & tone).
- Not applicable: `data-viz` (no chart encodings specified in copy), `deceptive-patterns` and `behavioral` (no conversion surface; the Financing "not a loan quote" notice was checked as part of DW-4.2), `journey` (page order is out of scope for DW-4.1/4.2), `design-systems`, `ai-native`.
- Deferred (if capped): none.

## Cross-Pillar Findings (ONE ranked report)
| Severity | Pillar | Problem | Principle | Fix |
|----------|--------|---------|-----------|-----|
| Minor | content | The same 12-month change has five labels: "up {yoy}% over the past year" (Overview headline), "over 12 months" (Overview KPI), "last year" (Market profile headline), "1-year change" (Explorer sort), "Change, 1 year" (Profile and Findings KPIs). | Nielsen #4 consistency; Voice & tone "Front-load the key info" and plain-word rule | Pick one phrase ("past year" in headlines, "Change, 1 year" in labels) and use it on every page. |
| Minor | content | Sign format is not specified for two headline values. Overview headline uses "forecast {fc}" and "up {yoy}%" with no sign rule; Voice & tone requires "signed percent with one decimal". Findings and ML forecast do sign their values. | Voice & tone "Numbers" rule | Specify `{fc}` and `{yoy}` as signed (`+1.3%`, `−0.8%`) in the Overview template, or state the abs-value convention for "up/down". |
| Minor | content | Regional explorer error copy is a directive, not copy: "Zillow-down standard (names which view, metro or state, is affected; the other view stays usable)". No literal message is written for the state-mode outage. | DW-4.1 completeness (error copy must be written); Voice & tone shared strings | Write the literal state-mode message, e.g. "Heads up: we can't reach Zillow's state data right now. The metro view still works." |
| Minor | content | Several tables have no column headers in the copy: Market profile "Compare with" table and "Similar markets" table; ML forecast "All metro forecasts" table; Financing "Rates by loan term" table; Explorer "Ranked regions" table. Findings is the only table with column labels. | Labels completeness (DW-4.1); Nielsen #6 recognition over recall | Add a column-label line to each Copy block, following the Findings pattern. |
| Minor | content | Explorer "Region history" picker has no label or placeholder. Flows say pickers default to "Choose a metro…", but this one is "Region". | Voice & tone empty-state rule ("one next step") | Add placeholder "Choose a region" to the Explorer block. |
| Minor | content | Error and empty copy uses different retry wording: "try again in a few minutes" (Overview, Financing, shared strings), "try again shortly" (Findings forecast failed; ML forecast training failed uses "Try again in a few minutes"). | Voice & tone consistency | Use one retry phrase, e.g. "Try again in a few minutes", for every training and data-down state. |
| Note | content | The disclaimer copy blocks reference "D1", "D2", "D3" rather than the literal sentence. The literal text lives in `## Voice & tone` "Shared strings". Presence is satisfied by reference, but a builder who copies only the page block would omit the text. | DW-4.2 presence (literal evidence) | When the build phase renders pages, print the literal D1/D2/D3 text, not the codes. |
| Note | content | D2 states a factual privacy claim: "Nothing you enter is stored, and we collect no personal data beyond a credit band." The spec does not verify it against the implementation. | Honest claims (deceptive-patterns: no unverifiable reassurance) | Verify against the code path (session state only, no logging, no analytics) before build, or soften to what is verifiable. |
| Note | content | Overview shows a 30-year mortgage rate KPI and a rate chart. The disclaimer D1 covers forecasts only. A mortgage rate is market data, not a financing estimate, so the DW-4.2 "financing figure" scope is ambiguous here. | DW-4.2 scope (judgment call) | Confirm with the owner whether market mortgage rates count as "financing figures". D1 already sits in the Overview footer, so no change is needed if they do not. |
| Note | content | Zillow-down message text differs by one comma between the Flows section ("Check your connection or try again") and the shared string ("Check your connection, or try again"). | Consistency | Keep the shared-string form; delete the Flows copy. |

## Requirement Fulfillment

### DW-4.1
PREMISE:  "Every page spec has a headline template, labels, and error/empty copy."
EVIDENCE: All six page specs were checked.
- Market overview: Headline "US home values: up {yoy}% over the past year; forecast {fc} next 12 months (80% range {lo} to {hi})." Labels: 4 KPI labels, Next-block heading/picker/button, 3 chart titles. Error/empty: "Empty/error: Zillow down: Zillow-down standard…; Mortgage down: warning 'Heads up: mortgage rates are unavailable right now…'; Case-Shiller down: KPI 'n/a'; Forecast unavailable: headline drops the forecast clause."
- Findings: Headline "Top predicted gainer: {metro} at {+X}% next 12 months (80% range {a} to {b})." Labels: 3 KPI labels, 5 section titles, 5 table column labels, row action "Use this metro". Error/empty: "Forecast failed: 'Couldn't build the forecast right now. Past performance is still shown below.'; No rows: 'No metros to show. Change the size filter or choose another view.'"
- Regional explorer: Headline "{N} metros shown. The median 1-year change is {+X}%, led by {metro} ({+Y}%)." Labels: 3 KPI labels, controls "Region type", "Sort by", expander "Filters", "Reset filters". Error/empty: "No regions match these filters. Widen the size or value range, or reset the filters."; "Choose a region from the table to see its price history." (Zillow-down portion is a directive; see Notes-level finding.)
- Market profile: Headline "{Metro}: typical home ${X}, up {Y}% in the last year, #{R} by size." Labels: 4 KPI labels, selector "Metro", "Compare with", section titles. Error/empty: "Choose a metro to see its profile."; "We couldn't find '{value}'. Choose a metro."; "Similar markets aren't available for {metro}…"
- ML forecast: Headline "{Metro} home values: forecast {+/-X}% over the next 12 months (80% range {a} to {b})." Labels: 3 KPI labels, section titles, expanders. Error/empty: "No forecast for {metro} yet…"; "Couldn't build the forecast right now…" with "Try again".
- Financing estimator: Headline "Estimated payment on a ${X} home in {metro}: ${Y}/month (30-year fixed at {r}%, {d}% down)." Labels: 4 KPI labels, 10+ input labels, expanders. Error/empty: "Heads up: we can't reach Zillow's home-value data…"; "Error: {specific cause} Change the value and the estimate will update."
VERDICT:  PASS

### DW-4.2
PREMISE:  "Disclaimers present on every page that shows a forecast or financing figure."
EVIDENCE: Pages that show a forecast or financing figure, and the disclaimer each carries:
- Market overview (headline forecast clause): "Disclaimer: D1, beside the headline forecast clause and in the footer." Content block 8 is the footer disclaimer. Present.
- Findings (predicted gainers and laggards): "Disclaimer: D1 in callout." Callout text includes D1. Present.
- ML forecast (forecast headline): "Disclaimer: D1 directly under the headline and in the footer." Present.
- Financing estimator (payment and equity figures): "Disclaimer: D2 under the headline, D3 on equity; D1 in footer." D2 = "This is an estimate, not a loan quote or offer, and not financial advice." Present.
- Regional explorer, Market profile: show no forecast or financing figure. Both still carry the footer D1 per the shared rule.
Count: 4 of 4 forecast/financing pages carry a disclaimer; 2 pages with no figure carry the footer D1 as a precaution. Literal text is in Voice & tone "Shared strings" (see Note above on presence by reference).
VERDICT:  PASS

**All requirements met:** YES

## Notes (non-blocking)
- Assessment B is N/A (no rendered .html). Visual pixel evidence is not applicable to this phase.
- Content-only review. Findings are at Minor or Note severity and do not block the phase. The Minor items are good to fix before build so copy drift does not reach the UI.
- The Financing privacy sentence (D2) is the one claim here that could be false in code. It should be verified before build, not after.
- Overall, the copy is strong: each page opens with its answer, the voice table is applied consistently, and the empty and error states name the cause and the next step.

## Issues (if FAIL)
None. No Critical or Major content-design violations were found, and no DW item is unmet.

**Verdict: PASS**

DESIGN-REVIEW PASS. Report written to /Users/gabriel/code/michiganmen/.design-foundations/build/2026-10-13-michiganmen-ui-phase-4-review.md
