"""ML forecasting: feature engineering, time-based validation, model fit.

No Streamlit import here.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from housing.data import to_wide

FEATURE_COLS = [
    "r1", "r3", "r6", "r12", "r24", "r36",
    "vol12", "accel", "drawdown36", "rel_us", "us_r12",
    "log_size_rank", "mort", "mort_chg12",
]

_US_REGION = "United States"


def _melt(df: pd.DataFrame, name: str) -> pd.DataFrame:
    m = df.reset_index().melt(id_vars="date", var_name="region", value_name=name)
    return m


def build_features(long_df: pd.DataFrame, mortgage: pd.Series | None = None) -> pd.DataFrame:
    """Panel of point-in-time features keyed (region, date).

    Every feature at date t is computed only from data available at or before t
    (no lookahead). Rows with NaN core return (r12) are dropped.
    """
    wide = to_wide(long_df)
    logp = np.log(wide)

    returns = {k: logp - logp.shift(k) for k in (1, 3, 6, 12, 24, 36)}
    vol12 = returns[1].rolling(12).std()
    accel = returns[3] - returns[3].shift(3)
    drawdown36 = logp - logp.rolling(36, min_periods=1).max()

    if _US_REGION not in logp.columns:
        raise ValueError(f"Expected a '{_US_REGION}' region column in the panel.")
    rel_us = logp.sub(logp[_US_REGION], axis=0)
    us_r12 = returns[12][_US_REGION]

    parts = [_melt(returns[k], f"r{k}") for k in (1, 3, 6, 12, 24, 36)]
    parts.append(_melt(vol12, "vol12"))
    parts.append(_melt(accel, "accel"))
    parts.append(_melt(drawdown36, "drawdown36"))
    parts.append(_melt(rel_us, "rel_us"))

    feat = parts[0]
    for p in parts[1:]:
        feat = feat.merge(p, on=["date", "region"], how="outer")

    us_r12_df = us_r12.rename("us_r12").reset_index()
    feat = feat.merge(us_r12_df, on="date", how="left")

    size_rank = long_df[["region", "date", "size_rank"]].drop_duplicates(["region", "date"])
    feat = feat.merge(size_rank, on=["region", "date"], how="left")
    feat["log_size_rank"] = np.log1p(feat["size_rank"])
    feat = feat.drop(columns=["size_rank"])

    if mortgage is not None:
        mort_df = mortgage.rename("mort").reset_index()
        mort_df = mort_df.rename(columns={mort_df.columns[0]: "date"})
        feat = feat.merge(mort_df, on="date", how="left")
        feat = feat.sort_values(["region", "date"])
        feat["mort_chg12"] = feat.groupby("region")["mort"].transform(lambda s: s - s.shift(12))
    else:
        feat["mort"] = np.nan
        feat["mort_chg12"] = np.nan

    feat = feat.dropna(subset=["r12"])
    feat = feat.set_index(["region", "date"]).sort_index()
    return feat


def build_target(long_df: pd.DataFrame, horizon: int = 12) -> pd.Series:
    """y = log(P[t+horizon] / P[t]), keyed (region, date=t)."""
    wide = to_wide(long_df)
    logp = np.log(wide)
    y = logp.shift(-horizon) - logp
    m = y.reset_index().melt(id_vars="date", var_name="region", value_name="y")
    m = m.dropna(subset=["y"])
    return m.set_index(["region", "date"])["y"]


def time_split(
    df: pd.DataFrame, test_months: int = 24, horizon: int = 12
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Time-based train/test split with no leakage.

    `df` must have a `date` column and only rows where the target is known.
    Test = the last `test_months` origins. Train = origins early enough that
    every train target window ends before the first test origin.
    """
    last_origin = df["date"].max()
    test_start = last_origin - pd.DateOffset(months=test_months - 1)
    train_cutoff = last_origin - pd.DateOffset(months=test_months + horizon)
    test = df[(df["date"] >= test_start) & (df["date"] <= last_origin)].copy()
    train = df[df["date"] <= train_cutoff].copy()
    return train, test


@dataclass
class ForecastResult:
    metrics: pd.DataFrame
    predictions: pd.DataFrame
    national_pred: float
    as_of: pd.Timestamp
    feature_importance: pd.Series | None = None


def _active_feature_cols(df: pd.DataFrame) -> list[str]:
    """FEATURE_COLS present and not entirely NaN (e.g. macro features when mortgage=None)."""
    return [c for c in FEATURE_COLS if c in df.columns and df[c].notna().any()]


def _fit_model(train: pd.DataFrame, feature_cols: list[str]) -> HistGradientBoostingRegressor:
    model = HistGradientBoostingRegressor(
        max_iter=300,
        learning_rate=0.05,
        max_leaf_nodes=31,
        min_samples_leaf=50,
        l2_regularization=1.0,
        random_state=0,
    )
    model.fit(train[feature_cols], train["y"])
    return model


def _direction_acc(pred_simple: np.ndarray, actual_simple: np.ndarray) -> float:
    return float(np.mean(np.sign(pred_simple) == np.sign(actual_simple)))


def train_and_evaluate(
    long_df: pd.DataFrame, mortgage: pd.Series | None, horizon: int = 12
) -> ForecastResult:
    feat = build_features(long_df, mortgage)
    target = build_target(long_df, horizon=horizon)
    combined = feat.join(target.rename("y"), how="inner").reset_index()

    train, test = time_split(combined, test_months=24, horizon=horizon)

    feature_cols = _active_feature_cols(combined)
    model = _fit_model(train, feature_cols)
    pred_log = model.predict(test[feature_cols])
    actual_log = test["y"].to_numpy()
    pred_simple = np.exp(pred_log) - 1.0
    actual_simple = np.exp(actual_log) - 1.0

    naive_pred_simple = np.exp(test["r12"].to_numpy()) - 1.0
    zero_pred_simple = np.zeros_like(actual_simple)

    metrics_rows = []
    for name, p in (
        ("model", pred_simple),
        ("naive_momentum", naive_pred_simple),
        ("zero", zero_pred_simple),
    ):
        mae = float(np.mean(np.abs(p - actual_simple))) * 100.0
        dacc = _direction_acc(p, actual_simple)
        metrics_rows.append({"model": name, "MAE": mae, "direction_acc": dacc, "n_test": len(test)})
    metrics = pd.DataFrame(metrics_rows).set_index("model")

    # Final fit on every row with a known target, then predict at the latest date.
    full_model = _fit_model(combined, feature_cols)

    as_of = feat.index.get_level_values("date").max()
    latest_feat = feat.xs(as_of, level="date").dropna(subset=feature_cols, how="any")
    latest_pred_log = full_model.predict(latest_feat[feature_cols])
    latest_pred_simple = np.exp(latest_pred_log) - 1.0

    latest_snapshot = long_df[long_df["date"] == as_of][["region", "state", "value"]].drop_duplicates(
        "region"
    )
    predictions = pd.DataFrame(
        {"region": latest_feat.index, "pred_12m": latest_pred_simple}
    ).merge(latest_snapshot, on="region", how="left")
    predictions = predictions[["region", "state", "value", "pred_12m"]].sort_values(
        "pred_12m", ascending=False
    ).reset_index(drop=True)

    us_row = predictions[predictions["region"] == _US_REGION]
    national_pred = float(us_row["pred_12m"].iloc[0]) if not us_row.empty else float("nan")

    return ForecastResult(
        metrics=metrics,
        predictions=predictions,
        national_pred=national_pred,
        as_of=as_of,
        feature_importance=None,
    )
