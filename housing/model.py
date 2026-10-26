"""ML forecasting: feature engineering, rolling-origin backtest, model fit.

The served forecast (`pred_12m`, `national_pred`) is the equal-weight blend of model and naive momentum;
it holds the cumulative change over the trained `horizon` months (3, 12 or 24), despite the column name.
The model fit uses exponential recency weights with a 3-year half-life.

Supply features (inventory YoY, price-cut share) start in 2018 and may be NaN; HGB handles NaN natively.

Each served forecast carries an 80% interval: empirical vol12-scaled quantiles of past blend backtest residuals.
At 24m the width is scaled by an out-of-sample conformal multiplier (calibrate_intervals, same gap as add_intervals).

No Streamlit import here.
"""
from __future__ import annotations

from dataclasses import dataclass

import math

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from housing.data import to_wide

FEATURE_COLS = [
    "r1", "r3", "r6", "r12", "r24", "r36",
    "vol12", "accel", "drawdown36", "rel_us", "us_r12",
    "log_size_rank", "mort", "mort_chg12",
    "inv_yoy", "pc", "pc_chg12",
    "msacsr", "msacsr_chg12",
]
MACRO_LAG_MONTHS = 1  # MSACSR is published ~4 weeks after month end
SUPPLY_COLS = ["inv_yoy", "pc", "pc_chg12"]

_US_REGION = "United States"


def _melt(df: pd.DataFrame, name: str) -> pd.DataFrame:
    m = df.reset_index().melt(id_vars="date", var_name="region", value_name=name)
    return m


def build_features(long_df: pd.DataFrame, mortgage: pd.Series | None = None, supply: pd.DataFrame | None = None,
                   months_supply: pd.Series | None = None) -> pd.DataFrame:
    """Panel of point-in-time features keyed (region, date).

    Every feature at date t is computed only from data available at or before t
    (no lookahead). Rows with NaN core return (r12) are dropped.
    National months' supply (FRED MSACSR, lagged 1 month) is NaN when the series is down.
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

    if supply is not None:
        inv = supply.pivot_table(index="date", columns="region", values="inventory")
        pc = supply.pivot_table(index="date", columns="region", values="price_cut")
        inv_yoy = np.log(inv / inv.shift(12)).replace([np.inf, -np.inf], np.nan)
        for df_, name in ((inv_yoy, "inv_yoy"), (pc, "pc"), (pc - pc.shift(12), "pc_chg12")):
            feat = feat.merge(_melt(df_, name), on=["region", "date"], how="left")
    else:
        for c in SUPPLY_COLS:
            feat[c] = np.nan

    if mortgage is not None:
        mort_df = mortgage.rename("mort").reset_index()
        mort_df = mort_df.rename(columns={mort_df.columns[0]: "date"})
        feat = feat.merge(mort_df, on="date", how="left")
        feat = feat.sort_values(["region", "date"])
        feat["mort_chg12"] = feat.groupby("region")["mort"].transform(lambda s: s - s.shift(12))
    else:
        feat["mort"] = np.nan
        feat["mort_chg12"] = np.nan

    if months_supply is not None:
        idx = pd.date_range(months_supply.index.min(), feat["date"].max(), freq="ME")
        ms = months_supply.reindex(idx).ffill().shift(MACRO_LAG_MONTHS)  # point-in-time; ffill covers a late release
        ms_df = pd.DataFrame({"date": idx, "msacsr": ms.to_numpy(), "msacsr_chg12": (ms - ms.shift(12)).to_numpy()})
        feat = feat.merge(ms_df, on="date", how="left")
    else:
        feat["msacsr"] = np.nan
        feat["msacsr_chg12"] = np.nan

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
    predictions: pd.DataFrame  # pred_12m is the served blend (cumulative change over `horizon` months)
    national_pred: float
    as_of: pd.Timestamp
    feature_importance: pd.Series | None = None
    national_interval: tuple[float, float] = (float("nan"), float("nan"))
    interval_k: float = 1.0
    model: HistGradientBoostingRegressor | None = None


def _active_feature_cols(df: pd.DataFrame, cols: list[str] = FEATURE_COLS) -> list[str]:
    """`cols` (default FEATURE_COLS) present and not entirely NaN (e.g. macro features when mortgage=None)."""
    return [c for c in cols if c in df.columns and df[c].notna().any()]


HALF_LIFE_YEARS = 3.0


def recency_weights(dates: pd.Series, ref_date: pd.Timestamp, half_life: float = HALF_LIFE_YEARS) -> np.ndarray:
    return np.asarray(0.5 ** (((ref_date - dates).dt.days / 365.25) / half_life))


def _fit_model(train: pd.DataFrame, feature_cols: list[str], ref_date: pd.Timestamp) -> HistGradientBoostingRegressor:
    model = HistGradientBoostingRegressor(
        max_iter=300,
        learning_rate=0.05,
        max_leaf_nodes=31,
        min_samples_leaf=50,
        l2_regularization=1.0,
        random_state=0,
    )
    model.fit(train[feature_cols], train["y"], sample_weight=recency_weights(train["date"], ref_date))
    return model


PREDICTORS = ["model", "blend", "naive_momentum", "zero"]
SERVED = "blend"
def blend(model_simple, naive_simple):
    """Equal-weight average of two simple-return forecasts."""
    return (model_simple + naive_simple) / 2


METRICS = ["MAE", "bias", "direction_acc", "rank_ic", "top_decile_lift", "coverage80", "width80"]
INTERVAL_Q = (0.1, 0.9)
VOL_FLOOR = 0.001


def interval_scale(vol12) -> np.ndarray:
    return np.maximum(np.asarray(vol12, float), VOL_FLOOR)


def z_quantiles(preds: pd.DataFrame) -> tuple[float, float]:
    """INTERVAL_Q quantiles of vol12-scaled blend residuals (NaN skipped)."""
    z = (preds["actual"] - preds[SERVED]) / interval_scale(preds["vol12"])
    lo, hi = z.dropna().quantile(list(INTERVAL_Q))
    return float(lo), float(hi)


def calibrate_intervals(preds: pd.DataFrame, horizon: int = 12) -> tuple[pd.DataFrame, float]:
    """Scale lo/hi about their center by the past 0.8-quantile of |actual-center|/half-width (years <= Y-gap). Returns (out, k_all)."""
    gap = 1 + math.ceil(horizon / 12)
    out = preds.copy()
    c, half = (preds["lo"] + preds["hi"]) / 2, (preds["hi"] - preds["lo"]) / 2
    s = (preds["actual"] - c).abs() / half
    for year in out["year"].unique():
        past = s[(preds["year"] <= year - gap) & preds["lo"].notna()].dropna()
        k = past.quantile(0.8) if not past.empty else 1.0
        m = (out["year"] == year) & preds["lo"].notna()
        out.loc[m, "lo"] = c[m] - k * half[m]
        out.loc[m, "hi"] = c[m] + k * half[m]
    return out, float(s.dropna().quantile(0.8))


def add_intervals(preds: pd.DataFrame, horizon: int = 12) -> pd.DataFrame:
    """Add lo/hi; year Y uses only residuals from years <= Y-gap, gap = 1 + ceil(horizon/12) (later outcomes are not yet known)."""
    gap = 1 + math.ceil(horizon / 12)
    out = preds.copy()
    out["lo"] = np.nan
    out["hi"] = np.nan
    for year in out["year"].unique():
        hist = preds[preds["year"] <= year - gap]
        if hist.empty:
            continue
        zlo, zhi = z_quantiles(hist)
        m = out["year"] == year
        scale = interval_scale(out.loc[m, "vol12"])
        out.loc[m, "lo"] = out.loc[m, SERVED] + zlo * scale
        out.loc[m, "hi"] = out.loc[m, SERVED] + zhi * scale
    return out


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
        cols = [c for c in feature_cols if train[c].notna().any()]
        m = _fit_model(train, cols, test["date"].min())
        model_col = np.exp(m.predict(test[cols])) - 1.0
        naive_col = np.exp(test["r12"].to_numpy() * horizon / 12) - 1.0
        out.append(pd.DataFrame({
            "region": test["region"].to_numpy(),
            "date": test["date"].to_numpy(),
            "year": year,
            "vol12": test["vol12"].to_numpy(),
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
            cov = wid = float("nan")
            if name == SERVED and {"lo", "hi"} <= set(y.columns) and y["lo"].notna().any():
                v = y[y["lo"].notna()]
                cov = float(((v["lo"] <= v["actual"]) & (v["actual"] <= v["hi"])).mean())
                wid = float((v["hi"] - v["lo"]).mean()) * 100.0
            by_date = [g for _, g in y.groupby("date")]
            rows.append({
                "year": year,
                "predictor": name,
                "MAE": float(err.abs().mean()) * 100.0,
                "bias": float(err.mean()) * 100.0,
                "direction_acc": float((np.sign(y[name]) == np.sign(y["actual"])).mean()),
                "rank_ic": pd.Series([_rank_ic(g, name) for g in by_date]).mean(),
                "top_decile_lift": pd.Series([_top_decile_lift(g, name) for g in by_date]).mean(),
                "coverage80": cov,
                "width80": wid,
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
    long_df: pd.DataFrame, mortgage: pd.Series | None, supply: pd.DataFrame | None = None, horizon: int = 12,
    months_supply: pd.Series | None = None, feature_cols: list[str] | None = None,
) -> ForecastResult:
    feat = build_features(long_df, mortgage, supply, months_supply)
    target = build_target(long_df, horizon=horizon)
    combined = feat.join(target.rename("y"), how="inner").reset_index()

    feature_cols = _active_feature_cols(combined, feature_cols or FEATURE_COLS)
    raw = add_intervals(rolling_backtest(combined, feature_cols, horizon), horizon)
    k = 1.0
    # ponytail: only 24m is calibrated (3m/12m already ~0.80 coverage); one global multiplier, per-year k is out-of-sample
    if horizon >= 24:
        raw, k = calibrate_intervals(raw, horizon)
    backtest = score_backtest(raw, PREDICTORS)
    zlo, zhi = z_quantiles(raw)
    metrics = summarize_backtest(backtest)

    # Final fit on every row with a known target, then predict at the latest date.
    as_of = feat.index.get_level_values("date").max()
    full_model = _fit_model(combined, feature_cols, as_of)

    latest_feat = feat.xs(as_of, level="date").dropna(
        subset=[c for c in feature_cols if c not in SUPPLY_COLS], how="any"
    )
    latest_pred_log = full_model.predict(latest_feat[feature_cols])
    latest_pred_simple = np.exp(latest_pred_log) - 1.0
    naive_latest = np.exp(latest_feat["r12"].to_numpy() * horizon / 12) - 1.0
    served = blend(latest_pred_simple, naive_latest)

    scale = interval_scale(latest_feat["vol12"].to_numpy())
    latest_snapshot = long_df[long_df["date"] == as_of][["region", "state", "value"]].drop_duplicates(
        "region"
    )
    c, half = served + (zlo + zhi) / 2 * scale, (zhi - zlo) / 2 * scale
    predictions = pd.DataFrame(
        {"region": latest_feat.index, "pred_12m": served, "lo_12m": c - k * half, "hi_12m": c + k * half}
    ).merge(latest_snapshot, on="region", how="left")
    predictions = predictions[["region", "state", "value", "pred_12m", "lo_12m", "hi_12m"]].sort_values(
        "pred_12m", ascending=False
    ).reset_index(drop=True)

    us_row = predictions[predictions["region"] == _US_REGION]
    national_pred = float(us_row["pred_12m"].iloc[0]) if not us_row.empty else float("nan")

    national_interval = (
        (float(us_row["lo_12m"].iloc[0]), float(us_row["hi_12m"].iloc[0])) if not us_row.empty else (float("nan"),) * 2
    )

    return ForecastResult(
        metrics=metrics,
        backtest=backtest,
        predictions=predictions,
        national_pred=national_pred,
        as_of=as_of,
        feature_importance=None,
        national_interval=national_interval,
        interval_k=k,
        model=full_model,
    )
