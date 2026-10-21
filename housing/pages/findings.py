"""Findings page."""
from __future__ import annotations

import streamlit as st

from housing import analysis, data, ui
from housing.ui import show, signed
from housing.shared import _data_dir_key, cached_fred, cached_supply, _safe_load_metro, metro_regions, _footer_disclaimer, _need, _try_forecast, _short, _table, _range_table, _forecast_failed


def render_findings() -> None:
    st.header("Findings")
    metro_df = _need(_safe_load_metro())
    metro_only = metro_df[metro_df["region_type"] != "country"]
    table = analysis.appreciation_table(metro_only)
    top_rank = table[table["size_rank"] <= 200]
    best5 = top_rank.sort_values("chg_5y", ascending=False)
    best1 = top_rank.sort_values("chg_1y", ascending=False)
    richest = table.sort_values("value", ascending=False)
    if table.empty:
        st.info("No metros to show. Change the size filter or choose another view.")
        _footer_disclaimer()
        return

    result = _try_forecast(metro_df)
    preds = result.predictions[result.predictions["region"] != "United States"] if result is not None else None
    up = preds.sort_values("pred_12m", ascending=False) if preds is not None and not preds.empty else None

    if up is not None:
        t = up.iloc[0]
        ui.headline(f"Top predicted gainer: {t['region']} at {signed(t['pred_12m'])} next 12 months "
                    f"(80% range {signed(t['lo_12m'])} to {signed(t['hi_12m'])}).")
    elif len(best1):
        b = best1.iloc[0]
        ui.headline(f"Best performer over the past year: {b['region']} at {signed(b['chg_1y'])}.")
    if result is None:
        _forecast_failed()
    if cached_supply(_data_dir_key()) is None:
        st.warning("Heads up: Zillow listings data is unavailable, so the forecast runs without inventory data.")
    if cached_fred("MORTGAGE30US", _data_dir_key()) is None:
        st.caption("Mortgage rates were unavailable, so the forecast may be less accurate.")

    k1, k2, k3 = st.columns(3)
    if up is not None:
        ui.kpi(k1, "Top predicted gainer", _short(up.iloc[0]["region"]), signed(up.iloc[0]["pred_12m"]))
    else:
        k1.metric("Top predicted gainer", "n/a", border=True)
    if len(best5):
        ui.kpi(k2, "Best performer, last 5 years", _short(best5.iloc[0]["region"]), signed(best5.iloc[0]["chg_5y"]))
    k3.metric("Most valuable metro", _short(richest.iloc[0]["region"]), border=True)
    k3.caption(f"${richest.iloc[0]['value']:,.0f} typical home")

    ui.metro_picker(metro_regions(), "findings")
    if st.session_state.get("metro"):
        ui.go_to("forecast", f"See forecast for {_short(st.session_state['metro'])}", primary=True)

    if up is not None:
        st.subheader("Predicted to gain most, next 12 months")
        _table(_range_table(up.head(15)), ["region", "state", "value", "pred"])
        st.subheader("Predicted to lag, next 12 months")
        _table(_range_table(preds.sort_values("pred_12m").head(10)), ["region", "state", "value", "pred"])
        ui.disclaimer(ui.D1 + " The 80% range is the span the actual change landed in about 80% of the time in past tests. "
                      "It is not a guarantee.")

    tab1, tab5 = st.tabs(["Past year", "Past 5 years"])
    with tab1:
        st.subheader("Best performers, past year")
        _table(best1.head(15), ["region", "state", "value", "chg_1y"])
    with tab5:
        st.subheader("Best performers, past 5 years")
        _table(best5.head(15), ["region", "state", "value", "chg_5y"])

    st.subheader("Most valuable metros")
    _table(richest.head(15), ["region", "state", "value"])
    _footer_disclaimer()


render_findings()
