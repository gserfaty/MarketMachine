import io
import os

import pandas as pd
import pytest

from housing import data
from housing.schemas import DataValidationError, validate

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
TODAY = pd.Timestamp("2026-10-26")


def _fixture(key):
    with open(os.path.join(FIX, data._OFFLINE_FILENAMES[key]), "rb") as f:
        buf = io.BytesIO(f.read())
    if "fredgraph" in data.URLS[key]:
        return data.parse_fred(buf, key)
    if key == "zillow_forecast":
        return data.parse_zillow_forecast(buf)
    return data.parse_zhvi(buf)


def _tidy(n_regions, last="2026-09-30"):
    dates = pd.date_range(end=last, periods=3, freq="ME")
    return pd.DataFrame(
        [(f"r{i}", i, d, 100.0) for i in range(n_regions) for d in dates],
        columns=["region", "region_id", "date", "value"],
    )


@pytest.mark.parametrize("key", list(data.URLS))
def test_fixture_passes(key):
    validate(key, _fixture(key), live=False)


def test_missing_columns():
    with pytest.raises(DataValidationError, match="value"):
        validate("zhvi_metro", _fixture("zhvi_metro").drop(columns="value"), live=False)
    with pytest.raises(DataValidationError, match="region_id"):
        validate("inventory_metro", _fixture("inventory_metro").drop(columns="region_id"), live=False)


@pytest.mark.parametrize(
    "key,col,val",
    [("zhvi_metro", "value", -1), ("price_cut_metro", "value", 1.5), ("afford_share", "value", 0),
     ("zillow_forecast", "zf_12m", 0.9)],
)
def test_out_of_range_frames(key, col, val):
    df = _fixture(key).copy()
    df.loc[df.index[0], col] = val
    with pytest.raises(DataValidationError):
        validate(key, df, live=False)


@pytest.mark.parametrize("key,val", [("MORTGAGE30US", 30.0), ("MSACSR", -1.0)])
def test_out_of_range_fred(key, val):
    s = _fixture(key).copy()
    s.iloc[-1] = val
    with pytest.raises(DataValidationError):
        validate(key, s, live=False)


def test_bad_dates():
    df = _fixture("zhvi_metro").copy()
    df.loc[df.index[0], "date"] = df.loc[df.index[0], "date"] - pd.Timedelta(days=1)
    with pytest.raises(DataValidationError, match="month_end"):
        validate("zhvi_metro", df, live=False)
    dup = pd.concat([_fixture("zhvi_metro"), _fixture("zhvi_metro").iloc[:1]], ignore_index=True)
    with pytest.raises(DataValidationError):
        validate("zhvi_metro", dup, live=False)
    s = _fixture("MORTGAGE30US")
    with pytest.raises(DataValidationError, match="monotonic"):
        validate("MORTGAGE30US", s.iloc[::-1], live=False)


def test_parse_boundary(tmp_path, monkeypatch):
    (tmp_path / "zhvi_metro.csv").write_text("RegionID,RegionName,not-a-date\n1,A,5.0\n")
    monkeypatch.setenv("MARKETMACHINE_DATA_DIR", str(tmp_path))
    with pytest.raises(DataValidationError, match="could not parse"):
        data.load_zhvi("metro")


def test_lazy_collects_multiple():
    df = _fixture("zhvi_metro").drop(columns="region_id")
    df.loc[df.index[0], "value"] = -1
    with pytest.raises(DataValidationError) as e:
        validate("zhvi_metro", df, live=False)
    assert len(e.value.problems) >= 2


def test_live_checks():
    validate("zhvi_metro", _tidy(850), live=True, today=TODAY)
    with pytest.raises(DataValidationError, match="regions"):
        validate("zhvi_metro", _tidy(10), live=True, today=TODAY)
    with pytest.raises(DataValidationError, match="stale"):
        validate("zhvi_metro", _tidy(850, last="2026-05-31"), live=True, today=TODAY)
    with pytest.raises(DataValidationError, match="stale"):
        validate("MORTGAGE30US", _fixture("MORTGAGE30US"), live=True, today=pd.Timestamp("2027-01-15"))
