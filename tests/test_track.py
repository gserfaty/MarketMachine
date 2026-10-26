import subprocess
import sys

import numpy as np
import pytest

from housing import track
from tests.conftest import FIXTURES_DIR


@pytest.fixture(scope="module")
def tracked(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("mlf")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("MARKETMACHINE_DATA_DIR", FIXTURES_DIR)
        track.setup(f"sqlite:///{tmp}/t.db", str(tmp / "art"))
        yield track.run_experiment(track.load_inputs(), 12)


def test_should_promote():
    ok = lambda cov, mae=1.0, champ=1.0: track.should_promote(  # noqa: E731
        {"blend_MAE": mae, "blend_coverage80": cov}, None if champ is None else {"blend_MAE": champ})[0]
    assert ok(0.8, champ=None)
    assert not ok(0.6, champ=None)
    assert ok(0.8, mae=1.01)
    assert not ok(0.8, mae=1.05)
    assert not ok(0.95)
    assert not ok(float("nan"))


def test_run_logged(tracked):
    assert tracked["version"] == "1"
    run = track.MlflowClient().get_run(tracked["run_id"])
    for p in ("horizon", "half_life_years", "features", "has_supply"):
        assert p in run.data.params
    assert run.data.params["horizon"] == "12"
    for m in ("blend_MAE", "naive_momentum_MAE", "blend_coverage80", "blend_rank_ic"):
        assert m in run.data.metrics
    assert "git_sha" in run.data.tags
    assert "backtest_by_year.csv" in [a.path for a in track.MlflowClient().list_artifacts(tracked["run_id"])]


def test_promote_and_load(tracked):
    assert track.load_champion(12) is None and track.load_champion(3) is None
    assert track.promote(12, "1", True).startswith("champion")
    m = track.load_champion(12)
    X = np.zeros((5, len(m.feature_names_in_)))
    assert len(m.predict(__import__("pandas").DataFrame(X, columns=m.feature_names_in_))) == 5
    champ_mae = tracked["metrics"]["blend_MAE"]
    with track.mlflow.start_run():
        track.mlflow.log_metric("blend_MAE", champ_mae + 1)
        track.mlflow.log_metric("blend_coverage80", 0.8)
        track.mlflow.sklearn.log_model(m, name="model", registered_model_name="marketmachine-12m",
                                       serialization_format="cloudpickle")
    assert track.promote(12, "2", True).startswith("challenger")
    c = track.MlflowClient()
    assert str(c.get_model_version_by_alias("marketmachine-12m", "champion").version) == "1"


def test_report(tracked):
    r = track.report()
    r = r[r["run_id"] == tracked["run_id"]]
    assert len(r) == 1 and r.iloc[0]["horizon"] == "12"
    assert r.iloc[0]["version"] == "1" and r.iloc[0]["alias"] == "champion"


def test_app_does_not_import_mlflow():
    code = "import sys, housing.shared, housing.model; assert 'mlflow' not in sys.modules"
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0
