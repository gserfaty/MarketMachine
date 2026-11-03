"""Head-to-head vs Zillow's published metro forecasts (zhvf_growth snapshots). No Streamlit import.

CLI: python -m housing.benchmark SNAPSHOT_DIR  (one <BaseDate>.csv per snapshot, as on the `snapshots` branch).
Our side is the rolling backtest, so each origin only sees models trained on earlier outcomes.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from housing import data, model

PREDICTORS = ["zillow", "blend", "model", "naive_momentum"]


def load_snapshots(paths) -> pd.DataFrame:
    """Long frame: region, date (BaseDate), h (months ahead), zillow (fraction, 0.05 = +5%)."""
    out = []
    for p in paths:
        df = pd.read_csv(p)
        base = pd.Timestamp(df["BaseDate"].iloc[0])
        for c in df.columns[df.columns.get_loc("BaseDate") + 1:]:
            t = pd.Timestamp(c)
            out.append(pd.DataFrame({"region": df["RegionName"], "date": base,
                                     "h": (t.year - base.year) * 12 + t.month - base.month, "zillow": df[c] / 100}))
    return pd.concat(out, ignore_index=True).dropna(subset=["zillow"])


def head_to_head(bt: pd.DataFrame, zf: pd.DataFrame, h: int) -> pd.DataFrame:
    """Per-snapshot scores (model.score_backtest rows, `year` = BaseDate) on metros both sides forecast."""
    j = bt.merge(zf.loc[zf["h"] == h, ["region", "date", "zillow"]], on=["region", "date"])
    j["year"] = j["date"]
    return model.score_backtest(j, PREDICTORS)


def summarize(scores: pd.DataFrame) -> pd.DataFrame:
    """Equal-weight mean over snapshots, plus how many snapshots each predictor beat Zillow's MAE."""
    out = scores.groupby("predictor")[["MAE", "bias", "direction_acc", "rank_ic"]].mean().reindex(PREDICTORS)
    mae = scores.pivot(index="year", columns="predictor", values="MAE")
    out["beats_zillow"] = [f"{int((mae[p] < mae['zillow']).sum())}/{len(mae)}" for p in PREDICTORS]
    out["metros"] = int(scores["n"].median())
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("snapshot_dir", type=Path)
    ap.add_argument("--horizons", type=int, nargs="+", default=[3, 12])
    args = ap.parse_args(argv)
    zf = load_snapshots(sorted(args.snapshot_dir.glob("*.csv")))
    inp = data.load_forecast_inputs()
    feat = model.build_features(inp["long_df"], inp["mortgage"], inp["supply"], inp["months_supply"])
    for h in args.horizons:
        combined = feat.join(model.build_target(inp["long_df"], h).rename("y"), how="inner").reset_index()
        cols = model._active_feature_cols(combined)
        bt = model.rolling_backtest(combined, cols, h, first_year=zf["date"].min().year)
        scores = head_to_head(bt, zf, h)
        print(f"\n{h}m: {scores['year'].nunique()} snapshots with outcomes "
              f"({scores['year'].min():%Y-%m} to {scores['year'].max():%Y-%m})")
        print(summarize(scores).round(3).to_string())


if __name__ == "__main__":
    main()
