"""Postgres forecast ledger + drift stats. Disabled unless DATABASE_URL is set; write errors are logged, never raised."""
from __future__ import annotations

import logging
import os
from datetime import date, datetime, timezone
from functools import lru_cache

import numpy as np
import pandas as pd
from sqlalchemy import Date, DateTime, Float, Integer, String, UniqueConstraint, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

log = logging.getLogger("marketmachine.ledger")


class Base(DeclarativeBase):
    pass


class Forecast(Base):
    __tablename__ = "forecasts"
    __table_args__ = (UniqueConstraint("as_of", "horizon", "region", "model_version"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    as_of: Mapped[date] = mapped_column(Date, index=True)
    horizon: Mapped[int] = mapped_column(Integer)
    region: Mapped[str] = mapped_column(String)
    pred: Mapped[float] = mapped_column(Float)
    lo: Mapped[float] = mapped_column(Float)
    hi: Mapped[float] = mapped_column(Float)
    model_version: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


@lru_cache
def _engine(url: str):
    return create_engine(url, pool_pre_ping=True)


def engine():
    url = os.environ.get("DATABASE_URL")
    return _engine(url) if url else None


def record(res, horizon: int, version: str | None) -> None:
    """Store every metro's prediction for this (as_of, horizon, version) once. SQL treats NULL versions as distinct in
    a unique constraint, so the existence check is what makes unversioned recording idempotent."""
    eng = engine()
    if eng is None:
        return
    try:
        as_of = res.as_of.date()
        with Session(eng) as s, s.begin():
            if s.scalar(select(func.count()).where(Forecast.as_of == as_of, Forecast.horizon == horizon,
                                                   Forecast.model_version == version)):
                return
            ok = res.predictions.dropna(subset=["pred_12m", "lo_12m", "hi_12m"])
            s.add_all(Forecast(as_of=as_of, horizon=horizon, region=r.region, pred=float(r.pred_12m),
                               lo=float(r.lo_12m), hi=float(r.hi_12m), model_version=version)
                      for r in ok.itertuples())
    except Exception:  # noqa: BLE001
        log.warning("ledger write failed", exc_info=True)


def psi(expected, actual, bins: int = 10) -> float:
    """Population stability index; bin edges are quantiles of `expected`, bin shares floored at 1e-4."""
    edges = np.unique(np.quantile(expected, np.linspace(0, 1, bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    e = np.clip(np.histogram(expected, edges)[0] / len(expected), 1e-4, None)
    a = np.clip(np.histogram(actual, edges)[0] / len(actual), 1e-4, None)
    return float(((a - e) * np.log(a / e)).sum())


def realized_error(rows: pd.DataFrame, long_df: pd.DataFrame, horizon: int) -> dict | None:
    """Error (pp) of ledger rows whose as_of + horizon months is already in the ZHVI data. rows: as_of, region, pred."""
    p = long_df.assign(m=long_df["date"].dt.to_period("M")).drop_duplicates(["m", "region"]).set_index(["m", "region"])["value"]
    m0 = pd.to_datetime(rows["as_of"]).dt.to_period("M")
    due = rows[m0 + horizon <= p.index.get_level_values("m").max()]
    if due.empty:
        return None
    m0 = pd.to_datetime(due["as_of"]).dt.to_period("M")
    start = p.reindex(pd.MultiIndex.from_arrays([m0, due["region"]])).to_numpy()
    end = p.reindex(pd.MultiIndex.from_arrays([m0 + horizon, due["region"]])).to_numpy()
    err = (due["pred"].to_numpy() - (end / start - 1)) * 100.0
    err = err[~np.isnan(err)]
    if not len(err):
        return None
    return {"n": int(len(err)), "mae": float(np.abs(err).mean()), "bias": float(err.mean())}


def drift(eng, horizon: int, long_df: pd.DataFrame, backtest_mae: float | None) -> dict:
    with Session(eng) as s:
        rows = pd.read_sql(select(Forecast.as_of, Forecast.region, Forecast.pred).where(Forecast.horizon == horizon),
                           s.connection())
    out = {"horizon": horizon, "backtest_mae": backtest_mae, "realized": realized_error(rows, long_df, horizon),
           "shift": None}
    # ponytail: a batch is one as_of date (versions at the same as_of mix); split by model_version if that matters
    dates = sorted(rows["as_of"].unique())
    if len(dates) >= 2:
        new, old = (rows.loc[rows["as_of"] == d, "pred"].to_numpy() for d in (dates[-1], dates[-2]))
        out["shift"] = {"latest_as_of": dates[-1], "previous_as_of": dates[-2], "n_latest": len(new),
                        "n_previous": len(old), "psi": psi(old, new), "mean_shift_pp": float(new.mean() - old.mean()) * 100.0}
    return out
