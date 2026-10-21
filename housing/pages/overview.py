"""Market overview page."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from housing import analysis, ui
from housing.ui import GREY, INK, TEAL, fmt_pct, show, signed
from housing.shared import _data_dir_key, cached_fred, _safe_load_metro, metro_regions, _footer_disclaimer, _need, _mon, _try_forecast


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
            text = f"US home values: {'up' if latest_yoy >= 0 else 'down'} {abs(latest_yoy) * 100:.1f}% over the past year"
        else:
            text = f"US home values: typical home ${latest_value:,.0f}"
        if fc:
            text += f"; forecast {signed(fc[0])} next 12 months (80% range {signed(fc[1])} to {signed(fc[2])})"
        with head.container():
            ui.headline(text + ".", takeaway)
            if fc:
                ui.disclaimer()

    head = st.empty()  # filled again once the forecast model has trained
    fill_head(None)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Typical home value", f"${latest_value:,.0f}", border=True,
                help="Zillow Home Value Index (ZHVI): the middle of the market, smoothed.")
    col2.metric("Change over 12 months", fmt_pct(latest_yoy), border=True, help="Year over year (YoY).")
    if has_mort:
        mort_latest = mortgage.iloc[-1]
        mort_chg = mort_latest - mortgage.iloc[-13] if len(mortgage) > 12 else float("nan")
        col3.metric("30-year mortgage rate", f"{mort_latest:.2f}%", border=True, help="Freddie Mac weekly average via FRED.")
        if pd.notna(mort_chg):  # neutral: a higher rate is not good or bad news in itself
            col3.caption(f"{'▲ +' if mort_chg >= 0 else '▼ −'}{abs(mort_chg):.2f} points vs a year ago")
    else:
        col3.metric("30-year mortgage rate", "n/a", border=True)
        st.warning("Heads up: mortgage rates are unavailable right now. The headline and home-value chart are "
                   "unaffected; the rate chart is hidden.")
    cs_yoy = float("nan")
    if case_shiller is not None and not case_shiller.empty:
        s = analysis.yoy(case_shiller)
        cs_yoy = s.iloc[-1] if len(s) else float("nan")
    col4.metric("Case-Shiller, 12 months", fmt_pct(cs_yoy), border=True,
                help="S&P Case-Shiller US National index, year over year.")
    col4.caption("Measured differently from Zillow, so the two can differ.")

    st.subheader("US typical home value since 2000")
    chart = st.empty()  # filled again once the forecast model has trained

    def fill_chart(fc) -> None:
        with chart.container():
            ui.show(ui.history_band(us_series, *(fc or (None, None, None)), name="US typical home value"))
            st.caption(f"Zillow, through {_mon(us_series.index.max())}.")

    fill_chart(None)

    st.subheader("Next: pick a metro")
    ui.metro_picker(metro_regions(), "overview")
    if st.session_state.get("metro"):
        ui.go_to("forecast", "See this metro's forecast", primary=True)
    else:
        st.button("See this metro's forecast", type="primary", disabled=True)
    c1, c2, _ = st.columns([1, 1, 2])
    with c1:
        ui.go_to("findings", "See top markets")
    with c2:
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

    st.caption(f"Zillow data as of {_mon(us_series.index.max())}."
               + (f" Mortgage rates as of {_mon(mortgage.index.max())}." if has_mort else ""))
    _footer_disclaimer()
    res = _try_forecast(metro_df)  # last, so the page above is visible while the model trains
    if res is not None and pd.notna(res.national_pred):
        fc = (res.national_pred, *res.national_interval)
        fill_head(fc)
        fill_chart(fc)


render_overview()
