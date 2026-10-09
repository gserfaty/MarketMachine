"""michiganmen — US housing market analytics and ML forecast (Streamlit app)."""
import streamlit as st

from housing.pages import render_explorer, render_findings, render_forecast, render_overview, render_market_profiles, render_financing

st.set_page_config(page_title="michiganmen — US Housing", layout="wide")

PAGES = {
    "Market overview": render_overview,
    "Regional explorer": render_explorer,
    "ML forecast": render_forecast,
    "Findings": render_findings,
    "Market Profile": render_market_profiles,
    "Financing estimator": render_financing,
}


def main() -> None:
    st.sidebar.title("michiganmen")
    st.sidebar.caption("US housing market analytics & ML forecast")
    choice = st.sidebar.radio("Page", list(PAGES.keys()))
    PAGES[choice]()
    st.sidebar.caption("Forecasts are statistical estimates, not financial advice.")


if __name__ == "__main__":
    main()
