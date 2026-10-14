import os
import shutil

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")
PAGES = ["overview", "findings", "explorer", "profile", "forecast", "financing"]

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _run_page(page: str, query: dict | None = None) -> AppTest:
    """Run app.py, then switch to a st.navigation page by url_path (AppTest.switch_page only knows files)."""
    at = AppTest.from_file(APP_PATH, default_timeout=120)
    if query:
        at.query_params.update(query)
    at.run()
    at._page_hash = next(h for h, i in at._registered_pages.items() if i.get("url_pathname", "") == ("" if page == "overview" else page))
    return at.run()


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
    monkeypatch.setenv("MICHIGANMEN_DATA_DIR", "/tmp/michiganmen-nonexistent-dir-xyz")
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
    monkeypatch.setenv("MICHIGANMEN_DATA_DIR", str(tmp_path))
    at = _run_page("financing")
    assert not at.exception
    assert any("unavailable" in w.value for w in at.warning)
    assert len(at.number_input) >= 2


def test_financing_equity_projection():
    at = _run_page("financing")
    assert not at.exception
    assert "Equity projection" in [s.value for s in at.subheader]
    assert any("highly uncertain" in w.value for w in at.warning)
