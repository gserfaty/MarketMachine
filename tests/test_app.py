import os
import shutil

import pytest
from streamlit.testing.v1 import AppTest

from housing import ui

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")
PAGES = ["overview", "explorer", "profile", "forecast", "financing", "affordability"]

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _run_page(page: str, query: dict | None = None) -> AppTest:
    """Run app.py, then switch to a page file registered with st.navigation."""
    at = AppTest.from_file(APP_PATH, default_timeout=120)
    if query:
        at.query_params.update(query)
    at.run()
    return at.switch_page(f"housing/pages/{page}.py").run()


@pytest.mark.parametrize("page_label", PAGES)
def test_page_renders_without_exception(page_label):
    at = _run_page(page_label)
    assert not at.exception


@pytest.mark.parametrize("page_label", PAGES)
def test_page_has_disclaimer(page_label):
    at = _run_page(page_label)
    texts = []
    texts += [m.value for m in at.markdown]
    texts += [c.value for c in at.caption]
    texts += [w.value for w in at.warning]
    combined = " ".join(texts).lower()
    assert "not financial advice" in combined


def test_overview_data_down_warns_with_retry(monkeypatch):
    monkeypatch.setenv("MARKETMACHINE_DATA_DIR", "/tmp/marketmachine-nonexistent-dir-xyz")
    at = AppTest.from_file(APP_PATH, default_timeout=60)
    at.run()
    assert not at.exception
    assert any(w.value.startswith("Heads up:") for w in at.warning)
    assert any(b.label == "Try again" for b in at.button)
    assert "not financial advice" in " ".join(m.value for m in at.markdown)


def test_metro_carried_from_query_param():
    at = _run_page("profile", {"metro": "Chicago, IL"})
    assert not at.exception
    assert at.session_state["metro"] == "Chicago, IL"
    assert any("Chicago: typical home" in m.value for m in at.markdown)


def test_unknown_metro_in_query_param_is_cleared():
    at = AppTest.from_file(APP_PATH, default_timeout=120)
    at.query_params["metro"] = "Atlantis"
    at.run()
    assert not at.exception
    assert at.session_state["metro"] is None
    assert any("couldn't find 'Atlantis'" in i.value for i in at.info)


def test_forecast_page_scorecard():
    at = _run_page("forecast")
    assert not at.exception
    assert len(at.dataframe) >= 2
    assert "ranking skill" in " ".join(m.value for m in at.markdown).lower()
    txt = " ".join([m.value for m in at.markdown] + [i.value for i in at.info]).lower()
    assert "served forecast" in txt and "blend" in txt
    assert "80% range" in " ".join(c.value for c in at.caption)


def test_financing_fred_down(tmp_path, monkeypatch):
    shutil.copy(os.path.join(FIXTURES, "zhvi_metro.csv"), tmp_path / "zhvi_metro.csv")
    monkeypatch.setenv("MARKETMACHINE_DATA_DIR", str(tmp_path))
    at = _run_page("financing")
    assert not at.exception
    assert any("unavailable" in w.value for w in at.warning)
    assert len(at.number_input) >= 2


def test_financing_equity_projection():
    at = _run_page("financing")
    assert not at.exception
    assert "Equity projection" in [s.value for s in at.subheader]
    assert any("highly uncertain" in w.value for w in at.warning)


def test_affordability_carried_metro():
    at = _run_page("affordability", {"metro": "Chicago, IL"})
    assert not at.exception
    assert any("Chicago, IL: $" in m.value or "Chicago, IL (your metro)" in m.value for m in at.markdown)
    assert any(b.label == "Estimate financing in Chicago" for b in at.button)


def test_affordability_fred_down(tmp_path, monkeypatch):
    shutil.copy(os.path.join(FIXTURES, "zhvi_metro.csv"), tmp_path / "zhvi_metro.csv")
    monkeypatch.setenv("MARKETMACHINE_DATA_DIR", str(tmp_path))
    at = _run_page("affordability")
    assert not at.exception
    warnings = " ".join(w.value for w in at.warning)
    assert "live mortgage rates are unavailable" in warnings and "affordability data is unavailable" in warnings
    assert "not financial advice" in " ".join(m.value for m in at.markdown)


def test_forecast_vs_zillow():
    at = _run_page("forecast")
    assert not at.exception
    md = " ".join(m.value for m in at.markdown)
    assert "We vs Zillow" in md and "metros in the same direction" in md


def test_forecast_zillow_down(tmp_path, monkeypatch):
    for f in os.listdir(FIXTURES):
        if f != "zillow_forecast.csv":
            shutil.copy(os.path.join(FIXTURES, f), tmp_path / f)
    monkeypatch.setenv("MARKETMACHINE_DATA_DIR", str(tmp_path))
    at = _run_page("forecast")
    assert not at.exception
    assert any("Zillow's own forecast is unavailable" in c.value for c in at.caption)
    assert "not financial advice" in " ".join(m.value for m in list(at.markdown) + list(at.caption)).lower()


def test_findings_alias_redirects():
    at = _run_page("findings")
    assert not at.exception
    assert "Market overview" in [h.value for h in at.header]


def test_overview_has_top_markets():
    at = _run_page("overview")
    subs = [x.value for x in at.subheader]
    assert "Top markets" in subs and "Predicted to gain most, next 12 months" in subs
    assert "80% range is the span" in " ".join(m.value for m in at.markdown)


@pytest.mark.parametrize("page", ["overview", "explorer"])
def test_headline_has_arrow(page):
    at = _run_page(page)
    assert any("mm-answer" in m.value and ("▲" in m.value or "▼" in m.value) for m in at.markdown)


def test_kpi_delta_inside_card():
    at = _run_page("explorer")
    assert any(str(m.delta).startswith(("▲", "▼")) for m in at.metric)
    at = _run_page("overview")
    assert not any("points vs a year ago" in c.value for c in at.caption)


def test_color_deltas():
    out = ui.color_deltas("a ▲ +1.2% b ▼ −0.4%")
    assert "mm-up" in out and "mm-down" in out
    assert ui.color_deltas("(80% range −1.0% to +2.0%)") == "(80% range −1.0% to +2.0%)"


def test_metro_source_caption():
    at = _run_page("forecast", {"metro": "Chicago, IL"})
    assert not any("from Market overview" in c.value for c in at.caption)
    at = AppTest.from_file(APP_PATH, default_timeout=120).run()
    at.selectbox(key="metro_pick_overview").set_value("Chicago, IL").run()
    at = at.switch_page("housing/pages/forecast.py").run()
    assert any("from Market overview" in c.value for c in at.caption)


def test_overview_corrupt_zhvi_shows_heads_up(tmp_path, monkeypatch):
    shutil.copytree(FIXTURES, tmp_path, dirs_exist_ok=True)
    p = tmp_path / "zhvi_metro.csv"
    lines = p.read_text().splitlines()
    cells = lines[2].split(",")
    cells[-1] = "-5"
    lines[2] = ",".join(cells)
    p.write_text("\n".join(lines) + "\n")
    monkeypatch.setenv("MARKETMACHINE_DATA_DIR", str(tmp_path))
    at = AppTest.from_file(APP_PATH, default_timeout=60)
    at.run()
    assert not at.exception
    assert any(w.value.startswith("Heads up:") for w in at.warning)
    assert any(b.label == "Try again" for b in at.button)
    assert "not financial advice" in " ".join(m.value for m in at.markdown)
