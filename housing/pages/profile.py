"""Market profile page."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from housing import analysis, data, ui
from housing.ui import INK, TEAL, fmt_pct, show
from housing.shared import CC, _safe_load_metro, _footer_disclaimer, _need, _mon, _lines, _short


def render_market_profiles():
    st.header("Market profile")
    metro_df = _need(_safe_load_metro(), "profile")
    metro_only = metro_df[metro_df["region_type"] != "country"]
    table = analysis.appreciation_table(metro_only)
    markets = sorted(metro_only["region"].dropna().unique())
    selected = st.session_state.get("metro")

    if selected:
        market = table[table["region"] == selected].iloc[0]
        text = f"{_short(selected)}: typical home ${market['value']:,.0f}"
        if pd.notna(market["chg_1y"]):
            text += f", {'up' if market['chg_1y'] >= 0 else 'down'} {abs(market['chg_1y']) * 100:.1f}% in the last year"
        text += f", #{int(market['size_rank'])} by size." if pd.notna(market["size_rank"]) else "."
        ui.headline(text)
    ui.metro_picker(markets, "profile")
    selected = st.session_state.get("metro")
    if not selected:
        st.info("Choose a metro to see its profile.")
        _footer_disclaimer()
        return
    market = table[table["region"] == selected].iloc[0]
    history = metro_only[metro_only["region"] == selected].sort_values("date")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Typical home value", f"${market['value']:,.0f}", border=True)
    c2.metric("Change, 1 year", fmt_pct(market["chg_1y"]), border=True)
    c3.metric("Change, 5 years", fmt_pct(market["chg_5y"]), border=True)
    c4.metric("Size rank", f"#{int(market['size_rank'])}" if pd.notna(market["size_rank"]) else "n/a", border=True,
              help="1 is the largest metro.")

    st.subheader("Home value history")
    hs = history.set_index("date")["value"]
    show(_lines([(_short(selected), hs, INK, "solid")], "Typical value ($)"))
    st.caption(f"Zillow, through {_mon(hs.index.max())}.")

    comparison_options = [m for m in markets if m != selected]
    if comparison_options:
        st.subheader("Compare with another metro")
        comparison_name = st.selectbox("Compare with", comparison_options)
        comparison = table[table["region"] == comparison_name].iloc[0]
        st.dataframe(pd.DataFrame({
            "Metric": ["Typical home value", "Change, 1 year", "Change, 5 years"],
            _short(selected): [f"${market['value']:,.0f}", fmt_pct(market["chg_1y"]), fmt_pct(market["chg_5y"])],
            _short(comparison_name): [f"${comparison['value']:,.0f}", fmt_pct(comparison["chg_1y"]), fmt_pct(comparison["chg_5y"])],
        }), width="stretch", hide_index=True)
        cs = metro_only[metro_only["region"] == comparison_name].sort_values("date").set_index("date")["value"]
        show(_lines([(_short(selected), hs, INK, "solid"), (_short(comparison_name), cs, TEAL, "solid")], "Typical value ($)"))

    st.subheader("Similar markets")
    try:
        similar = analysis.find_similar_markets(metro_only, selected, n_neighbors=5)
        st.caption(f"Metros whose price history and size look most like {_short(selected)}.")
        sim = similar[["region", "state", "value", "chg_1y", "chg_5y"]].copy()
        sim[["chg_1y", "chg_5y"]] *= 100
        st.dataframe(sim, hide_index=True, width="stretch", column_config={
            "region": CC.TextColumn("Metro", pinned=True), "state": CC.TextColumn("State", width="small"),
            "value": CC.NumberColumn("Typical value", format="$%,d"),
            "chg_1y": CC.NumberColumn("Change, 1 year", format="%+.1f%%", help="Blank means no data for that period."),
            "chg_5y": CC.NumberColumn("Change, 5 years", format="%+.1f%%", help="Blank means no data for that period.")})
    except ValueError:
        st.info(f"Similar markets aren't available for {_short(selected)}. There isn't enough comparable data.")

    b1, b2, b3 = st.columns(3)
    with b1:
        ui.go_to("forecast", f"See {_short(selected)} forecast")
    with b2:
        ui.go_to("financing", "Estimate financing")
    with b3:
        ui.go_to("explorer", "Back to Regional explorer")
    _footer_disclaimer()


render_market_profiles()
