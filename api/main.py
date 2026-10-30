"""Versioned REST API: thin routes over housing.*. Run: uvicorn api.main:app. No streamlit, no mlflow unless a registry exists."""
from __future__ import annotations

import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from enum import IntEnum
from pathlib import Path
from typing import Callable, Literal, TypeVar

import pandas as pd
from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api import models as m
from housing import analysis, data, finance, model
from housing.schemas import DataValidationError

T = TypeVar("T")
log = logging.getLogger("marketmachine.api")
ROOT = Path(__file__).resolve().parents[1]
TTL = 86400


class Horizon(IntEnum):  # Literal[3, 12, 24] does not coerce query strings
    m3 = 3
    m12 = 12
    m24 = 24

# ponytail: per-process cache, Redis in step G
_cache: dict[tuple, tuple[float, object]] = {}
_locks: dict[tuple, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock(key: tuple) -> threading.Lock:
    with _locks_guard:  # setdefault on a shared dict needs a guard to hand out one lock per key
        return _locks.setdefault(key, threading.Lock())


def cached(key: tuple, ttl: float, fn: Callable[[], T]) -> T:
    with _lock(key):
        hit = _cache.get(key)
        if hit and time.monotonic() - hit[0] < ttl:
            return hit[1]
        val = fn()
        _cache[key] = (time.monotonic(), val)
        return val


def _dd() -> str | None:
    return os.environ.get("MARKETMACHINE_DATA_DIR")


def inputs() -> dict:
    return cached(("inputs", _dd()), TTL, data.load_forecast_inputs)


def _build_metros() -> pd.DataFrame:
    long_df = inputs()["long_df"]
    t = analysis.appreciation_table(long_df[long_df["region_type"] != "country"])
    ids = long_df.drop_duplicates("region")[["region", "region_id"]]
    return t.merge(ids, on="region", how="left")


def metros() -> pd.DataFrame:
    return cached(("metros", _dd()), TTL, _build_metros)


def resolve(region: str) -> pd.Series:
    long_df = inputs()["long_df"]
    rows = long_df.drop_duplicates("region")
    if region.isdigit():
        hit = rows[rows["region_id"] == int(region)]
    else:
        hit = rows[rows["region"].str.lower() == region.lower()]
    if hit.empty:
        raise HTTPException(404, f"Unknown metro: {region}")
    return hit.iloc[0]


def _champion(h: int):
    if not os.environ.get("MLFLOW_TRACKING_URI") and not (ROOT / "mlruns.db").exists():
        return None
    try:
        from housing import track
        track.setup()
        mdl, ver = track.load_champion(h), track.champion_version(h)
        return (mdl, ver) if mdl is not None and ver else None
    except Exception:  # noqa: BLE001
        log.warning("registry model unavailable for %sm; training on demand", h, exc_info=True)
        return None


def forecast(h: int) -> tuple[model.ForecastResult, m.ModelInfo]:
    i = inputs()
    key = ("forecast", _dd(), model.as_of_key(i["long_df"], i["supply"], i["months_supply"]), h)

    def build():
        champ = _champion(h)
        res = model.train_and_evaluate(
            i["long_df"], i["mortgage"], supply=i["supply"], horizon=h, months_supply=i["months_supply"],
            final_model=champ[0] if champ else None)
        if champ and res.model is champ[0]:
            return res, m.ModelInfo(source="registry", name=f"marketmachine-{h}m", version=champ[1])
        return res, m.ModelInfo(source="trained on demand")

    return cached(key, TTL, build)


def _rates() -> dict:
    def build():
        r30 = data.load_fred("MORTGAGE30US")
        try:
            r15 = data.load_fred("MORTGAGE15US")
        except Exception:  # noqa: BLE001
            r15 = None
        if r30 is None or r30.dropna().empty:
            raise OSError("MORTGAGE30US unavailable")
        a = float(r30.dropna().iloc[-1])
        b = float(r15.dropna().iloc[-1]) if r15 is not None and not r15.dropna().empty else a
        return {"base": finance.base_rates(a, b), "rate_30y": a, "rate_15y": b,
                "rates_as_of": r30.dropna().index[-1].date()}

    return cached(("rates", _dd()), TTL, build)


def _f(x):
    return None if x is None or pd.isna(x) else float(x)


def _i(x):
    return None if x is None or pd.isna(x) else int(x)


def _page(df: pd.DataFrame, limit: int, offset: int) -> pd.DataFrame:
    return df.iloc[offset: offset + limit]


@asynccontextmanager
async def lifespan(_app):
    if os.environ.get("MARKETMACHINE_WARM") == "1":
        def warm():
            try:
                forecast(12)
            except Exception:  # noqa: BLE001
                log.exception("warm start failed")
        threading.Thread(target=warm, daemon=True).start()
    yield


app = FastAPI(title="MarketMachine API", version="1.0.0", lifespan=lifespan)
v1 = APIRouter(prefix="/v1")
ERR = {c: {"model": m.ErrorResponse} for c in (404, 422, 503)}


def _err(status: int, code: str, message: str, details: list | None = None) -> JSONResponse:
    body = {"error": {"status": status, "code": code, "message": message, "details": details or []}}
    return JSONResponse(body, status_code=status)


@app.exception_handler(StarletteHTTPException)
async def _http(_r: Request, e: StarletteHTTPException):
    code = "not_found" if e.status_code == 404 else "validation_error" if e.status_code == 422 else "http_error"
    return _err(e.status_code, code, str(e.detail))


@app.exception_handler(RequestValidationError)
async def _validation(_r: Request, e: RequestValidationError):
    return _err(422, "validation_error", "Invalid request.", jsonable_encoder(e.errors()))


@app.exception_handler(DataValidationError)
async def _invalid(_r: Request, e: DataValidationError):
    return _err(503, "data_invalid", str(e), e.problems)


@app.exception_handler(OSError)
async def _down(_r: Request, e: OSError):
    log.warning("data source unavailable", exc_info=e)
    return _err(503, "data_unavailable", "A data source is unavailable. Try again later.")


@v1.get("/health", response_model=m.Health)
def health():
    return {"status": "ok"}


@v1.get("/ready", response_model=m.Ready, responses=ERR)
def ready():
    t = metros()
    as_of = inputs()["long_df"]["date"].max().date()
    done = sorted({k[3] for k in list(_cache) if k[0] == "forecast" and k[1] == _dd()})
    return {"status": "ready", "zhvi_as_of": as_of, "metros": len(t), "forecasts_cached": done}


@v1.get("/metros", response_model=m.MetroList, responses=ERR)
def list_metros(state: str | None = Query(None, min_length=2, max_length=2), q: str | None = None,
                sort: Literal["value", "size_rank", "chg_1y", "chg_5y", "chg_10y"] = "size_rank",
                order: Literal["asc", "desc"] = "asc", limit: int = Query(50, ge=1, le=500),
                offset: int = Query(0, ge=0)):
    t = metros()
    if state:
        t = t[t["state"].str.upper() == state.upper()]
    if q:
        t = t[t["region"].str.contains(q, case=False, regex=False)]
    t = t.sort_values(sort, ascending=order == "asc", na_position="last")
    items = [m.Metro(region_id=int(r.region_id), region=r.region, state=r.state, size_rank=_i(r.size_rank),
                     value=float(r.value), chg_1y=_f(r.chg_1y), chg_5y=_f(r.chg_5y), chg_10y=_f(r.chg_10y))
             for r in _page(t, limit, offset).itertuples()]
    return {"as_of": inputs()["long_df"]["date"].max().date(), "total": len(t), "limit": limit, "offset": offset,
            "items": items}


@v1.get("/metros/{region}/forecast", response_model=m.Forecast, responses=ERR)
def metro_forecast(region: str, horizon: Horizon = Horizon.m12):
    row = resolve(region)
    horizon = int(horizon)
    res, info = forecast(horizon)
    hit = res.predictions[res.predictions["region"] == row["region"]]
    if hit.empty:
        raise HTTPException(404, "no forecast for this metro")
    p = hit.iloc[0]
    return {"region_id": int(row["region_id"]), "region": row["region"], "state": p["state"], "horizon": horizon,
            "value": float(p["value"]), "pred": _f(p["pred_12m"]), "lo80": _f(p["lo_12m"]),
            "hi80": _f(p["hi_12m"]), "as_of": res.as_of.date(), "model": info}


@v1.get("/forecast/summary", response_model=m.ForecastSummary, responses=ERR)
def forecast_summary(horizon: Horizon = Horizon.m12):
    horizon = int(horizon)
    res, info = forecast(horizon)
    scores = [m.PredictorScore(predictor=k, years=int(r["years"]), **{c: _f(r[c]) for c in model.METRICS})
              for k, r in res.metrics.iterrows()]
    lo, hi = res.national_interval
    return {"horizon": horizon, "as_of": res.as_of.date(), "national_pred": _f(res.national_pred),
            "national_lo80": _f(lo), "national_hi80": _f(hi), "interval_k": _f(res.interval_k),
            "scores": scores, "model": info}


@v1.get("/affordability", response_model=m.AffordList, responses=ERR)
def affordability(income: float = Query(gt=0), down_pct: float = Query(20, ge=0, lt=100),
                  debts: float = Query(0, ge=0), affordable_only: bool = False,
                  limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    r = _rates()
    t = metros()
    try:
        out = finance.affordability_table(t[["region", "state", "value"]], income, down_pct, r["base"], debts)
    except ValueError as e:
        raise HTTPException(422, str(e))
    out = out.merge(t[["region", "region_id"]], on="region")
    if affordable_only:
        out = out[out["affordable"]]
    out = out.sort_values("share")
    items = [m.AffordRow(region_id=int(x.region_id), region=x.region, state=x.state, value=float(x.value),
                         payment=float(x.payment), share=float(x.share), affordable=bool(x.affordable))
             for x in _page(out, limit, offset).itertuples()]
    return {"income": income, "down_pct": down_pct, "debts": debts, "rate_30y": r["rate_30y"],
            "rates_as_of": r["rates_as_of"], "total": len(out), "limit": limit, "offset": offset, "items": items}


@v1.post("/financing/estimate", response_model=m.FinancingEstimate, responses=ERR)
def financing_estimate(req: m.FinancingRequest):
    r = _rates()
    try:
        est = finance.estimate(req.price, req.down_pct, req.loan_type, req.credit_band, req.state,
                               req.term_years, r["base"], req.fees_pct)
    except ValueError as e:
        raise HTTPException(422, str(e))
    est.pop("schedule")
    return {**est, "apr": _f(est["apr"]), "rates_as_of": r["rates_as_of"]}


app.include_router(v1)
