# Plan: michiganmen UI/UX refresh

- Date: 2026-10-13
- Track: Standard
- Entry stage: Discover (no DESIGN.md or JOURNEY.md exist)
- **Status:** in-progress
- **Started:** 2026-10-13
- **Current Phase:** done (design); app implementation next
- Seed: `.design-foundations/research/2026-10-13-michiganmen-ui.md`

## Context

**Problem:** Turn the michiganmen Streamlit app from a data notebook into a clean, airy consumer real-estate app (Redfin-like, red and white) that walks the user from the overall market → a specific metro → that metro's forecast and financing, with each page leading with its answer.

**Constraints:**
- Stay in Streamlit: `.streamlit/config.toml` theme + layout + a small injected CSS layer. No framework rewrite.
- Laptop browser widths (≥1280px primary). Mobile is not a target.
- Red = brand/action accent only. Never encodes "down/negative".
- Keep all disclaimers ("estimate, not a loan quote/offer; not financial advice"), every existing page (incl. the user-added Market Profile), and passing pytest/AppTest suites.

**Success criteria:** WCAG AA contrast on all text; one token-driven color/type/spacing system with no stray hex; each page's headline answer visible above the fold; selected metro carries across pages; design-review-agent returns no Critical findings.

## Chosen Approach

Journey first (the market → metro → money flow and per-page headline answers), then lock a red/white DNA in DESIGN.md, then translate it into a Streamlit-shaped design system, with words and chart specs composed in parallel. Mock renders static HTML of two key pages for sign-off before the build touches Streamlit.

## Rejected Approaches
- Custom top navigation bar replacing Streamlit's sidebar — fights the framework (state, routing) for little gain.
- Rewrite in React/Next — out of scope; user chose Streamlit.

## Assumptions
- Selected metro persists in `st.session_state` and the URL query param (`?metro=`), so refresh/bookmarks keep it.
- "Down" = deep slate blue; "up" = calm green; always paired with ▲/▼ and a sign so color is never the only cue.
- Fonts must be web-loadable from Google Fonts (Streamlit supports custom fonts via theme/CSS).

## Decision Log
- 2026-10-13: Red pinned by user; drops use slate blue (avoid red-as-crash). Airy density pinned. Streamlit retained. Metro persists via session + URL.

---

### Phase 1: Journey & page specs
**Stage:** Discover
**Model:** sonnet
**Doctrine:** journey, usability
**Gate:** Standard

**Goal:** Specify the market → metro → money journey and a page spec for each of the six pages, each led by its headline answer.

**Scope:**
- IN: JTBD job story (one school: Moesta Switch forces), IA for the 6 pages (order, labels, grouping), metro-selection flow and persistence, page specs (purpose, entry points, headline answer, content blocks in priority order, states incl. data-source-down, exits).
- OUT: visual styling, copy polish (Phase 4), chart encoding (Phase 5).

**Constraints:** Page order follows the user's stated flow (market first). Hick's law (1952) guides trimming sidebar options; Cowan (~4±1) caps headline KPIs per page.
**Edge cases:** FRED/Zillow down states; manual home price with no metro; metro missing from forecast predictions; Market Profile page owned by a collaborator (spec it, don't redesign its logic).

**Produces:** `JOURNEY.md` — `## Job`, `## Journey`, `## IA`, `## Flows`, `## Page specs` (6 entries).
**Depends on:** research doc | **Unlocks:** Phase 2

**Done when:**
- [ ] DW-1.1: JOURNEY.md `## Page specs` has 6 entries, each with purpose, entry points, headline answer, prioritized content blocks, states, and exits.
- [ ] DW-1.2: Metro-persistence flow specified (select, carry, change, invalid/missing metro).
- [ ] DW-1.3: Every page spec lists its empty/error states (data source down).
- [ ] DW-1.4: Each page spec shows ≤4 headline KPIs above the fold (Cowan ~4±1) and the sidebar lists ≤6 page options (Hick's law).

### Phase 2: Design DNA — red/white identity
**Stage:** Design
**Model:** opus (override: fable unavailable — no usage credits)
**Doctrine:** design-dna, color, fonts
**Gate:** Full

**Goal:** Lock a red/white consumer-real-estate visual identity in DESIGN.md.

**Scope:**
- IN: DNA candidates under the pins, type pairing + scale, color tokens via `palette.mjs` (brand red, neutrals, surfaces, slate-blue negative, green positive, functional colors), airy spacing/radius/elevation scale, signature move, Never list.
- OUT: component specs (Phase 3), chart palettes beyond the semantic up/down pair (Phase 5).

**Constraints (pins, user law):** hue = red; density = airy (Redfin-like); register = clean consumer, not analyst terminal; red never means "down".
**Edge cases:** red accent failing AA for white-on-red buttons → darken solid step; red vs. error color collision → error must be distinguishable from brand red (icon + wording, or shifted hue).

**Produces:** `DESIGN.md` (locked) — `## Type`, `## Color tokens`, `## Space, shape, depth`, `## Never`.
**Depends on:** Phase 1 | **Unlocks:** Phases 3, 4, 5

**Done when:**
- [ ] DW-2.1: DESIGN.md locked (token block present + user-confirmed).
- [ ] DW-2.2: All text/background pairs pass WCAG AA (≥4.5:1 body, ≥3:1 large), verified via `palette.mjs`.
- [ ] DW-2.3: Semantic aliases resolved (`--background`, `--surface`, `--text`, `--accent-solid`, `--positive`, `--negative`); type scale `--text-xs`…`--text-4xl` present; functional colors defined.

### Phase 3: Streamlit design system
**Stage:** Design
**Model:** sonnet
**Doctrine:** design-systems, usability
**Gate:** Standard

**Goal:** Turn DESIGN.md tokens into a Streamlit theme + CSS layer and component specs.

**Scope:**
- IN: token tiers (global → alias → component) mapped to `config.toml` theme keys and CSS variables; components: brand header, headline-answer block, KPI card row, metro picker, sidebar nav, disclaimer callout, warning/info states.
- OUT: final copy (Phase 4), chart internals and tables (Phase 5).

**Constraints:** Only tokens from DESIGN.md; CSS layer targets stable Streamlit selectors/`data-testid`s and degrades to the plain theme if a selector changes.
**Edge cases:** Streamlit theme key limits (single primaryColor) → CSS supplies the rest; focus states for keyboard users.

**Produces:** `## Components` section in DESIGN.md (component tokens + specs) and a theme/CSS mapping table.
**Depends on:** Phase 2 | **Unlocks:** mock, build

**Done when:**
- [ ] DW-3.1: Every component spec references alias/component tokens only — no hard-coded hex.
- [ ] DW-3.2: Interactive elements (buttons, picker, nav) pass AA non-text contrast (≥3:1) with visible focus.

### Phase 4: Words
**Stage:** Design
**Model:** sonnet
**Doctrine:** content-design
**Gate:** Standard

**Goal:** Plain-language headlines, labels, states, and disclaimers for every page spec.

**Scope:**
- IN: page titles, headline-answer templates (e.g. "Austin homes: up 2.1% next year (−1% to +5%)"), metric labels replacing jargon (rank IC, MAE → plain terms with the technical term in a tooltip), empty/error copy (cause + fix, Yifrah), disclaimer wording kept intact in meaning.
- OUT: legal changes to disclaimer substance.

**Produces:** copy blocks in JOURNEY.md `## Page specs`.
**Depends on:** Phases 1, 2 | **Unlocks:** mock, build

**Done when:**
- [ ] DW-4.1: Every page spec has a headline template, labels, and error/empty copy.
- [ ] DW-4.2: Disclaimers present on every page that shows a forecast or financing figure.

### Phase 5: Charts & tables
**Stage:** Design
**Model:** sonnet
**Doctrine:** data-viz
**Gate:** Standard

**Goal:** Specify token-driven, truthful chart and table styling for all pages.

**Scope:**
- IN: a Plotly template (fonts, gridlines, colors from tokens), series palette (colorblind-safe), up/down encoding (green ▲ / slate-blue ▼, never red), range bands for forecasts/equity, table styling (number alignment, zebra-free airy rows), chart-type review per page.
- OUT: new analytics.

**Constraints:** Data-ink first (Tufte 1983); one preattentive attribute per encoding (Knaflic 2015); no dual axes without labels (Cairo 2019).
**Edge cases:** many-series charts (cap highlighted series, grey the rest); negative-only datasets.

**Produces:** `## Data surfaces` section in DESIGN.md (Plotly template spec + table spec + per-page chart list).
**Depends on:** Phases 1, 2 | **Unlocks:** mock, build

**Done when:**
- [ ] DW-5.1: Chart palette passes colorblind check and up/down is redundantly encoded (sign/arrow + color).
- [ ] DW-5.2: Chart text and gridline colors resolve to DESIGN.md tokens; chart text passes AA.

---

## Verification plan
- DW-1.1–1.3: read JOURNEY.md; count 6 page specs; check states per page.
- DW-2.1–2.3: DESIGN.md token block + user lock line; `palette.mjs` output shows all pairs ≥ AA.
- DW-3.1: grep component specs/CSS for `#[0-9a-f]{3,6}` outside the token block → 0.
- DW-3.2: contrast of button/picker borders and focus rings ≥ 3:1.
- DW-4.1–4.2: each page spec has headline/labels/error copy; disclaimer present on forecast/financing/findings/equity surfaces.
- DW-5.1–5.2: palette colorblind simulation; chart text tokens ≥ AA.
- Dirty cases: DESIGN.md missing → Phases 3–5 halt (gate); white-on-red button < 4.5:1 → darken solid step and re-run `palette.mjs`; a page spec lacking a headline answer → Phase 1 not done; any red used for a negative delta → DW-5.1 fails.
- Final: design-review-agent cross-pillar pass on the mock returns no Critical findings; Majors resolved or accepted.

## Execution log

### Phase 1: Journey & page specs (Gate: Standard)
- [x] BUILD: Discovery + design + production complete
- [x] REVIEW: fail->pass (2 attempts)
- [x] Committed
Summary: JOURNEY.md specifies the market → metro → money journey, Market/Metro/Money sidebar order, metro persistence via session + ?metro=, and 6 answer-first page specs with data-down states; Lucas sign-off pending on Market profile presentation changes.

### Phase 2: Design DNA (Gate: Full)
- [x] BUILD: 3 candidates; user locked "Open House"
- [x] REVIEW: PASS
- [x] Committed
Summary: DESIGN.md locked as "Open House" — red #c74248 accent on true white, Newsreader display + Public Sans body, slate-blue negative / green positive, errors distinguished by form (✕ + 'Error:'), data-down uses amber warning; all text pairs AA.

### Phase 3: Streamlit design system (Gate: Standard)
- [x] BUILD: complete
- [x] REVIEW: fail->pass (4 attempts)
- [x] Committed
Summary: DESIGN.md ## Components maps tokens to Streamlit 1.64 theme keys first (fonts via theme URL form, borderColor, radius) and a minimal CSS layer for Roofline, button states, catch-all :focus-visible ring and the react-aria picker list; st.navigation with Market/Metro/Money sections; metric deltas use green/violet/gray (never normal/inverse). Pixel checks pending in build: primary text color, slider :has() rule, aria-selected option, double focus ring on selectbox.

### Phase 4: Words (Gate: Standard)
- [x] BUILD: complete
- [x] REVIEW: PASS
- [x] Committed
Summary: JOURNEY.md Copy blocks per page + ## Voice & tone with shared strings (D1/D2/D3 disclaimers, data-down, loading); Copy blocks are authoritative over older spec fields. Minor follow-ups: unify the 12-month-change label, sign format in overview headline, table column headers, verify D2 'nothing stored' claim at build.

### Phase 5: Charts & tables (Gate: Standard)
- [x] BUILD: complete
- [x] REVIEW: fail->pass (4 attempts)
- [x] Committed
Summary: DESIGN.md ## Data surfaces specifies the michiganmen Plotly template (theme=None), --viz-* tokens, CVD-checked palette with co-occurrence rules, classed symmetric choropleth with auto-contrast state labels, 80% range bands, ≤4 series, and st.column_config tables. Minor follow-ups: equity amber with 2 series, amber/grey dash overlap, NumberColumn ASCII hyphen.
