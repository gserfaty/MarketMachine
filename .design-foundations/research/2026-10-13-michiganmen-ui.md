# michiganmen UI/UX refresh — design brief

**Summary:** Restyle the michiganmen Streamlit app from a data-notebook look into a clean, airy consumer real-estate app (Redfin-like) in red and white, organized around a market → metro → money flow.

- Date: 2026-10-13
- Status: **draft**

## Open questions
- Visual identity / design DNA: no existing logo, typeface, or exact red. Resolve in planning (pick a specific red, type, spacing scale).
- Exact neutral/blue used for "down / negative" values in charts and deltas.
- How far Streamlit theming + custom CSS can go before it fights the framework (sidebar nav vs. top nav, metric cards, tables).
- Whether the selected metro should persist across page reloads (URL query param) or only within a session.

## What
A US housing-market analytics app (Streamlit): pages for Market overview, Regional explorer, ML forecast, Findings, Market Profile, and Financing estimator (fixed + ARM loans, equity projection). Data and ML already exist; this work changes presentation and flow, not models.

## Who
Two users: Gabriel (owner) and co-collaborator Lucas. Laptop browser, focused sessions.

## Job to be done
"Tell me how the housing market is doing, then how a specific metro is doing, then what it would cost to finance a home there and whether it's likely to gain value."

Today every page starts from scratch, leads with tables and long scrolls, and stacks metrics one per line; the answer is buried.

## Primary flow (drives information architecture)
1. **Overall market** first (home screen).
2. **A specific metro** next.
3. **ML forecast / financing** for that metro last.

Implications:
- The selected metro should carry across pages (pick once; forecast and financing already show it).
- Each page leads with its headline answer (e.g. "US market: up +1.3% next 12 months (0% to +3.6%)"), detail below.

## Brand & mood
- Feel: clean consumer app — Redfin / Zillow, not an analyst terminal.
- Color: **red and white**. Red = brand and action/accent (headers, primary buttons, highlights). White, generous surfaces.
- **Red must NOT mean "down."** Negative values / price drops use a neutral gray or deep blue; positive can use a calm green or the default text color. Avoids every chart reading as a crash.

## Taste signals
- Airy and spacious like Redfin listings — generous whitespace over density.
- Red/white palette (pin).
- Consumer-friendly, plain-language labels over jargon.

## Constraints
- Stay in **Streamlit** (theme via `.streamlit/config.toml`, layout, custom CSS). No rewrite to another framework.
- Primary surface: laptop browser (desktop widths); mobile is not a target.
- Must keep existing disclaimers ("estimate, not financial advice").
- Existing tests (pytest + Streamlit AppTest) must keep passing; don't break the user-added Market Profile page.

## References
- Redfin (primary feel reference), Zillow (secondary).
