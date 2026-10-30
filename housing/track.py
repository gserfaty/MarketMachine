"""Experiment tracking + model registry (MLflow, local sqlite). CLI: python -m housing.track [--promote|--report].

Only the CLI and tests import this; the Streamlit app never imports mlflow. No Streamlit import here.
"""
from __future__ import annotations

import argparse
import math
import os
import subprocess
from pathlib import Path

os.environ.setdefault("MLFLOW_DISABLE_TELEMETRY", "true")
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

import mlflow  # noqa: E402
import mlflow.sklearn  # noqa: E402
import pandas as pd  # noqa: E402
from mlflow import MlflowClient  # noqa: E402
from mlflow.exceptions import MlflowException  # noqa: E402

from housing import data, model  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = "marketmachine"
HORIZONS = (3, 12, 24)
TOL_MAE = 0.02  # pp, reproduction tolerance (RESEARCH.md)
COVERAGE_BOUNDS = (0.70, 0.90)


def setup(tracking_uri: str | None = None, artifact_dir: str | None = None) -> str:
    uri = tracking_uri or os.environ.get("MLFLOW_TRACKING_URI") or f"sqlite:///{ROOT / 'mlruns.db'}"
    mlflow.set_tracking_uri(uri)
    if mlflow.get_experiment_by_name(EXPERIMENT) is None:
        mlflow.create_experiment(EXPERIMENT, artifact_location=Path(artifact_dir or ROOT / "mlartifacts").resolve().as_uri())
    mlflow.set_experiment(EXPERIMENT)
    return uri


load_inputs = data.load_forecast_inputs


def _git_sha() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _asof(x) -> str:
    if x is None:
        return "none"
    d = x["date"].max() if isinstance(x, pd.DataFrame) else x.last_valid_index()
    return str(pd.Timestamp(d).date())


def run_experiment(inputs: dict, horizon: int, feature_cols: list[str] | None = None, register: bool = True) -> dict:
    res = model.train_and_evaluate(
        inputs["long_df"], inputs["mortgage"], supply=inputs["supply"], horizon=horizon,
        months_supply=inputs["months_supply"], feature_cols=feature_cols,
    )
    with mlflow.start_run(run_name=f"{horizon}m") as run:
        params = {
            "horizon": horizon, "features": ",".join(res.model.feature_names_in_),
            "half_life_years": model.HALF_LIFE_YEARS, "first_backtest_year": 2010,
            "served": "blend(model,naive_momentum)",
            "as_of_zhvi": res.as_of.date(), "as_of_mortgage": _asof(inputs["mortgage"]),
            "as_of_supply": _asof(inputs["supply"]), "as_of_msacsr": _asof(inputs["months_supply"]),
            "has_mortgage": inputs["mortgage"] is not None, "has_supply": inputs["supply"] is not None,
            "has_msacsr": inputs["months_supply"] is not None,
        }
        params.update({f"hgb_{k}": v for k, v in res.model.get_params().items()})
        mlflow.log_params(params)
        metrics = {"interval_k": res.interval_k}
        for pred, row in res.metrics.iterrows():
            for m in model.METRICS:
                metrics[f"{pred}_{m}"] = float(row[m])
        metrics = {k: v for k, v in metrics.items() if math.isfinite(v)}
        mlflow.log_metrics(metrics)
        mlflow.set_tag("git_sha", _git_sha())
        mlflow.log_text(res.backtest.to_csv(index=False), "backtest_by_year.csv")
        version = None
        if register:
            info = mlflow.sklearn.log_model(
                res.model, name="model", registered_model_name=f"marketmachine-{horizon}m",
                serialization_format="cloudpickle",
            )
            version = str(info.registered_model_version)
    return {"horizon": horizon, "run_id": run.info.run_id, "version": version, "metrics": metrics}


def should_promote(new: dict, champ: dict | None, tol: float = TOL_MAE, bounds=COVERAGE_BOUNDS) -> tuple[bool, str]:
    cov = new.get("blend_coverage80", float("nan"))
    if cov is None or math.isnan(cov) or not bounds[0] <= cov <= bounds[1]:
        return False, f"coverage80 {cov} outside {bounds}"
    if champ is None:
        return True, "no champion yet"
    if new["blend_MAE"] <= champ["blend_MAE"] + tol:
        return True, f"MAE {new['blend_MAE']:.3f} <= champion {champ['blend_MAE']:.3f} + {tol}"
    return False, f"MAE {new['blend_MAE']:.3f} > champion {champ['blend_MAE']:.3f} + {tol}"


def _champion_version(client: MlflowClient, name: str):
    try:
        return client.get_model_version_by_alias(name, "champion")
    except MlflowException:
        return None


def promote(horizon: int, version: str, apply: bool) -> str:
    client, name = MlflowClient(), f"marketmachine-{horizon}m"
    new = client.get_run(client.get_model_version(name, version).run_id).data.metrics
    champ_v = _champion_version(client, name)
    champ = client.get_run(champ_v.run_id).data.metrics if champ_v else None
    ok, reason = should_promote(new, champ)
    alias = "champion" if apply and ok else "challenger"
    client.set_registered_model_alias(name, alias, version)
    return f"{alias}: {reason}"


def champion_version(horizon: int) -> str | None:
    try:
        v = _champion_version(MlflowClient(), f"marketmachine-{horizon}m")
        return str(v.version) if v else None
    except Exception:
        return None


def load_champion(horizon: int):
    try:
        return mlflow.sklearn.load_model(f"models:/marketmachine-{horizon}m@champion")
    except Exception:
        return None


def report() -> pd.DataFrame:
    runs = mlflow.search_runs(experiment_names=[EXPERIMENT], order_by=["start_time DESC"])
    if runs.empty:
        return runs
    client, alias = MlflowClient(), {}
    for h in HORIZONS:
        name = f"marketmachine-{h}m"
        try:
            aliases = client.get_registered_model(name).aliases
        except MlflowException:  # horizon never registered
            continue
        by_ver = {}  # search_model_versions leaves .aliases empty; the registered model has the alias map
        for a, ver in aliases.items():
            by_ver.setdefault(str(ver), []).append(a)
        for v in client.search_model_versions(f"name='{name}'"):
            alias[v.run_id] = (str(v.version), ",".join(by_ver.get(str(v.version), [])))
    cols = {"run_id": "run_id", "start_time": "start", "tags.mlflow.runName": "run", "params.horizon": "horizon",
            "metrics.blend_MAE": "blend_MAE", "metrics.model_MAE": "model_MAE",
            "metrics.naive_momentum_MAE": "naive_MAE", "metrics.zero_MAE": "zero_MAE",
            "metrics.blend_bias": "blend_bias", "metrics.blend_rank_ic": "rank_ic",
            "metrics.blend_top_decile_lift": "top_decile_lift", "metrics.blend_coverage80": "coverage80",
            "metrics.blend_width80": "width80", "tags.git_sha": "git_sha"}
    out = runs.reindex(columns=list(cols)).rename(columns=cols)
    out["version"] = [alias.get(r, ("", ""))[0] for r in runs["run_id"]]
    out["alias"] = [alias.get(r, ("", ""))[1] for r in runs["run_id"]]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m housing.track")
    ap.add_argument("--horizons", type=int, nargs="+", default=list(HORIZONS))
    ap.add_argument("--promote", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)
    setup()
    if args.report:
        print(report().to_string(index=False))
        return 0
    inputs, results = load_inputs(), []
    for h in args.horizons:
        r = run_experiment(inputs, h)
        print(f"{h}m v{r['version']} -> {promote(h, r['version'], args.promote)}")
        results.append(r)
    ids = {r["run_id"] for r in results}
    t = report()
    cols = ["horizon", "blend_MAE", "blend_bias", "rank_ic", "coverage80", "width80", "version", "alias"]
    t = t[t["run_id"].isin(ids)].sort_values("horizon", key=lambda s: s.astype(int))
    print(t[cols].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
