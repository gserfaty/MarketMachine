"""Pure I/O and tidy transforms for housing market data.

No Streamlit import here — this module must be importable and testable without
a Streamlit runtime and without network access (see tests/conftest.py, which
blocks sockets and points MARKETMACHINE_DATA_DIR at local fixtures).
"""
from __future__ import annotations

import io
import logging
import os
from typing import Literal
from urllib.request import urlopen

import pandas as pd

from housing import schemas

URLS: dict[str, str] = {
    "zhvi_metro": (
        "https://files.zillowstatic.com/research/public_csvs/zhvi/"
        "Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
    ),
    "zhvi_state": (
        "https://files.zillowstatic.com/research/public_csvs/zhvi/"
        "State_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
    ),
    "inventory_metro": (
        "https://files.zillowstatic.com/research/public_csvs/invt_fs/Metro_invt_fs_uc_sfrcondo_sm_month.csv"
    ),
    "price_cut_metro": (
        "https://files.zillowstatic.com/research/public_csvs/perc_listings_price_cut/Metro_perc_listings_price_cut_uc_sfrcondo_sm_month.csv"
    ),
    "afford_payment": (
        "https://files.zillowstatic.com/research/public_csvs/total_monthly_payment/"
        "Metro_total_monthly_payment_downpayment_0.20_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
    ),
    "afford_income": (
        "https://files.zillowstatic.com/research/public_csvs/new_homeowner_income_needed/"
        "Metro_new_homeowner_income_needed_downpayment_0.20_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
    ),
    "afford_share": (
        "https://files.zillowstatic.com/research/public_csvs/new_homeowner_affordability/"
        "Metro_new_homeowner_affordability_downpayment_0.20_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
    ),
    "zillow_forecast": (
        "https://files.zillowstatic.com/research/public_csvs/zhvf_growth/"
        "Metro_zhvf_growth_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
    ),
    "MORTGAGE30US": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US",
    "MORTGAGE15US": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE15US",
    "SOFR30DAYAVG": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=SOFR30DAYAVG",
    "CSUSHPINSA": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CSUSHPINSA",
    "MSACSR": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MSACSR",
}

# Offline fixture filenames, keyed the same way as URLS.
_OFFLINE_FILENAMES: dict[str, str] = {
    "zhvi_metro": "zhvi_metro.csv",
    "zhvi_state": "zhvi_state.csv",
    "inventory_metro": "inventory_metro.csv",
    "price_cut_metro": "price_cut_metro.csv",
    "afford_payment": "afford_payment.csv",
    "afford_income": "afford_income.csv",
    "afford_share": "afford_share.csv",
    "zillow_forecast": "zillow_forecast.csv",
    "MORTGAGE30US": "MORTGAGE30US.csv",
    "MORTGAGE15US": "MORTGAGE15US.csv",
    "SOFR30DAYAVG": "SOFR30DAYAVG.csv",
    "CSUSHPINSA": "CSUSHPINSA.csv",
    "MSACSR": "MSACSR.csv",
}

STATE_ABBR: dict[str, str] = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI",
    "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX",
    "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}


def source(name: str) -> str:
    """Return the URL for `name`, or a local fixture path if MARKETMACHINE_DATA_DIR is set."""
    data_dir = os.environ.get("MARKETMACHINE_DATA_DIR")
    if data_dir:
        return os.path.join(data_dir, _OFFLINE_FILENAMES[name])
    return URLS[name]


def _read_bytes(path_or_url: str) -> bytes:
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        with urlopen(path_or_url, timeout=30) as resp:  # noqa: S310
            return resp.read()
    with open(path_or_url, "rb") as f:
        return f.read()


def parse_zhvi(buf) -> pd.DataFrame:
    """Parse a Zillow ZHVI CSV (metro or state layout) into a tidy long dataframe.

    Columns: region_id, region, region_type, state, size_rank, date (datetime64,
    month-end), value. Rows with NaN value are dropped.
    """
    raw = pd.read_csv(buf)
    id_cols = ["RegionID", "SizeRank", "RegionName", "RegionType", "StateName"]
    present_id_cols = [c for c in id_cols if c in raw.columns]
    date_cols = [c for c in raw.columns if c not in id_cols]

    long_df = raw.melt(
        id_vars=present_id_cols, value_vars=date_cols, var_name="date", value_name="value"
    )
    long_df["date"] = pd.to_datetime(long_df["date"]) + pd.offsets.MonthEnd(0)
    long_df = long_df.rename(
        columns={
            "RegionID": "region_id",
            "SizeRank": "size_rank",
            "RegionName": "region",
            "RegionType": "region_type",
            "StateName": "state",
        }
    )
    if "state" not in long_df.columns:
        long_df["state"] = pd.NA
    if "region_type" not in long_df.columns:
        long_df["region_type"] = pd.NA

    long_df = long_df.dropna(subset=["value"])
    long_df = long_df[
        ["region_id", "region", "region_type", "state", "size_rank", "date", "value"]
    ]
    return long_df.sort_values(["region", "date"]).reset_index(drop=True)


def parse_fred(buf, series_id: str) -> pd.Series:
    """Parse a FRED fredgraph.csv into a month-end-indexed monthly-mean series.

    Values of "." are coerced to NaN. Input may be weekly (mortgage) or monthly
    (Case-Shiller); either way we resample to month-end mean.
    """
    raw = pd.read_csv(buf)
    raw["observation_date"] = pd.to_datetime(raw["observation_date"])
    raw[series_id] = pd.to_numeric(raw[series_id], errors="coerce")
    raw = raw.set_index("observation_date")
    monthly = raw[series_id].resample("ME").mean()
    monthly.name = series_id
    monthly.index.name = "date"
    return monthly


def parse_zillow_forecast(buf) -> pd.DataFrame:
    """Parse Zillow's ZHVF growth CSV. Columns: region, region_type, base_date, zf_1m, zf_3m, zf_12m (fractions).

    Horizons are found by month offset from BaseDate, since the date headers change every release.
    """
    raw = pd.read_csv(buf)
    base = pd.to_datetime(raw["BaseDate"]).max() + pd.offsets.MonthEnd(0)
    cols = {}
    for c in raw.columns:
        d = pd.to_datetime(c, errors="coerce", format="%Y-%m-%d")
        if pd.notna(d) and (d.year - base.year) * 12 + d.month - base.month in (1, 3, 12):
            cols[c] = f"zf_{(d.year - base.year) * 12 + d.month - base.month}m"
    if "zf_3m" not in cols.values() and "zf_12m" not in cols.values():
        raise ValueError("Zillow forecast has no 3-month or 12-month column")
    out = raw.rename(columns={"RegionName": "region", "RegionType": "region_type", **cols})
    out[list(cols.values())] = out[list(cols.values())] / 100
    out["base_date"] = base
    out = out.dropna(subset=list(cols.values()), how="all")
    return out[["region", "region_type", "base_date", *sorted(cols.values())]].reset_index(drop=True)


def _parsed(key: str) -> pd.DataFrame | pd.Series:
    """Read, parse and validate one source. Raises DataValidationError on any bad data."""
    src = source(key)
    buf = io.BytesIO(_read_bytes(src))
    try:
        if "fredgraph" in URLS[key]:
            out = parse_fred(buf, key)
        elif key == "zillow_forecast":
            out = parse_zillow_forecast(buf)
        else:
            out = parse_zhvi(buf)
        return schemas.validate(key, out, live=src.startswith("http"))
    except schemas.DataValidationError as err:
        logging.getLogger(__name__).warning(str(err))
        raise
    except Exception as e:
        err = schemas.DataValidationError(key, [f"could not parse: {e}"])
        logging.getLogger(__name__).warning(str(err))
        raise err from e


def load_zhvi(kind: Literal["metro", "state"]) -> pd.DataFrame:
    return _parsed("zhvi_metro" if kind == "metro" else "zhvi_state")


def load_fred(series_id: str) -> pd.Series:
    return _parsed(series_id)


def load_zillow_forecast() -> pd.DataFrame:
    return _parsed("zillow_forecast")


def load_supply() -> pd.DataFrame:
    """Metro for-sale inventory and price-cut share. Columns: region, date, inventory, price_cut."""
    parts = []
    for key, name in (("inventory_metro", "inventory"), ("price_cut_metro", "price_cut")):
        df = _parsed(key)
        parts.append(df[["region", "date", "value"]].rename(columns={"value": name}))
    return parts[0].merge(parts[1], on=["region", "date"], how="outer")


def load_affordability() -> pd.DataFrame:
    """Zillow affordability (20% down), latest month per region. Columns: region, date, z_payment, z_income_needed, z_share."""
    out = None
    for key, name in (("afford_payment", "z_payment"), ("afford_income", "z_income_needed"), ("afford_share", "z_share")):
        df = _parsed(key)[["region", "date", "value"]].rename(columns={"value": name})
        out = df if out is None else out.merge(df, on=["region", "date"], how="outer")
    return out.sort_values("date").groupby("region", as_index=False).last()[["region", "date", "z_payment", "z_income_needed", "z_share"]]


def to_wide(long_df: pd.DataFrame) -> pd.DataFrame:
    """Pivot a tidy long dataframe to wide: index date, columns region."""
    return long_df.pivot_table(index="date", columns="region", values="value")


def load_forecast_inputs() -> dict:
    """Inputs for train_and_evaluate. ZHVI is required (raises); the rest degrade to None."""
    def opt(fn, *a):
        try:
            return fn(*a)
        except Exception:
            return None
    return {"long_df": load_zhvi("metro"), "mortgage": opt(load_fred, "MORTGAGE30US"),
            "supply": opt(load_supply), "months_supply": opt(load_fred, "MSACSR")}
