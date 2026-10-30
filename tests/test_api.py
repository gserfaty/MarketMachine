import shutil
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

import api.main as am
from tests.conftest import FIXTURES_DIR

CHI = "/v1/metros/Chicago%2C%20IL/forecast"


@pytest.fixture(scope="module")
def client():
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("MARKETMACHINE_DATA_DIR", FIXTURES_DIR)
        mp.setattr(am, "_champion", lambda h: None)
        am._cache.clear()
        c = TestClient(am.app)
        r = c.get(CHI, params={"horizon": 12})
        assert r.status_code == 200, r.text
        c.warm = r.json()
        yield c
    am._cache.clear()


def test_health(client):
    assert client.get("/v1/health").json() == {"status": "ok"}


def test_ready(client):
    b = client.get("/v1/ready").json()
    assert 12 in b["forecasts_cached"] and b["metros"] == 10


def test_metros(client):
    b = client.get("/v1/metros").json()
    assert b["total"] == 10 and all(i["region"] != "United States" for i in b["items"])


def test_metros_filter_sort(client):
    assert client.get("/v1/metros?state=TX").json()["total"] == 2
    assert [i["region"] for i in client.get("/v1/metros?q=chicago").json()["items"]] == ["Chicago, IL"]
    v = [i["value"] for i in client.get("/v1/metros?sort=value&order=desc").json()["items"]]
    assert v == sorted(v, reverse=True)


def test_metros_paging(client):
    p = client.get("/v1/metros?limit=3&offset=3").json()
    assert len(p["items"]) == 3 and p["items"][0]["size_rank"] == 4
    assert client.get("/v1/metros?limit=0").status_code == 422


def test_forecast_name_and_id(client):
    a, b = client.warm, client.get("/v1/metros/10003/forecast").json()
    assert a == b and a["region_id"] == 10003
    assert a["lo80"] <= a["pred"] <= a["hi80"]
    assert a["model"]["source"] == "trained on demand" and a["disclaimer"]


def test_forecast_errors(client):
    r = client.get(CHI, params={"horizon": 6})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


def test_unknown_routes_and_metros(client):
    for k in ("Nowhere%2C%20ZZ", "99999"):
        r = client.get(f"/v1/metros/{k}/forecast")
        assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
    r = client.get("/v1/nope")
    assert r.status_code == 404 and r.json()["error"]["status"] == 404


def test_summary(client):
    r = client.get("/v1/forecast/summary")
    assert r.status_code == 200
    b = r.json()
    assert "NaN" not in r.text and len(b["scores"]) == 4
    assert [s for s in b["scores"] if s["predictor"] == "blend"][0]["coverage80"] is not None


def test_affordability(client):
    b = client.get("/v1/affordability?income=120000").json()
    s = [i["share"] for i in b["items"]]
    assert s == sorted(s) and b["total"] > 0
    assert len(client.get("/v1/affordability?income=120000&limit=2&offset=1").json()["items"]) == 2


def test_affordability_validation(client):
    assert client.get("/v1/affordability?income=0").status_code == 422


def test_financing(client):
    body = {"price": 450000, "down_pct": 20, "state": "TX"}
    r = client.post("/v1/financing/estimate", json=body)
    assert r.status_code == 200 and r.json()["piti"] > r.json()["pi"]
    assert client.post("/v1/financing/estimate", json={**body, "loan_type": "fha", "down_pct": 1}).status_code == 422
    assert client.post("/v1/financing/estimate", json={**body, "state": "ZZ"}).status_code == 422
    assert client.post("/v1/financing/estimate", json={"down_pct": 20, "state": "TX"}).status_code == 422


def test_openapi(client):
    paths = [p for p in client.get("/openapi.json").json()["paths"] if p.startswith("/v1/")]
    assert len(paths) == 7


def test_corrupt_zhvi_503(tmp_path, monkeypatch):
    shutil.copytree(FIXTURES_DIR, tmp_path, dirs_exist_ok=True)
    p = tmp_path / "zhvi_metro.csv"
    lines = p.read_text().splitlines()
    cells = lines[2].split(",")
    cells[-1] = "-5"
    lines[2] = ",".join(cells)
    p.write_text("\n".join(lines) + "\n")
    monkeypatch.setenv("MARKETMACHINE_DATA_DIR", str(tmp_path))
    c = TestClient(am.app)
    for path in ("/v1/ready", "/v1/metros"):
        r = c.get(path)
        e = r.json()["error"]
        assert r.status_code == 503 and e["code"] == "data_invalid" and "zhvi_metro" in e["message"]


def test_registry_path(client, monkeypatch):
    am._cache_keys = [k for k in am._cache if k[0] == "forecast"]
    res, _ = am._cache[am._cache_keys[0]][1]
    for k in am._cache_keys:
        del am._cache[k]
    monkeypatch.setattr(am, "_champion", lambda h: (res.model, "7"))
    b = client.get(CHI).json()
    assert b["model"] == {"source": "registry", "name": "marketmachine-12m", "version": "7"}


def test_cached_ttl_and_exceptions():
    n = []
    am.cached(("t",), 0, lambda: n.append(1))
    am.cached(("t",), 0, lambda: n.append(1))
    assert len(n) == 2
    am.cached(("t2",), 1000, lambda: n.append(1))
    am.cached(("t2",), 1000, lambda: n.append(1))
    assert len(n) == 3

    def boom():
        raise RuntimeError

    for _ in range(2):
        with pytest.raises(RuntimeError):
            am.cached(("t3",), 1000, boom)
    assert am.cached(("t3",), 1000, lambda: 5) == 5


def test_api_imports_no_streamlit():
    code = "import api.main, sys; assert 'streamlit' not in sys.modules and 'mlflow' not in sys.modules"
    subprocess.run([sys.executable, "-c", code], check=True)


def test_concurrent_first_requests_compute_once():
    import threading
    import time as _t

    from api import main as api_main

    calls = []

    def slow():
        calls.append(1)
        _t.sleep(0.2)
        return "v"

    key = ("test-concurrency", _t.monotonic())
    out = []
    threads = [threading.Thread(target=lambda: out.append(api_main.cached(key, 60, slow))) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert out == ["v"] * 5 and len(calls) == 1
