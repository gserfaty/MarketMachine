"""Pydantic v2 response/request models for the /v1 API. Fractions (0.034 = +3.4%); scorecard MAE/bias/width80 in pp."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from housing import finance

DISCLAIMER = "Statistical estimate, not financial advice."


class ErrorBody(BaseModel):
    status: int
    code: str
    message: str
    details: list = []


class ErrorResponse(BaseModel):
    error: ErrorBody


class Health(BaseModel):
    status: str


class Ready(BaseModel):
    status: str
    zhvi_as_of: date
    metros: int
    forecasts_cached: list[int]


class Metro(BaseModel):
    region_id: int
    region: str
    state: str | None = None
    size_rank: int | None = None
    value: float
    chg_1y: float | None = None
    chg_5y: float | None = None
    chg_10y: float | None = None


class MetroList(BaseModel):
    as_of: date
    total: int
    limit: int
    offset: int
    items: list[Metro]


class ModelInfo(BaseModel):
    source: Literal["registry", "trained on demand"]
    name: str | None = None
    version: str | None = None


class Forecast(BaseModel):
    region_id: int
    region: str
    state: str | None = None
    horizon: int
    value: float
    pred: float | None = None
    lo80: float | None = None
    hi80: float | None = None
    as_of: date
    model: ModelInfo
    disclaimer: str = DISCLAIMER


class PredictorScore(BaseModel):
    predictor: str
    MAE: float | None = None
    bias: float | None = None
    direction_acc: float | None = None
    rank_ic: float | None = None
    top_decile_lift: float | None = None
    coverage80: float | None = None
    width80: float | None = None
    years: int


class ForecastSummary(BaseModel):
    horizon: int
    as_of: date
    served: Literal["blend"] = "blend"
    national_pred: float | None = None
    national_lo80: float | None = None
    national_hi80: float | None = None
    interval_k: float | None = None
    scores: list[PredictorScore]
    model: ModelInfo
    disclaimer: str = DISCLAIMER


class AffordRow(BaseModel):
    region_id: int
    region: str
    state: str | None = None
    value: float
    payment: float
    share: float
    affordable: bool


class AffordList(BaseModel):
    income: float
    down_pct: float
    debts: float
    rate_30y: float
    rates_as_of: date
    total: int
    limit: int
    offset: int
    items: list[AffordRow]


class FinancingRequest(BaseModel):
    price: float = Field(gt=0, le=1e8)
    down_pct: float = Field(ge=0, lt=100)
    credit_band: Literal[tuple(finance.CREDIT_BANDS)] = "740-759"
    loan_type: Literal["conventional", "fha", "va"] = "conventional"
    state: Literal[tuple(finance.PROPERTY_TAX_PCT)]
    term_years: Literal[30, 20, 15, 10] = 30
    fees_pct: float = Field(1.0, ge=0, le=10)


class FinancingEstimate(BaseModel):
    term: int
    rate: float
    loan: float
    pi: float
    tax: float
    ins: float
    mi: float
    piti: float
    apr: float | None = None
    total_interest: float
    ltv: float
    jumbo: bool
    upfront: float
    rates_as_of: date
    disclaimer: str = DISCLAIMER
