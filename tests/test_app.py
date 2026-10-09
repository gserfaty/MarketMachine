import os
import shutil

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")
PAGE_LABELS = ["Market overview", "Regional explorer", "ML forecast", "Findings", "Financing estimator"]

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _run_page(page_label: str) -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=60)
    at.run()
    at.sidebar.radio[0].set_value(page_label).run()
    return at


@pytest.mark.parametrize("page_label", PAGE_LABELS)
def test_page_renders_without_exception(page_label):
    at = _run_page(page_label)
    assert not at.exception


@pytest.mark.parametrize("page_label", PAGE_LABELS)
def test_page_has_disclaimer(page_label):
    at = _run_page(page_label)
    texts = []
    texts += [m.value for m in at.markdown]
    texts += [c.value for c in at.caption]
    texts += [w.value for w in at.warning]
    combined = " ".join(texts).lower()
    assert "not financial advice" in combined


def test_overview_shows_error_when_data_dir_missing(monkeypatch):
    monkeypatch.setenv("MICHIGANMEN_DATA_DIR", "/tmp/michiganmen-nonexistent-dir-xyz")
    at = AppTest.from_file(APP_PATH, default_timeout=60)
    at.run()
    assert not at.exception
    assert len(at.error) > 0


def test_forecast_page_scorecard():
    at = _run_page("ML forecast")
    assert not at.exception
    assert len(at.dataframe) >= 2
    assert "rank ic" in " ".join(m.value for m in at.markdown).lower()
    txt = " ".join([m.value for m in at.markdown] + [i.value for i in at.info]).lower()
    assert "served forecast" in txt and "blend" in txt
    assert "80% range" in " ".join(c.value for c in at.caption)


def test_financing_fred_down(tmp_path, monkeypatch):
    shutil.copy(os.path.join(FIXTURES, "zhvi_metro.csv"), tmp_path / "zhvi_metro.csv")
    monkeypatch.setenv("MICHIGANMEN_DATA_DIR", str(tmp_path))
    at = _run_page("Financing estimator")
    assert not at.exception
    assert any("unavailable" in w.value for w in at.warning)
    assert len(at.number_input) >= 2
