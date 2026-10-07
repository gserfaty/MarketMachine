"""Streamlit rendering for the 4 app pages."""
from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from housing import analysis, data, model

DISCLAIMER = "Forecasts are statistical estimates, not financial advice."


def _data_dir_key() -> str | None:
    # Included in cache keys below so that a changed MICHIGANMEN_DATA_DIR (e.g.
    # between test runs, or offline vs. online) correctly invalidates the cache.
    return os.environ.get("MICHIGANMEN_DATA_DIR")


@st.cache_data(ttl=86400, show_spinner="Loading Zillow home value data...")
def cached_zhvi(kind: str, data_dir: str | None = None) -> pd.DataFrame:
    return data.load_zhvi(kind)


@st.cache_data(ttl=86400, show_spinner="Loading FRED series...")
def cached_fred(series_id: str, data_dir: str | None = None) -> pd.Series | None:
    try:
        return data.load_fred(series_id)
    except Exception:
        return None


@st.cache_resource(show_spinner="Training forecast model...")
def cached_forecast(as_of_key: str, _long_df: pd.DataFrame, _mortgage) -> model.ForecastResult:
    return model.train_and_evaluate(_long_df, _mortgage)


def _safe_load_metro() -> pd.DataFrame | None:
    try:
        return cached_zhvi("metro", _data_dir_key())
    except Exception as e:  # noqa: BLE001
        st.error(f"Zillow data unavailable: {e}")
        return None


def _safe_load_state() -> pd.DataFrame | None:
    try:
        return cached_zhvi("state", _data_dir_key())
    except Exception as e:  # noqa: BLE001
        st.error(f"Zillow data unavailable: {e}")
        return None


def _footer_disclaimer() -> None:
    st.caption(DISCLAIMER)


def render_overview() -> None:
    st.header("Market overview")
    metro_df = _safe_load_metro()
    if metro_df is None:
        st.stop()
        return

    us_series = analysis.national_series(metro_df)
    mortgage = cached_fred("MORTGAGE30US", _data_dir_key())
    case_shiller = cached_fred("CSUSHPINSA", _data_dir_key())

    latest_value = us_series.iloc[-1]
    yoy_series = analysis.yoy(us_series)
    latest_yoy = yoy_series.iloc[-1] if len(yoy_series) else float("nan")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("US typical home value", f"${latest_value:,.0f}")
    col2.metric("YoY change", f"{latest_yoy * 100:,.1f}%" if pd.notna(latest_yoy) else "n/a")

    if mortgage is not None and not mortgage.empty:
        mort_latest = mortgage.iloc[-1]
        mort_12m_ago = mortgage.iloc[-13] if len(mortgage) > 12 else float("nan")
        mort_chg = mort_latest - mort_12m_ago if pd.notna(mort_12m_ago) else float("nan")
        col3.metric(
            "30-yr mortgage rate",
            f"{mort_latest:.2f}%",
            f"{mort_chg:+.2f} pp (12m)" if pd.notna(mort_chg) else None,
        )
    else:
        col3.metric("30-yr mortgage rate", "n/a")
        st.warning("FRED mortgage data unavailable; macro charts hidden.")

    if case_shiller is not None and not case_shiller.empty:
        cs_yoy = analysis.yoy(case_shiller)
        cs_latest_yoy = cs_yoy.iloc[-1] if len(cs_yoy) else float("nan")
        col4.metric("Case-Shiller YoY", f"{cs_latest_yoy * 100:,.1f}%" if pd.notna(cs_latest_yoy) else "n/a")
    else:
        col4.metric("Case-Shiller YoY", "n/a")

    st.caption(
        f"Zillow data as of {us_series.index.max():%Y-%m-%d}"
        + (f" · FRED as of {mortgage.index.max():%Y-%m-%d}" if mortgage is not None and not mortgage.empty else "")
    )

    st.subheader("US typical home value since 2000")
    st.plotly_chart(px.line(us_series, labels={"value": "Typical value ($)", "date": "Date"}), use_container_width=True)

    st.subheader("YoY change vs. mortgage rate")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=yoy_series.index, y=yoy_series * 100, name="US ZHVI YoY %"))
    if mortgage is not None and not mortgage.empty:
        fig.add_trace(
            go.Scatter(x=mortgage.index, y=mortgage, name="30-yr mortgage rate %", yaxis="y2")
        )
    fig.update_layout(
        yaxis=dict(title="ZHVI YoY %"),
        yaxis2=dict(title="Mortgage rate %", overlaying="y", side="right"),
        legend=dict(orientation="h"),
    )
    st.plotly_chart(fig, use_container_width=True)

    if case_shiller is not None and not case_shiller.empty:
        st.subheader("Case-Shiller US National Home Price Index")
        st.plotly_chart(px.line(case_shiller), use_container_width=True)

    _footer_disclaimer()


def render_explorer() -> None:
    st.header("Regional explorer")
    mode = st.radio("Region type", ["Metro", "State"], horizontal=True)

    if mode == "Metro":
        long_df = _safe_load_metro()
    else:
        long_df = _safe_load_state()
    if long_df is None:
        st.stop()
        return

    metro_only = long_df[long_df["region_type"] != "country"]
    table = analysis.appreciation_table(metro_only)

    if mode == "Metro":
        states = sorted(table["state"].dropna().unique().tolist())
        chosen_states = st.multiselect("States", states)
        max_rank = int(table["size_rank"].max()) if not table.empty else 200
        min_rank = st.slider("Top N metros by size rank", 1, max(max_rank, 1), min(200, max(max_rank, 1)))
        table = table[table["size_rank"] <= min_rank]
        if chosen_states:
            table = table[table["state"].isin(chosen_states)]

    if not table.empty:
        vmin, vmax = float(table["value"].min()), float(table["value"].max())
        if vmin < vmax:
            value_range = st.slider("Value range ($)", vmin, vmax, (vmin, vmax))
            table = table[(table["value"] >= value_range[0]) & (table["value"] <= value_range[1])]

    sort_choice = st.selectbox("Sort by", ["1-yr change", "5-yr change", "10-yr change", "Value"])
    sort_col = {
        "1-yr change": "chg_1y",
        "5-yr change": "chg_5y",
        "10-yr change": "chg_10y",
        "Value": "value",
    }[sort_choice]
    table = table.sort_values(sort_col, ascending=False)

    display = table.copy()
    for c in ("chg_1y", "chg_5y", "chg_10y"):
        display[c] = (display[c] * 100).map(lambda v: f"{v:,.1f}%" if pd.notna(v) else "n/a")
    display["value"] = display["value"].map(lambda v: f"${v:,.0f}")
    st.dataframe(display, use_container_width=True, hide_index=True)

    st.subheader(f"Top 20 by {sort_choice}")
    top20 = table.head(20)
    if not top20.empty:
        st.plotly_chart(
            px.bar(top20, x="region", y=sort_col, labels={sort_col: sort_choice}), use_container_width=True
        )

    if mode == "State":
        metric_choice = st.selectbox("Choropleth metric", ["chg_1y", "chg_5y", "chg_10y", "value"], key="choropleth")
        choro = table.dropna(subset=[metric_choice])
        if not choro.empty:
            choro = choro.copy()
            choro["state_abbr"] = choro["state"].map(data.STATE_ABBR).fillna(choro["region"].map(data.STATE_ABBR))
            choro = choro.dropna(subset=["state_abbr"])
            if not choro.empty:
                st.plotly_chart(
                    px.choropleth(
                        choro,
                        locations="state_abbr",
                        locationmode="USA-states",
                        color=metric_choice,
                        scope="usa",
                    ),
                    use_container_width=True,
                )

    if not table.empty:
        region_choice = st.selectbox("Region history", table["region"].tolist())
        region_hist = metro_only[metro_only["region"] == region_choice].sort_values("date")
        us_hist = analysis.national_series(long_df if mode == "Metro" else _safe_load_metro())
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=region_hist["date"], y=region_hist["value"], name=region_choice))
        if us_hist is not None and not us_hist.empty:
            fig.add_trace(go.Scatter(x=us_hist.index, y=us_hist, name="United States"))
        st.plotly_chart(fig, use_container_width=True)

    _footer_disclaimer()


def render_forecast() -> None:
    st.header("ML forecast")
    metro_df = _safe_load_metro()
    if metro_df is None:
        st.stop()
        return
    mortgage = cached_fred("MORTGAGE30US", _data_dir_key())

    as_of_key = str(metro_df["date"].max())
    result = cached_forecast(as_of_key, metro_df, mortgage)

    st.subheader("How well has the model done? (backtest)")
    m = result.metrics
    disp = m.copy()
    for c in ("MAE", "bias", "top_decile_lift"):
        disp[c] = m[c].map(lambda v: "n/a" if pd.isna(v) else f"{v:.2f} pp")
    disp["direction_acc"] = m["direction_acc"].map(lambda v: f"{v * 100:.1f}%")
    disp["rank_ic"] = m["rank_ic"].map(lambda v: "n/a" if pd.isna(v) else f"{v:.2f}")
    st.dataframe(disp, use_container_width=True)

    bt = result.backtest
    per_year = bt[bt["predictor"].isin(["model", "naive_momentum"])].pivot(
        index="year", columns="predictor", values=["MAE", "bias", "rank_ic", "top_decile_lift"]
    )
    per_year.columns = [f"{metric} · {pred}" for metric, pred in per_year.columns]
    per_year["n"] = bt[bt["predictor"] == "model"].set_index("year")["n"]
    st.dataframe(per_year.round(2), use_container_width=True)

    ic = bt[bt["predictor"].isin(["model", "naive_momentum"])]
    st.plotly_chart(px.line(ic, x="year", y="rank_ic", color="predictor", title="Rank IC by year"),
                    use_container_width=True)

    mo, nv, zr = m.loc["model"], m.loc["naive_momentum"], m.loc["zero"]
    tone = "pessimistic" if mo["bias"] < 0 else "optimistic"
    st.markdown(
        f"- Average miss: model {mo['MAE']:.2f} pp vs momentum {nv['MAE']:.2f} pp vs no-change {zr['MAE']:.2f} pp.\n"
        f"- Bias: model is on average {abs(mo['bias']):.2f} pp too {tone}.\n"
        f"- Ranking (rank IC {mo['rank_ic']:.2f} vs {nv['rank_ic']:.2f} for momentum): "
        "0 = random ordering, 1 = perfect; above ~0.3 is a useful ranking.\n"
        f"- Top-10% picks beat the average metro by {mo['top_decile_lift']:.2f} pp/yr "
        f"(momentum: {nv['top_decile_lift']:.2f} pp).\n"
        f"- Direction right {mo['direction_acc'] * 100:.0f}% of the time."
    )

    if mo["MAE"] < nv["MAE"] and mo["rank_ic"] > nv["rank_ic"]:
        st.success("The model beats the naive momentum baseline on both error (MAE) and ranking (rank IC).")
    else:
        st.info("The model does not beat the naive momentum baseline on both error (MAE) and ranking (rank IC).")

    direction = "Up" if result.national_pred >= 0 else "Down"
    st.metric(
        "National 12-month call",
        f"{direction}, {result.national_pred * 100:+.1f}% predicted",
    )

    st.subheader("Distribution of metro-level 12-month predictions")
    st.plotly_chart(px.histogram(result.predictions, x="pred_12m", nbins=30), use_container_width=True)

    st.subheader("Per-metro predictions")
    search = st.text_input("Search region")
    preds = result.predictions.copy()
    if search:
        preds = preds[preds["region"].str.contains(search, case=False, na=False)]
    preds_display = preds.copy()
    preds_display["pred_12m"] = (preds_display["pred_12m"] * 100).map(lambda v: f"{v:+.1f}%")
    preds_display["value"] = preds_display["value"].map(lambda v: f"${v:,.0f}")
    st.dataframe(preds_display, use_container_width=True, hide_index=True)

    with st.expander("Methodology"):
        st.write(
            "A gradient-boosted tree model is trained on point-in-time price-momentum, "
            "volatility, and macro features to predict each metro's 12-month log return. "
            "It is evaluated with a yearly rolling-origin backtest (2010 onward): each year is "
            "predicted by a model trained only on rows whose 12-month outcome was already known "
            "at the start of that year, and compared with a naive momentum baseline and a "
            "zero-change baseline. Backtest fits use quarterly origins only, for speed."
        )

    _footer_disclaimer()


def render_findings() -> None:
    st.header("Findings")
    metro_df = _safe_load_metro()
    if metro_df is None:
        st.stop()
        return
    mortgage = cached_fred("MORTGAGE30US", _data_dir_key())

    metro_only = metro_df[metro_df["region_type"] != "country"]
    table = analysis.appreciation_table(metro_only)
    top_rank = table[table["size_rank"] <= 200]

    st.subheader("Top 15 gainers — 1 year")
    st.dataframe(
        top_rank.sort_values("chg_1y", ascending=False).head(15)[["region", "state", "value", "chg_1y"]],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Top 15 gainers — 5 years")
    st.dataframe(
        top_rank.sort_values("chg_5y", ascending=False).head(15)[["region", "state", "value", "chg_5y"]],
        use_container_width=True,
        hide_index=True,
    )

    as_of_key = str(metro_df["date"].max())
    result = cached_forecast(as_of_key, metro_df, mortgage)
    preds = result.predictions[result.predictions["region"] != "United States"]

    st.subheader("Top 15 predicted gainers (next 12 months)")
    st.dataframe(preds.sort_values("pred_12m", ascending=False).head(15), use_container_width=True, hide_index=True)

    st.subheader("Bottom 10 predicted (next 12 months)")
    st.dataframe(preds.sort_values("pred_12m", ascending=True).head(10), use_container_width=True, hide_index=True)

    st.subheader("Top 15 most valuable metros")
    st.dataframe(
        table.sort_values("value", ascending=False).head(15)[["region", "state", "value"]],
        use_container_width=True,
        hide_index=True,
    )

    st.warning(DISCLAIMER)

def render_market_profiles():
    st.header("Market Profiles")

    metro_df = _safe_load_metro()
    if metro_df is None:
        st.stop()
        return

    metro_only = metro_df[metro_df["region_type"] != "country"]
    table = analysis.appreciation_table(metro_only)
    markets = sorted(metro_only["region"].dropna().unique())

    selected = st.selectbox("Select a market", markets)
    market = table[table["region"] == selected].iloc[0]
    history = metro_only[metro_only["region"] == selected].sort_values("date")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Home Value", f"${market['value']:,.0f}")
    c2.metric("1Y Appreciation", f"{market['chg_1y']:.1%}")
    c3.metric("5Y Appreciation", f"{market['chg_5y']:.1%}")
    c4.metric("Size Rank", f"#{int(market['size_rank'])}")

    st.subheader("Home Value History")
    st.line_chart(history, x="date", y="value")

    # Compare markets
    st.subheader("Compare Markets")
    comparison_options = [m for m in markets if m != selected]
    comparison_name = st.selectbox("Compare with", comparison_options)
    comparison = table[table["region"] == comparison_name].iloc[0]

    comparison_table = pd.DataFrame({
        "Metric": ["Home Value", "1Y Appreciation", "5Y Appreciation"],
        selected: [
            f"${market['value']:,.0f}",
            f"{market['chg_1y']:.1%}",
            f"{market['chg_5y']:.1%}",
        ],
        comparison_name: [
            f"${comparison['value']:,.0f}",
            f"{comparison['chg_1y']:.1%}",
            f"{comparison['chg_5y']:.1%}",
        ],
    })

    st.dataframe(comparison_table, use_container_width=True, hide_index=True)

    comparison_history = metro_only[
        metro_only["region"] == comparison_name
    ].sort_values("date")

    chart_data = pd.concat([
        history[["date", "value"]].assign(market=selected),
        comparison_history[["date", "value"]].assign(market=comparison_name),
    ]).pivot(index="date", columns="market", values="value")

    st.line_chart(chart_data)

    # KNN similar markets
    st.subheader("Similar Markets")
    try:
        similar = analysis.find_similar_markets(metro_only, selected, n_neighbors=5)

        st.dataframe(
            similar[["region", "state", "value", "chg_1y", "chg_5y"]],
            use_container_width=True,
            hide_index=True,
        )
    except ValueError:
        st.info(f"Similar market analysis isn't available for {selected}.")

    st.warning(DISCLAIMER)