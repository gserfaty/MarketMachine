"""Streamlit rendering for the 4 app pages."""
from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from housing import analysis, data, finance, model

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


@st.cache_data(ttl=86400, show_spinner="Loading Zillow listings data...")
def cached_supply(data_dir: str | None = None) -> pd.DataFrame | None:
    try:
        return data.load_supply()
    except Exception:
        return None


@st.cache_resource(show_spinner="Training forecast model...")
def cached_forecast(as_of_key: str, _long_df: pd.DataFrame, _mortgage, _supply) -> model.ForecastResult:
    return model.train_and_evaluate(_long_df, _mortgage, supply=_supply)


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


def fmt_range(pred, lo, hi) -> str:
    return f"{pred*100:+.1f}% ({lo*100:+.1f}% to {hi*100:+.1f}%)"


def _range_table(df: pd.DataFrame) -> pd.DataFrame:
    out = df[["region", "state", "value"]].copy()
    out["12-month forecast (80% range)"] = [fmt_range(p, l, h) for p, l, h in zip(df["pred_12m"], df["lo_12m"], df["hi_12m"])]
    return out


def render_forecast() -> None:
    st.header("ML forecast")
    metro_df = _safe_load_metro()
    if metro_df is None:
        st.stop()
        return
    mortgage = cached_fred("MORTGAGE30US", _data_dir_key())

    supply = cached_supply(_data_dir_key())
    if supply is None:
        st.warning("Zillow listings data unavailable; forecast runs without supply features.")
    as_of_key = f"{metro_df['date'].max()}|supply={supply is not None}"
    result = cached_forecast(as_of_key, metro_df, mortgage, supply)

    st.subheader("How well has the model done? (backtest)")
    m = result.metrics
    disp = m.copy()
    for c in ("MAE", "bias", "top_decile_lift"):
        disp[c] = m[c].map(lambda v: "n/a" if pd.isna(v) else f"{v:.2f} pp")
    disp["direction_acc"] = m["direction_acc"].map(lambda v: f"{v * 100:.1f}%")
    disp["coverage80"] = m["coverage80"].map(lambda v: "n/a" if pd.isna(v) else f"{v * 100:.1f}%")
    disp["width80"] = m["width80"].map(lambda v: "n/a" if pd.isna(v) else f"{v:.1f} pp")
    disp["rank_ic"] = m["rank_ic"].map(lambda v: "n/a" if pd.isna(v) else f"{v:.2f}")
    st.dataframe(disp, use_container_width=True)

    bt = result.backtest
    per_year = bt[bt["predictor"].isin(["model", "blend", "naive_momentum"])].pivot(
        index="year", columns="predictor", values=["MAE", "bias", "rank_ic", "top_decile_lift"]
    )
    per_year.columns = [f"{metric} · {pred}" for metric, pred in per_year.columns]
    blend_iv = bt[bt["predictor"] == "blend"].set_index("year")
    per_year["coverage80 · blend"] = blend_iv["coverage80"]
    per_year["width80 · blend"] = blend_iv["width80"]
    per_year["n"] = bt[bt["predictor"] == "model"].set_index("year")["n"]
    st.dataframe(per_year.round(2), use_container_width=True)

    ic = bt[bt["predictor"].isin(["model", "blend", "naive_momentum"])]
    st.plotly_chart(px.line(ic, x="year", y="rank_ic", color="predictor", title="Rank IC by year"),
                    use_container_width=True)

    mo, bl, nv, zr = m.loc["model"], m.loc["blend"], m.loc["naive_momentum"], m.loc["zero"]
    tone = "pessimistic" if mo["bias"] < 0 else "optimistic"
    st.markdown(
        f"- Average miss: model {mo['MAE']:.2f} pp vs blend {bl['MAE']:.2f} pp vs momentum {nv['MAE']:.2f} pp vs no-change {zr['MAE']:.2f} pp.\n"
        f"- Bias: model is on average {abs(mo['bias']):.2f} pp too {tone}.\n"
        f"- Ranking (rank IC {mo['rank_ic']:.2f} model, {bl['rank_ic']:.2f} blend, {nv['rank_ic']:.2f} momentum): "
        "0 = random ordering, 1 = perfect; above ~0.3 is a useful ranking.\n"
        f"- Top-10% picks beat the average metro by {mo['top_decile_lift']:.2f} pp/yr "
        f"(momentum: {nv['top_decile_lift']:.2f} pp).\n"
        f"- Direction right {mo['direction_acc'] * 100:.0f}% of the time."
    )

    st.info(
        "Served forecast: **blend** = average of the ML model and naive momentum (simple returns). "
        f"Backtest average MAE: blend {bl['MAE']:.2f} pp vs model {mo['MAE']:.2f} pp vs momentum {nv['MAE']:.2f} pp; "
        f"rank IC: blend {bl['rank_ic']:.2f} vs model {mo['rank_ic']:.2f} vs momentum {nv['rank_ic']:.2f}. "
        "The blend is served because averaging two partly independent forecasts cuts the miss. "
        "The model weights recent history more (3-year half-life), which lowered backtest MAE slightly; "
        "it does not remove the pessimistic bias. "
        "Since step 4 the model also uses metro for-sale inventory (YoY) and the share of listings "
        "with a price cut (Zillow, from 2018)."
    )
    if bl["MAE"] > mo["MAE"]:
        st.warning("In this backtest the blend no longer beats the model on MAE.")

    direction = "Up" if result.national_pred >= 0 else "Down"
    st.metric(
        "National 12-month call (blend, 80% range)",
        f"{direction}, {fmt_range(result.national_pred, *result.national_interval)}",
    )
    st.caption(
        f"80% range: in the backtest (2012+, ranges built only from earlier years) the actual 12-month change "
        f"fell inside it {bl['coverage80']:.0%} of the time; average width {bl['width80']:.1f} pp. "
        "Misses cluster in market-wide shocks (2020, 2022), when the range is too narrow for every metro at once."
    )

    st.subheader("Distribution of metro-level 12-month predictions")
    st.plotly_chart(px.histogram(result.predictions, x="pred_12m", nbins=30), use_container_width=True)

    st.subheader("Per-metro predictions (blend)")
    search = st.text_input("Search region")
    preds = result.predictions.copy()
    if search:
        preds = preds[preds["region"].str.contains(search, case=False, na=False)]
    preds_display = preds.copy()
    preds_display["pred_12m"] = [fmt_range(p, l, h) for p, l, h in zip(
        preds_display["pred_12m"], preds_display["lo_12m"], preds_display["hi_12m"])]
    preds_display = preds_display.drop(columns=["lo_12m", "hi_12m"])
    preds_display["value"] = preds_display["value"].map(lambda v: f"${v:,.0f}")
    st.dataframe(preds_display, use_container_width=True, hide_index=True)

    with st.expander("Methodology"):
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

    supply = cached_supply(_data_dir_key())
    as_of_key = f"{metro_df['date'].max()}|supply={supply is not None}"
    result = cached_forecast(as_of_key, metro_df, mortgage, supply)
    preds = result.predictions[result.predictions["region"] != "United States"]

    st.subheader("Top 15 predicted gainers (next 12 months)")
    st.dataframe(_range_table(preds.sort_values("pred_12m", ascending=False).head(15)),
                 use_container_width=True, hide_index=True)

    st.subheader("Bottom 10 predicted (next 12 months)")
    st.dataframe(_range_table(preds.sort_values("pred_12m", ascending=True).head(10)),
                 use_container_width=True, hide_index=True)
    st.caption("Ranges (80% range) are statistical estimates, not guarantees.")

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


def _render_arm(res: dict, loan_type: str) -> None:
    st.subheader("Adjustable-rate (SOFR ARM) comparison")
    if loan_type != "conventional":
        st.info("ARM comparison shown for conventional loans only.")
        return
    s = cached_fred("SOFR30DAYAVG", _data_dir_key())
    s = s.dropna() if s is not None else None
    if s is None or s.empty:
        st.warning("SOFR index (FRED) unavailable — enter index manually.")
        sofr = st.number_input("SOFR 30-day average (%)", 0.0, 15.0, 4.0, 0.05)
    else:
        sofr = float(s.iloc[-1])
        st.caption(f"30-day average SOFR, {s.index[-1]:%b %Y} avg (NY Fed via FRED): {sofr:.2f}%")
    with st.expander("ARM assumptions"):
        margin = st.number_input("ARM margin (pp)", 1.0, 3.0, finance.ARM_MARGIN, 0.125)
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
    st.dataframe(pd.DataFrame(rows, index=["Initial rate", "Initial P&I", "Rate after first reset", "P&I after first reset",
                                           "Max P&I", "Max rate", "Total interest"]).T, use_container_width=True)
    plan = st.radio("ARM chart", list(finance.ARM_PLANS), horizontal=True)
    fig = go.Figure()
    for name, d in all_sc[plan].items():
        fig.add_scatter(x=d["month"], y=d["payment"], name=name, mode="lines")
    fig.add_scatter(x=fixed30["month"], y=fixed30["payment"], name="30-year fixed", mode="lines", line=dict(dash="dash"))
    fig.update_layout(xaxis_title="Month", yaxis_title="Monthly P&I ($)", legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("ARM initial rates are approximations (no public ARM rate survey since 2022); payments after reset depend on the future index.")


def render_financing() -> None:
    st.header("Financing estimator")
    st.warning(
        "Estimate only — not a loan quote or offer, and not financial advice. Nothing you enter is stored; "
        "no personal data beyond a credit band is collected."
    )
    metro_df = _safe_load_metro()
    table = None
    if metro_df is not None:
        table = analysis.appreciation_table(metro_df[metro_df["region_type"] != "country"]).sort_values("size_rank")

    c1, c2 = st.columns(2)
    with c1:
        use_metro = table is not None and st.radio("Price source", ["Metro typical value", "Manual"]) == "Metro typical value"
        state_default = "CA"
        if use_metro:
            metro = st.selectbox("Metro", table["region"].tolist())
            row = table[table["region"] == metro].iloc[0]
            price = float(row["value"])
            st.caption(f"Typical home value: ${price:,.0f}")
            if row["state"] in finance.PROPERTY_TAX_PCT:
                state_default = row["state"]
        else:
            price = st.number_input("Home price ($)", min_value=10_000.0, value=400_000.0, step=10_000.0)
        down_mode = st.radio("Down payment as", ["%", "$"], horizontal=True)
        if down_mode == "%":
            down_pct = st.number_input("Down payment (%)", min_value=0.0, max_value=99.0, value=20.0, step=1.0)
        else:
            down_pct = st.number_input("Down payment ($)", min_value=0.0, value=price * 0.2, step=5_000.0) / price * 100
    with c2:
        band = st.selectbox("Credit score band", finance.CREDIT_BANDS, index=finance.CREDIT_BANDS.index("740-759"))
        loan_type = st.selectbox("Loan type", list(finance.MIN_DOWN_PCT), format_func=lambda x: {"conventional": "Conventional", "fha": "FHA", "va": "VA"}[x])
        states = sorted(finance.PROPERTY_TAX_PCT)
        state = st.selectbox("State", states, index=states.index(state_default))
        fees_pct = st.number_input("Lender fees (% of loan, for APR)", min_value=0.0, max_value=10.0, value=1.0, step=0.25)

    with st.expander("Override tax/insurance"):
        tax_pct = st.number_input("Property tax (% of value / yr)", min_value=0.0, value=float(finance.PROPERTY_TAX_PCT[state]), step=0.05, key=f"tax_{state}")
        ins_annual = st.number_input("Home insurance ($ / yr)", min_value=0.0, value=float(finance.HOME_INS_ANNUAL[state]), step=100.0, key=f"ins_{state}")
    with st.expander("DTI check"):
        income = st.number_input("Gross monthly income ($)", min_value=0.0, value=0.0, step=500.0)
        debts = st.number_input("Other monthly debts ($)", min_value=0.0, value=0.0, step=50.0)

    s30 = cached_fred("MORTGAGE30US", _data_dir_key())
    s15 = cached_fred("MORTGAGE15US", _data_dir_key())
    s30 = s30.dropna() if s30 is not None else None
    s15 = s15.dropna() if s15 is not None else None
    if s30 is None or s15 is None or s30.empty or s15.empty:
        st.warning("Live mortgage rates (FRED) unavailable — enter rates manually.")
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
        st.error(str(e))
        _footer_disclaimer()
        return

    if res[30]["jumbo"]:
        st.info("Jumbo: pricing varies by lender; high-cost counties allow up to $1,249,125.")
    m = lambda k: [f"${res[t][k]:,.0f}" for t in finance.TERMS]  # noqa: E731
    out = pd.DataFrame(
        {
            "Rate": [f"{res[t]['rate']:.3f}%" for t in finance.TERMS],
            "APR": [f"{res[t]['apr']:.3f}%" for t in finance.TERMS],
            "P&I": m("pi"), "Tax": m("tax"), "Insurance": m("ins"), "PMI/MIP": m("mi"), "PITI": m("piti"),
            "Total interest": m("total_interest"), "Upfront fee": m("upfront"),
        },
        index=[f"{t}-year" for t in finance.TERMS],
    ).T
    st.dataframe(out, use_container_width=True)

    if income > 0:
        for t in (30, 15):
            front, back = finance.dti(res[t]["piti"], debts, income)
            msg = f"{t}-year DTI: front-end {front:.1f}%, back-end {back:.1f}%."
            if back > finance.DTI_MAX:
                st.warning(msg + f" Back-end DTI above {finance.DTI_MAX:.0f}%: most lenders would decline.")
            elif back > finance.DTI_WARN:
                st.warning(msg + f" Back-end DTI above {finance.DTI_WARN:.0f}%: approval gets harder.")
            else:
                st.write(msg)

    _render_arm(res, loan_type)

    term = st.selectbox("Amortization chart term", finance.TERMS, format_func=lambda t: f"{t}-year")
    sch = res[term]["schedule"].assign(year=lambda d: (d["month"] - 1) // 12 + 1)
    yearly = sch.groupby("year").agg(principal=("principal", "sum"), interest=("interest", "sum"), balance=("balance", "last"))
    fig = go.Figure()
    fig.add_bar(x=yearly.index, y=yearly["principal"], name="Principal")
    fig.add_bar(x=yearly.index, y=yearly["interest"], name="Interest")
    fig.add_scatter(x=yearly.index, y=yearly["balance"], name="Remaining balance", yaxis="y2")
    fig.update_layout(
        barmode="stack", xaxis_title="Year", yaxis_title="Paid per year ($)",
        yaxis2=dict(title="Balance ($)", overlaying="y", side="right"), legend=dict(orientation="h"),
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Sources & assumptions"):
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
            "- **Not modeled:** county loan limits, points, HOA, flood insurance, ARM APR/MI, index paths; MI and FHA/VA adjustments are approximations."
        )
    _footer_disclaimer()
