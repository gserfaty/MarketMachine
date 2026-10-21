"""Financing estimator page."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from housing import analysis, finance, ui
from housing.ui import AMBER, GREY, INK, TEAL, VIOLET, show
from housing.shared import _data_dir_key, cached_fred, _safe_load_metro, _footer_disclaimer, _forecast


def _render_arm(res: dict, loan_type: str) -> dict[str, pd.DataFrame]:
    if loan_type != "conventional":
        st.info("ARM comparison is only shown for conventional loans.")
        return {}
    with st.expander("Adjustable-rate (ARM) comparison"):
        s = cached_fred("SOFR30DAYAVG", _data_dir_key())
        s = s.dropna() if s is not None else None
        if s is None or s.empty:
            st.warning("Heads up: the SOFR index is unavailable. Enter it below.")
            sofr = st.number_input("SOFR 30-day average (%)", 0.0, 15.0, 4.0, 0.05)
        else:
            sofr = float(s.iloc[-1])
            st.caption(f"30-day average SOFR, {s.index[-1]:%b %Y} avg (NY Fed via FRED): {sofr:.2f}%")
        margin = st.number_input("ARM margin (points)", 1.0, 3.0, finance.ARM_MARGIN, 0.125)
        fixed30 = res[30]["schedule"]
        rows = {"30-year fixed": [f"{res[30]['rate']:.3f}%", f"${fixed30['payment'].iloc[0]:,.0f}", "-", "-",
                                  f"${fixed30['payment'].max():,.0f}", f"{res[30]['rate']:.3f}%",
                                  f"${res[30]['total_interest']:,.0f}"]}
        all_sc = {}
        for plan, cfg in finance.ARM_PLANS.items():
            init = res[30]["rate"] - finance.ARM_INITIAL_DISCOUNT[plan]
            sc = finance.arm_scenarios(res[30]["loan"], init, sofr, margin, plan)
            all_sc[plan], fm = sc, cfg["fixed_months"]
            for name, d in sc.items():
                rows[f"{plan} - {name}"] = [
                    f"{init:.3f}%", f"${d['payment'].iloc[0]:,.0f}", f"{d['rate'].iloc[fm]:.3f}%",
                    f"${d['payment'].iloc[fm]:,.0f}", f"${d['payment'].max():,.0f}", f"{d['rate'].max():.3f}%",
                    f"${d['interest'].sum():,.0f}"]
        st.dataframe(pd.DataFrame(rows, index=[
            "Starting rate", "Starting payment (principal and interest)", "Rate after first reset", "Payment after first reset",
            "Highest possible payment", "Highest possible rate", "Total interest"]).T, width="stretch")
        plan = st.radio("ARM scenario", list(finance.ARM_PLANS), horizontal=True)
        # at most 4 named series per chart: the four index scenarios; the 30-year fixed stays in the table above
        fig = go.Figure()
        for (name, d), color, dash in zip(all_sc[plan].items(), (INK, TEAL, AMBER, VIOLET), ("solid", "solid", "dash", "dot")):
            fig.add_scatter(x=d["month"], y=d["payment"], name=name, mode="lines", line=dict(color=color, dash=dash, width=2.5))
        fig.update_layout(xaxis_title="Month", yaxis_title="Monthly payment, principal and interest ($)")
        fig.update_yaxes(tickformat="$,.0f")
        show(fig)
        st.caption("ARM initial rates are approximations (no public ARM rate survey since 2022); payments after reset depend on the future index.")
    return {f"{p} ARM (index flat)": sc["Index flat"] for p, sc in all_sc.items()}


def _render_equity(metro_df, region, price, schedules) -> None:
    st.subheader("Equity projection")
    if metro_df is None:
        st.info("Equity projection needs Zillow price history, which is unavailable right now.")
        return
    if region is None:
        region = st.selectbox("Growth based on", ["United States"] + sorted(metro_df.loc[metro_df["region_type"] != "country", "region"].unique()))
    c1, c2 = st.columns(2)
    with c1:
        loan = st.selectbox("Loan for projection", list(schedules))
    with c2:
        sell = st.number_input("Selling costs (% of sale price)", 0.0, 15.0, finance.SELL_COST_PCT, 0.5)
    hist = metro_df[metro_df["region"] == region].sort_values("date")
    try:
        mu, sd5 = finance.appreciation_params(hist["value"])
    except ValueError:
        st.caption(f"{region} has under {finance.MIN_HISTORY_MONTHS} months of price history, so this uses United States growth.")
        region = "United States"
        hist = metro_df[metro_df["region"] == region].sort_values("date")
        mu, sd5 = finance.appreciation_params(hist["value"])
    year1, result = None, None
    try:
        result = _forecast(metro_df)
        row = result.predictions[result.predictions["region"] == region]
        if not row.empty:
            r = row.iloc[0]
            year1 = (float(r["lo_12m"]), float(r["pred_12m"]), float(r["hi_12m"]))
    except Exception:
        pass
    if year1 is None:
        st.caption(f"No ML forecast for {region}, so year 1 uses the historical trend.")
    d = finance.equity_projection(price, schedules[loan], mu, sd5, year1, sell)

    def cell(r, c):
        return f"${r[c]:,.0f} (${r[c + '_lo']:,.0f}–${r[c + '_hi']:,.0f})"
    rows = d[d["year"].isin(finance.PROJECTION_YEARS)]
    st.dataframe(pd.DataFrame({
        "Home value": [cell(r, "value") for _, r in rows.iterrows()],
        "Remaining balance": [f"${b:,.0f}" for b in rows["balance"]],
        "Equity": [cell(r, "equity") for _, r in rows.iterrows()],
        "Net equity if sold": [cell(r, "net") for _, r in rows.iterrows()],
    }, index=[f"Year {y}" for y in rows["year"]]), width="stretch")
    fig = go.Figure()
    fig.add_scatter(x=d["year"], y=d["equity_lo"], mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip")
    fig.add_scatter(x=d["year"], y=d["equity_hi"], mode="lines", line=dict(width=0), fill="tonexty",
                    fillcolor=ui.BAND, name="Equity 80% range", hoverinfo="skip")
    fig.add_scatter(x=d["year"], y=d["equity"], mode="lines", name="Equity", line=dict(color=INK, width=2.5), hovertemplate="%{y:$,.0f}")
    fig.add_scatter(x=d["year"], y=d["net"], mode="lines", name="Net equity if sold", line=dict(color=AMBER, dash="dash", width=1.5),
                    hovertemplate="%{y:$,.0f}")
    fig.update_layout(xaxis_title="Year", yaxis_title="Equity ($)")
    fig.update_yaxes(tickformat="$,.2s")
    show(fig)
    st.warning(ui.D3)
    y1 = (f"Year 1 uses the ML forecast with its 80% range (as of {result.as_of:%b %Y})." if year1 is not None
          else "Year 1 uses the historical trend.")
    st.caption(f"{y1} Years 2+ use {region}'s average growth since {hist['date'].min():%Y} ({np.exp(mu) - 1:.1%} a year). "
               "Values are nominal and exclude maintenance, taxes and improvements.")


def render_financing() -> None:
    st.header("Financing estimator")
    head, kpis = st.container(), st.container()  # filled after the inputs below produce the estimate
    metro_df = _safe_load_metro()
    table = None
    if metro_df is not None:
        table = analysis.appreciation_table(metro_df[metro_df["region_type"] != "country"]).sort_values("size_rank")
    else:
        st.warning("Heads up: we can't reach Zillow's home-value data right now, so metro prices are unavailable. "
                   "Enter a home price below, or try again in a few minutes.")
        ui.retry_button("retry_zillow")

    c1, c2 = st.columns(2)
    with c1:
        metro = ui.metro_picker(None if table is None else table["region"].tolist(), "financing")
        use_metro = False
        if table is not None:
            src = st.radio("Home price source", ["Metro typical value", "Enter my own price"], index=0 if metro else 1)
            use_metro = bool(metro) and src == "Metro typical value"
        else:
            st.caption("Metro prices unavailable - enter a home price.")
        state_default = "CA"
        if metro and table is not None and (table["region"] == metro).any():
            row = table[table["region"] == metro].iloc[0]
            if row["state"] in finance.PROPERTY_TAX_PCT:
                state_default = row["state"]
        if use_metro:
            price = float(row["value"])
            st.caption(f"Typical {metro} home: ${price:,.0f}")
        else:
            price = st.number_input("Home price ($)", min_value=10_000.0, value=400_000.0, step=10_000.0)
            if metro and table is not None:
                st.caption(f"Using your price, {metro} growth")
        down_mode = st.radio("Down payment as", ["% of price", "$ amount"], horizontal=True)
        if down_mode == "% of price":
            down_pct = st.number_input("Down payment (%)", min_value=0.0, max_value=99.0, value=20.0, step=1.0)
        else:
            down_pct = st.number_input("Down payment ($)", min_value=0.0, value=price * 0.2, step=5_000.0) / price * 100
    with c2:
        band = st.selectbox("Credit score range", finance.CREDIT_BANDS, index=finance.CREDIT_BANDS.index("740-759"))
        loan_type = st.selectbox("Loan type", list(finance.MIN_DOWN_PCT), format_func=lambda x: {"conventional": "Conventional", "fha": "FHA", "va": "VA"}[x])
        states = sorted(finance.PROPERTY_TAX_PCT)
        state = st.selectbox("State", states, index=states.index(state_default), key=f"state_{state_default}")
        fees_pct = st.number_input("Lender fees (% of loan)", min_value=0.0, max_value=10.0, value=1.0, step=0.25,
                                   help="Used only to compute the APR.")

    with st.expander("Change property tax and insurance"):
        tax_pct = st.number_input("Property tax (% of home value per year)", min_value=0.0, value=float(finance.PROPERTY_TAX_PCT[state]), step=0.05, key=f"tax_{state}")
        ins_annual = st.number_input("Home insurance ($ per year)", min_value=0.0, value=float(finance.HOME_INS_ANNUAL[state]), step=100.0, key=f"ins_{state}")
    with st.expander("Check debt-to-income"):
        income = st.number_input("Gross monthly income ($)", min_value=0.0, value=0.0, step=500.0,
                                 help="Used for the debt-to-income ratio (DTI).")
        debts = st.number_input("Other monthly debts ($)", min_value=0.0, value=0.0, step=50.0)

    s30 = cached_fred("MORTGAGE30US", _data_dir_key())
    s15 = cached_fred("MORTGAGE15US", _data_dir_key())
    s30 = s30.dropna() if s30 is not None else None
    s15 = s15.dropna() if s15 is not None else None
    hand_rates = s30 is None or s15 is None or s30.empty or s15.empty
    if hand_rates:
        st.warning("Heads up: live mortgage rates are unavailable. Enter your own rates below.")
        r30 = st.number_input("30-year fixed rate (%)", min_value=0.0, max_value=20.0, value=6.5, step=0.05)
        r15 = st.number_input("15-year fixed rate (%)", min_value=0.0, max_value=20.0, value=5.8, step=0.05)
    else:
        r30, r15 = float(s30.iloc[-1]), float(s15.iloc[-1])
        st.caption(f"PMMS average, {s30.index[-1]:%b %Y}: 30y {r30:.2f}%, 15y {r15:.2f}% (Freddie Mac via FRED). "
                   "20y is interpolated and 10y extrapolated from these.")
    rb = finance.base_rates(r30, r15)

    try:
        res = {t: finance.estimate(price, down_pct, loan_type, band, state, t, rb, fees_pct, tax_pct, ins_annual)
               for t in finance.TERMS}
    except ValueError as e:
        with head:
            ui.headline("Estimated payment unavailable.")
            st.error(f"Error: {e} Change the value and the estimate will update.")
        _footer_disclaimer()
        return

    r = res[30]["rate"]
    where = f"in {metro}" if metro else "(your price)"
    with head:
        ui.headline(f"Estimated payment on a ${price:,.0f} home {where}: ${res[30]['piti']:,.0f}/month "
                    f"(30-year fixed at {r:.2f}%{' (your rate)' if hand_rates else ''}, {down_pct:g}% down).",
                    None if metro else "Tax and insurance use US averages. Choose a metro for a local equity projection.")
        ui.disclaimer(ui.D2)
    k = kpis.columns(4)
    k[0].metric("Monthly payment", f"${res[30]['piti']:,.0f}", border=True,
                help="Principal, interest, property tax and insurance (PITI), 30-year.")
    k[1].metric("Rate and APR", f"{r:.2f}% / {res[30]['apr']:.2f}%", border=True, help="APR includes lender fees.")
    k[2].metric("Cash down", f"${price * down_pct / 100:,.0f}", border=True)
    k[3].metric("Total interest, 30 years", f"${res[30]['total_interest']:,.0f}", border=True)

    if res[30]["jumbo"]:
        st.info("Loan is above the standard conforming limit. Pricing varies by lender; high-cost counties allow up to $1,249,125.")
    st.subheader("Rates by loan term")
    m = lambda k: [f"${res[t][k]:,.0f}" for t in finance.TERMS]  # noqa: E731
    st.dataframe(pd.DataFrame(
        {
            "Rate": [f"{res[t]['rate']:.3f}%" for t in finance.TERMS],
            "APR": [f"{res[t]['apr']:.3f}%" for t in finance.TERMS],
            "Principal and interest": m("pi"), "Property tax": m("tax"), "Insurance": m("ins"), "Mortgage insurance": m("mi"),
            "Monthly payment": m("piti"), "Total interest": m("total_interest"), "Upfront fee": m("upfront"),
        },
        index=[f"{t} years" for t in finance.TERMS],
    ), width="stretch")

    if income > 0:
        for t in (30, 15):
            front, back = finance.dti(res[t]["piti"], debts, income)
            if back > finance.DTI_MAX:
                st.warning(f"{t}-year loan: your debt-to-income ratio is {back:.1f}%. Most lenders decline above {finance.DTI_MAX:.0f}%.")
            elif back > finance.DTI_WARN:
                st.warning(f"{t}-year loan: your debt-to-income ratio is {back:.1f}%. Approval gets harder above {finance.DTI_WARN:.0f}%.")
            else:
                st.write(f"{t}-year loan: debt-to-income ratio {back:.1f}% (housing only {front:.1f}%).")

    arm = _render_arm(res, loan_type)

    st.subheader("Where each payment goes")
    term = st.selectbox("Loan term", finance.TERMS, format_func=lambda t: f"{t} years", index=finance.TERMS.index(30))
    sch = res[term]["schedule"].assign(year=lambda d: (d["month"] - 1) // 12 + 1)
    yearly = sch.groupby("year").agg(principal=("principal", "sum"), interest=("interest", "sum"), balance=("balance", "last"))
    fig = go.Figure()
    fig.add_bar(x=yearly.index, y=yearly["principal"], name="Principal", marker_color=TEAL, hovertemplate="%{y:$,.0f}")
    fig.add_bar(x=yearly.index, y=yearly["interest"], name="Interest", marker_color=GREY, hovertemplate="%{y:$,.0f}")
    fig.update_layout(barmode="stack", xaxis_title="Year", yaxis_title="Paid per year ($)")
    fig.update_yaxes(tickformat="$,.0f")
    show(fig)
    bal = go.Figure(go.Scatter(x=yearly.index, y=yearly["balance"], line=dict(color=INK, width=2.5), hovertemplate="%{y:$,.0f}"))
    bal.update_layout(xaxis_title="Year", yaxis_title="Remaining balance ($)")
    bal.update_yaxes(tickformat="$,.0f")
    show(bal, 280)

    _render_equity(metro_df, metro if (metro and table is not None) else None, price,
                   {f"{t}-year fixed": res[t]["schedule"] for t in finance.TERMS} | arm)

    with st.expander("Sources and assumptions"):
        st.markdown(
            "- **Base rates:** Freddie Mac PMMS 30y and 15y via FRED (monthly average); 20y linearly interpolated, 10y linearly extrapolated.\n"
            "- **Conforming limit:** $832,750 (FHFA, release of 2025-11-25); high-cost ceiling $1,249,125.\n"
            "- **Property tax:** Tax Foundation, Property Taxes by State and County (2024 ACS, published 2026-03-16).\n"
            "- **Insurance:** NAIC 2022 via III Facts + Statistics. 2022 data, likely below 2026 premiums.\n"
            "- **Conventional rate adjustment:** approximate Fannie Mae LLPA Matrix Table 1 (purchase, effective 2023-05-01), terms over 15 years only, at 0.25% rate per point vs the PMMS reference borrower. Approximate.\n"
            "- **PMI:** illustrative rate card, not verified; drops off when the balance reaches 78% of price.\n"
            "- **FHA MIP:** HUD Mortgagee Letter 2023-05 (effective 2023-03-20); 1.75% upfront, financed.\n"
            "- **VA funding fee:** first use, purchase, VA.gov effective 2023-04-07; financed; no MI.\n"
            "- **FHA/VA rate:** conventional base minus 0.25 plus a small credit adder (rule of thumb).\n"
            "- **APR:** rate at which the present value of payments (P&I plus MI) equals the loan less lender fees.\n"
            "- **ARM index:** 30-day Average SOFR (FRED `SOFR30DAYAVG`); required by both GSEs for new SOFR ARMs (Freddie Mac SOFR ARMs Fact Sheet, April 2025).\n"
            "- **ARM caps:** ARRC SOFR-indexed ARM white paper (2019): 5/6 = 2/1/5, 10/6 = 5/1/5 (initial/periodic/lifetime), 6-month resets.\n"
            "- **ARM floor:** rate never falls below the margin (Fannie Mae Selling Guide B2-1.4-02, effective 2025-12-10).\n"
            "- **ARM margin:** 2.75 default (ARRC range 2.75-3; Freddie Mac allows 1.00-3.00).\n"
            "- **ARM rounding:** new rate = index + margin rounded to the nearest 0.125 (unverified convention).\n"
            "- **ARM initial rate:** approximation, adjusted 30y fixed rate minus 0.50 (5/6) or 0.25 (10/6); not sourced.\n"
            "- **Equity projection:** year 1 = served ML blend with its 80% range (historical trend if unavailable); years 2+ = region's "
            "average log growth since 2000 with an 80% range of 1.2816 x sd of historical 5-year returns x sqrt(years/5). Nominal dollars. "
            "Selling costs default to ~6% (rule of thumb). ARMs assume the index stays flat.\n"
            "- **Not modeled:** county loan limits, points, HOA, flood insurance, ARM APR/MI, index paths; MI and FHA/VA adjustments are approximations."
        )
    _footer_disclaimer()


render_financing()
