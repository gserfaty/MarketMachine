"""Shared loaders, caches and cross-page helpers for the app pages."""
from __future__ import annotations

import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

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
    return model.train_and_evaluate(_long_df, _mortgage, supply=_supply, horizon=horizon, months_supply=_months_supply)


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
