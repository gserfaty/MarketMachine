# Discovery + Design: Phase 3 - Streamlit design system

## Artifacts Found / Current State
- DESIGN.md locked (Open House). JOURNEY.md present. `.streamlit/config.toml` has the old blue theme (`#2E86AB`, "sans serif"): to be replaced at build, not now.
- `app.py` uses `st.sidebar.radio` for nav (no groups, no `aria-current`). Streamlit 1.64.0 in `.venv`.

## Gaps
- No component tier, no theme mapping, no focus spec. `--border` tokens are decorative only, so controls need `--control-border` (handled).
- Native `st.metric` colors a negative delta red by default (`delta_color="normal"`): would break "red never means down". Resolved by named colors (green / violet / gray) and theme color families.

## Gate Status
DESIGN.md locked: YES (append-only used). JOURNEY.md present: YES. Prerequisites met.

## DW Verification
| DW-ID | Done-When Item | Status | Evidence |
|-------|---------------|--------|----------|
| DW-3.1 | Component specs use alias/component tokens only | COVERED | grep for hex inside `## Components` of DESIGN.md returns 0 matches |
| DW-3.2 | Interactive elements >= 3:1 non-text, visible focus | COVERED | Contrast ledger in DESIGN.md (all >= 3.09), focus spec 4.26 to 4.77, computed with the WCAG formula from locked tokens |
**All items COVERED:** YES (2 of 2)

## Design Decisions
- Theme-first (Frost/DTCG tiers): 25+ theme keys carry color, type, radius, borders; CSS is limited to page width, KPI card padding, nav active state, alert left bar, focus ring, and our own `.mm-*` components.
- Fonts via the theme's `<name>:<css url>` form, not CSS `@import`. Headings via `headingFont`.
- Color families (red/yellow/blue/green/violet/gray) are used as semantic slots so native alerts and metric deltas follow DESIGN.md without CSS. Violet = negative delta.
- Nav: `st.navigation` sections (native `aria-current`, groups) instead of a radio. Active state = bar + weight + fill (Norman: not color alone).
- Focus: one 2px `--focus-ring` outline, 2px offset, for all interactive elements (Streamlit's default tinted ring is not guaranteed 3:1).
- Cited: Frost 2013, DTCG, Fitts 1954, Hick, Cowan, Jakob 2000, Norman, Nielsen #1/#4/#9, WCAG 1.4.11, 2.4.7, 2.4.11, 2.5.8.
- Risks to verify at build: Streamlit's on-primary text color; `borderColor` also affecting dataframe borders (dataframeBorderColor can be set separately); `data-baseweb="select"` hook is not a testid.

## Reference config.toml (hex copied from DESIGN.md tokens; build phase writes this)
```toml
[theme]
base = "light"
primaryColor = "#c74248"            # --accent-solid
backgroundColor = "#fdfcfc"         # --background
secondaryBackgroundColor = "#faf8f8"  # --surface
textColor = "#312d2c"               # --text
linkColor = "#974847"               # --accent-text
linkUnderline = true
font = "Public Sans:https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;600&display=swap, system-ui, sans-serif"
headingFont = "Newsreader:https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,600&display=swap, Georgia, serif"
headingFontSizes = ["2.25rem", "1.5rem", "1.25rem", "1.25rem", "1.25rem", "1.25rem"]
headingFontWeights = [600, 600, 600, 600, 600, 600]
baseFontSize = 16
metricValueFontSize = "1.875rem"
metricValueFontWeight = 600
baseRadius = "6px"
buttonRadius = "6px"
borderColor = "#948584"             # --control-border
showWidgetBorder = true
showSidebarBorder = true
redColor = "#974843"                # error family
redTextColor = "#974843"            # --error-text
redBackgroundColor = "#ffebe9"      # --error-bg
yellowColor = "#76602f"
yellowTextColor = "#76602f"         # --warning-text
yellowBackgroundColor = "#f9f0dd"   # --warning-bg
blueColor = "#3d6886"
blueTextColor = "#3d6886"           # --info-text
blueBackgroundColor = "#e3f3ff"     # --info-bg
greenColor = "#35742f"
greenTextColor = "#35742f"          # --positive
greenBackgroundColor = "#e0f9dd"    # --positive-bg
violetColor = "#41629f"
violetTextColor = "#41629f"         # --negative
violetBackgroundColor = "#e9f1ff"   # --negative-bg
grayColor = "#696160"
grayTextColor = "#696160"           # --text-secondary

[theme.sidebar]
backgroundColor = "#faf8f8"         # --surface
secondaryBackgroundColor = "#fdfcfc"  # --background
headingFont = "Public Sans"
```
(Check at build that `base = "light"` plus these keys render `st.error` as bar + container; the `theme.*` color keys here match the 1.64.0 `config.py` list.)

## Recommendation
BUILD (done): `## Components` appended to DESIGN.md.
