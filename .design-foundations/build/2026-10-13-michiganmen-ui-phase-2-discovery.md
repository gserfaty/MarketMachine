# Discovery + Design: Phase 2 - Design DNA (red/white identity)

## Artifacts Found / Current State
- No DESIGN.md. JOURNEY.md exists (Phase 1, done).
- `.streamlit/config.toml` uses the old theme (`primaryColor = "#2E86AB"`, `font = "sans serif"`). Phase 3 replaces it. This phase does not touch app code.

## Gaps
- `palette.mjs` maps `--accent-solid` to step 9. For a red seed, step 9 sits at the hue's cusp lightness, so white text fails on it (3.8 to 4.0:1). Because of that, the script picks near-black `on-solid` text. Fix: `--accent-solid` uses step 10 and white `--on-accent`. This is the edge case's "darken solid step" fix.
- `palette.mjs` puts its functional `error` at hue 25. That is the brand red. `error-11` is #974843 and `accent-11` is #974847, so the two cannot be told apart by color. Fix: errors are told apart by form and wording (rule below), not by color.
- `palette.mjs` does not emit `--positive`, `--negative`, `--on-accent`, or a type scale. These are added as aliases in DESIGN.md. The extra pairs are checked with the same WCAG 2.x formula (scratchpad `cr.mjs`).
- `--border-strong` (neutral-8) is only 2.27:1 on the background, so it fails non-text 3:1. Input and control borders use `--control-border` (neutral-9, 3.45:1). This feeds Phase 3, DW-3.2.

## Gate Status
- DESIGN.md: not locked. Written as **DRAFT**. The user must pick and lock it (DW-2.1).
- JOURNEY.md: present. Prerequisites are met.
- Pins honored on all 3 candidates: hue red, airy density, clean consumer register, red never means "down". Negative is slate blue and positive is green, always shown with ▲/▼ and a sign.

## DW Verification
| DW-ID | Done-When Item | Status | Evidence |
|-------|---------------|--------|----------|
| DW-2.1 | DESIGN.md locked (token block + user-confirmed) | COVERED (token block + DRAFT). The lock is pending the user | DESIGN.md has the verbatim `palette.mjs` CSS (seed 22, balanced, triadic, exit 0). The orchestrator gets the user's pick and lock |
| DW-2.2 | All text/bg pairs pass WCAG AA | COVERED | `palette.mjs` report: 8/8 PASS, exit 0. Extra pairs (table below): all ≥4.5:1 text and ≥3:1 non-text |
| DW-2.3 | Semantic aliases, type scale xs..4xl, functional colors | COVERED | DESIGN.md `## Color tokens` (aliases), `## Type` (`--text-xs`…`--text-4xl`), functional error/success/warning/info |

**All items COVERED:** YES (DW-2.1's lock depends on the user)

### Extra contrast evidence (recommended palette, light; `cr.mjs`, WCAG 2.x)
| Pair | Ratio | Target |
|---|---|---|
| #ffffff on accent-10 #c74248 (`--on-accent` on `--accent-solid`) | 4.88 | 4.5 |
| #ffffff on accent-11 #974847 (hover) | 6.30 | 4.5 |
| neutral-12 on neutral-1 (`--text` on `--background`) | 13.30 | 4.5 |
| neutral-11 on neutral-1 / neutral-3 (`--text-secondary`) | 5.89 / 5.29 | 4.5 |
| accent-11 on neutral-1 / accent-3 | 6.15 / 5.50 | 4.5 |
| green-11 on neutral-1 / green-3 (`--positive`) | 5.56 / 5.08 | 4.5 |
| blue-11 on neutral-1 / blue-3 (`--negative`) | 5.91 / 5.32 | 4.5 |
| error-11 / warning-11 / info-11 / success-11 on their step-3 | 5.51 / 5.32 / 5.26 / 5.05 | 4.5 |
| accent-10 on neutral-1 (focus ring, non-text) | 4.77 | 3.0 |
| neutral-9 on neutral-1 (`--control-border`) | 3.45 | 3.0 |
| neutral-8 on neutral-1 (`--border-strong`): **decorative only** | 2.27 | n/a |

White-on-solid for the other candidates: B #ffffff on #df0025 = 5.04:1. C #ffffff on #ae5b5f = 4.71:1.

## Design Decisions — Diverge (3 candidates; the hue is pinned, so they differ on type, chroma, and signature)
Grounding for all three: Redfin is the primary reference (research brief), and each candidate adds a second reference from outside it. Composition is the same for all: airy, a single column under the headline, white surfaces (pinned). The dealer was not run because density and register are pinned and this is a cheap diverge.

```
## Open House  (RECOMMENDED)
GROUNDING   Redfin's airy white listing surfaces + a newspaper real-estate section's serif headline sentence
            The answer-first pages (JOURNEY) read as one plain sentence, so the headline gets the serif voice and data gets a sober sans.
TYPE        Newsreader (display, 500/600, opsz) over Public Sans (body/UI, 400/600, tabular-nums) — editorial answer, civic-plain data
COLOR       seed red h22 · balanced · white bg · triadic (green 142 = positive, blue 262 = negative) · swatches: #c74248 (solid) #974847 (text) #ffebea (subtle) #35742f (+) #41629f (−)
COMPOSITION airy single column, 1.25 scale, 8px radius cards, hairline borders, low hue-shifted shadow
MOTION      state-only, 150ms ease-out; no chart animation
REGISTER    calm structure · expressive at: page headline answer (modest)
DNA         clean-consumer base + type voice borrowed from editorial · dominant: type voice
SIGNATURE   "Roofline": a 40×4px red chevron rule (a shallow roof peak) above every page's headline-answer sentence; nowhere else
```
Critique: Strongest: the serif answer sentence makes "lead with the answer" visible and uncommon for Streamlit. Weakest: serif plus warm red sits near the cream/serif/terracotta AI-tell cluster. That is avoided only if the background stays true white and the red stays crimson rather than terracotta, so keep `--background` #fdfcfc and never add a cream tint. Tells: none hit (it does not use Inter/Roboto, and it has no card grid).

```
## Yard Sign
GROUNDING   Redfin's red-on-white action buttons + a real-estate yard sign's bold rider panel
            Loud, confident signage energy for a consumer who wants a quick verdict.
TYPE        Bricolage Grotesque (display, 700, condensed opsz) over Figtree (body 400/600) — punchy, friendly
COLOR       seed red h25 · vivid · white bg · triadic · swatches: #df0025 (solid) #a93433 (text) #ffebe9 (subtle) #03791f (+) #365cbb (−)
COMPOSITION same airy column (pinned)
MOTION      state-only, 150ms; button press scale 0.98
REGISTER    calm structure · expressive at: headline answer + primary CTA (medium)
DNA         clean-consumer base + type voice from signage · dominant: color
SIGNATURE   "Sign rider": each headline answer card has a solid red tab on its top-left edge with the step label in white caps ("1 · MARKET")
```
Critique: Strongest: the most memorable, and the closest to Redfin's energy. Weakest: vivid #df0025 is very hot for a money/forecast context. Ch09 says red dominance hurts analytical calm, and on the forecast page the red tab could read as alarm. Tells: two sans faces with no serif pairing. That is defensible (display vs body roles) but only moderately distinct.

```
## Quiet Listing
GROUNDING   Redfin's whitespace + a Swiss transit timetable's single-family tabular discipline
            The most restrained: numbers carry the page, and red is rationed.
TYPE        Schibsted Grotesk only (400/500/700, tabular-nums) — one family, hierarchy by size and weight
COLOR       seed red h18 · muted · white bg · triadic (lime 138 = positive, blue 258 = negative) · swatches: #ae5b5f (solid) #865354 (text) #ffebeb (subtle) #4e6d44 (+) #4e6485 (−)
COMPOSITION same airy column (pinned)
MOTION      none beyond Streamlit defaults
REGISTER    calm structure · expressive at: none (accent scarcity is the expression)
DNA         clean-consumer base + type voice from Swiss timetable · dominant: type voice
SIGNATURE   "Rationed red": red appears ONLY on the primary button and the active sidebar nav marker. Headlines, links, and charts stay neutral
```
Critique: Strongest: the calmest. It suits forecasts and money, and it leaves no chance of red reading as "down". Weakest: muted #ae5b5f drifts to dusty rose or brick. It barely satisfies the "red and white" pin and loses Redfin's crispness. Tells: low risk. The muted positive leans lime, so it is weaker than green as an "up" cue.

### Recommendation rationale
Open House keeps a recognizably red brand at a calmer chroma than Yard Sign, which suits forecast and financing pages. Its serif answer sentence directly expresses the JOURNEY "lead with the answer" spec. Swaps the user could make when locking: Yard Sign's sign-rider signature on Open House's palette, or Quiet Listing's red rationing as a usage rule.

### Error vs brand red (edge case)
Errors are never shown by red color alone. An error = an `--error-bg` tinted container + a 4px `--error-text` left border + a ✕ icon + the wording "Error:" or "Couldn't …". Brand red is never used as a tinted container with a left border; `--accent-bg-subtle` is reserved for the active nav item. "Data source down" states use **warning** (amber), not error.

## Recommendation
BUILD. DESIGN.md is written as DRAFT (Open House). It needs the user to pick and lock it.
