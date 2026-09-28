"""Descriptive statistics over tidy housing value series. No Streamlit import."""
from __future__ import annotations

import numpy as np
import pandas as pd


def yoy(series: pd.Series) -> pd.Series:
    """Percent change vs. 12 months earlier (fraction, e.g. 0.05 = +5%)."""
    return series / series.shift(12) - 1.0


def _pct_change_n_months_back(s: pd.Series, months: int) -> float:
    if len(s) <= months:
        return np.nan
    latest = s.iloc[-1]
    prior = s.iloc[-1 - months]
    if pd.isna(latest) or pd.isna(prior) or prior == 0:
        return np.nan
    return latest / prior - 1.0


def appreciation_table(long_df: pd.DataFrame) -> pd.DataFrame:
    """One row per region at the latest date with 1/5/10-year change.

    Columns: region, state, size_rank, value, chg_1y, chg_5y, chg_10y (fractions;
    NaN when history is too short).
    """
    rows = []
    for region, g in long_df.groupby("region", sort=False):
        g = g.sort_values("date")
        latest = g.iloc[-1]
        rows.append(
            {
                "region": region,
                "state": latest.get("state"),
                "size_rank": latest.get("size_rank"),
                "value": latest["value"],
                "chg_1y": _pct_change_n_months_back(g["value"], 12),
                "chg_5y": _pct_change_n_months_back(g["value"], 60),
                "chg_10y": _pct_change_n_months_back(g["value"], 120),
            }
        )
    out = pd.DataFrame(rows)
    return out.sort_values("value", ascending=False).reset_index(drop=True)


def national_series(long_df: pd.DataFrame) -> pd.Series:
    """The United States / country row as a date-indexed value series."""
    country = long_df[long_df["region_type"] == "country"]
    if country.empty:
        country = long_df[long_df["region"] == "United States"]
    country = country.sort_values("date")
    return country.set_index("date")["value"]
