from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import api.main as am
from api import ledger
from housing.model import ForecastResult


@pytest.fixture
def eng(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/l.db")
    e = ledger.engine()
    ledger.Base.metadata.create_all(e)
    return e


def _res(as_of, preds):
    df = pd.DataFrame({"region": list(preds), "pred_12m": list(preds.values())})
    df["lo_12m"], df["hi_12m"] = df["pred_12m"] - 0.05, df["pred_12m"] + 0.05
    return ForecastResult(metrics=None, backtest=None, predictions=df, national_pred=0.0, as_of=pd.Timestamp(as_of))


def _count(e):
    with Session(e) as s:
        return s.scalar(select(func.count()).select_from(ledger.Forecast))


def test_record_idempotent(eng):
    r = _res("2026-01-31", {"A": 0.03, "B": 0.05})
    for _ in range(2):
        ledger.record(r, 12, None)
        ledger.record(r, 12, "7")
    assert _count(eng) == 4


def test_record_disabled_and_errors_swallowed(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    ledger.record(_res("2026-01-31", {"A": 0.03}), 12, None)
    monkeypatch.setenv("DATABASE_URL", "sqlite:////nonexistent-dir/x.db")
    ledger.record(_res("2026-01-31", {"A": 0.03}), 12, None)  # no raise


def test_realized_error_only_matured():
    d = pd.to_datetime(["2025-01-31", "2026-01-31", "2026-02-28"])
    long_df = pd.DataFrame({"date": list(d) * 2, "region": ["A"] * 3 + ["B"] * 3,
                            "value": [100, 110, 111, 200, 190, 191]})
    rows = pd.DataFrame({"as_of": pd.to_datetime(["2025-01-31"] * 2 + ["2026-02-28"]),
                         "region": ["A", "B", "A"], "pred": [0.12, 0.0, 0.5]})
    r = ledger.realized_error(rows, long_df, 12)  # actual A +10%, B -5%; the 2026-02 forecast has not matured
    assert r["n"] == 2 and r["mae"] == pytest.approx(3.5) and r["bias"] == pytest.approx(3.5)
    assert ledger.realized_error(rows.iloc[2:], long_df, 12) is None


def test_psi_toy():
    base = [i / 100 for i in range(100)]
    assert ledger.psi(base, base) == pytest.approx(0.0, abs=1e-9)
    assert ledger.psi(base, [x + 0.5 for x in base]) > 0.25


def test_drift_shift_from_two_batches(eng):
    ledger.record(_res("2026-01-31", {"A": 0.01, "B": 0.02, "C": 0.03}), 12, None)
    ledger.record(_res("2026-02-28", {"A": 0.02, "B": 0.03, "C": 0.04}), 12, None)
    long_df = pd.DataFrame({"date": pd.to_datetime(["2026-02-28"]), "region": ["A"], "value": [1.0]})
    out = ledger.drift(eng, 12, long_df, 3.0)
    assert out["realized"] is None and out["shift"]["mean_shift_pp"] == pytest.approx(1.0)
    assert out["shift"]["latest_as_of"] == date(2026, 2, 28)


def test_endpoint_disabled(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    r = TestClient(am.app).get("/v1/monitoring/drift")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
