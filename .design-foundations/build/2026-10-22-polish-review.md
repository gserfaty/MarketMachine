# Design Review (3rd pass): polish, 2026-10-22
Live app http://localhost:8597 at 1280x800, all six pages re-rendered after restart. Assessment B: N/A (Streamlit JS shell, no static .html).

## Requirements
- P1 PASS. Headline sentences (overview, forecast "▼ −2.6%", explorer, profile "▼ −4.3%", affordability "▲ +7.4%") show arrow + sign, green/slate blue, none red.
- P2 PASS. Equal heights: overview 4x171 (was 204), forecast 3x134, explorer 3x147, profile 4x121, financing 4x134, affordability 4 equal. No truncation/wrap ("273 of 389", "$2,966").
- P3 PASS. No legend overlaps. Overview defaults to last 10 years (2016-09..2027-11), band 56x24px + legend label. Explorer/profile axes end 2026-11. /forecast ends 2027-11.
- P4 PASS (direct /forecast?metro=Austin,%20TX has no "from Market overview"; overview-picked path verified pass 1).
- P5 PASS. "Top markets" below main blocks, disclaimer right under headline.
- P6 PASS. Exactly 6 nav items; /findings loads and lands on "/" (Market overview).
- P7 FAIL (one item). DOM text audit passes everywhere (min 4.89:1); slider tick labels now #696160 (~6.3:1, fixed). But the Regional explorer dataframe "Metro" column is canvas text whose darkest pixel samples as rgb(131,128,127) (~3.9:1 on white), visibly lighter than State/number columns. Not fixed on /explorer (profile's Similar markets table is now dark and fine).

## Remaining findings
| Sev | Page | Problem | Principle | Fix |
|---|---|---|---|---|
| Major (blocks P7) | /explorer Ranked regions | Metro column (index) rendered in grey ~3.9:1 | WCAG 1.4.3 | `st.dataframe(..., hide_index=True)` with Metro as a normal column (as done on /profile), or set the grid text color |
| Minor | /explorer Filters | "Home value range" slider shows raw "147374.95 / 1523615.44" | Content-design | `format="$%d"` |
| Minor | /profile Similar markets | Deltas use ASCII hyphen "-2.1%" and no arrow, unlike "−"/▲▼ elsewhere | Consistency (Nielsen #4) | Use the shared signed formatter |

## Previous findings status
1 slider tick contrast: FIXED. 2 financing equity table: FIXED (9 numeric columns fit at 1280, no scroll/clipping). 3 profile Metro column: FIXED (no clipping, dark). 4 overview KPI height: FIXED (171px). 5 affordability income: FIXED (caption "$100,000 per year"). 6 explorer first column: NOT fixed. /forecast minus: FIXED ("−0.1 points", 0 ASCII minus).

**Verdict: FAIL** (single blocker: explorer Metro column contrast).
