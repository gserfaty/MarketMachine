"""MarketMachine — US housing market analytics and ML forecast (Streamlit app)."""
import streamlit as st

from housing import shared, ui

st.set_page_config(page_title="MarketMachine — US Housing", layout="wide")

NAV = {
    "overview": st.Page("housing/pages/overview.py", title="Market overview", url_path="overview", default=True),
    "findings": st.Page("housing/pages/findings.py", title="Findings", url_path="findings", visibility="hidden"),
    "explorer": st.Page("housing/pages/explorer.py", title="Regional explorer", url_path="explorer"),
    "profile": st.Page("housing/pages/profile.py", title="Market profile", url_path="profile"),
    "forecast": st.Page("housing/pages/forecast.py", title="ML forecast", url_path="forecast"),
    "financing": st.Page("housing/pages/financing.py", title="Financing estimator", url_path="financing"),
    "affordability": st.Page("housing/pages/affordability.py", title="Affordability", url_path="affordability"),
}


def main() -> None:
    ui.inject_css()
    st.session_state["_nav"] = NAV
    regions = shared.metro_regions()
    ui.sync_metro(regions)
    ui.sidebar(regions)
    pg = st.navigation({
        "Market": [NAV["overview"], NAV["findings"]],
        "Metro": [NAV["explorer"], NAV["profile"]],
        "Money": [NAV["forecast"], NAV["financing"], NAV["affordability"]],
    })
    pg.run()


if __name__ == "__main__":
    main()
