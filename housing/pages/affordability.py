"""Affordability page: which metros fit the user's income."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from housing import analysis, finance, ui
from housing.ui import fmt_pct, signed
from housing.shared import (CC, _data_dir_key, _footer_disclaimer, _mon, _need, _num_cols, _safe_load_metro, _short,
                            _try_forecast, cached_affordability, cached_fred, fmt_range)

SORTS = {"Payment share": ("share", True), "12-month forecast": ("pred_12m", False),
         "Typical value": ("value", False), "Size rank": ("size_rank", True)}


def render_affordability() -> None:
    st.header("Affordability")
    head, kpis = st.container(), st.container()
    metro_df = _need(_safe_load_metro())
    table = analysis.appreciation_table(metro_df[metro_df["region_type"] != "country"])

    c1, c2, c3 = st.columns(3)
    income = c1.number_input("Household income ($ per year)", min_value=0.0, value=100_000.0, step=5_000.0, format="%d",
                             help="Before taxes. The 30% rule: lenders and Zillow treat a home as affordable when the monthly "
                                  "payment, including property tax and insurance, is at most 30% of gross income.")
    c1.caption(f"${income:,.0f} per year")
    down = c2.number_input("Down payment (%)", min_value=3.0, max_value=99.0, value=20.0, step=1.0)
    debts = c3.number_input("Other monthly debts ($)", min_value=0.0, value=0.0, step=50.0,
                            help="Car, student loan and card payments. If you enter debts, a metro also needs total debts under 43% of income.")
    st.caption("Assumes a 30-year fixed conventional loan, credit score 740-759, and your state's average property tax and "
               "insurance. Change these on the Financing estimator.")

    s30 = cached_fred("MORTGAGE30US", _data_dir_key())
    s30 = s30.dropna() if s30 is not None else None
    s15 = cached_fred("MORTGAGE15US", _data_dir_key())
    s15 = s15.dropna() if s15 is not None else None
    manual = s30 is None or s30.empty
    if manual:
        st.warning("Heads up: live mortgage rates are unavailable. Enter your own rate below.")
        r30 = st.number_input("30-year fixed rate (%)", 0.0, 20.0, 6.5, 0.05)
        r15 = r30
    else:
        r30 = float(s30.iloc[-1])
        r15 = float(s15.iloc[-1]) if s15 is not None and not s15.empty else r30
        st.caption(f"PMMS average, {_mon(s30.index[-1])}: 30-year fixed {r30:.2f}% (Freddie Mac via FRED).")
    rb = finance.base_rates(r30, r15)

    z = cached_affordability(_data_dir_key())
    if z is None:
        st.warning("Heads up: Zillow's affordability data is unavailable, so we rank all metros and hide Zillow's own "
                   "payment and income columns.")
    else:
        table = table[table["region"].isin(z["region"])]
    try:
        t = finance.affordability_table(table[["region", "state", "value"]], income, down, rb, debts)
    except ValueError as e:
        with head:
            ui.headline("Affordability unavailable.")
        st.error(f"Error: {e} Change the value and the ranking will update.")
        _footer_disclaimer()
        return
    t = t.merge(table[["region", "size_rank"]], on="region")
    if z is not None:
        t = t.merge(z.drop(columns="date"), on="region", how="left")

    res = _try_forecast(metro_df)
    if res is not None:
        t = t.merge(res.predictions[["region", "pred_12m", "lo_12m", "hi_12m"]], on="region", how="left")
        t["pred"] = [fmt_range(p, lo, hi) for p, lo, hi in zip(t["pred_12m"], t["lo_12m"], t["hi_12m"])]
    else:
        t["pred_12m"], t["pred"] = float("nan"), "n/a"
        st.info("The 12-month forecast is unavailable right now, so that column shows n/a.")

    n, N = int(t["affordable"].sum()), len(t)
    ok = t[t["affordable"]]
    if n:
        best = ok.loc[ok["pred_12m"].idxmax()] if res is not None and ok["pred_12m"].notna().any() else ok.loc[ok["share"].idxmin()]
        tail = f"forecast {fmt_pct(best['pred_12m'])}" if res is not None and pd.notna(best["pred_12m"]) else f"{best['share']:.0%} of income"
        text = (f"On ${income:,.0f}/yr, {n} of {N} metros keep the payment under 30% of your income. "
                f"Best value: {_short(best['region'])} ({tail}).")
    else:
        best = t.loc[t["share"].idxmin()]
        text = (f"On ${income:,.0f}/yr, none of {N} metros keep the payment under 30% of your income. "
                f"Lowest: {_short(best['region'])} at {best['share']:.0%}.")
    with head:
        ui.headline(text, f"30-year fixed at {r30:.2f}%{' (your rate)' if manual else ''}, {down:g}% down.")
        ui.disclaimer(ui.D2 + " " + ui.D1)

    metro = st.session_state.get("metro")
    mrow = t[t["region"] == metro] if metro else t.iloc[0:0]
    cheapest = t.loc[t["payment"].idxmin()]
    k = kpis.columns(4)
    ui.kpi(k[0], "Metros within 30%", f"{n} of {N}")
    ui.kpi(k[1], "Typical payment share", f"{t['share'].median():.0%}")
    ui.kpi(k[2], "Best value", _short(best["region"]), signed(best["pred_12m"]) if res is not None and pd.notna(best["pred_12m"]) else None)
    if len(mrow):
        m = mrow.iloc[0]
        ui.kpi(k[3], f"{_short(metro)}: monthly payment", f"${m['payment']:,.0f}", help=f"{m['share']:.0%} of income")
        rank = int((t["share"] < m["share"]).sum()) + 1
        st.write(f"{metro}: ${m['payment']:,.0f}/month, {m['share']:.0%} of your income, rank {rank} of {N}.")
    else:
        ui.kpi(k[3], "Lowest payment", _short(cheapest["region"]), help=f"${cheapest['payment']:,.0f}/mo")
        if metro:
            st.info(f"No home-value data for {metro}, so it is not ranked.")

    f1, f2, f3 = st.columns([1, 2, 1])
    only = f1.toggle("Only metros within 30%", value=False)
    states = f2.multiselect("States", sorted(t["state"].unique()))
    sort = f3.selectbox("Sort by", list(SORTS))
    shown = t[t["affordable"]] if only else t
    if states:
        shown = shown[shown["state"].isin(states)]
    col, asc = SORTS[sort]
    shown = shown.sort_values(col, ascending=asc, na_position="last")
    if len(mrow) and metro in set(shown["region"]):
        shown = pd.concat([shown[shown["region"] == metro], shown[shown["region"] != metro]])
        shown["region"] = shown["region"].where(shown["region"] != metro, metro + " (your metro)")
    st.subheader("Metros ranked by payment")
    if shown.empty:
        st.info("No metros match these filters. Clear the state filter or turn off 'Only metros within 30%'.")
    else:
        shown = shown.assign(share_txt=shown["share"].map("{:.0%}".format))
        cols = ["region", "state", "value", "payment", "share_txt", "pred"] + (["z_payment", "z_income_needed", "z_share"] if z is not None else [])
        cfg = _num_cols() | {
            "payment": CC.NumberColumn("Estimated payment", format="$%,d", help="Principal, interest, property tax, insurance and any mortgage insurance at your down payment."),
            "share_txt": CC.TextColumn("Share of your income"),
            "z_payment": CC.NumberColumn("Zillow payment (20% down)", format="$%,d"),
            "z_income_needed": CC.NumberColumn("Zillow income needed", format="$%,d"),
            "z_share": CC.NumberColumn("Zillow payment share", format="percent", help="Zillow's estimate of the share of the metro's median income a new buyer spends on the payment, 20% down."),
        }
        ev = st.dataframe(shown[cols], hide_index=True, width="stretch", column_config=cfg,
                          on_select="rerun", selection_mode="single-row", key="afford_table")
        if ev.selection.rows:
            pick = shown["region"].iloc[ev.selection.rows[0]].removesuffix(" (your metro)")
            if pick != metro:
                st.session_state["metro"] = pick
                st.query_params["metro"] = pick
                st.rerun()
    metro = st.session_state.get("metro")
    if metro:
        ui.go_to("financing", f"Estimate financing in {_short(metro)}", primary=True)
    st.caption("Select a row to make it your metro.")

    when = f" (Zillow, through {_mon(z['date'].max())})" if z is not None else ""
    with st.expander("Sources and assumptions"):
        st.markdown(
            "- Payment: `finance.estimate` with the Freddie Mac PMMS 30-year rate and state tax and insurance tables, same as the Financing estimator.\n"
            "- 30% rule: a metro is affordable when the payment is at most 30% of gross income.\n"
            f"- Zillow columns: Zillow affordability files, 20% down, metro median income{when}.\n"
            "- Forecast: the served 12-month blend from the ML forecast page.")
    _footer_disclaimer()


render_affordability()
