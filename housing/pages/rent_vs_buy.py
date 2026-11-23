"""Rent vs buy page."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from housing import analysis, finance, ui
from housing.ui import INK, TEAL, show
from housing.shared import CC, _data_dir_key, _footer_disclaimer, _safe_load_metro, _try_forecast, cached_fred

RENT_TO_PRICE = 0.005  # monthly rent = 0.5% of price (rule of thumb; no rent data source)


def render_rent_vs_buy() -> None:
    st.header("Rent vs buy")
    head = st.container()
    metro_df = _safe_load_metro()
    table = None
    if metro_df is not None:
        table = analysis.appreciation_table(metro_df[metro_df["region_type"] != "country"]).sort_values("size_rank")
    metro = ui.metro_picker(None if table is None else table["region"].tolist(), "rentbuy")
    price0, app0, app_note = 400_000.0, 3.0, "Assumption: 3% a year."
    if metro and table is not None and (table["region"] == metro).any():
        price0 = float(table[table["region"] == metro].iloc[0]["value"])
        res = _try_forecast(metro_df)
        row = None if res is None else res.predictions[res.predictions["region"] == metro]
        if row is not None and not row.empty:
            app0 = float(row.iloc[0]["pred_12m"]) * 100
            app_note = f"Default is {metro}'s 12-month forecast. Long-run growth is uncertain."
    s30 = cached_fred("MORTGAGE30US", _data_dir_key())
    s30 = s30.dropna() if s30 is not None else None
    rate0 = float(s30.iloc[-1]) if s30 is not None and not s30.empty else 6.5
    if s30 is None or s30.empty:
        st.warning("Heads up: live mortgage rates are unavailable, so the rate below is a guess.")

    k = f"_{metro}"
    c = st.columns(3)
    price = c[0].number_input("Home price ($)", 10_000.0, value=float(round(price0, -3)), step=10_000.0, key="rb_price" + k)
    rent = c[1].number_input("Monthly rent ($)", 0.0, value=float(round(price0 * RENT_TO_PRICE, -1)), step=50.0, key="rb_rent" + k,
                             help="Default is 0.5% of the home price. Enter a real local rent for a better answer.")
    years = c[2].number_input("Years you will stay", 1, 30, 10, 1)
    c = st.columns(3)
    down = c[0].number_input("Down payment (%)", 0.0, 99.0, 20.0, 1.0)
    rate = c[1].number_input("30-year mortgage rate (%)", 0.0, 20.0, round(rate0, 2), 0.05)
    app = c[2].number_input("Home appreciation (% a year)", -10.0, 20.0, round(app0, 1), 0.5, key="rb_app" + k, help=app_note)
    with st.expander("More assumptions"):
        c = st.columns(4)
        rg = c[0].number_input("Rent growth (% a year)", 0.0, 15.0, 3.0, 0.5)
        inv = c[1].number_input("Investment return (% a year)", -5.0, 20.0, 5.0, 0.5,
                                help="What the renter earns on the down payment and monthly savings.")
        tax = c[2].number_input("Property tax (% of value)", 0.0, 5.0, 1.0, 0.05)
        ins = c[3].number_input("Insurance ($ a year)", 0.0, value=1500.0, step=100.0)
        c = st.columns(3)
        maint = c[0].number_input("Maintenance (% of value a year)", 0.0, 5.0, 1.0, 0.25)
        buy_c = c[1].number_input("Buying costs (%)", 0.0, 10.0, finance.BUY_COST_PCT, 0.5)
        sell_c = c[2].number_input("Selling costs (%)", 0.0, 15.0, finance.SELL_COST_PCT, 0.5)
    st.caption(f"Appreciation: {app_note}")

    d = finance.rent_vs_buy(price, down, rate, rent, int(years), app, rg, inv, tax, ins, maint, buy_c, sell_c)
    be, last = finance.break_even_year(d), d.iloc[-1]
    with head:
        if be:
            ui.headline(f"Buying comes out ahead after {be} year{'s' if be > 1 else ''}.",
                        f"After {int(years)} years buying is ${last['diff']:,.0f} ahead.")
        else:
            ui.headline(f"Renting comes out ahead over {int(years)} years.",
                        f"Buying is ${-last['diff']:,.0f} behind and has not caught up. Try a longer stay.")
        ui.disclaimer(ui.D2)

    fig = go.Figure()
    fig.add_scatter(x=d["year"], y=d["buy"], name="Buy: equity after selling costs", mode="lines", line=dict(color=INK, width=2.5), hovertemplate="%{y:$,.0f}")
    fig.add_scatter(x=d["year"], y=d["rent"], name="Rent: invested savings", mode="lines", line=dict(color=TEAL, width=2.5), hovertemplate="%{y:$,.0f}")
    fig.update_layout(xaxis_title="Year", yaxis_title="Net worth ($)")
    fig.update_yaxes(tickformat="$,.2s")
    show(fig)
    t = pd.DataFrame({"Year": d["year"], "Buy": d["buy"], "Rent": d["rent"], "Buy minus rent": d["diff"]})
    st.dataframe(t, hide_index=True, width="stretch", column_config={
        "Year": CC.NumberColumn(format="%d", width="small"), **{x: CC.NumberColumn(format="$%,d") for x in t.columns[1:]}})
    st.caption("Fixed 30-year loan. The renter invests the down payment, buying costs and any monthly savings. The buyer's net worth is "
               "home value minus loan and selling costs. Ignores capital-gains tax and the mortgage interest deduction.")
    _footer_disclaimer()


render_rent_vs_buy()
