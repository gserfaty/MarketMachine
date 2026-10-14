# Design Review: Phase 3 - Components (spec-only)

## Rendered Evidence (Step 0)
- Screenshot: none — spec-only phase; no rendered surface exists yet. Structure-level critique only; pixel-level contrast/spacing/hierarchy is unverified and is a coverage gap (see Notes).
- Surface reviewed: `/Users/gabriel/code/michiganmen/DESIGN.md`, section `## Components` (lines 160–361), read against the locked token blocks above it (lines 41–158, not edited) and the JOURNEY.md contract. Installed Streamlit 1.64.0 in `.venv` used to check selectors and theme keys.

## Assessment B — Deterministic Detector
- Command: not run. No rendered `.html`/mock exists in this phase.
- Exit: N/A (no rendered artifact). Carve-out applies; this is not a skipped detector.
- Findings: N/A — no rendered artifact.
- Opened only after Assessment A findings were frozen: N/A

## Triage
- Baseline (always-on): visual + usability.
- Dispatched: `usability` (the component specs are operable controls: buttons, picker, nav, tabs, focus behavior); `design-systems` (the section defines a token tier stack and governance, which is what the doctrine covers). Visual baseline applied to the component specs.
- Not applicable: `data-viz` (charts deferred to Phase 5 per the spec), `content-design` (copy deferred to Phase 4), `journey` and `behavioral`/`deceptive-patterns` (JOURNEY.md is not under review here).
- Deferred (if capped): none.

## Cross-Pillar Findings (ONE ranked report)
| Severity | Pillar | Problem | Principle | Fix |
|----------|--------|---------|-----------|-----|
| Minor | visual | Roofline geometry contradicts itself. Direction (locked) says a 40×4px rule with a 6px rise. The component spec draws a 40×10px box with `clip-path: polygon(0 100%, 50% 0, 100% 100%, …)`, so the apex sits 10px above the ends, not 6px. | Spec-to-build fidelity; the signature move must be one unambiguous shape | Pick one geometry (40×4 with 6px rise, or a 10px box with a 6px apex) and make the polygon match it |
| Minor | design-systems | Alias-tier spacing and radius tokens are re-declared in the component `:root` block (lines 173–175: `--space-*`, `--radius-*`) while the locked block (lines 141–142) already defines them. Two sources of truth for the same values. The tier table also says "no new layer." | Token tier discipline (Frost 2013; DTCG tiers): one definition per tier, components only reference | Delete the duplicate declarations in the component block and reference the locked values |
| Minor | design-systems | The rule "Component tokens are the only layer the CSS rules read" is contradicted by the spec itself. Several CSS rules and component specs read alias tokens directly (`--control-border` on the secondary button, `--surface-hover` on tertiary and expander hover, `--focus-ring`, `--text-secondary`). | Token tier semantics: components consume component tokens, not raw alias tokens | Either add the missing `--c-*` mappings, or relax the sentence to "components read component or alias tokens; never global tokens" |
| Minor | usability | The picker's open-list focus is described as `var(--c-focus-outline)` "inset". CSS `outline` cannot be inset; the outline shorthand has no inset keyword. The build would have to guess. | Implementability of a stated focus treatment (WCAG 2.4.7 visible focus) | Specify `box-shadow: inset 0 0 0 2px var(--focus-ring)` for the highlighted option, or a negative `outline-offset` |
| Minor | usability | Headline-answer sentence is specified as `<h1>` while the page title is also an h1 (Streamlit `st.title`). Two h1 elements per page. | Heading structure for assistive tech (WCAG 1.3.1) | Make the answer sentence a `<p>` or `<h2>`-level element styled with `.mm-answer`, keeping the page title as the only h1 |
| Minor | design-systems | The spec names W3C DTCG as the token format but authors no DTCG (`$type`/`$value`) output; governance has a changelog note but no versioning scheme and no deprecation process. | design-systems doctrine: "governance without … a versioning scheme and a deprecation process is shelfware" | Add a one-line semver rule and a deprecation rule to Governance, or state explicitly that DTCG is a later export step |
| Minor | usability | Focus catch-all `[data-testid="stAppViewContainer"] :focus-visible` plus the explicit `input` hook can paint two rings on one selectbox (wrapper and inner input). Cosmetic only. | Consistency (Nielsen #4); avoid redundant cues | Scope the `input` hook to exclude elements already covered by the wrapper rule, or verify in the build screenshot |
| Note | usability | The sidebar-contains-focus claim ("this includes the sidebar, which is inside it") is asserted, not verified against the 1.64.0 DOM. The `:has()` slider-thumb rule is also flagged in the spec itself as unconfirmed. | Selector correctness (degrade rule covers failure) | Confirm both in the build screenshot, as the spec already requires |

Contrast ledger (DW-3.2) and token-only check (DW-3.1) produced no Critical or Major findings. Detail is in the requirement section.

## Requirement Fulfillment

### DW-3.1
PREMISE:  "Every component spec references alias/component tokens only — no hard-coded hex."
EVIDENCE: Pattern search over DESIGN.md lines 160–361 (the Components section) for `#[0-9a-fA-F]{3,8}`, `rgb(`, `rgba(`, `hsl(`, `hsla(` returned 0 matches. Search for global-tier references (`--neutral-*`, `--accent-<digit>`, `--green-*`, `--blue-*`, `--error-<digit>`, etc.) inside the Components section returned 0 matches; components reference only alias names (`--accent-solid`, `--control-border`, `--surface-hover`, `--text-secondary`, …) and component tokens (`--c-*`). Every `var(--…)` referenced in the section is defined somewhere in the document (no dangling references). The only hex values in the document are in the locked blocks above line 160 and in the "Project overrides" block, which are out of scope for this item. Literal non-color dimensions (`40×10px`, `2px`, `2.5rem`, `4px`, `150ms`) appear in component tokens; these are not hex and the requirement does not cover them.
VERDICT:  PASS

Note on evidence: the Components section itself states that hex appears only in the generated `.streamlit/config.toml`, and the theme-key table (lines 268–280) maps to token names, not values. Consistent with the requirement.

### DW-3.2
PREMISE:  "Interactive elements (buttons, picker, nav) pass AA non-text contrast (≥3:1) with visible focus."
EVIDENCE: I recomputed the WCAG 2.x ratios from the locked hex values (neutral and accent ramps and the project overrides, lines 41–140) with the standard relative-luminance formula. My values match the spec's ledger to ±0.01 for every pair I checked:
- `--control-border` (neutral-9 #948584) on `--background` (#fdfcfc): 3.45 (≥3 PASS). On `--surface` (#faf8f8): 3.34 PASS. On `--surface-hover` (#f3efef): 3.09 PASS.
- Primary fill `--accent-solid` (accent-10 #c74248) on `--background`: 4.77 PASS. Primary text `#ffffff` on that fill: 4.88 (≥4.5 PASS). Primary hover fill accent-11 #974847 on background: 6.15 PASS; white on hover: 6.30 PASS.
- Tertiary link text accent-11 on background: 6.15 PASS; on `--surface`: 5.95 PASS.
- Nav active bar accent-10 on `--surface`: 4.61 PASS. Nav active text accent-11 on `--accent-bg-subtle` (accent-3 #ffebea): 5.50 PASS. Nav item text `--text` (neutral-12) on `--surface`: 12.87 PASS.
- Focus ring `--focus-ring` (accent-10) on background 4.77, on `--surface` 4.61, on `--surface-hover` 4.28, on `--surface-active` (neutral-4 #ece6e6) 3.96, on `--accent-bg-subtle` 4.26. All ≥3 PASS.
- Secondary pressed border `--text-secondary` (neutral-11) on `--surface-active`: 4.89 PASS.
- Tab selected bar accent-10 on background: 4.77 PASS. Unselected tab text neutral-11 on background 5.89 PASS, on hover fill 5.29 PASS.
- Visible focus: the spec defines a 2px `--focus-ring` with 2px offset on every focusable class (buttons, nav links, tabs, expander summary, selectbox, multiselect, inputs, slider thumb, checkbox, radio) through a catch-all `:focus-visible` rule plus named hooks. All class selectors named in the spec (`stBaseButton-*`, `stSidebarNavLink`, `stTab`, `stExpander`, `stSelectbox`, `stMultiSelect`, `stSlider`, `stCheckbox`, `stRadio`, `stAlertContainer`, `stMetric`, `stSelectboxVirtualDropdown`, `stTabPanel`) were grep-confirmed in `.venv/lib/python3.13/site-packages/streamlit/static` for Streamlit 1.64.0.
- Known gap owned by the spec, not a failure: the sidebar-inside-`stAppViewContainer` nesting and the slider `:has()` thumb rule are not verified against the DOM. The spec says to confirm both in the build screenshot and provides a fallback.
- Disabled controls (metro picker "Metro list unavailable", disabled primary text) are exempt under WCAG 1.4.11 and the spec says they must read as unavailable through label text. Recorded as exempt, not as a failure.
VERDICT:  PASS

**Edge case — Streamlit theme key limits (single `primaryColor`):** handled. The spec routes `primaryColor` to `--accent-solid` for the resting fill only, and supplies CSS for primary hover, pressed, disabled and on-fill text (`[data-testid="stBaseButton-primary"]`), secondary pressed and disabled, tabs, the picker list, and the Roofline. Every CSS rule is marked as standing alone (degrade rule). Verdict: handled, PASS.

**Edge case — Focus states for keyboard users:** handled. Keyboard-only `:focus-visible` ring defined in `--c-focus-outline`, a catch-all covering every focusable element, named hooks where Streamlit overrides outlines, the picker highlighted-option treatment distinct from hover, and a 2px ring that is not clipped by the sidebar scroll area (`--space-2` inner padding). Verdict: handled, PASS. The Minor implementability issue on the picker inset ring is listed in Cross-Pillar Findings and does not make the edge case unhandled, because the state is specified with a color and a weight and the highlight remains distinct from hover.

## JOURNEY.md consistency (check of the contract, not a separate requirement)
- Change target ≥24px (JOURNEY Flows) vs component min-height 2rem (32px): consistent.
- Disclaimer "in the footer and next to any forecast or financing headline" (JOURNEY) vs disclaimer callout placement (Component 6): consistent.
- Zillow-down "Try again" (JOURNEY) vs warning callout with secondary "Try again" button (Component 7): consistent.
- Error reserved for real failures; warning for data-source-down (JOURNEY) vs Component 7 table: consistent.
- Max 4 headline KPIs (JOURNEY) vs `st.columns(n)`, n ≤ 4 (Component 3): consistent.

**All requirements met:** YES

## Notes (non-blocking)
- **Coverage gap, pixel evidence:** no screenshot exists (spec-only phase). All contrast verdicts are computed from token values, not measured on rendered pixels. Verification of the focus rules, the Roofline, and Streamlit DOM nesting belongs in the build-phase screenshot, which the spec already requires.
- **Usability doctrine, heuristic check (against the spec, not the pixels):** Fitts (1954) — nav items 40px, change target 32px, tabs 40px: adequate. Hick (1952) — 6 nav items, one primary per region: within cap. Nielsen #9 — warning/error use `role="alert"` by Streamlit default: adopted. Nielsen #1 — active nav carried by bar and weight, not fill alone: adopted. Nielsen #4 — primary reserved for brand and action; red never used for "down": consistent with DESIGN.md Usage rules.
- **Signature move:** the Roofline is decorative (`::before`, aria-hidden is not applicable to generated content). Not a defect, but the spec wording should not claim an aria attribute the browser ignores.
- **Systematic caveat:** the sidebar readout's uppercase group captions are said to come from "theme default"; Streamlit's sidebar group captions are not verified to be uppercase. Cosmetic, confirm in build.
- The picker's disabled state is exempt from 1.4.11 by WCAG; the spec correctly keeps the label text as the unavailable cue.

## Issues (if FAIL)
None. No blocker survived verification.

**Verdict: PASS**

DESIGN-REVIEW PASS. Report written to /Users/gabriel/code/michiganmen/.design-foundations/build/2026-10-13-michiganmen-ui-phase-3-review.md
