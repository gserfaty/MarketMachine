"""Regional explorer page."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from housing import analysis, data, ui
from housing.ui import GREY, INK, UP, DOWN, fmt_pct, show, signed
from housing.shared import CC, SORTS, CENTER, _safe_load_metro, _safe_load_state, _footer_disclaimer, _need, _mon, _lines, _short, _num_cols


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
                lo, hi = st.slider("Home value range", vmin, vmax, (vmin, vmax), format="$%d", key=f"f_value_{mode}_{vmin}_{vmax}")
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
        ui.headline(f"{len(table)} {noun} shown." + (f" The median 1-year change is {fmt_pct(med)}, led by {top['region']} ({fmt_pct(top['chg_1y'])})."
                                                     if top is not None else ""))
    k1, k2, k3 = kpis.columns(3)
    ui.kpi(k1, "Regions shown", f"{len(table):,}")
    ui.kpi(k2, "Median 1-year change", fmt_pct(med))
    if top is not None:
        ui.kpi(k3, "Top mover", _short(top["region"]), signed(top["chg_1y"]))
    else:
        ui.kpi(k3, "Top mover", "n/a")

    st.subheader("Ranked regions")
    cols = ["region", "state", "value", "chg_1y", "chg_5y", "chg_10y"]
    if mode == "State":
        cols.remove("state")
    st.dataframe(table.assign(**{c: table[c].map(fmt_pct) for c in ("chg_1y", "chg_5y", "chg_10y")})[cols], hide_index=True,
                 width="stretch", column_config=_num_cols() | {"region": CC.TextColumn(mode)})

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


render_explorer()
