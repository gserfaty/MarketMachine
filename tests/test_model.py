import numpy as np
import pandas as pd

from housing import data, model


def _load():
    long_df = data.load_zhvi("metro")
    mortgage = data.load_fred("MORTGAGE30US")
    return long_df, mortgage


def test_build_features_no_lookahead():
    long_df, mortgage = _load()
    feat_full = model.build_features(long_df, mortgage)

    cutoff = pd.Timestamp("2018-06-30")
    long_df_altered = long_df.copy()
    mask = long_df_altered["date"] > cutoff
    rng = np.random.default_rng(1)
    long_df_altered.loc[mask, "value"] = long_df_altered.loc[mask, "value"] * (
        1 + rng.normal(0, 0.5, mask.sum())
    ).clip(min=0.01)

    mortgage_altered = mortgage.copy()
    mortgage_altered.loc[mortgage_altered.index > cutoff] = 999.0

    feat_altered = model.build_features(long_df_altered, mortgage_altered)

    at_cutoff_full = feat_full.xs(cutoff, level="date", drop_level=False)
    at_cutoff_altered = feat_altered.xs(cutoff, level="date", drop_level=False)
    common_idx = at_cutoff_full.index.intersection(at_cutoff_altered.index)
    assert len(common_idx) > 0
    pd.testing.assert_frame_equal(
        at_cutoff_full.loc[common_idx], at_cutoff_altered.loc[common_idx], check_exact=False
    )


def test_build_target_basic():
    long_df, _ = _load()
    y = model.build_target(long_df, horizon=12)
    assert not y.empty
    assert "United States" in y.index.get_level_values("region")


def test_time_split_no_leakage():
    long_df, mortgage = _load()
    feat = model.build_features(long_df, mortgage)
    target = model.build_target(long_df, horizon=12)
    combined = feat.join(target.rename("y"), how="inner").reset_index()

    train, test = model.time_split(combined, test_months=24, horizon=12)
    assert not train.empty
    assert not test.empty
    max_train_origin = train["date"].max()
    min_test_origin = test["date"].min()
    assert max_train_origin + pd.DateOffset(months=12) < min_test_origin


def test_train_and_evaluate_with_mortgage():
    long_df, mortgage = _load()
    result = model.train_and_evaluate(long_df, mortgage)

    assert set(result.metrics.index) == {"model", "naive_momentum", "zero"}
    assert (result.metrics["MAE"] >= 0).all()
    assert (result.metrics["direction_acc"] >= 0).all()
    assert (result.metrics["direction_acc"] <= 1).all()
    assert (result.metrics["n_test"] > 0).all()

    n_metros = long_df.loc[long_df["date"] == long_df["date"].max(), "region"].nunique()
    assert len(result.predictions) == n_metros
    assert np.isfinite(result.national_pred)
    assert result.as_of == long_df["date"].max()


def test_train_and_evaluate_without_mortgage():
    long_df, _ = _load()
    result = model.train_and_evaluate(long_df, mortgage=None)
    assert not result.predictions.empty
    assert np.isfinite(result.national_pred)
