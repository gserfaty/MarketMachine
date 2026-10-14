"""Streamlit rendering for the 6 app pages (presentation and wiring only; logic lives in analysis/model/finance)."""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from housing import analysis, data, finance, model, ui
from housing.ui import AMBER, GREY, INK, TEAL, UP, DOWN, VIOLET, fmt_pct, show, signed

DISCLAIMER = ui.D1
CC = st.column_config
SORTS = {"1-year change": "chg_1y", "5-year change": "chg_5y", "10-year change": "chg_10y", "Typical value": "value"}
# approximate state centroids (lat, lon) for the map's per-state labels
CENTER = {
    "AL": (32.8, -86.8), "AK": (64.2, -152.5), "AZ": (34.3, -111.7), "AR": (34.9, -92.4), "CA": (37.2, -119.5),
    "CO": (39.0, -105.5), "CT": (41.6, -72.7), "DE": (39.0, -75.5), "DC": (38.9, -77.0), "FL": (28.6, -82.4),
    "GA": (32.7, -83.4), "HI": (20.8, -156.3), "ID": (44.4, -114.6), "IL": (40.0, -89.2), "IN": (39.9, -86.3),
    "IA": (42.1, -93.5), "KS": (38.5, -98.4), "KY": (37.5, -85.3), "LA": (31.1, -92.0), "ME": (45.3, -69.2),
    "MD": (39.0, -76.8), "MA": (42.3, -71.8), "MI": (44.3, -85.4), "MN": (46.3, -94.3), "MS": (32.7, -89.7),
    "MO": (38.4, -92.5), "MT": (47.0, -109.6), "NE": (41.5, -99.8), "NV": (39.3, -116.6), "NH": (43.7, -71.6),
    "NJ": (40.1, -74.7), "NM": (34.4, -106.1), "NY": (42.9, -75.5), "NC": (35.5, -79.4), "ND": (47.5, -100.5),
    "OH": (40.3, -82.8), "OK": (35.6, -97.5), "OR": (43.9, -120.6), "PA": (40.9, -77.8), "RI": (41.7, -71.5),
    "SC": (33.9, -80.9), "SD": (44.4, -100.2), "TN": (35.9, -86.4), "TX": (31.5, -99.3), "UT": (39.3, -111.7),
    "VT": (44.0, -72.7), "VA": (37.5, -78.8), "WA": (47.4, -120.5), "WV": (38.6, -80.6), "WI": (44.6, -89.9),
    "WY": (43.0, -107.6),
}


def _data_dir_key() -> str | None:
    # Included in cache keys below so that a changed MICHIGANMEN_DATA_DIR (e.g.
    # between test runs, or offline vs. online) correctly invalidates the cache.
    return os.environ.get("MICHIGANMEN_DATA_DIR")


@st.cache_data(ttl=86400, show_spinner="Loading home-value data")
def cached_zhvi(kind: str, data_dir: str | None = None) -> pd.DataFrame:
    return data.load_zhvi(kind)


@st.cache_data(ttl=86400, show_spinner="Loading mortgage rates")
def cached_fred(series_id: str, data_dir: str | None = None) -> pd.Series | None:
    try:
        return data.load_fred(series_id)
    except Exception:
        return None


@st.cache_data(ttl=86400, show_spinner="Loading listings data")
def cached_supply(data_dir: str | None = None) -> pd.DataFrame | None:
    try:
        return data.load_supply()
    except Exception:
        return None


@st.cache_resource(show_spinner="Training the forecast model (first load takes a minute)")
def cached_forecast(as_of_key: str, _long_df: pd.DataFrame, _mortgage, _supply) -> model.ForecastResult:
    return model.train_and_evaluate(_long_df, _mortgage, supply=_supply)


def _safe_load_metro() -> pd.DataFrame | None:
    try:
        return cached_zhvi("metro", _data_dir_key())
    except Exception:  # noqa: BLE001
        return None


def _safe_load_state() -> pd.DataFrame | None:
    try:
        return cached_zhvi("state", _data_dir_key())
    except Exception:  # noqa: BLE001
        return None


def metro_regions() -> list[str] | None:
    """Metro names for the pickers; None when the Zillow metro data cannot be loaded."""
    df = _safe_load_metro()
    if df is None:
        return None
    return sorted(df.loc[df["region_type"] != "country", "region"].dropna().unique())


def _footer_disclaimer() -> None:
    ui.disclaimer()


def _need(df: pd.DataFrame | None, picker_key: str | None = None, text: str = ui.ZILLOW_DOWN) -> pd.DataFrame:
    """Zillow-down standard: warning + Try again, disabled picker, footer disclaimer, stop."""
    if df is None:
        if picker_key:
            ui.metro_picker(None, picker_key)
        ui.data_down(text)
        _footer_disclaimer()
        st.stop()
    return df


def _mon(ts) -> str:
    return f"{ts:%b %Y}"


def _try_forecast(metro_df: pd.DataFrame) -> model.ForecastResult | None:
    try:
        return _forecast(metro_df)
    except Exception:  # noqa: BLE001
        return None


def _lines(series: list[tuple[str, pd.Series, str, str]], ytitle: str, height: int = 360) -> go.Figure:
    """Named lines (name, date-indexed values, color, dash) with direct end labels instead of a legend."""
    fig = go.Figure()
    for i, (name, s, color, dash) in enumerate(series):
        fig.add_scatter(x=s.index, y=s.values, name=name, mode="lines", line=dict(color=color, dash=dash, width=2.5 if i == 0 else 1.5),
                        hovertemplate="%{y:$,.0f}")
        fig.add_annotation(x=s.index[-1], y=s.iloc[-1], text=name, showarrow=False, xanchor="left", xshift=6,
                           font=dict(size=12, color=ui.INK))
    fig.update_layout(showlegend=False, margin=dict(r=150), height=height)
    ys = pd.concat([x[1] for x in series])
    pad = (ys.max() - ys.min()) * 0.05
    fig.update_yaxes(tickformat="$,.0f", title=ytitle, range=[ys.min() - pad, ys.max() + pad])
    return fig


def _short(name: str) -> str:
    return name.split(",")[0]


def _num_cols() -> dict:
    return {
        "region": CC.TextColumn("Metro", pinned=True), "state": CC.TextColumn("State", width="small"),
        "value": CC.NumberColumn("Typical value", format="$%,d"),
        "size_rank": CC.NumberColumn("Size rank", format="%d"),
        "chg_1y": CC.TextColumn("Change, 1 year"), "chg_5y": CC.TextColumn("Change, 5 years"),
        "chg_10y": CC.TextColumn("Change, 10 years"),
        "pred": CC.TextColumn("Predicted change (80% range)"),
    }


def _table(df: pd.DataFrame, cols: list[str], **kw) -> None:
    """Dataframe with plain-word headers; change columns become signed ▲/▼ strings."""
    out = df[cols].copy()
    for c in ("chg_1y", "chg_5y", "chg_10y"):
        if c in out:
            out[c] = out[c].map(fmt_pct)
    st.dataframe(out, hide_index=True, width="stretch", column_config=_num_cols(), **kw)


# ---------------------------------------------------------------------------------------------------------------
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


def _state_map(table: pd.DataFrame, metric: str, label: str) -> None:
    t = table.dropna(subset=[metric]).copy()
    t["abbr"] = t["state"].map(data.STATE_ABBR).fillna(t["region"].map(data.STATE_ABBR))
    t = t.dropna(subset=["abbr"])
    if t.empty:
        return
    is_val = metric == "value"
    v = t[metric] if is_val else t[metric] * 100
    if is_val:
        steps = [[0, "#e3dcdc"], [0.4, "#b4a7a7"], [0.4, "#696160"], [1, "#312d2c"]]
        zmin, zmax = float(v.min()), float(v.max())
        zmax = zmax if zmax > zmin else zmin + 1
        z = v
        tv = [zmin, zmax]
        tt = [f"${zmin / 1000:,.0f}k", f"${zmax / 1000:,.0f}k"]
        frac = (z - zmin) / (zmax - zmin)
        white = frac > 0.4  # ink label on the light classes, white on the dark ones
    else:
        m = float(max(abs(np.nanpercentile(v, 5)), abs(np.nanpercentile(v, 95)))) or 1.0
        steps = [[0, DOWN], [0.2, DOWN], [0.2, "#e9f1ff"], [0.5, "#e3dcdc"], [0.8, "#e0f9dd"], [0.8, UP], [1, UP]]
        zmin, zmax, z = -m, m, v.clip(-m, m)
        tv = [-m, 0, m]
        tt = [f"−{m:.0f}%", "0%", f"+{m:.0f}%"]
        frac = (z + m) / (2 * m)
        white = (frac <= 0.2) | (frac > 0.8)
    txt = [f"{a} {fmt_pct(c)}" if not is_val else f"{a} ${x / 1000:,.0f}k" for a, c, x in zip(t["abbr"], t[metric], t["value"])]
    fig = go.Figure(go.Choropleth(
        locations=t["abbr"], locationmode="USA-states", z=z, zmin=zmin, zmax=zmax, colorscale=steps,
        marker=dict(line=dict(color="#fdfcfc", width=1)), text=txt, hoverinfo="text",
        colorbar=dict(title=label if is_val else "Change", tickvals=tv, ticktext=tt, thickness=12)))
    lat = [CENTER[a][0] for a in t["abbr"]]
    lon = [CENTER[a][1] for a in t["abbr"]]
    fig.add_trace(go.Scattergeo(lat=lat, lon=lon, mode="text", text=txt, hoverinfo="skip", showlegend=False,
                                textfont=dict(size=12, color=["#fdfcfc" if w else INK for w in white])))
    fig.update_geos(scope="usa", showlakes=False, bgcolor="#fdfcfc")
    fig.update_layout(height=420, margin=dict(l=0, r=0, t=0, b=0))
    c1, c2 = st.columns([3, 1])
    with c1:
        show(fig)
    with c2:
        st.dataframe(pd.DataFrame({"State": t["abbr"], label: [fmt_pct(x) if not is_val else f"${x:,.0f}" for x in t[metric]]})
                     .iloc[np.argsort(-t[metric].to_numpy())], hide_index=True, width="stretch")


def render_explorer() -> None:
    st.header("Regional explorer")
    head, kpis = st.container(), st.container()  # headline and KPIs first; filled once the controls below have run
    mode = st.radio("Region type", ["Metro", "State"], horizontal=True)
    kind = "metro" if mode == "Metro" else "state"
    long_df = _need(_safe_load_metro() if mode == "Metro" else _safe_load_state(),
                    text=f"Heads up: we can't reach Zillow's {kind}-level home-value data right now. "
                    "Check your connection, or try again in a few minutes."
                    + " The other region type may still work.")
    sort_choice = st.selectbox("Sort by", list(SORTS))
    sort_col = SORTS[sort_choice]

    metro_only = long_df[long_df["region_type"] != "country"]
    table = analysis.appreciation_table(metro_only)

    def _reset() -> None:
        for k in [k for k in st.session_state if str(k).startswith("f_")]:
            del st.session_state[k]

    with st.expander("Filters"):
        if mode == "Metro":
            states = sorted(table["state"].dropna().unique().tolist())
            chosen_states = st.multiselect("States", states, key="f_states")
            max_rank = int(table["size_rank"].max()) if not table.empty else 200
            top_n = st.slider("Largest metros to include", 1, max(max_rank, 1), min(200, max(max_rank, 1)), key="f_rank",
                              help="Size rank: 1 is the largest metro.")
            table = table[table["size_rank"] <= top_n]
            if chosen_states:
                table = table[table["state"].isin(chosen_states)]
        if not table.empty:
            vmin, vmax = float(table["value"].min()), float(table["value"].max())
            if vmin < vmax:
                lo, hi = st.slider("Home value range", vmin, vmax, (vmin, vmax), key=f"f_value_{mode}_{vmin}_{vmax}")
                table = table[(table["value"] >= lo) & (table["value"] <= hi)]
        st.button("Reset filters", on_click=_reset)

    table = table.sort_values(sort_col, ascending=False)
    if table.empty:
        st.info("No regions match these filters. Widen the size or value range, or reset the filters.")
        _footer_disclaimer()
        return

    noun = "metros" if mode == "Metro" else "states"
    med = table["chg_1y"].median()
    top = table.loc[table["chg_1y"].idxmax()] if table["chg_1y"].notna().any() else None
    with head:
        ui.headline(f"{len(table)} {noun} shown." + (f" The median 1-year change is {signed(med)}, led by {top['region']} ({signed(top['chg_1y'])})."
                                                     if top is not None else ""))
    k1, k2, k3 = kpis.columns(3)
    k1.metric("Regions shown", f"{len(table):,}", border=True)
    k2.metric("Median 1-year change", fmt_pct(med), border=True)
    if top is not None:
        ui.kpi(k3, "Top mover", _short(top["region"]), signed(top["chg_1y"]))
    else:
        k3.metric("Top mover", "n/a", border=True)

    st.subheader("Ranked regions")
    cols = ["region", "state", "value", "chg_1y", "chg_5y", "chg_10y"]
    if mode == "State":
        cols.remove("state")
    st.dataframe(table.assign(**{c: table[c].map(fmt_pct) for c in ("chg_1y", "chg_5y", "chg_10y")})[cols], hide_index=True,
                 width="stretch", column_config=_num_cols() | {"region": CC.TextColumn(mode, pinned=True)})

    st.subheader(f"Top 20 by {sort_choice.lower()}")
    top20 = table.head(20)
    is_val = sort_col == "value"
    x = top20[sort_col] if is_val else top20[sort_col] * 100
    colors = [INK if is_val else (UP if v > 0 else DOWN) for v in x]
    labels = [f"${v:,.0f}" if is_val else fmt_pct(v / 100) for v in x]
    fig = go.Figure(go.Bar(y=top20["region"], x=x, orientation="h", marker_color=colors, text=labels, textposition="outside",
                           textfont=dict(size=12, color=INK), hoverinfo="skip", cliponaxis=False))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showgrid=True, gridcolor="#ece6e6", showline=False, zeroline=False)
    if is_val:
        fig.update_xaxes(tickformat="$,.0f")
    else:
        ui.signed_axis(fig, min(0.0, float(x.min())), max(0.0, float(x.max())), axis="x")
    if not is_val:
        fig.add_vline(x=0, line_width=1, line_color=GREY)
    fig.update_layout(height=max(280, 28 * len(top20) + 80), margin=dict(l=48, r=80, t=16, b=40), hovermode="closest")
    show(fig)

    if mode == "State":
        st.subheader("Map by state")
        label = st.selectbox("Map shows", list(SORTS), key="choropleth")
        _state_map(table, SORTS[label], label if SORTS[label] == "value" else "12-month change" if SORTS[label] == "chg_1y" else label)

    if mode == "Metro":
        region = ui.metro_picker(sorted(metro_only["region"].dropna().unique()), "explorer", label="Region",
                                 placeholder="Choose a metro")
    else:
        region = st.selectbox("Region", table["region"].tolist(), index=None, placeholder="Choose a state")
    if region:
        st.subheader(f"{region} price history")
        hist = metro_only[metro_only["region"] == region].sort_values("date").set_index("date")["value"]
        us_src = long_df if mode == "Metro" else _safe_load_metro()
        us_hist = analysis.national_series(us_src) if us_src is not None else None
        lines = [(_short(region), hist, INK, "solid")]
        if us_hist is not None and not us_hist.empty:
            lines.append(("United States", us_hist, GREY, "dash"))
        show(_lines(lines, "Typical value ($)"))
        st.caption(f"{_short(region)} compared with the United States. Zillow, through {_mon(hist.index.max())}.")
        if mode == "Metro":
            c1, c2, _ = st.columns([1, 1, 2])
            with c1:
                ui.go_to("profile", f"See {_short(region)} profile")
            with c2:
                ui.go_to("forecast", "See forecast")
    else:
        st.write("Choose a region from the table to see its price history.")

    _footer_disclaimer()


def fmt_range(pred, lo, hi) -> str:
    return f"{fmt_pct(pred)} ({signed(lo)} to {signed(hi)})"


def _range_table(df: pd.DataFrame) -> pd.DataFrame:
    out = df[["region", "state", "value"]].copy()
    out["pred"] = [fmt_range(p, l, h) for p, l, h in zip(df["pred_12m"], df["lo_12m"], df["hi_12m"])]
    return out


def _forecast(metro_df: pd.DataFrame) -> model.ForecastResult:
    mortgage = cached_fred("MORTGAGE30US", _data_dir_key())
    supply = cached_supply(_data_dir_key())
    as_of_key = f"{metro_df['date'].max()}|supply={supply is not None}"
    return cached_forecast(as_of_key, metro_df, mortgage, supply)


def _forecast_failed() -> None:
    st.error("Couldn't build the forecast right now. This is usually temporary. Try again in a few minutes.")
    ui.retry_button("retry_forecast")


def render_forecast() -> None:
    st.header("ML forecast")
    st.caption("Where prices may be headed, and how far to trust it.")
    metro_df = _need(_safe_load_metro(), "forecast", ui.ZILLOW_DOWN + " The national forecast needs the same data.")
    supply = cached_supply(_data_dir_key())
    result = _try_forecast(metro_df)
    if result is None:
        _forecast_failed()
        _footer_disclaimer()
        st.stop()

    m = result.metrics
    mo, bl, nv, zr = m.loc["model"], m.loc["blend"], m.loc["naive_momentum"], m.loc["zero"]
    metro = st.session_state.get("metro")
    row = result.predictions[result.predictions["region"] == metro] if metro else result.predictions.iloc[0:0]
    if len(row):
        r = row.iloc[0]
        pred, lo, hi, region = r["pred_12m"], r["lo_12m"], r["hi_12m"], metro
        text = f"{_short(metro)} home values: forecast {signed(pred)} over the next 12 months (80% range {signed(lo)} to {signed(hi)})."
    else:
        pred, (lo, hi), region = result.national_pred, result.national_interval, "United States"
        text = (f"US home values: forecast {signed(pred)} over the next 12 months (80% range {signed(lo)} to {signed(hi)})."
                + ("" if metro else " Choose a metro for its forecast."))
    ui.headline(text, f"80% range: in past tests, the actual change landed inside a range this wide {bl['coverage80']:.0%} of the time.")
    ui.disclaimer()
    if len(row):
        st.caption(f"Using {metro} (from Market overview).")
    elif metro:
        st.info(f"No forecast for {metro} yet. It doesn't have enough price history. Showing the US forecast instead.")
    ui.metro_picker(metro_regions(), "forecast", placeholder="Choose a metro to see its forecast")
    if supply is None:
        st.warning("Heads up: Zillow listings data is unavailable, so the forecast runs without inventory data.")
    if cached_fred("MORTGAGE30US", _data_dir_key()) is None:
        st.warning("Heads up: mortgage rates are unavailable, so the forecast runs without them and may be less accurate.")
    if bl["MAE"] > mo["MAE"]:
        st.warning("Heads up: in this round of tests the combined forecast was slightly less accurate than the model alone.")

    k1, k2, k3 = st.columns(3)
    k1.metric("Typical miss (points)", f"{bl['MAE']:.1f}", border=True,
              help="Average miss (mean absolute error, MAE) of the combined forecast.")
    dacc = bl["direction_acc"] if pd.notna(bl["direction_acc"]) else mo["direction_acc"]
    k2.metric("Direction calls right", f"{round(dacc * 10)} of 10", border=True,
              help="Share of cases where the forecast got up versus down right (direction accuracy).")
    k3.metric("Versus a no-change guess (points)", f"{bl['MAE']:.1f} vs {zr['MAE']:.1f}", border=True,
              help="Typical miss of our combined forecast versus assuming prices stay flat.")
    st.caption("Across all metros, past tests.")

    hist = metro_df[metro_df["region"] == region].sort_values("date").set_index("date")["value"]
    st.subheader(f"{_short(region)} price history and forecast" if region != "United States" else "US price history and forecast")
    ui.show(ui.history_band(hist, pred, lo, hi, name=_short(region)))
    st.caption(f"Zillow, through {_mon(hist.index.max())}. Dashed line and shaded area: forecast and its 80% range.")

    st.subheader("What goes into this forecast")
    mort = cached_fred("MORTGAGE30US", _data_dir_key())
    inv = float("nan")
    if supply is not None:
        s = supply[supply["region"] == region].sort_values("date").set_index("date")["inventory"].dropna()
        inv = s.iloc[-1] / s.iloc[-13] - 1 if len(s) > 12 else float("nan")
    w1, w2, w3 = st.columns(3)
    w1.metric("12-month price change", fmt_pct(hist.iloc[-1] / hist.iloc[-13] - 1 if len(hist) > 12 else float("nan")))
    w2.metric("Mortgage rate", f"{mort.dropna().iloc[-1]:.2f}%" if mort is not None and not mort.dropna().empty else "n/a")
    w3.metric("Homes for sale trend", fmt_pct(inv))

    if metro and len(row):
        c1, c2, _ = st.columns([1, 1, 1])
        with c1:
            ui.go_to("financing", f"Estimate financing in {_short(metro)}", primary=True)
        with c2:
            ui.go_to("profile", f"See {_short(metro)} profile")

    st.subheader("All metro forecasts")
    st.caption("How many metros fall at each predicted change.")
    fig = go.Figure(go.Histogram(x=result.predictions["pred_12m"] * 100, nbinsx=30, marker_color=GREY))
    fig.add_vline(x=0, line_width=1, line_color=INK, annotation_text="0% (no change)", annotation_font=dict(size=12, color="#696160"))
    px_ = result.predictions["pred_12m"] * 100
    ui.signed_axis(fig, float(px_.min()), float(px_.max()), axis="x", title="Predicted 12-month change")
    fig.update_yaxes(title="Metros")
    show(fig, 280)
    search = st.text_input("Search metros")
    preds = result.predictions.copy()
    if search:
        preds = preds[preds["region"].str.contains(search, case=False, na=False)]
    _table(_range_table(preds), ["region", "state", "value", "pred"], height=320)

    with st.expander("How we tested this"):
        _backtest_detail(result)

    with st.expander("How the forecast works"):
        st.write(
            "A gradient-boosted tree model is trained on point-in-time price-momentum, "
            "volatility, and macro features to predict each metro's 12-month log return. "
            "It is evaluated with a yearly rolling-origin backtest (2010 onward): each year is "
            "predicted by a model trained only on rows whose 12-month outcome was already known "
            "at the start of that year, and compared with a naive momentum baseline and a "
            "zero-change baseline. Backtest fits use quarterly origins only, for speed. The served forecast is the equal-weight "
            "average of the model and the trailing-12-month momentum, in simple-return space, and it "
            "is scored in the same backtest."
        )

    _footer_disclaimer()


def _backtest_detail(result: model.ForecastResult) -> None:
    m = result.metrics
    names = {"model": "ML model", "blend": "Combined forecast", "naive_momentum": "Recent trend", "zero": "No change"}
    disp = m.copy()
    disp["direction_acc"] *= 100
    disp["coverage80"] *= 100
    disp = disp.rename(index=names, columns={
        "MAE": "Typical miss (points)", "bias": "Bias (points)", "direction_acc": "Direction right (%)",
        "rank_ic": "Ranking skill", "top_decile_lift": "Top picks beat average (points)", "coverage80": "Range hit rate (%)",
        "width80": "Range width (points)", "years": "Years tested"})
    st.dataframe(disp.round(2), width="stretch")

    bt = result.backtest
    per_year = bt[bt["predictor"].isin(["model", "blend", "naive_momentum"])].pivot(
        index="year", columns="predictor", values=["MAE", "bias", "rank_ic", "top_decile_lift"]
    )
    per_year.columns = [f"{metric} · {names[pred]}" for metric, pred in per_year.columns]
    blend_iv = bt[bt["predictor"] == "blend"].set_index("year")
    per_year["coverage80 · blend"] = blend_iv["coverage80"]
    per_year["width80 · blend"] = blend_iv["width80"]
    per_year["n"] = bt[bt["predictor"] == "model"].set_index("year")["n"]
    st.dataframe(per_year.round(2), width="stretch")

    st.subheader("Ranking skill by year")
    fig = go.Figure()
    for p, color, dash in (("model", INK, "solid"), ("blend", TEAL, "solid"), ("naive_momentum", GREY, "dash")):
        d = bt[bt["predictor"] == p].sort_values("year")
        fig.add_scatter(x=d["year"], y=d["rank_ic"], name=names[p], line=dict(color=color, dash=dash, width=2.5 if p == "model" else 1.5))
    fig.add_hline(y=0, line_width=1, line_color=GREY)
    fig.update_yaxes(title="Ranking skill (rank IC)")
    fig.update_xaxes(dtick=1)
    show(fig, 280)

    mo, bl, nv, zr = m.loc["model"], m.loc["blend"], m.loc["naive_momentum"], m.loc["zero"]
    tone = "pessimistic" if mo["bias"] < 0 else "optimistic"
    st.markdown(
        f"- Typical miss: model {mo['MAE']:.2f} points vs combined forecast {bl['MAE']:.2f} vs recent trend {nv['MAE']:.2f} vs no-change {zr['MAE']:.2f}.\n"
        f"- The model leans {tone} by {abs(mo['bias']):.2f} points on average.\n"
        f"- Ranking skill (rank IC {mo['rank_ic']:.2f} model, {bl['rank_ic']:.2f} blend, {nv['rank_ic']:.2f} momentum): "
        "how well forecasts order metros from best to worst. 0 = random ordering, 1 = perfect; above ~0.3 is useful.\n"
        f"- Top picks (top 10%) beat the average metro by {mo['top_decile_lift']:.2f} points a year "
        f"(recent trend: {nv['top_decile_lift']:.2f}).\n"
        f"- Direction right {mo['direction_acc'] * 100:.0f}% of the time."
    )
    st.info(
        "Served forecast: **blend** (combined forecast) = average of the ML model and naive momentum (simple returns). "
        f"Backtest average MAE: blend {bl['MAE']:.2f} pp vs model {mo['MAE']:.2f} pp vs momentum {nv['MAE']:.2f} pp; "
        f"rank IC: blend {bl['rank_ic']:.2f} vs model {mo['rank_ic']:.2f} vs momentum {nv['rank_ic']:.2f}. "
        "The blend is served because averaging two partly independent forecasts cuts the miss. "
        "The model weights recent history more (3-year half-life), which lowered backtest MAE slightly; "
        "it does not remove the pessimistic bias. "
        "Since step 4 the model also uses metro for-sale inventory (YoY) and the share of listings "
        "with a price cut (Zillow, from 2018)."
    )
    st.caption(
        f"80% range: in the backtest (2012+, ranges built only from earlier years) the actual 12-month change "
        f"fell inside it {bl['coverage80']:.0%} of the time; average width {bl['width80']:.1f} pp. "
        "Misses cluster in market-wide shocks (2020, 2022), when the range is too narrow for every metro at once."
    )


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
