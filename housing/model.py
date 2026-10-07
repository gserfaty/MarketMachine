"""ML forecasting: feature engineering, rolling-origin backtest, model fit.

The served forecast (`pred_12m`, `national_pred`) is the equal-weight blend of model and naive momentum.

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


def split_for_year(
    df: pd.DataFrame, year: int, horizon: int = 12
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Expanding-window split: test = origins in `year`; train = rows whose target
    window ends no later than the first test origin (no leakage)."""
    test = df[df["date"].dt.year == year].copy()
    if test.empty:
        return df.iloc[0:0].copy(), test
    train = df[df["date"] + pd.DateOffset(months=horizon) <= test["date"].min()].copy()
    return train, test


@dataclass
class ForecastResult:
    metrics: pd.DataFrame
    backtest: pd.DataFrame
    predictions: pd.DataFrame  # pred_12m is the served blend
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


PREDICTORS = ["model", "blend", "naive_momentum", "zero"]
SERVED = "blend"
def blend(model_simple, naive_simple):
    """Equal-weight average of two simple-return forecasts."""
    return (model_simple + naive_simple) / 2


METRICS = ["MAE", "bias", "direction_acc", "rank_ic", "top_decile_lift"]


def rolling_backtest(
    combined: pd.DataFrame, feature_cols: list[str], horizon: int = 12, first_year: int = 2010
) -> pd.DataFrame:
    """Yearly expanding-window backtest on metros. Long frame of simple-return predictions."""
    df = combined[combined["region"] != _US_REGION]
    out = []
    for year in range(first_year, int(df["date"].dt.year.max()) + 1):
        train, test = split_for_year(df, year, horizon)
        if test.empty or train.empty:
            continue
        # ponytail: fit on quarterly origins only (1/3 of rows, ~3.5x faster); drop if CPU allows
        train = train[train["date"].dt.month.isin([1, 4, 7, 10])]
        m = _fit_model(train, feature_cols)
        model_col = np.exp(m.predict(test[feature_cols])) - 1.0
        naive_col = np.exp(test["r12"].to_numpy()) - 1.0
        out.append(pd.DataFrame({
            "region": test["region"].to_numpy(),
            "date": test["date"].to_numpy(),
            "year": year,
            "actual": np.exp(test["y"].to_numpy()) - 1.0,
            "model": model_col,
            "blend": blend(model_col, naive_col),
            "naive_momentum": naive_col,
            "zero": 0.0,
        }))
    if not out:
        raise ValueError("No test years with data for the backtest.")
    return pd.concat(out, ignore_index=True)


def _rank_ic(g: pd.DataFrame, col: str) -> float:
    if g[col].nunique() < 2:
        return float("nan")
    return float(g[col].rank().corr(g["actual"].rank()))


def _top_decile_lift(g: pd.DataFrame, col: str) -> float:
    if g[col].nunique() < 2:
        return float("nan")
    k = max(1, int(np.ceil(0.1 * len(g))))
    top = g[g[col].rank(method="first", ascending=False) <= k]
    return float(top["actual"].mean() - g["actual"].mean()) * 100.0


def score_backtest(preds: pd.DataFrame, predictors: list[str]) -> pd.DataFrame:
    """One row per (year, predictor): MAE, bias, direction_acc, rank_ic, top_decile_lift, n."""
    rows = []
    for year, y in preds.groupby("year"):
        for name in predictors:
            err = y[name] - y["actual"]
            by_date = [g for _, g in y.groupby("date")]
            rows.append({
                "year": year,
                "predictor": name,
                "MAE": float(err.abs().mean()) * 100.0,
                "bias": float(err.mean()) * 100.0,
                "direction_acc": float((np.sign(y[name]) == np.sign(y["actual"])).mean()),
                "rank_ic": pd.Series([_rank_ic(g, name) for g in by_date]).mean(),
                "top_decile_lift": pd.Series([_top_decile_lift(g, name) for g in by_date]).mean(),
                "n": len(y),
            })
    return pd.DataFrame(rows)


def summarize_backtest(scores: pd.DataFrame) -> pd.DataFrame:
    """Equal-weight mean over years (NaN skipped) per predictor, plus year count."""
    g = scores.groupby("predictor")
    out = g[METRICS].mean()
    out["years"] = g["year"].nunique()
    return out.reindex([p for p in PREDICTORS if p in out.index])


def train_and_evaluate(
    long_df: pd.DataFrame, mortgage: pd.Series | None, horizon: int = 12
) -> ForecastResult:
    feat = build_features(long_df, mortgage)
    target = build_target(long_df, horizon=horizon)
    combined = feat.join(target.rename("y"), how="inner").reset_index()

    feature_cols = _active_feature_cols(combined)
    backtest = score_backtest(rolling_backtest(combined, feature_cols, horizon), PREDICTORS)
    metrics = summarize_backtest(backtest)

    # Final fit on every row with a known target, then predict at the latest date.
    full_model = _fit_model(combined, feature_cols)

    as_of = feat.index.get_level_values("date").max()
    latest_feat = feat.xs(as_of, level="date").dropna(subset=feature_cols, how="any")
    latest_pred_log = full_model.predict(latest_feat[feature_cols])
    latest_pred_simple = np.exp(latest_pred_log) - 1.0
    naive_latest = np.exp(latest_feat["r12"].to_numpy()) - 1.0
    served = blend(latest_pred_simple, naive_latest)

    latest_snapshot = long_df[long_df["date"] == as_of][["region", "state", "value"]].drop_duplicates(
        "region"
    )
    predictions = pd.DataFrame(
        {"region": latest_feat.index, "pred_12m": served}
    ).merge(latest_snapshot, on="region", how="left")
    predictions = predictions[["region", "state", "value", "pred_12m"]].sort_values(
        "pred_12m", ascending=False
    ).reset_index(drop=True)

    us_row = predictions[predictions["region"] == _US_REGION]
    national_pred = float(us_row["pred_12m"].iloc[0]) if not us_row.empty else float("nan")

    return ForecastResult(
        metrics=metrics,
        backtest=backtest,
        predictions=predictions,
        national_pred=national_pred,
        as_of=as_of,
        feature_importance=None,
    )
