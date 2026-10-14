"""Pure I/O and tidy transforms for housing market data.

No Streamlit import here — this module must be importable and testable without
a Streamlit runtime and without network access (see tests/conftest.py, which
blocks sockets and points MARKETMACHINE_DATA_DIR at local fixtures).
"""
from __future__ import annotations

import io
import os
from typing import Literal
from urllib.request import urlopen

import pandas as pd

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
    "MORTGAGE30US": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US",
    "MORTGAGE15US": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE15US",
    "SOFR30DAYAVG": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=SOFR30DAYAVG",
    "CSUSHPINSA": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CSUSHPINSA",
}

# Offline fixture filenames, keyed the same way as URLS.
_OFFLINE_FILENAMES: dict[str, str] = {
    "zhvi_metro": "zhvi_metro.csv",
    "zhvi_state": "zhvi_state.csv",
    "inventory_metro": "inventory_metro.csv",
    "price_cut_metro": "price_cut_metro.csv",
    "MORTGAGE30US": "MORTGAGE30US.csv",
    "MORTGAGE15US": "MORTGAGE15US.csv",
    "SOFR30DAYAVG": "SOFR30DAYAVG.csv",
    "CSUSHPINSA": "CSUSHPINSA.csv",
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


def load_zhvi(kind: Literal["metro", "state"]) -> pd.DataFrame:
    key = "zhvi_metro" if kind == "metro" else "zhvi_state"
    raw_bytes = _read_bytes(source(key))
    return parse_zhvi(io.BytesIO(raw_bytes))


def load_fred(series_id: str) -> pd.Series:
    raw_bytes = _read_bytes(source(series_id))
    return parse_fred(io.BytesIO(raw_bytes), series_id)


def load_supply() -> pd.DataFrame:
    """Metro for-sale inventory and price-cut share. Columns: region, date, inventory, price_cut."""
    parts = []
    for key, name in (("inventory_metro", "inventory"), ("price_cut_metro", "price_cut")):
        df = parse_zhvi(io.BytesIO(_read_bytes(source(key))))
        parts.append(df[["region", "date", "value"]].rename(columns={"value": name}))
    return parts[0].merge(parts[1], on=["region", "date"], how="outer")


def to_wide(long_df: pd.DataFrame) -> pd.DataFrame:
    """Pivot a tidy long dataframe to wide: index date, columns region."""
    return long_df.pivot_table(index="date", columns="region", values="value")
