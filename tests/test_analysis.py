import pytest
import numpy as np
import pandas as pd

from housing import analysis


def _build_long_df(n_months: int, start: float, end_value_growth: float) -> pd.DataFrame:
    dates = pd.date_range("2020-01-31", periods=n_months, freq="ME")
    # Linear path from `start` to start*(1+end_value_growth) over the window.
    values = np.linspace(start, start * (1 + end_value_growth), n_months)
    return pd.DataFrame(
        {
            "region_id": 1,
            "region": "Testville",
            "region_type": "msa",
            "state": "MI",
            "size_rank": 5,
            "date": dates,
            "value": values,
        }
    )


def test_yoy_correct():
    s = pd.Series([100.0] * 12 + [110.0], index=pd.date_range("2020-01-31", periods=13, freq="ME"))
    result = analysis.yoy(s)
    assert np.isclose(result.iloc[-1], 0.10, atol=1e-9)
    assert result.iloc[:12].isna().all()


def test_appreciation_table_1y_change_and_short_history_nan():
    long_df = _build_long_df(n_months=13, start=100.0, end_value_growth=0.10)
    table = analysis.appreciation_table(long_df)
    row = table.iloc[0]
    assert row["region"] == "Testville"
    assert np.isclose(row["chg_1y"], 0.10, atol=1e-9)
    assert pd.isna(row["chg_10y"])
    assert pd.isna(row["chg_5y"])


def test_appreciation_table_columns():
    long_df = _build_long_df(n_months=13, start=100.0, end_value_growth=0.10)
    table = analysis.appreciation_table(long_df)
    required = {"region", "state", "size_rank", "value", "chg_1y", "chg_5y", "chg_10y"}
    assert required.issubset(table.columns)


def test_national_series():
    us = _build_long_df(n_months=13, start=200.0, end_value_growth=0.05)
    us["region"] = "United States"
    us["region_type"] = "country"
    other = _build_long_df(n_months=13, start=100.0, end_value_growth=0.10)
    long_df = pd.concat([us, other], ignore_index=True)
    series = analysis.national_series(long_df)
    assert len(series) == 13
    assert np.isclose(series.iloc[0], 200.0)


def test_compare_to_zillow():
    preds = pd.DataFrame({"region": ["United States", "A", "B", "C"], "pred_12m": [0.02, 0.05, -0.01, 0.03]})
    zf = pd.DataFrame({"region": ["United States", "A", "B", "C", "Atlantis"],
                       "zf_12m": [0.01, 0.03, 0.02, np.nan, 0.1]})
    r = analysis.compare_to_zillow(preds, zf, 12)
    assert r["n"] == 2 and r["same_dir"] == 1
    assert r["median_diff_pp"] == pytest.approx(-0.5)
    assert analysis.compare_to_zillow(preds, zf, 24) is None
