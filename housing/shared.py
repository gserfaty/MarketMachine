"""Shared loaders, caches and cross-page helpers for the app pages."""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
import plotly.colors as pcolors
import plotly.graph_objects as go
import streamlit as st

from housing import analysis, data, finance, model, precompute, ui
from housing.ui import AMBER, GREY, INK, TEAL, UP, DOWN, VIOLET, fmt_pct, show, signed

DISCLAIMER = ui.D1
CC = st.column_config
SORTS = {"1-year change": "chg_1y", "5-year change": "chg_5y", "10-year change": "chg_10y", "Typical value": "value"}


def _data_dir_key() -> str | None:
    # Included in cache keys below so that a changed MARKETMACHINE_DATA_DIR (e.g.
    # between test runs, or offline vs. online) correctly invalidates the cache.
    return os.environ.get("MARKETMACHINE_DATA_DIR")


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


@st.cache_data(ttl=86400, show_spinner="Loading Zillow's forecast")
def cached_zillow_forecast(data_dir: str | None = None) -> pd.DataFrame | None:
    try:
        return data.load_zillow_forecast()
    except Exception:
        return None


@st.cache_data(ttl=86400, show_spinner="Loading affordability data")
def cached_affordability(data_dir: str | None = None) -> pd.DataFrame | None:
    try:
        return data.load_affordability()
    except Exception:
        return None


@st.cache_resource(show_spinner="Training the forecast model (first load takes a minute)")
def cached_forecast(as_of_key: str, _long_df: pd.DataFrame, _mortgage, _supply, horizon: int = 12, _months_supply=None) -> model.ForecastResult:
    if (pre := precompute.use(_cached_precomputed(horizon), as_of_key)) is not None:
        return pre
    return model.train_and_evaluate(_long_df, _mortgage, supply=_supply, horizon=horizon, months_supply=_months_supply)


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _cached_precomputed(horizon: int) -> str | None:
    return precompute.fetch(horizon)


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


def _try_forecast(metro_df: pd.DataFrame, horizon: int = 12) -> model.ForecastResult | None:
    try:
        return _forecast(metro_df, horizon)
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
    ui.end_range(fig, min(s.index[0] for _, s, _, _ in series), max(s.index[-1] for _, s, _, _ in series))
    ys = pd.concat([x[1] for x in series])
    pad = (ys.max() - ys.min()) * 0.05
    fig.update_yaxes(tickformat="$,.0f", title=ytitle, range=[ys.min() - pad, ys.max() + pad])
    return fig


def _short(name: str) -> str:
    return name.split(",")[0]


def _num_cols() -> dict:
    return {
        "region": CC.TextColumn("Metro"), "state": CC.TextColumn("State", width="small"),
        "value": CC.NumberColumn("Typical value", format="$%,d"),
        "size_rank": CC.NumberColumn("Size rank", format="%d"),
        "chg_1y": CC.TextColumn("Change, 1 year"), "chg_5y": CC.TextColumn("Change, 5 years"),
        "chg_10y": CC.TextColumn("Change, 10 years"),
        "pred": CC.TextColumn("Predicted change (80% range)"),
        "zillow": CC.TextColumn("Zillow's forecast"),
    }


def _table(df: pd.DataFrame, cols: list[str], **kw) -> None:
    """Dataframe with plain-word headers; change columns become signed ▲/▼ strings."""
    out = df[cols].copy()
    for c in ("chg_1y", "chg_5y", "chg_10y"):
        if c in out:
            out[c] = out[c].map(fmt_pct)
    st.dataframe(out, hide_index=True, width="stretch", column_config=_num_cols(), **kw)


def fmt_range(pred, lo, hi) -> str:
    return f"{fmt_pct(pred)} ({signed(lo)} to {signed(hi)})"


def _range_table(df: pd.DataFrame) -> pd.DataFrame:
    out = df[["region", "state", "value"]].copy()
    out["pred"] = [fmt_range(p, l, h) for p, l, h in zip(df["pred_12m"], df["lo_12m"], df["hi_12m"])]
    return out


def _forecast(metro_df: pd.DataFrame, horizon: int = 12) -> model.ForecastResult:
    mortgage = cached_fred("MORTGAGE30US", _data_dir_key())
    supply = cached_supply(_data_dir_key())
    ms = cached_fred("MSACSR", _data_dir_key())
    return cached_forecast(model.as_of_key(metro_df, supply, ms), metro_df, mortgage, supply, horizon, ms)


def _forecast_failed() -> None:
    st.error("Couldn't build the forecast right now. This is usually temporary. Try again in a few minutes.")
    ui.retry_button("retry_forecast")


NEUTRAL = "#e9e3e2"  # map color for 0% / lowest value; dark enough to show against the page


def _state_map(table: pd.DataFrame, metric: str, label: str) -> None:
    """US choropleth of one metric per state; numbers on hover and in the sorted table beside it."""
    t = table.dropna(subset=[metric]).copy()
    t["abbr"] = t["state"].map(data.STATE_ABBR).fillna(t["region"].map(data.STATE_ABBR))
    t = t.dropna(subset=["abbr"])
    if t.empty:
        return
    is_val = metric == "value"
    name = t["state"].where(t["state"].isin(data.STATE_ABBR), t["region"])
    shown = [f"${x:,.0f}" if is_val else fmt_pct(x) for x in t[metric]]
    if is_val:
        z, zmin, zmax = t[metric], float(t[metric].min()), float(t[metric].max())
        scale = [[0, NEUTRAL], [1, INK]]
        tv, tt = [zmin, zmax], [f"${zmin / 1000:,.0f}k", f"${zmax / 1000:,.0f}k"]
    else:
        v = t[metric] * 100
        lo, hi = min(0.0, float(np.nanpercentile(v, 5))), max(0.0, float(np.nanpercentile(v, 95)))
        hi = hi if hi > lo else lo + 1.0
        z, zmin, zmax = v.clip(lo, hi), lo, hi
        mid = -lo / (hi - lo)  # where 0% sits, so the scale only spends color on the side the data uses
        m = max(-lo, hi)  # same intensity for the same size of move up or down
        tint = lambda c, x: pcolors.label_rgb(pcolors.find_intermediate_color(pcolors.hex_to_rgb(NEUTRAL), pcolors.hex_to_rgb(c), x / m, "tuple"))
        scale = [[0, tint(DOWN, -lo)], [mid, NEUTRAL], [1, tint(UP, hi)]]
        tv = sorted({x for x in (lo, 0.0, hi) if x == 0.0 or abs(x) > 0.12 * (hi - lo)})
        tt = [f"{x:+.0f}%".replace("-", "−") if x else "0%" for x in tv]
    fig = go.Figure(go.Choropleth(
        locations=t["abbr"], locationmode="USA-states", z=z, zmin=zmin, zmax=max(zmax, zmin + 1e-9), colorscale=scale,
        marker=dict(line=dict(color="#fdfcfc", width=1)), customdata=list(zip(name, shown)),
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>",
        colorbar=dict(tickvals=tv, ticktext=tt, orientation="h", x=0.5, y=0, yanchor="top", len=0.5, thickness=8,
                      outlinewidth=0)))
    fig.update_geos(scope="usa", showlakes=False, bgcolor="rgba(0,0,0,0)")
    fig.update_layout(height=380, margin=dict(l=0, r=0, t=0, b=40), dragmode=False)
    c1, c2 = st.columns([5, 2])
    with c1:
        show(fig)
    with c2:
        order = np.argsort(-t[metric].to_numpy())
        st.dataframe(pd.DataFrame({"State": name.to_numpy()[order], label: np.array(shown)[order]}),
                     hide_index=True, width="stretch", height=380)
