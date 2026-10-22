"""Market overview page."""
from __future__ import annotations

import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from housing import analysis, ui
from housing.ui import GREY, INK, TEAL, fmt_pct, show, signed
from housing.shared import (_data_dir_key, cached_fred, cached_supply, _safe_load_metro, metro_regions, _footer_disclaimer, _need, _mon,
                            _try_forecast, _short, _table, _range_table, _forecast_failed)


def render_overview() -> None:
    st.header("Market overview")
    metro_df = _need(_safe_load_metro())

    us_series = analysis.national_series(metro_df)
    mortgage = cached_fred("MORTGAGE30US", _data_dir_key())
    case_shiller = cached_fred("CSUSHPINSA", _data_dir_key())
    has_mort = mortgage is not None and not mortgage.empty

    latest_value = us_series.iloc[-1]
    yoy_series = analysis.yoy(us_series)
    latest_yoy = yoy_series.iloc[-1] if len(yoy_series) else float("nan")

    metro = st.session_state.get("metro")
    takeaway = f"Continue with {metro}." if metro else "Next, choose a metro to see its forecast."

    def fill_head(fc) -> None:
        if pd.notna(latest_yoy):
            text = f"US home values: {fmt_pct(latest_yoy)} over the past year"
        else:
            text = f"US home values: typical home ${latest_value:,.0f}"
        if fc:
            text += f"; forecast {fmt_pct(fc[0])} next 12 months (80% range {signed(fc[1])} to {signed(fc[2])})"
        with head.container():
            ui.headline(text + ".", takeaway)
            if fc:
                ui.disclaimer()

    head = st.empty()  # filled again once the forecast model has trained
    fill_head(None)

    col1, col2, col3, col4 = st.columns(4)
    ui.kpi(col1, "Typical home value", f"${latest_value:,.0f}",
           help="Zillow Home Value Index (ZHVI): the middle of the market, smoothed.")
    ui.kpi(col2, "Change over 12 months", fmt_pct(latest_yoy), help="Year over year (YoY).")
    if has_mort:
        mort_latest = mortgage.iloc[-1]
        mort_chg = mort_latest - mortgage.iloc[-13] if len(mortgage) > 12 else float("nan")
        # neutral gray: a higher rate is not good or bad news in itself
        ui.kpi(col3, "30-year mortgage rate", f"{mort_latest:.2f}%",
               f"{'▲ +' if mort_chg >= 0 else '▼ −'}{abs(mort_chg):.2f} points vs a year ago" if pd.notna(mort_chg) else None,
               help="Freddie Mac weekly average via FRED.")
    else:
        ui.kpi(col3, "30-year mortgage rate", "n/a")
        st.warning("Heads up: mortgage rates are unavailable right now. The headline and home-value chart are "
                   "unaffected; the rate chart is hidden.")
    cs_yoy = float("nan")
    if case_shiller is not None and not case_shiller.empty:
        s = analysis.yoy(case_shiller)
        cs_yoy = s.iloc[-1] if len(s) else float("nan")
    ui.kpi(col4, "Case-Shiller, 12 months", fmt_pct(cs_yoy), "Differs from Zillow's method.",
           help="S&P Case-Shiller US National index, year over year.")

    st.subheader("US typical home value since 2000")
    window = st.radio("Chart window", ["Last 10 years", "All"], horizontal=True, label_visibility="collapsed")
    chart = st.empty()  # filled again once the forecast model has trained

    def fill_chart(fc) -> None:
        with chart.container():
            ui.show(ui.history_band(us_series, *(fc or (None, None, None)), name="US typical home value",
                                       years=10 if window == "Last 10 years" else None))
            st.caption(f"Zillow, through {_mon(us_series.index.max())}.")

    fill_chart(None)

    st.subheader("Next: pick a metro")
    ui.metro_picker(metro_regions(), "overview")
    if st.session_state.get("metro"):
        ui.go_to("forecast", "See this metro's forecast", primary=True)
    else:
        st.button("See this metro's forecast", type="primary", disabled=True)
    ui.go_to("explorer", "Explore regions")

    st.subheader("Home values and mortgage rates")
    rows = 2 if has_mort else 1
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.12)
    y = (yoy_series * 100).dropna()
    fig.add_scatter(x=y.index, y=y, name="US home value, 12-month change", line=dict(color=INK, width=2.5),
                    hovertemplate="%{y:+.1f}%", row=1, col=1)
    fig.add_hline(y=0, line_width=1, line_color=GREY, row=1, col=1)
    ui.signed_axis(fig, float(y.min()), float(y.max()), title="Home values, 12-month change (%)", row=1, col=1)
    fig.update_xaxes(range=[y.index.min(), y.index.max()])
    if has_mort:
        fig.add_scatter(x=mortgage.index, y=mortgage, name="30-year mortgage rate", line=dict(color=TEAL, width=2.5),
                        hovertemplate="%{y:.2f}%", row=2, col=1)
        fig.update_yaxes(tickformat=".1f", ticksuffix="%", title="30-year rate (%)", row=2, col=1)
    fig.update_layout(showlegend=False, height=220 * rows + 60)
    show(fig)
    st.caption(f"Zillow, through {_mon(us_series.index.max())}"
               + (f". Freddie Mac via FRED, through {_mon(mortgage.index.max())}." if has_mort else "."))

    if case_shiller is not None and not case_shiller.empty:
        st.subheader("Case-Shiller US National Home Price Index")
        fig = go.Figure(go.Scatter(x=case_shiller.index, y=case_shiller.values, line=dict(color=INK, width=2.5),
                                   hovertemplate="%{y:.1f}"))
        fig.update_yaxes(title="Index (Jan 2000 = 100)")
        show(fig)
        st.caption(f"S&P Case-Shiller via FRED, through {_mon(case_shiller.index.max())}.")

    res = _try_forecast(metro_df)  # after the charts, so the page above is visible while the model trains
    if res is not None and pd.notna(res.national_pred):
        fc = (res.national_pred, *res.national_interval)
        fill_head(fc)
        fill_chart(fc)
    _top_markets(metro_df, res)

    st.caption(f"Zillow data as of {_mon(us_series.index.max())}."
               + (f" Mortgage rates as of {_mon(mortgage.index.max())}." if has_mort else ""))
    _footer_disclaimer()


def _top_markets(metro_df: pd.DataFrame, res) -> None:
    st.subheader("Top markets")
    metro_only = metro_df[metro_df["region_type"] != "country"]
    table = analysis.appreciation_table(metro_only)
    if table.empty:
        st.info("No metros to show. Change the size filter or choose another view.")
        return
    best5 = table[table["size_rank"] <= 200].sort_values("chg_5y", ascending=False)
    best1 = table[table["size_rank"] <= 200].sort_values("chg_1y", ascending=False)
    richest = table.sort_values("value", ascending=False)
    preds = res.predictions[res.predictions["region"] != "United States"] if res is not None else None
    up = preds.sort_values("pred_12m", ascending=False) if preds is not None and not preds.empty else None

    if up is not None:
        t = up.iloc[0]
        text = (f"Top predicted gainer: {t['region']} at {fmt_pct(t['pred_12m'])} next 12 months "
                f"(80% range {signed(t['lo_12m'])} to {signed(t['hi_12m'])}).")
    elif len(best1):
        text = f"Best performer over the past year: {best1.iloc[0]['region']} at {fmt_pct(best1.iloc[0]['chg_1y'])}."
    else:
        text = None
    if text:
        st.markdown(ui.color_deltas(html.escape(text)), unsafe_allow_html=True)
    if up is not None:
        ui.disclaimer(ui.D1 + " The 80% range is the span the actual change landed in about 80% of the time in past tests. "
                      "It is not a guarantee.")
    if res is None:
        _forecast_failed()
    if cached_supply(_data_dir_key()) is None:
        st.warning("Heads up: Zillow listings data is unavailable, so the forecast runs without inventory data.")

    k1, k2, k3 = st.columns(3)
    if up is not None:
        ui.kpi(k1, "Top predicted gainer", _short(up.iloc[0]["region"]), signed(up.iloc[0]["pred_12m"]))
    else:
        ui.kpi(k1, "Top predicted gainer", "n/a")
    if len(best5):
        ui.kpi(k2, "Best performer, last 5 years", _short(best5.iloc[0]["region"]), signed(best5.iloc[0]["chg_5y"]))
    ui.kpi(k3, "Most valuable metro", _short(richest.iloc[0]["region"]), f"${richest.iloc[0]['value']:,.0f} typical home")

    if up is not None:
        st.subheader("Predicted to gain most, next 12 months")
        _table(_range_table(up.head(15)), ["region", "state", "value", "pred"])
        st.subheader("Predicted to lag, next 12 months")
        _table(_range_table(preds.sort_values("pred_12m").head(10)), ["region", "state", "value", "pred"])

    tab1, tab5 = st.tabs(["Past year", "Past 5 years"])
    with tab1:
        st.subheader("Best performers, past year")
        _table(best1.head(15), ["region", "state", "value", "chg_1y"])
    with tab5:
        st.subheader("Best performers, past 5 years")
        _table(best5.head(15), ["region", "state", "value", "chg_5y"])

    st.subheader("Most valuable metros")
    _table(richest.head(15), ["region", "state", "value"])


render_overview()
