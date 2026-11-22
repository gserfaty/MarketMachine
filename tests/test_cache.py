import fakeredis
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import api.cache as rc
import api.main as am
from housing import model
from tests.conftest import FIXTURES_DIR

CHI = "/v1/metros/Chicago%2C%20IL/forecast"


def fake_train(long_df, *a, **k):
    names = long_df.drop_duplicates("region")["region"]
    pred = pd.DataFrame({"region": names, "state": "IL", "value": 100.0, "pred_12m": 0.03, "lo_12m": 0.0, "hi_12m": 0.06})
    metrics = pd.DataFrame({c: 1.0 for c in model.METRICS} | {"years": 5}, index=["blend"])
    return model.ForecastResult(metrics, pd.DataFrame(), pred, 0.03, pd.Timestamp("2026-01-01"), national_interval=(0.0, 0.06))


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr(am.model, "train_and_evaluate", fake_train)
    monkeypatch.setenv("MARKETMACHINE_DATA_DIR", FIXTURES_DIR)
    monkeypatch.setattr(am, "_champion", lambda h: None)
    monkeypatch.setattr(rc, "_client", None)
    monkeypatch.setattr(rc, "_warned", False)
    am._cache.clear()
    yield monkeypatch
    am._cache.clear()


def test_shared_cache_across_workers(env):
    fake = fakeredis.FakeRedis()
    env.setattr(rc, "_client", fake)
    first = TestClient(am.app).get(CHI).json()
    assert any(k.startswith(b"mm:forecast") for k in fake.keys())
    am._cache.clear()  # a second worker: empty in-process cache, same Redis
    env.setattr(am.model, "train_and_evaluate", lambda *a, **k: pytest.fail("recomputed"))
    assert TestClient(am.app).get(CHI).json() == first


def test_rate_limit(env):
    env.setattr(rc, "_client", fakeredis.FakeRedis())
    env.setenv("RATE_LIMIT_PER_MIN", "3")
    c = TestClient(am.app)
    assert [c.get("/v1/metros").status_code for _ in range(3)] == [200] * 3
    r = c.get("/v1/metros")
    assert r.status_code == 429 and 0 < int(r.headers["Retry-After"]) <= 60
    assert r.json()["error"]["code"] == "rate_limited"
    assert c.get("/v1/health").status_code == 200 and c.get("/v1/ready").status_code == 200


def test_fail_open_when_redis_errors(env):
    class Boom:
        def __getattr__(self, _):
            def f(*a, **k):
                raise ConnectionError("down")
            return f
    env.setattr(rc, "_client", Boom())
    env.setenv("RATE_LIMIT_PER_MIN", "1")
    c = TestClient(am.app)
    assert [c.get("/v1/metros").status_code for _ in range(3)] == [200] * 3
    assert c.get(CHI).status_code == 200


def test_429_and_redis_hit_are_observed(env):
    from api import obs
    env.setattr(rc, "_client", fakeredis.FakeRedis())
    c = TestClient(am.app)
    c.get(CHI)
    am._cache.clear()
    hits = obs.CACHE.labels("forecast", "redis_hit")._value.get()
    c.get(CHI)
    assert obs.CACHE.labels("forecast", "redis_hit")._value.get() == hits + 1
    env.setenv("RATE_LIMIT_PER_MIN", "1")
    before = obs.REQUESTS.labels("GET", "unmatched", 429)._value.get()
    assert c.get("/v1/metros").status_code == 429  # earlier calls already used the window
    assert obs.REQUESTS.labels("GET", "unmatched", 429)._value.get() == before + 1
