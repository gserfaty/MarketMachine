"""ML forecast page."""
from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from housing import analysis, data, model, ui
from housing.ui import GREY, INK, TEAL, fmt_pct, show, signed
from housing.shared import _data_dir_key, cached_fred, cached_supply, cached_zillow_forecast, _safe_load_metro, metro_regions, _footer_disclaimer, _need, _mon, _try_forecast, _short, _table, _range_table, _forecast_failed


def render_forecast() -> None:
    st.header("ML forecast")
    st.caption("Where prices may be headed, and how far to trust it.")
    label = st.radio("Forecast horizon", ["3 months", "12 months", "24 months"], index=1, horizontal=True, key="forecast_horizon")
    h = int(label.split()[0])
    metro_df = _need(_safe_load_metro(), "forecast", ui.ZILLOW_DOWN + " The national forecast needs the same data.")
    supply = cached_supply(_data_dir_key())
    result = _try_forecast(metro_df, h)
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
        text = f"{_short(metro)} home values: forecast {signed(pred)} over the next {label} (80% range {signed(lo)} to {signed(hi)})."
    else:
        pred, (lo, hi), region = result.national_pred, result.national_interval, "United States"
        text = (f"US home values: forecast {signed(pred)} over the next {label} (80% range {signed(lo)} to {signed(hi)})."
                + ("" if metro else " Choose a metro for its forecast."))
    ui.headline(text, f"80% range: in past tests, the actual change landed inside a range this wide {bl['coverage80']:.0%} of the time.")
    if h == 24:
        st.caption("24-month forecasts are the total (cumulative) change over two years, not a yearly rate.")
    ui.disclaimer()
    zf = cached_zillow_forecast(_data_dir_key())
    cmp = analysis.compare_to_zillow(result.predictions, zf, h) if zf is not None else None
    if h == 24:
        st.caption("Zillow doesn't publish a 24-month forecast, so there's no comparison at this horizon.")
    elif cmp is None:
        st.caption("Zillow's own forecast is unavailable right now, so there's no comparison.")
    else:
        zr_ = zf[zf["region"] == region]
        z = zr_[f"zf_{h}m"].iloc[0] if len(zr_) else float("nan")
        st.markdown(
            f"Zillow's forecast for {_short(region)}: {signed(z)} over the next {label}. "
            f"We vs Zillow: {cmp['same_dir']} of {cmp['n']} metros in the same direction; "
            f"median difference {cmp['median_diff_pp']:+.1f} points (ours minus Zillow)."
        )
        st.caption(f"Zillow's forecast from {_mon(zf['base_date'].iloc[0])} data. This compares forecasts only, "
                   "not which has been more accurate; that needs the forecasts to come due.")
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
    ui.show(ui.history_band(hist, pred, lo, hi, name=_short(region), months=h))
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
    ui.signed_axis(fig, float(px_.min()), float(px_.max()), axis="x", title=f"Predicted {h}-month change")
    fig.update_yaxes(title="Metros")
    show(fig, 280)
    search = st.text_input("Search metros")
    preds = result.predictions.copy()
    if search:
        preds = preds[preds["region"].str.contains(search, case=False, na=False)]
    tbl, tcols = _range_table(preds), ["region", "state", "value", "pred"]
    if cmp is not None:
        tbl["zillow"] = tbl["region"].map(zf.set_index("region")[f"zf_{h}m"]).map(signed)
        tcols.append("zillow")
    _table(tbl, tcols, height=320)

    with st.expander("How we tested this"):
        _backtest_detail(result, h)

    with st.expander("How the forecast works"):
        st.write(
            f"A gradient-boosted tree model is trained on point-in-time price-momentum, "
            f"volatility, and macro features to predict each metro's {h}-month log return. "
            "It is evaluated with a yearly rolling-origin backtest (2010 onward): each year is "
            f"predicted by a model trained only on rows whose {h}-month outcome was already known "
            "at the start of that year, and compared with a naive momentum baseline and a "
            "zero-change baseline. Backtest fits use quarterly origins only, for speed. The served forecast is the equal-weight "
            "average of the model and the trailing-12-month momentum scaled to the horizon, in simple-return space, and it "
            "is scored in the same backtest."
        )

    _footer_disclaimer()


def _backtest_detail(result: model.ForecastResult, h: int) -> None:
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
        f"- Top picks (top 10%) beat the average metro by {mo['top_decile_lift']:.2f} points over {h} months "
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
        f"80% range: in the backtest ({2010 + 1 + math.ceil(h / 12)}+, ranges built only from earlier years) the actual {h}-month change "
        f"fell inside it {bl['coverage80']:.0%} of the time; average width {bl['width80']:.1f} pp. "
        "Misses cluster in market-wide shocks (2020, 2022), when the range is too narrow for every metro at once."
    )


render_forecast()
