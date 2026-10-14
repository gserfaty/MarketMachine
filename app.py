"""MarketMachine — US housing market analytics and ML forecast (Streamlit app)."""
import streamlit as st

from housing import pages, ui

st.set_page_config(page_title="MarketMachine — US Housing", layout="wide")

NAV = {
    "overview": st.Page(pages.render_overview, title="Market overview", url_path="overview", default=True),
    "findings": st.Page(pages.render_findings, title="Findings", url_path="findings"),
    "explorer": st.Page(pages.render_explorer, title="Regional explorer", url_path="explorer"),
    "profile": st.Page(pages.render_market_profiles, title="Market profile", url_path="profile"),
    "forecast": st.Page(pages.render_forecast, title="ML forecast", url_path="forecast"),
    "financing": st.Page(pages.render_financing, title="Financing estimator", url_path="financing"),
}


def main() -> None:
    ui.inject_css()
    st.session_state["_nav"] = NAV
    regions = pages.metro_regions()
    ui.sync_metro(regions)
    ui.sidebar(regions)
    pg = st.navigation({
        "Market": [NAV["overview"], NAV["findings"]],
        "Metro": [NAV["explorer"], NAV["profile"]],
        "Money": [NAV["forecast"], NAV["financing"]],
    })
    pg.run()


if __name__ == "__main__":
    main()
