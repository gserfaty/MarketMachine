# JOURNEY.md

The structural and temporal spec for michiganmen. For visual tokens, see DESIGN.md (Phase 2, not yet written). Phase 4 copy blocks (per page, plus `## Voice & tone`) are the final wording and supersede draft strings elsewhere in this file. Chart encoding is Phase 5. Specs describe the target UI; "Today" notes mark what the code does now (`app.py`, `housing/pages.py`).

## Job

**Job story (Moesta / Switch school):** When I am thinking about buying, selling, or investing in a home, I want to see how the US market is doing, then how one specific metro is doing, then what it would cost to finance a home there and whether it is likely to gain value, so I can decide whether and where to look further.

- **Functional job:** get a plain answer at each step (market, metro, forecast, payment) without reading tables.
- **Emotional job:** feel oriented and un-overwhelmed; trust the number because its uncertainty is stated.
- **Social job:** be able to say "here is why" to a partner, agent, or collaborator.

**Switch forces** (inferred from the owner's brief, not interviewed):
- Push: today every page starts from scratch, leads with tables and long scrolls, and the answer is buried.
- Pull: Redfin-like clarity; each page opens with its answer; pick a metro once.
- Anxiety: "Is a forecast trustworthy?" "Is this a loan quote?" Mitigation: state the 80% range, the track record, and the disclaimers.
- Habit: spreadsheets and Zillow/Redfin listing pages; the sidebar-of-pages notebook feel.

**JTBD school used:** Moesta. Users: Gabriel (owner) and Lucas (collaborator); laptop, focused sessions.

## Journey

**Actor:** home buyer / market watcher using michiganmen on a laptop (>=1280px).
**Scenario:** understand the market, choose a metro, check its forecast, estimate financing.
**Scope:** current app, future-state UI. Mobile out of scope.

| Phase | Page(s) | User action | Mindset | Emotion | Opportunity |
|-------|---------|-------------|---------|---------|-------------|
| 1 Market | Market overview, Findings | Read the headline; scan leaders | "Is now a good time?" | Curious, mildly anxious | Answer in one sentence; "Next: pick a metro" |
| 2 Metro | Regional explorer, Market profile | Find or compare metros; choose one | "Where should I look?" | Exploring (messy middle: explore <-> evaluate loop, Google 2020) | Pick once, carry everywhere |
| 3 Forecast | ML forecast | Read the forecast and how reliable it is | "Can I trust this?" | Skeptical | Range and track record up front |
| 4 Money | Financing estimator | Set price/down payment; read monthly payment and equity | "Can I afford it, will it grow?" | Decisive, wary of being sold to | Payment first; clear "not a quote" |

The path is not a funnel: users loop between metro and forecast/financing (switch metro, re-check). Return loop: re-check monthly when Zillow data refreshes.

**Theater flag (journey-caveats):** this map comes from the owner's stated flow, not user research. Owner: Gabriel. Cadence: revisit at each design-phase gate and after first real use by Lucas. Treat as hypothesis.

## IA

**Structure:** hub-and-spoke on a shared "selected metro" spine; flat global navigation (Rosenfeld/Morville: global nav + contextual nav). **Organization scheme:** task/stage (ambiguous scheme), ordered by the stated flow.

**Sidebar (global nav): 6 options, at or below the Hick cap (Hick-Hyman 1952).** Non-interactive group captions are not options. Labels in sentence case.

| # | Group caption | Label | Today's label / position |
|---|---------------|-------|--------------------------|
| 1 | Market | Market overview | same, position 1 |
| 2 | Market | Findings | was 4 (moved up: market-wide rankings help choose a metro) |
| 3 | Metro | Regional explorer | was 2 |
| 4 | Metro | Market profile | was 5, "Market Profile"; page header was "Market Profiles" |
| 5 | Money | ML forecast | was 3 |
| 6 | Money | Financing estimator | same label, was 6 |

Note: order differs from the approved wireframe mock (which kept today's order). Needs user confirmation; if rejected, fall back to today's order with no loss to the other specs.

**Sidebar also carries (not nav options):** brand, the "Selected metro" control (see Flows), and the one-line disclaimer. Home screen = Market overview.

**Labeling:** plain words over jargon; technical terms (MAE, rank IC, bias) only inside tooltips or the methodology expander (Phase 4). Validation: no card sort or tree test run; 6 flat items make a tree test low-value, but confirm labels with Lucas.

## Flows

### Primary task flow

Market overview (headline) -> choose metro (picker on "Next" block) -> ML forecast (that metro) -> Financing estimator (that metro). Side paths: Findings and Regional explorer help choose the metro; Market profile compares it.

### Metro persistence flow (DW-1.2)

Source of truth: `st.session_state["metro"]` (a `region` string exactly as in the Zillow metro data, e.g. "Austin, TX"), mirrored to the URL `?metro=Austin%2C%20TX`. Never put anything but the region name in the URL.

1. **Select.** Any metro picker (overview "Next" block, sidebar control, Explorer "Region history" in Metro mode, Market profile selector, Financing "Metro", forecast header) sets the state. The picker defaults to a "Choose a metro..." placeholder when state is empty (no silent default like "largest metro").
2. **Carry.** On every page load: read state; if empty, read `?metro=`; validate; write back to both. All metro-aware pages (Market profile, ML forecast, Financing estimator) open on the carried metro without asking again. Overview, Explorer, Findings show it in the sidebar and offer it as the next-step target.
3. **Change.** The sidebar "Selected metro" block shows the name and a "Change" control with a click target >= 24px (WCAG 2.2 SC 2.5.8; Fitts 1954); changing it updates state and URL and re-renders the current page. The readout renders from state, not from a widget, so it always equals the picker (fixes mock-review finding: "None yet" shown beside a filled select). Page-local compare selectors (Market profile "Compare with") are NOT persisted.
4. **Invalid or missing.**

| Case | Behavior |
|------|----------|
| No metro, market-level page | Page works fully; sidebar says "No metro selected"; next-step block asks to choose one |
| No metro, ML forecast | Page leads with the national 12-month call plus an inline picker "Choose a metro to see its forecast"; not blocked |
| No metro, Financing | Price source = Manual at the existing $400,000 default, plus an inline "or choose a metro" picker; equity series defaults to United States |
| Metro in `?metro=` not in the Zillow metro list (typo, stale bookmark, "United States") | Clear state, show a one-line notice "We couldn't find '<value>'. Choose a metro.", page renders as "no metro" |
| Metro valid in ZHVI but absent from forecast predictions | ML forecast shows a notice "No forecast for <metro> yet (not enough history)", falls back to the national call; Financing equity already falls back to United States with a caption; Profile unaffected |
| Metro has < `MIN_HISTORY_MONTHS` history | Same as above for equity (existing behavior) |
| Zillow data down | Metro list cannot load: pickers are disabled with "Metro list unavailable"; state kept but not validated (do not wipe it on a transient outage); Financing falls to Manual price |
| Manual home price with metro selected | Price is the user's number; metro still drives state/tax defaults and the equity series; label "Using your price, <metro> growth" |

### Data-source-down flow (shared)

**Zillow-down standard (every page):** (1) message states cause and fix, e.g. "We can't reach Zillow's home-value data right now. Check your connection or try again in a few minutes."; (2) a visible "Try again" button that clears the cached load and reruns; (3) metro pickers and metro-dependent controls are disabled ("Metro list unavailable"); (4) the page body below the message stops (`st.stop()`, existing pattern) except where its spec says it degrades; (5) the sidebar and disclaimer still render. Pages below say "Zillow-down standard" plus their page-specific part. FRED down: page degrades, never stops (existing for mortgage/SOFR). Zillow listings (supply) down: forecast runs, with a warning.

## Page specs

Shared rules for all six: headline answer is the first element under the page title; <=4 headline KPIs in the first row above the fold (Cowan ~4+-1; laptop fold ~ 720px); the disclaimer ("Forecasts are statistical estimates, not financial advice.") is on every page, in the footer, and also next to any forecast or financing headline; Financing keeps its extended "not a loan quote or offer" notice. Every forecast interval is labeled "80% range".

### 1. Market overview

- **Purpose:** tell the user in one sentence how the US market is doing, then hand off to choosing a metro.
- **Entry points:** app home (default page); sidebar; brand link.
- **Headline answer:** "US home values: up 1.2% over the past year; forecast +1.3% next 12 months (80% range 0% to +3.6%)." Named data month: "Zillow data as of Sep 2026." Today: no headline; the forecast figure requires the trained model (cached; first load shows a "Training forecast model" spinner). If forecast unavailable: "US home values: up 1.2% over the past year" only.
- **Headline KPIs (above the fold), 4:** Typical home value; Year over year (arrow + sign); 30-year mortgage rate (with 12-month change); Case-Shiller YoY with caption "different index method than Zillow" (explains why two YoY figures differ).
- **Content blocks (priority order):** 1 headline + one-line takeaway; 2 KPI row; 3 home-value chart with forecast band; 4 "Next: pick a metro" block (picker + "See this metro's forecast" CTA); 5 YoY vs mortgage rate chart (today a dual axis; Phase 5 decides); 6 Case-Shiller chart; 7 as-of line (Zillow month, FRED month); 8 disclaimer.
- **States:** *Zillow down:* Zillow-down standard; headline and KPIs absent. *FRED mortgage down:* mortgage KPI shows "n/a", warning "Mortgage rates unavailable", rate chart hidden; headline unaffected. *Case-Shiller down:* tile shows "n/a", chart omitted. *Forecast unavailable or errors:* headline drops the forecast clause. *Loading:* spinners per cached loader. *No metro:* default state, "Next" block shows placeholder picker. *Metro carried:* "Next" block says "Continue with <metro>" plus "Change".
- **Exits:** primary: "See this metro's forecast" -> ML forecast; secondary: Findings ("See top markets"), Regional explorer.
- **Copy (Phase 4, final; supersedes draft wording above):**
  - Title: "Market overview". Nav label: same.
  - Headline: "US home values: up {yoy}% over the past year; forecast {fc} next 12 months (80% range {lo} to {hi})." Fallback (no forecast): "US home values: up {yoy}% over the past year." Down year: "down {yoy}%". As-of line: "Zillow data as of {Mon YYYY}. Mortgage rates as of {Mon YYYY}." Takeaway line under headline: "Next, choose a metro to see its forecast."
  - KPI labels (tooltip in parentheses): "Typical home value" (Zillow Home Value Index, ZHVI: the middle of the market, smoothed); "Change over 12 months" (year over year, YoY); "30-year mortgage rate" with delta "{+0.12} points vs a year ago" (Freddie Mac weekly average via FRED); "Case-Shiller, 12 months" with caption "Measured differently from Zillow, so the two can differ." (S&P Case-Shiller US National index, year over year).
  - Chart titles: "US typical home value since 2000"; "Home values and mortgage rates"; "Case-Shiller US National Home Price Index".
  - Next block: heading "Next: pick a metro". Picker label "Metro"; placeholder "Choose a metro"; button "See this metro's forecast". When carried: "Continue with {metro}" + button "Change metro".
  - Secondary links: "See top markets" (Findings), "Explore regions" (Regional explorer).
  - Empty/error: Zillow down: Zillow-down standard (Voice & tone). Mortgage down: warning "Heads up: mortgage rates are unavailable right now. The headline and home-value chart are unaffected; the rate chart is hidden." KPI value "n/a". Case-Shiller down: KPI "n/a", chart omitted, no message. Forecast unavailable: headline drops the forecast clause, no message.
  - Loading: "Loading home-value data" ; "Loading mortgage rates"; "Training the forecast model (first load takes a minute)".
  - Disclaimer: D1, beside the headline forecast clause and in the footer.

### 2. Findings

- **Purpose:** show which metros lead and lag, so the user can choose where to look.
- **Entry points:** sidebar (group Market); Overview secondary link.
- **Headline answer:** "Top predicted gainer: <metro> at +X% next 12 months (80% range a to b)." Today: no headline; five stacked tables opened by "Top 15 gainers - 1 year".
- **Headline KPIs (above the fold), 3:** Best predicted metro (name + %); Best performer last 5 years; Most valuable metro. (Derived from existing tables; no new analytics.)
- **Content blocks:** 1 headline; 2 KPI row; 3 Predicted gainers top 15 (with 80% range column); 4 Predicted laggards bottom 10; 5 Best past 1-yr and 5-yr gainers (tabs, to reduce scroll); 6 Most valuable metros; 7 disclaimer callout (kept as a callout, not only a caption). Each metro name offers "Use this metro" (sets shared metro) where the Streamlit version supports row selection; otherwise a "Choose a metro" picker above the tables.
- **States:** *Zillow down:* Zillow-down standard; no tables. *Forecast training fails:* tables of past performance still show, predicted sections replaced by "Forecast unavailable right now" and headline falls back to best past performer. *FRED down:* forecast trains without macro (existing) - no UI change, caption "Mortgage data unavailable; forecast may be less accurate." *Supply down:* forecast warning. *Loading:* spinners (data, then "Training forecast model..."). *Empty tables (no metros match size filter):* "No metros to show."
- **Exits:** "See forecast for <metro>" -> ML forecast (after use-this-metro); Regional explorer for filtering; Market overview.
- **Copy (Phase 4, final):**
  - Title: "Findings". Nav label: same.
  - Headline: "Top predicted gainer: {metro} at {+X}% next 12 months (80% range {a} to {b})." Fallback (forecast unavailable): "Best performer over the past year: {metro} at {+X}%."
  - KPI labels: "Top predicted gainer"; "Best performer, last 5 years"; "Most valuable metro" (value shown as "$X typical home").
  - Section titles: "Predicted to gain most, next 12 months"; "Predicted to lag, next 12 months"; "Best performers, past year" and "Best performers, past 5 years" (tabs: "Past year", "Past 5 years"); "Most valuable metros".
  - Table column labels: "Metro", "Typical home value", "Predicted change (80% range)", "Change, 1 year", "Change, 5 years". Row action: "Use this metro". Fallback picker above tables: label "Metro", placeholder "Choose a metro", button "See forecast for {metro}".
  - Callout (kept as callout): D1 plus "The 80% range is the span the actual change landed in about 80% of the time in past tests. It is not a guarantee."
  - Empty/error: Zillow down: Zillow-down standard. Forecast failed: "Couldn't build the forecast right now. Past performance is still shown below. Try again shortly." (Error form; button "Try again"). Mortgage data down: caption "Mortgage rates were unavailable, so the forecast may be less accurate." Listings down: "Heads up: Zillow listings data is unavailable, so the forecast runs without inventory data." No rows: "No metros to show. Change the size filter or choose another view."
  - Loading: "Loading home-value data"; "Training the forecast model".
  - Disclaimer: D1 in callout.

### 3. Regional explorer

- **Purpose:** let the user filter and compare metros or states, and pick one metro.
- **Entry points:** sidebar (group Metro); Overview/Findings secondary links.
- **Headline answer:** "<N> metros shown; the median 1-year change is +X%, led by <metro> (+Y%)." In State mode: "<N> states shown; median ..., led by <state>." Today: no headline; filters first.
- **Headline KPIs (above the fold), 3:** Regions shown; Median 1-year change; Top mover (name + %).
- **Content blocks:** 1 headline; 2 KPI row; 3 filters in one compact row (Region type, States, Size rank, Value range, Sort by) - progressive: only Region type + Sort visible, others in an "Filters" expander (Hick); 4 ranked table; 5 Top 20 bar chart; 6 State mode only: choropleth with metric select; 7 "Region history" for the selected metro vs United States (bound to shared metro in Metro mode); 8 disclaimer.
- **States:** *Zillow down:* Zillow-down standard; Metro mode fails when the metro dataset is down, State mode when the state dataset is down (the other mode stays usable). *Filters match nothing:* "No regions match these filters. Widen the size or value range." with a reset action (today: an empty table). *Value slider degenerate (vmin == vmax):* slider hidden (existing). *No metro selected:* history block asks to choose a region from the table. *Metro carried:* history block opens on it. *Loading:* data spinner.
- **Exits:** "See <metro> profile" -> Market profile; "See forecast" -> ML forecast; back to Overview.
- **Copy (Phase 4, final):**
  - Title: "Regional explorer". Nav label: same.
  - Headline (metro): "{N} metros shown. The median 1-year change is {+X}%, led by {metro} ({+Y}%)." (state): "{N} states shown. The median 1-year change is {+X}%, led by {state} ({+Y}%)."
  - KPI labels: "Regions shown"; "Median 1-year change"; "Top mover".
  - Control labels: "Region type" (Metro | State); "Sort by" (options "1-year change", "5-year change", "10-year change", "Typical value"); expander "Filters" containing "States", "Largest metros to include" (tooltip: size rank, 1 is the largest), "Home value range"; reset button "Reset filters". Choropleth select "Map shows" (same four options as Sort by; never raw keys like chg_1y).
  - Section titles: "Ranked regions"; "Top 20 by {sort}"; "Map by state"; "{Region} price history" with picker label "Region" and a comparison line "compared with the United States".
  - Row/exits: "See {metro} profile"; "See forecast".
  - Empty/error: Zillow down: Zillow-down standard (names which view, metro or state, is affected; the other view stays usable). No match: "No regions match these filters. Widen the size or value range, or reset the filters." No region picked: "Choose a region from the table to see its price history."
  - Loading: "Loading home-value data".
  - Disclaimer: none required (no forecast shown); footer D1 stays per shared rule.

### 4. Market profile

Owner: collaborator (Lucas). The analytics logic (metrics, compare, KNN similar markets, `analysis.*` calls) is unchanged. The spec changes presentation and wiring only: (a) the "Select a market" selector binds to the shared metro (and shows a placeholder when empty); (b) a new headline sentence and block order; (c) the page title and nav label become "Market profile"; (d) the 1y/5y/rank tiles format missing values as "n/a" instead of erroring.

- **Purpose:** show one metro's value, growth, and history, compared with another and with similar markets.
- **Entry points:** sidebar (group Metro); Explorer "See profile"; carried metro.
- **Headline answer:** "<Metro>: typical home $X, up Y% in the last year, #R by size." Today: header "Market Profiles" and a bare selector.
- **Headline KPIs (above the fold), 4:** Home value; 1-year appreciation; 5-year appreciation; Size rank (the existing four metrics).
- **Content blocks:** 1 headline + metro selector (bound to shared metro, placeholder when empty); 2 KPI row; 3 home-value history; 4 Compare markets ("Compare with" is page-local, not persisted; table + overlay chart); 5 Similar markets (KNN table); 6 disclaimer. Page title label: "Market profile" (sentence case, matches nav).
- **States:** *Zillow down:* Zillow-down standard; picker disabled. *Loading:* spinner while data loads. *No metro selected:* empty state "Choose a metro to see its profile." with the picker; KPIs hidden. *Carried metro valid:* opens on it. *Invalid carried metro:* notice per Flows, then empty state. *Compare options empty (one metro only):* compare block hidden. *Similar markets unavailable (ValueError, existing):* "Similar market analysis isn't available for <metro>." *Region has missing 1y/5y change:* tile shows "n/a" (today a format error risk; spec requires "n/a").
- **Exits:** "See <metro> forecast" -> ML forecast; "Estimate financing" -> Financing estimator; back to Regional explorer.
- **Copy (Phase 4, final):**
  - Title and nav label: "Market profile" (not "Market Profiles").
  - Headline: "{Metro}: typical home ${X}, up {Y}% in the last year, #{R} by size." Down year: "down {Y}%". Missing 1-year value: "{Metro}: typical home ${X}, #{R} by size."
  - Selector label: "Metro" (was "Select a market"); placeholder "Choose a metro".
  - KPI labels: "Typical home value"; "Change, 1 year"; "Change, 5 years"; "Size rank" (tooltip: 1 is the largest metro). Missing value: "n/a".
  - Section titles: "Home value history"; "Compare with another metro" (selector label "Compare with"); "Similar markets" (caption "Metros whose price history and size look most like {metro}.").
  - Exits: "See {metro} forecast"; "Estimate financing"; "Back to Regional explorer".
  - Empty/error: no metro: "Choose a metro to see its profile." Invalid carried metro: "We couldn't find '{value}'. Choose a metro." Compare empty: block hidden, no message. Similar markets unavailable: "Similar markets aren't available for {metro}. There isn't enough comparable data." Zillow down: Zillow-down standard, picker shows "Metro list unavailable".
  - Loading: "Loading home-value data".
  - Disclaimer: D1 in footer (page shows no forecast figure; kept for consistency with the shared rule).

### 5. ML forecast

- **Purpose:** tell the user where the selected metro's prices are headed and how far to trust that.
- **Entry points:** Overview "See this metro's forecast" (primary); sidebar (group Money); Findings/Profile exits; carried metro.
- **Headline answer:** "<Metro> home values: forecast -2.1% over the next 12 months (80% range -5.4% to +1.0%)." Subline: "80% range: in backtests, the actual change landed inside a range this wide <coverage>% of the time." Placed with the disclaimer. Today: opens with backtest tables; national call appears mid-page; no per-metro view except a searchable table.
- **Headline KPIs (above the fold), 3 (the market-wide model track record, worded as such; not per-metro):** Track record (typical miss in points, from MAE); Direction calls (e.g. "7 of 10", from direction accuracy); Versus a simple guess (error of blend vs no-change baseline, quantified e.g. "2.4 vs 3.1 pts"). Metric names in tooltips only.
- **Content blocks:** 1 headline + subline; 2 reliability KPI row; 3 metro history chart with the 12-month 80% range; 4 "What goes into this forecast": the metro's latest 12-month price change, mortgage rate, inventory trend as values only - no per-factor "pulls up/down" (needs attribution analytics; out of scope; revisit if the model exposes contributions); 5 Next-step CTA "Estimate financing in <metro>"; 6 distribution of all metro predictions + per-metro table with search (secondary, below fold); 7 backtest detail (per-year tables, rank-IC chart, bias notes) in an expander "How we tested this"; 8 Methodology expander; 9 disclaimer.
- **States:** *Zillow down:* Zillow-down standard; the national forecast cannot be shown either. *FRED down:* forecast trains without macro features (existing), caption notes it. *Supply (listings) down:* existing warning "Zillow listings data unavailable; forecast runs without supply features." *Training error:* "The forecast couldn't be built right now. Try again shortly." with retry; the page keeps the disclaimer (today uncaught). *Training in progress:* spinner "Training forecast model...". *No metro selected:* national call as headline + inline picker. *Metro not in predictions:* notice per Flows, national call shown. *Blend no longer beats model (existing warning):* kept, in plain words. *Metro carried:* header caption "Using <metro> (from Market overview)" as a sentence-case meta line, not an uppercase eyebrow chip.
- **Exits:** primary "Estimate financing in <metro>" -> Financing estimator; "See <metro> profile"; change metro.
- **Copy (Phase 4, final):**
  - Title: "ML forecast". Nav label: same. Page subtitle: "Where prices may be headed, and how far to trust it."
  - Headline: "{Metro} home values: forecast {+/-X}% over the next 12 months (80% range {a} to {b})." Subline: "80% range: in past tests, the actual change landed inside a range this wide {coverage}% of the time." No-metro headline: "US home values: forecast {X}% over the next 12 months (80% range {a} to {b}). Choose a metro for its forecast." Meta line when carried: "Using {metro} (from Market overview)."
  - Picker: label "Metro", placeholder "Choose a metro to see its forecast".
  - KPI labels (all market-wide, caption "Across all metros, past tests"): "Typical miss" value "{x.x} points" (average miss, mean absolute error, MAE); "Direction calls right" value "{7 of 10}" (share of cases where the forecast got up vs down right, direction accuracy); "Versus a no-change guess" value "{2.4} vs {3.1} points" (typical miss of our blend vs assuming prices stay flat).
  - Other jargon map (labels visible, term in tooltip): "ranking skill" (rank IC: how well forecasts order metros from best to worst; 0 is random, 1 is perfect, above about 0.3 is useful); "leans {optimistic/pessimistic} by {x} points" (bias); "top picks beat the average by {x} points a year" (top-decile lift); "range hit rate" (80% range coverage); "range width" (80% range width); "momentum" kept as "recent trend" (naive momentum); "blend" kept as "combined forecast" (average of the ML model and recent trend).
  - Section titles: "{Metro} price history and forecast"; "What goes into this forecast" (rows: "12-month price change", "Mortgage rate", "Homes for sale trend"; values only); "All metro forecasts" (histogram caption "How many metros fall at each predicted change"); table search label "Search metros"; expander "How we tested this" (backtest tables, ranking-skill chart titled "Ranking skill by year"); expander "How the forecast works" (methodology text unchanged).
  - Button: "Estimate financing in {metro}"; secondary "See {metro} profile".
  - Empty/error: Zillow down: Zillow-down standard, plus "The national forecast needs the same data." Metro not in predictions: "No forecast for {metro} yet. It doesn't have enough price history. Showing the US forecast instead." Listings down: "Heads up: Zillow listings data is unavailable, so the forecast runs without inventory data." Mortgage down: "Heads up: mortgage rates are unavailable, so the forecast runs without them and may be less accurate." Training failed: "Couldn't build the forecast right now. This is usually temporary. Try again in a few minutes." with button "Try again". Blend no longer beats model: "Heads up: in this round of tests the combined forecast was slightly less accurate than the model alone."
  - Loading: "Training the forecast model (first load takes a minute)".
  - Disclaimer: D1 directly under the headline and in the footer.

### 6. Financing estimator

- **Purpose:** show what owning a home in the selected metro costs per month, and how equity may grow.
- **Entry points:** ML forecast primary CTA; sidebar (group Money); Profile exit; carried metro.
- **Headline answer:** "Estimated payment on a $X home in <metro>: $Y/month (30-year fixed at r%, 20% down)." Rendered from sensible defaults on first load, so the answer exists before any input. **No-metro variant (manual price, no metro selected):** "Estimated payment on a $400,000 home (your price): $Y/month (30-year fixed at r%, 20% down). Tax and insurance use US averages; choose a metro for a local equity projection." The price shown is the user's current manual price. The metro variant applies as soon as a metro is selected. Today: the estimate is a transposed table under a column of inputs; no headline.
- **Headline KPIs (above the fold), 4:** Monthly payment (PITI, 30-year); Rate and APR; Cash down; Total interest (30-year).
- **Content blocks:** 1 headline + "Estimate only - not a loan quote or offer, and not financial advice" notice (kept, shortened); 2 KPI row; 3 inputs panel (price source and metro, down payment, credit band, loan type, state) beside or below the answer, each with sensible defaults; 4 rate comparison table by term (10/15/20/30); 5 optional blocks in expanders: Override tax/insurance, DTI check; 6 ARM comparison (conventional only, existing rule; otherwise the existing "ARM comparison shown for conventional loans only" info); 7 amortization chart; 8 equity projection with 80% range and its long-horizon uncertainty warning (kept verbatim in meaning); 9 Sources & assumptions expander; 10 disclaimer.
- **States:** *Zillow down:* the one page that degrades instead of stopping: Zillow-down standard message with "Try again", metro picker disabled, price source forced to Manual ("Metro prices unavailable - enter a home price."), the estimate still works; equity block says "Equity projection needs Zillow history (unavailable)." (existing). *FRED mortgage down:* warning "Live mortgage rates unavailable - enter rates manually" with manual 30y/15y inputs (existing); headline uses those. *SOFR down:* warning + manual index (existing). *Invalid inputs (ValueError from the estimator):* inline error with cause (existing `st.error`), disclaimer still shown, KPIs hidden. *No metro:* Manual price default $400,000 + inline metro picker; headline uses the no-metro variant above. *Manual price with metro:* label "Using your price, <metro> growth". *Metro lacks history or forecast:* equity caption "<metro> has under N months of history; using United States." / "ML forecast unavailable for <metro>; year 1 uses the historical trend." (existing). *Jumbo / DTI over limit:* existing info/warning kept. *Loading:* spinners.
- **Exits:** back to ML forecast for the metro; change metro; Market profile. Terminal page of the journey.
- **Copy (Phase 4, final):**
  - Title: "Financing estimator". Nav label: same.
  - Headline (metro): "Estimated payment on a ${X} home in {metro}: ${Y}/month (30-year fixed at {r}%, {d}% down)." No-metro: "Estimated payment on a ${X} home (your price): ${Y}/month (30-year fixed at {r}%, {d}% down). Tax and insurance use US averages. Choose a metro for a local equity projection." Rates entered by hand: "at {r}% (your rate)". Notice under headline (D2): "This is an estimate, not a loan quote or offer, and not financial advice. Nothing you enter is stored, and we collect no personal data beyond a credit band."
  - KPI labels: "Monthly payment" (tooltip: principal, interest, property tax and insurance; PITI); "Rate and APR" (tooltip: APR includes lender fees); "Cash down"; "Total interest, 30 years".
  - Input labels: "Home price source" (options "Metro typical value", "Enter my own price"); "Metro" (placeholder "Choose a metro"); "Home price ($)"; "Down payment as" (options "% of price", "$ amount") then "Down payment (%)" / "Down payment ($)"; "Credit score range" (was band); "Loan type" (Conventional, FHA, VA); "State"; "Lender fees (% of loan)" (tooltip: used only to compute APR). Caption with metro: "Typical {metro} home: ${X}". With own price and metro: "Using your price, {metro} growth".
  - Expanders: "Change property tax and insurance" (labels "Property tax (% of home value per year)", "Home insurance ($ per year)"); "Check debt-to-income" (labels "Gross monthly income ($)", "Other monthly debts ($)"; tooltip: DTI); "Adjustable-rate (ARM) comparison" with "ARM assumptions" (labels "ARM margin (points)", "SOFR 30-day average (%)"); "Sources and assumptions".
  - Section titles: "Rates by loan term" (rows 10/15/20/30 years); "Where each payment goes" (amortization chart; term select "Loan term", options "{n} years"); "Equity projection" (selects "Growth based on" with options United States or a metro, "Loan for projection"; "Selling costs (% of sale price)"); ARM chart toggle "ARM scenario".
  - Estimate table row labels: "Starting rate", "Starting payment (principal and interest)", "Rate after first reset", "Payment after first reset", "Highest possible payment", "Highest possible rate", "Total interest".
  - Equity notices: warning (D3) "Long-horizon projections are highly uncertain: years 2 and later extend this market's past growth. Not a prediction and not financial advice." Caption: "Year 1 uses the ML forecast with its 80% range (as of {Mon YYYY}). Years 2+ use {region}'s average growth since {YYYY} ({x}% a year). Values are nominal and exclude maintenance, taxes and improvements." Fallbacks: "{metro} has under {N} months of price history, so this uses United States growth." / "No ML forecast for {metro}, so year 1 uses the historical trend."
  - Empty/error: Zillow down (degrades): warning "Heads up: we can't reach Zillow's home-value data right now, so metro prices are unavailable. Enter a home price below, or try again in a few minutes." Button "Try again"; picker shows "Metro list unavailable"; equity block: "Equity projection needs Zillow price history, which is unavailable right now." Mortgage down: "Heads up: live mortgage rates are unavailable. Enter your own rates below." (inputs "30-year fixed rate (%)", "15-year fixed rate (%)"). SOFR down: "Heads up: the SOFR index is unavailable. Enter it below." Invalid input: "Error: {specific cause, e.g. 'Down payment must be less than the home price.'} Change the value and the estimate will update." (written per validation, never the raw exception). ARM not offered: "ARM comparison is only shown for conventional loans." Jumbo: "Loan is above the standard conforming limit. Pricing varies by lender; high-cost counties allow up to $1,249,125." DTI warn: "Your debt-to-income ratio is {x}%. Approval gets harder above {DTI_WARN}%." DTI over: "Your debt-to-income ratio is {x}%. Most lenders decline above {DTI_MAX}%."
  - Loading: "Loading home-value data"; "Loading mortgage rates".
  - Disclaimer: D2 under the headline, D3 on equity; D1 in footer.

## Voice & tone

**Voice (stable):** plain, direct, calm. Say the answer first, with the number. No hype, no hedging filler, no jargon, no blame. We say "we" for the app and "you" for the reader (Podmajersky: voice stays constant; tone shifts with the moment).

| Moment | Tone | Example |
|--------|------|---------|
| Answer / headline | Confident, specific | "US home values: up 1.2% over the past year." |
| Forecast / uncertainty | Honest, measured | "forecast +1.3% (80% range 0% to +3.6%)" |
| Data source down | Reassuring, practical (warning form, "Heads up:") | "Heads up: ... Try again in a few minutes." |
| Real failure | Plain, accountable (error form, "Error:" or "Couldn't ...") | "Couldn't build the forecast right now." |
| Empty state | Helpful, one next step | "Choose a metro to see its profile." |

**Rules:** sentence case for titles, labels, buttons (Redish scannability). Front-load the key info. Errors follow Yifrah: what happened, why, how to fix; never blame ("Check the value", not "You entered an invalid value"). Numbers: signed percent with one decimal, "points" for percentage-point differences, `$` with thousands separators, months as "Sep 2026". Placeholders in {braces} are filled at render. Name the data month on pages that show data. "80% range" is the only name for forecast intervals. Technical terms live in tooltips (`help=`) or the "How we tested this" expander, never as a visible label.

**Shared strings (referenced by page Copy blocks):**
- D1 (forecast disclaimer, every page footer and beside any forecast headline): "Forecasts are statistical estimates, not financial advice."
- D2 (financing notice): "This is an estimate, not a loan quote or offer, and not financial advice. Nothing you enter is stored, and we collect no personal data beyond a credit band."
- D3 (equity projection): "Long-horizon projections are highly uncertain: years 2 and later extend this market's past growth. Not a prediction and not financial advice."
- Zillow down (warning, "Heads up:"): "Heads up: we can't reach Zillow's home-value data right now. Check your connection, or try again in a few minutes." Button "Try again". Pickers: "Metro list unavailable". The `{e}` exception text is never shown.
- Sidebar: brand "michiganmen"; tagline "US housing market analytics and forecasts"; selected metro block: label "Selected metro", empty "No metro selected", action "Choose a metro" / "Change"; footer D1.
- Loading (no trailing ellipsis): "Loading home-value data"; "Loading mortgage rates"; "Loading listings data"; "Training the forecast model (first load takes a minute)".
- Unknown metro in URL: "We couldn't find '{value}'. Choose a metro."
- Metro-list-down pickers: placeholder "Metro list unavailable".

## Verification notes (Phase 1)

- Page spec count: 6 (Market overview, Findings, Regional explorer, Market profile, ML forecast, Financing estimator); nav options: 6.
- Max headline KPIs on any page: 4.
- Open items for the user: Lucas (collaborator) signs off on the Market profile changes (shared-metro selector binding, headline, title, "n/a" formatting) before build; confirm sidebar reorder (IA); confirm that "What drives this forecast" attribution is dropped from scope; confirm Overview forecast clause is worth the first-load model training.
