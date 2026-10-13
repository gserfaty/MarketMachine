# Design Review: Phase 1 - JOURNEY.md page spec

## Rendered Evidence (Step 0)
- Screenshot: none. Spec-only phase; no rendered pixels exist.
- Surface reviewed: `/Users/gabriel/code/michiganmen/JOURNEY.md` (159 lines, text spec).
- Coverage gap (non-blocking): all checks are spec-level (structure, copy, state coverage). Above-the-fold KPI counts and the 24px target size are unverified at pixel level.

## Assessment B — Deterministic Detector
- Command: `node /Users/gabriel/.claude/plugins/cache/rtd/design-for-ai/4.2.0/scripts/detect.mjs` (no html path supplied)
- Exit: 3 (N/A, no rendered artifact). Output: `"status": "na"`, `"naReason": "no html artifact supplied — nothing rendered yet"`.
- Findings: N/A — no rendered artifact.
- Opened only after Assessment A findings were frozen: YES (its output carried no findings).

## Triage
- Baseline (always-on): visual + usability. Visual is N/A because there is no rendered surface.
- Dispatched: `journey` (page specs, IA, flows, JOURNEY.md structure) and `usability` (nav option count, KPI count, states, CTA placement, error recovery). Both named by the dispatch.
- Not applicable: `visual` (no surface), `data-viz` (charts are deferred to Phase 5, JOURNEY.md line 3), `ai-native` (no agent surface).
- Deferred (not dispatched, not capped): `content-design` (copy is draft, Phase 4 owns it, line 3) and `deceptive-patterns` / `behavioral` (the disclaimer and "not a quote" notices were checked only as requirements). Copy observations appear in Notes only.

## Cross-Pillar Findings (ONE ranked report)
| Severity | Pillar | Problem | Principle | Fix |
|----------|--------|---------|-----------|-----|
| Minor | usability | Overview primary CTA "See this metro's forecast" (line 96, 100) has no defined behavior in the no-metro state. Line 100 only specifies the placeholder picker in the "Next" block. | Nielsen #5 error prevention; Hick (choice at the branch) | State the CTA as disabled until a metro is chosen, or route it to the national call. |
| Minor | journey | Scope statement for the collaborator-owned Market profile (line 125) says the analytics logic is unchanged, then lists a headline (129), block reorder (131), and a tile-formatting change to "n/a" (132). The list is accurate, but the summary sentence reads broader than the changes. | Edge case: "spec it, don't redesign its logic" | Reword line 125 to enumerate the four changes (a)-(d) as the full scope. Keep the Lucas sign-off open item (line 159). |
| Minor | journey | Card sort and tree test not run (line 57). The spec gives a reason and defers to a confirm-with-Lucas step. The doctrine asks for validation before visual design (journey.md §D step 6; "Sitemap ≠ IA"). | journey.md Rules; §D.6 | Keep the stated reason. Add a Phase 4 item: run a short card sort or record Lucas's label confirmation in JOURNEY.md. |
| Minor | journey | Citation gaps. These recommendations have no named law or source: sidebar reorder (line 47, "market-wide rankings help"), "Choose a metro..." placeholder with no silent default (line 69), footer plus headline disclaimer placement (line 91). | journey.md Rules ("Cite the principle") | Add a source to each, for example Nielsen #6 recognition over recall for the placeholder, and Hick for the reorder rationale. |
| Minor | journey | JOURNEY.md cross-links are incomplete. Line 3 points to a DESIGN.md that is "not yet written". The doctrine requires linking from DESIGN.md and from a CLAUDE.md `## Design Context` block (journey.md §H.3). The repo CLAUDE.md I was pointed to has no such block. | journey.md §H step 3 | Add the links when DESIGN.md and the CLAUDE.md block exist. Track as a Phase 2 item. |
| Minor | usability | No accessibility requirements beyond the 24px "Change" target (line 71). The forecast band and the Overview/Explorer charts have no text alternative, and keyboard operation of the metro pickers is not specified. | usability SKILL.md (WCAG POUR, inclusive design) | Add an accessibility line to each page spec, or a shared rule: charts carry a text summary; pickers are keyboard operable. Can be deferred to Phase 5 for charts. |
| Minor | journey | The journey map has no touchpoints/channels lane and the emotion column is text, not a curve (journey.md §C step 3). Not required by a DW item. | journey.md §C | Optional for Phase 1. Add if the map is used to drive decisions. |
| Minor | usability | Findings "Use this metro" depends on Streamlit row-selection support (line 109), with a picker fallback. The chosen path is not specified until build. | Nielsen #4 consistency | Decide at build, or pick the picker for consistency across pages. |
| Note | usability | Overview forecast clause needs the model trained on first load (line 97; open item line 159). A training spinner on the landing page is a response-time risk. | Nielsen #1 visibility of system status | Keep the open item. Consider a cached or warm-up forecast. |
| Note | journey | Primary task flow is written as a linear arrow chain (line 63) and the phase table reads as a 1-4 sequence (lines 27-32). The loop is acknowledged at line 34. | journey.md Rules ("No linear funnel"); §E task flow | No change needed. The loop note is the correct treatment. |
| Note | usability | Sidebar carries the "Selected metro" control and the disclaimer next to 6 nav options (line 55). Hick counts navigation options, so the 6-option cap holds. | Hick-Hyman 1952 | None needed. |
| Note | usability | "Hick cap" (line 42) and "Cowan ~4±1" (lines 91, 98) are presented as hard thresholds. Doctrine says laws are tendencies, and Cowan governs memory load, not visible item count. The caps are reasonable conventions. Line 91 and 98 also show "4+-1" where "4 ± 1" is meant. | usability SKILL.md Rules ("Laws are tendencies"); journey.md §D | Keep the caps. Cite them as conventions with Hick and Cowan as rationale. Fix the "+-" typo. |

## Requirement Fulfillment
### DW-1.1
PREMISE:  "JOURNEY.md `## Page specs` has 6 entries, each with purpose, entry points, headline answer, prioritized content blocks, states, and exits."
EVIDENCE: `## Page specs` (line 89) has six `###` entries: 1 Market overview (93), 2 Findings (103), 3 Regional explorer (113), 4 Market profile (123), 5 ML forecast (135), 6 Financing estimator (145). Each has labeled **Purpose**, **Entry points**, **Headline answer**, numbered **Content blocks** in priority order, **States**, and **Exits**. Example, line 99: "7 as-of line ... 8 disclaimer." Count verified: 6.
VERDICT:  PASS

### DW-1.2
PREMISE:  "Metro-persistence flow specified (select, carry, change, invalid/missing metro)."
EVIDENCE: `### Metro persistence flow (DW-1.2)` (line 65) with numbered steps **1. Select** (line 69), **2. Carry** (line 70), **3. Change** (line 71, sidebar "Change" control with ≥24px target), **4. Invalid or missing** (lines 72-83, a 7-row case table covering no-metro market pages, forecast, financing, unknown `?metro=`, metro missing from predictions, short history, Zillow down, manual price with metro).
VERDICT:  PASS

### DW-1.3
PREMISE:  "Every page spec lists its empty/error states (data source down)."
EVIDENCE: Every page has a **States** line. Zillow-down is listed for all six: Overview (line 100), Findings (110), Regional explorer (120), Market profile (132), ML forecast (142), Financing estimator (152). FRED-down is listed on Overview (100), Findings (110), ML forecast (142), Financing (152). Empty states: Findings "Empty tables" (110), Explorer "Filters match nothing" (120), Profile "No metro selected" empty state (132).
VERDICT:  PASS

### DW-1.4
PREMISE:  "Each page spec shows ≤4 headline KPIs above the fold (Cowan ~4±1) and the sidebar lists ≤6 page options (Hick's law)."
EVIDENCE: Headline KPI counts stated in each spec: Overview 4 (line 98), Findings 3 (108), Explorer 3 (118), Profile 4 (130), ML forecast 3 (140), Financing 4 (150). Sidebar table has 6 options (lines 46-51), with group captions explicitly excluded (line 42). Verification notes (lines 157-158) agree.
VERDICT:  PASS

**All requirements met:** YES

## Edge case verification
| Edge case | Verdict | Evidence |
|-----------|---------|----------|
| FRED / Zillow down | PASS | Shared Zillow-down standard (lines 85-87). Per-page Zillow-down states on all six pages. FRED-down on Overview (100, mortgage KPI "n/a"), Findings (110), ML forecast (142), Financing (152). |
| Manual home price with no metro | PASS | Manual $400,000 default plus inline picker (line 78). Dedicated no-metro headline variant "Estimated payment on a $400,000 home (your price): $Y/month..." (line 149). State row (line 152). |
| Metro missing from forecast predictions | PASS | Flow row (line 80). ML forecast state "No forecast for <metro> yet ... falls back to national call" (line 142). Financing equity fallback caption (line 152). Profile unaffected (line 80). |
| Market Profile owned by collaborator | PASS (Minor note) | Spec present (lines 123-133). Analytics logic (metrics, compare, KNN, `analysis.*`) is declared unchanged (line 125). Changes are presentation and wiring only. The summary sentence is broader than the list (see Minor row). Lucas sign-off open (line 159). |

## Notes (non-blocking)
- Earlier review file at this path, which I overwrote, reported a blocker that the Financing no-metro headline is undefined. JOURNEY.md line 149 defines that variant explicitly, so the blocker does not hold. Its other findings on missing loading states for Findings and Profile are also not supported: lines 110 and 132 both list loading.
- No pixel evidence (spec-only phase). All checks are against spec text.
- Copy (headlines, error messages, the placeholder "Zillow data as of Sep 2026", the "<coverage>%" placeholder) is draft. Phase 4 owns final wording (line 3). content-design was not dispatched, so copy quality was not doctrine-reviewed.
- Line 53: the sidebar order differs from the approved wireframe mock. The spec includes a fallback, and the owner-confirmation open item is already listed (line 159).
- Line 159 open items (Lucas sign-off, sidebar reorder, attribution dropped, first-load training) are real open decisions. They are not spec defects.
- Doctrine applied: journey.md (altitude choice, JTBD school named as Moesta, theater flag at line 36 with owner and cadence, no linear-funnel claim, loyalty/messy-middle loop at line 34) and usability SKILL.md (Nielsen 10 walk on the states, Hick, Fitts for the 24px target, Nielsen #1 for loading and system status).

## Issues (if FAIL)
None. No verdict rule is violated. The findings above are Minor or Note level and are not blockers.

**Verdict: PASS**
