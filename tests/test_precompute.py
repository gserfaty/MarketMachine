import dataclasses
import json

import pandas as pd
import pytest

from housing import model, precompute


def make_result() -> model.ForecastResult:
    pred = pd.DataFrame({"region": ["A", "B"], "state": ["IL", "TX"], "value": [100.0, 200.0],
                         "pred_12m": [0.03, 0.01], "lo_12m": [0.0, -0.02], "hi_12m": [0.06, 0.04]})
    metrics = pd.DataFrame({"MAE": [1.5], "years": [5]}, index=["blend"])
    bt = pd.DataFrame({"year": [2020, 2021], "predictor": ["blend"] * 2, "MAE": [1.0, float("nan")]})
    return model.ForecastResult(metrics, bt, pred, 0.03, pd.Timestamp("2026-01-01"),
                                feature_importance=pd.Series([0.6, 0.4], index=["r12", "vol12"]),
                                national_interval=(0.0, 0.06), interval_k=1.3, blend_weight=0.8)


def test_round_trip_all_fields():
    a = make_result()
    b = model.result_from_json(model.result_to_json(a))
    for f in dataclasses.fields(a):
        x, y = getattr(a, f.name), getattr(b, f.name)
        if f.name == "model":
            assert y is None
        elif isinstance(x, pd.DataFrame):
            pd.testing.assert_frame_equal(x, y, check_dtype=False)
        elif isinstance(x, pd.Series):
            pd.testing.assert_series_equal(x, y, check_dtype=False)
        else:
            assert x == y and type(x) is type(y), f.name


def payload(key):
    return json.dumps({"as_of_key": key, "horizon": 12, "result": model.result_to_json(make_result())})


def test_use_matching_key():
    assert precompute.use(payload("k"), "k").blend_weight == 0.8


@pytest.mark.parametrize("p,key", [(payload("old"), "k"), (None, "k"), ("not json", "k")])
def test_use_falls_back(p, key):
    assert precompute.use(p, key) is None


def test_fetch_error_returns_none(monkeypatch):
    def boom(*a, **k):
        raise OSError("down")
    monkeypatch.setattr(precompute.urllib.request, "urlopen", boom)
    assert precompute.fetch(12) is None


def test_shared_cached_forecast_prefers_precomputed(monkeypatch):
    from housing import shared
    monkeypatch.setattr(precompute, "fetch", lambda h: payload("k"))
    monkeypatch.setattr(model, "train_and_evaluate", lambda *a, **k: pytest.fail("trained"))
    shared._cached_precomputed.clear()
    assert shared.cached_forecast.__wrapped__("k", None, None, None, 12).interval_k == 1.3
    monkeypatch.setattr(model, "train_and_evaluate", lambda *a, **k: "trained")
    assert shared.cached_forecast.__wrapped__("other", None, None, None, 12) == "trained"
    shared._cached_precomputed.clear()
