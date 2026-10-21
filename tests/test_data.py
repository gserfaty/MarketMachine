import io
import os

import pandas as pd

from housing import data

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def test_parse_zhvi_metro_long_columns():
    with open(os.path.join(FIXTURES_DIR, "zhvi_metro.csv"), "rb") as f:
        df = data.parse_zhvi(f)
    required = {"region_id", "region", "region_type", "state", "size_rank", "date", "value"}
    assert required.issubset(df.columns)
    assert pd.api.types.is_datetime64_any_dtype(df["date"])
    assert (df["region_type"] == "country").any()
    assert (df.loc[df["region_type"] == "country", "region"] == "United States").all()


def test_parse_zhvi_no_nan_values():
    with open(os.path.join(FIXTURES_DIR, "zhvi_metro.csv"), "rb") as f:
        df = data.parse_zhvi(f)
    assert df["value"].notna().all()


def test_parse_fred_handles_dot_and_resamples_monthly():
    with open(os.path.join(FIXTURES_DIR, "MORTGAGE30US.csv"), "rb") as f:
        s = data.parse_fred(f, "MORTGAGE30US")
    assert pd.api.types.is_datetime64_any_dtype(s.index)
    assert s.index.is_monotonic_increasing
    # Weekly input resampled down to <= one row per month.
    n_months = (s.index.to_period("M").nunique())
    assert len(s) == n_months
    assert s.notna().sum() > 0


def test_source_uses_offline_dir(monkeypatch):
    monkeypatch.setenv("MARKETMACHINE_DATA_DIR", "/tmp/does-not-matter")
    path = data.source("zhvi_metro")
    assert path == "/tmp/does-not-matter/zhvi_metro.csv"


def test_load_zhvi_metro_offline():
    df = data.load_zhvi("metro")
    assert not df.empty
    assert "United States" in df["region"].unique()


def test_load_fred_offline():
    s = data.load_fred("CSUSHPINSA")
    assert not s.empty


def test_load_supply_offline():
    df = data.load_supply()
    assert set(df.columns) == {"region", "date", "inventory", "price_cut"}
    assert not df.empty and "United States" in set(df["region"])


def test_to_wide_pivots_by_region():
    df = data.load_zhvi("metro")
    wide = data.to_wide(df)
    assert "United States" in wide.columns
    assert wide.index.is_monotonic_increasing


def test_load_affordability_offline():
    df = data.load_affordability()
    assert list(df.columns) == ["region", "date", "z_payment", "z_income_needed", "z_share"]
    assert df["region"].is_unique and "Boise City, ID" not in set(df["region"])
    assert (df["date"] == pd.Timestamp("2026-08-31")).all()
    assert (df[["z_payment", "z_income_needed", "z_share"]] > 0).all().all()
