"""Pandera data contracts, one per external source. No Streamlit import."""
from __future__ import annotations

import pandas as pd
import pandera.pandas as pa


class DataValidationError(ValueError):
    def __init__(self, key: str, problems: list[str]):
        self.key, self.problems = key, problems
        super().__init__(f"{key} failed validation: " + "; ".join(problems[:10]))


MONTH_END = pa.Check(lambda s: s.dt.is_month_end, name="month_end")


def _zillow(value_check) -> pa.DataFrameSchema:
    return pa.DataFrameSchema(
        {
            "region": pa.Column(nullable=False),
            "region_id": pa.Column("int64"),
            "date": pa.Column(pa.DateTime, MONTH_END),
            "value": pa.Column(float, value_check, nullable=False),
        },
        unique=["region", "date"],
    )


def _fred(lo: float, hi: float) -> pa.SeriesSchema:
    return pa.SeriesSchema(
        float,
        [
            pa.Check.in_range(lo, hi),
            pa.Check(lambda s: bool(s.index.is_month_end.all()), name="month_end"),
            pa.Check(lambda s: bool(s.index.is_monotonic_increasing), name="monotonic_increasing"),
            pa.Check(lambda s: bool(s.index.is_unique), name="unique_index"),
        ],
        nullable=True,
    )


def _zf_col() -> pa.Column:
    return pa.Column(float, pa.Check.in_range(-0.5, 0.5), nullable=True, required=False)


ZF = pa.DataFrameSchema(
    {
        "region": pa.Column(nullable=False, unique=True),
        "region_type": pa.Column(),
        "base_date": pa.Column(pa.DateTime, MONTH_END),
        "zf_1m": _zf_col(),
        "zf_3m": _zf_col(),
        "zf_12m": _zf_col(),
    }
)

_POS = pa.Check.gt(0)
# key -> (schema, min regions/rows/non-null months when live, max age in months when live)
CONTRACTS: dict[str, tuple[object, int, int]] = {
    "zhvi_metro": (_zillow(_POS), 800, 3),
    "zhvi_state": (_zillow(_POS), 50, 3),
    "inventory_metro": (_zillow(pa.Check.ge(0)), 800, 3),
    "price_cut_metro": (_zillow(pa.Check.in_range(0, 1)), 800, 3),
    "afford_payment": (_zillow(_POS), 300, 3),
    "afford_income": (_zillow(_POS), 300, 3),
    "afford_share": (_zillow(pa.Check.in_range(0, 25, include_min=False)), 300, 3),
    "zillow_forecast": (ZF, 800, 3),
    "MORTGAGE30US": (_fred(0, 25), 240, 2),
    "MORTGAGE15US": (_fred(0, 25), 240, 2),
    "SOFR30DAYAVG": (_fred(0, 25), 60, 2),
    "CSUSHPINSA": (_fred(1, 2000), 240, 5),
    "MSACSR": (_fred(0, 25), 240, 4),
}


def validate(key: str, obj, *, live: bool, today: pd.Timestamp | None = None):
    """Return `obj` unchanged, or raise DataValidationError listing every problem."""
    schema, min_count, max_age = CONTRACTS[key]
    problems: list[str] = []
    try:
        schema.validate(obj, lazy=True)
    except pa.errors.SchemaErrors as e:
        fc = e.failure_cases
        problems += [f"{r.column}/{r.check}: {r.failure_case}" for r in fc.itertuples()]
    if len(obj) == 0:
        problems.append("empty")
    elif live:
        is_series = isinstance(obj, pd.Series)
        if is_series:
            count, latest = int(obj.notna().sum()), obj.last_valid_index()
        elif key == "zillow_forecast":
            count, latest = len(obj), obj["base_date"].max() if "base_date" in obj else None
        else:
            count = obj["region"].nunique() if "region" in obj else 0
            latest = obj["date"].max() if "date" in obj else None
        if count < min_count:
            problems.append(f"only {count} regions/rows, need {min_count} (regions)")
        if latest is not None and pd.notna(latest):
            t = today or pd.Timestamp.today()
            if (t.year - latest.year) * 12 + t.month - latest.month > max_age:
                problems.append(f"stale: latest {latest:%Y-%m-%d}, max age {max_age} months")
    if problems:
        raise DataValidationError(key, problems)
    return obj
