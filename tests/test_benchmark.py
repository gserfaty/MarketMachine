import pandas as pd
import pytest

from housing import benchmark


def test_snapshot_parse_and_head_to_head(tmp_path):
    p = tmp_path / "2024-01-31.csv"
    p.write_text(
        "RegionID,SizeRank,RegionName,RegionType,StateName,BaseDate,2024-02-29,2024-04-30,2025-01-31\n"
        "1,1,A,msa,MI,2024-01-31,0.1,1.0,4.0\n"
        "2,2,B,msa,OH,2024-01-31,0.2,2.0,-2.0\n"
    )
    zf = benchmark.load_snapshots([p])
    assert sorted(zf["h"].unique()) == [1, 3, 12]
    assert zf.loc[(zf["region"] == "A") & (zf["h"] == 12), "zillow"].item() == pytest.approx(0.04)

    date = pd.Timestamp("2024-01-31")
    bt = pd.DataFrame({"region": ["A", "B", "C"], "date": date, "actual": [0.05, -0.01, 0.0],
                       "blend": [0.05, -0.02, 0.0], "model": 0.0, "naive_momentum": 0.0})
    scores = benchmark.head_to_head(bt, zf, 12).set_index("predictor")
    assert scores.loc["zillow", "n"] == 2  # C has no Zillow forecast
    assert scores.loc["zillow", "MAE"] == pytest.approx((1 + 1) / 2)
    assert scores.loc["blend", "MAE"] == pytest.approx((0 + 1) / 2)
    assert benchmark.summarize(scores.reset_index()).loc["blend", "beats_zillow"] == "1/1"
