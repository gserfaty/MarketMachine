import pytest
import numpy as np
import pandas as pd

from housing import data, model


def _load():
    long_df = data.load_zhvi("metro")
    mortgage = data.load_fred("MORTGAGE30US")
    return long_df, mortgage


def test_build_features_no_lookahead():
    long_df, mortgage = _load()
    supply = data.load_supply()
    feat_full = model.build_features(long_df, mortgage, supply)

    cutoff = pd.Timestamp("2020-06-30")
    long_df_altered = long_df.copy()
    mask = long_df_altered["date"] > cutoff
    rng = np.random.default_rng(1)
    long_df_altered.loc[mask, "value"] = long_df_altered.loc[mask, "value"] * (
        1 + rng.normal(0, 0.5, mask.sum())
    ).clip(min=0.01)

    mortgage_altered = mortgage.copy()
    mortgage_altered.loc[mortgage_altered.index > cutoff] = 999.0

    supply_altered = supply.copy()
    sm = supply_altered["date"] > cutoff
    supply_altered.loc[sm, ["inventory", "price_cut"]] *= 3

    feat_altered = model.build_features(long_df_altered, mortgage_altered, supply_altered)

    at_cutoff_full = feat_full.xs(cutoff, level="date", drop_level=False)
    at_cutoff_altered = feat_altered.xs(cutoff, level="date", drop_level=False)
    common_idx = at_cutoff_full.index.intersection(at_cutoff_altered.index)
    assert len(common_idx) > 0
    pd.testing.assert_frame_equal(
        at_cutoff_full.loc[common_idx], at_cutoff_altered.loc[common_idx], check_exact=False
    )


def test_supply_features():
    long_df, mortgage = _load()
    feat = model.build_features(long_df, mortgage, data.load_supply())
    d = feat.index.get_level_values("date")
    r = feat.index.get_level_values("region")
    assert feat.loc[d < "2019-03-01", "inv_yoy"].isna().all()
    assert feat.loc[(d >= "2019-03-01") & (r != "Boise City, ID"), "inv_yoy"].notna().all()
    assert feat.loc[r == "Boise City, ID", "inv_yoy"].isna().all()
    assert feat["pc"].dropna().between(0, 1).all()
    none = model.build_features(long_df, mortgage)
    assert none[model.SUPPLY_COLS].isna().all().all()


def test_build_target_basic():
    long_df, _ = _load()
    y = model.build_target(long_df, horizon=12)
    assert not y.empty
    assert "United States" in y.index.get_level_values("region")


@pytest.mark.parametrize("horizon", [3, 12, 24])
def test_split_for_year_no_leakage(horizon):
    long_df, mortgage = _load()
    feat = model.build_features(long_df, mortgage)
    target = model.build_target(long_df, horizon=horizon)
    combined = feat.join(target.rename("y"), how="inner").reset_index()
    seen = 0
    for year in range(2010, 2026):
        train, test = model.split_for_year(combined, year, horizon)
        if test.empty:
            continue
        seen += 1
        assert (test["date"].dt.year == year).all()
        assert train["date"].max() + pd.DateOffset(months=horizon) <= test["date"].min()
    assert seen >= (8 if horizon == 24 else 10)


def test_score_backtest_known_values():
    rows = []
    for d in pd.to_datetime(["2020-01-31", "2020-02-29"]):
        for i in range(10):
            a = (i - 4.5) / 100
            rows.append({"region": f"r{i}", "date": d, "year": 2020, "actual": a,
                         "model": a, "reversed": -a, "zero": 0.0})
    s = model.score_backtest(pd.DataFrame(rows), ["model", "reversed", "zero"]).set_index("predictor")
    assert s.loc["model", "MAE"] == 0 and s.loc["model", "bias"] == 0
    assert np.isclose(s.loc["model", "rank_ic"], 1) and np.isclose(s.loc["reversed", "rank_ic"], -1)
    assert np.isnan(s.loc["zero", "rank_ic"]) and np.isnan(s.loc["zero", "top_decile_lift"])
    # top 1 of 10 is actual 0.045; mean is 0 -> lift 4.5 pp
    assert np.isclose(s.loc["model", "top_decile_lift"], 4.5)


@pytest.fixture(scope="module")
def mortgage_result():
    from conftest import FIXTURES_DIR
    with pytest.MonkeyPatch.context() as mp:  # autouse offline fixture is function-scoped
        mp.setenv("MARKETMACHINE_DATA_DIR", FIXTURES_DIR)
        long_df, mortgage = _load()
        return model.train_and_evaluate(long_df, mortgage, supply=data.load_supply())


def test_train_and_evaluate_with_mortgage(mortgage_result):
    long_df, _ = _load()
    result = mortgage_result

    assert set(result.metrics.index) == {"model", "blend", "naive_momentum", "zero"}
    assert (result.metrics["MAE"] >= 0).all()
    assert (result.metrics["direction_acc"] >= 0).all()
    assert (result.metrics["direction_acc"] <= 1).all()
    assert {"rank_ic", "top_decile_lift"} <= set(result.metrics.columns)
    assert result.backtest["year"].nunique() >= 10

    n_metros = long_df.loc[long_df["date"] == long_df["date"].max(), "region"].nunique()
    assert len(result.predictions) == n_metros
    assert np.isfinite(result.national_pred)
    assert result.as_of == long_df["date"].max()

    p = result.predictions
    assert (p.lo_12m <= p.pred_12m).all() and (p.pred_12m <= p.hi_12m).all()
    m = result.metrics
    assert 0 <= m.loc["blend", "coverage80"] <= 1 and m.loc["blend", "width80"] > 0
    assert np.isnan(m.loc["model", "coverage80"])
    assert np.isfinite(result.national_interval).all()


def test_add_intervals_no_leakage():
    rng = np.random.default_rng(0)
    rows = [(r, y, rng.normal(0.03, 0.02), rng.normal(0.03, 0.02)) for y in range(2010, 2015) for r in "abcde"]
    df = pd.DataFrame(rows, columns=["region", "year", "blend", "actual"])
    df["vol12"] = 0.01

    def run(**over):
        d = df.copy()
        for y, v in over.items():
            d.loc[d.year == int(y[1:]), "actual"] = [10, -10, 10, -10, 10]
        return model.add_intervals(d)

    base = run()
    assert base.loc[base.year < 2012, ["lo", "hi"]].isna().all().all()
    ok = base[base.year >= 2012]
    assert (ok.lo <= ok.blend).all() and (ok.blend <= ok.hi).all()
    # 2012 outcomes feed 2014 intervals but not 2013; 2013-2014 outcomes feed neither.
    alt = run(y2012=1)
    assert np.allclose(alt.loc[alt.year == 2013, "lo"], base.loc[base.year == 2013, "lo"])
    assert not np.allclose(alt.loc[alt.year == 2014, "lo"], base.loc[base.year == 2014, "lo"])
    alt = run(y2013=1, y2014=1)
    assert np.allclose(alt.loc[alt.year == 2014, "lo"], base.loc[base.year == 2014, "lo"])


def test_calibrate_intervals_no_leakage():
    rng = np.random.default_rng(0)
    rows = [(r, y, rng.normal(0.03, 0.02), rng.normal(0.03, 0.02)) for y in range(2010, 2018) for r in "abcde"]
    df = pd.DataFrame(rows, columns=["region", "year", "blend", "actual"])
    df["vol12"] = 0.01

    def run(*years):
        d = df.copy()
        for y in years:
            d.loc[d.year == y, "actual"] = [5, -5, 5, -5, 5]
        return model.calibrate_intervals(model.add_intervals(d, 24), 24)

    cal, k = run()
    last = lambda c: c.loc[c.year == 2017, ["lo", "hi"]].to_numpy()  # gap 3: years <= 2014 allowed
    assert np.allclose(last(run(2016, 2015)[0]), last(cal))
    assert not np.allclose(last(run(2014)[0]), last(cal))
    base = model.add_intervals(df, 24)
    c, half = (base.lo + base.hi) / 2, (base.hi - base.lo) / 2
    inside = ((base.actual - c).abs() <= k * half)[base.lo.notna()].sum()
    assert abs(inside - 0.8 * base.lo.notna().sum()) <= 1


def test_add_intervals_gap_24m():
    rng = np.random.default_rng(0)
    rows = [(r, y, rng.normal(0.03, 0.02), rng.normal(0.03, 0.02)) for y in range(2010, 2017) for r in "abcde"]
    df = pd.DataFrame(rows, columns=["region", "year", "blend", "actual"])
    df["vol12"] = 0.01

    def run(y2012=None):
        d = df.copy()
        if y2012 is not None:
            d.loc[d.year == 2012, "actual"] = y2012
        return model.add_intervals(d, horizon=24)

    base, alt = run(), run([10, -10, 10, -10, 10])
    assert base.loc[base.year < 2013, ["lo", "hi"]].isna().all().all()
    assert np.allclose(alt.loc[alt.year == 2014, "lo"], base.loc[base.year == 2014, "lo"])
    assert not np.allclose(alt.loc[alt.year == 2015, "lo"], base.loc[base.year == 2015, "lo"])


def test_backtest_blend_is_average(mortgage_result):
    b = mortgage_result.metrics["bias"]
    assert np.isclose(b["blend"], (b["model"] + b["naive_momentum"]) / 2)


def test_served_is_blend(monkeypatch):
    assert model.blend(np.array([0.02]), np.array([0.06]))[0] == 0.04
    monkeypatch.setattr(model, "blend", lambda m, n: n)
    long_df, mortgage = _load()
    r = model.train_and_evaluate(long_df, mortgage)
    us_r12 = model.build_features(long_df, mortgage).loc[("United States", r.as_of), "r12"]
    assert np.isclose(r.national_pred, np.exp(us_r12) - 1)


def test_train_and_evaluate_without_mortgage():
    long_df, _ = _load()
    result = model.train_and_evaluate(long_df, mortgage=None)
    assert not result.predictions.empty
    assert np.isfinite(result.national_pred)


def test_recency_weights():
    dates = pd.Series(pd.to_datetime(["2020-01-01", "2017-01-01", "2014-01-01"]))
    w = model.recency_weights(dates, pd.Timestamp("2020-01-01"))
    assert np.allclose(w, [1, 0.5, 0.25], atol=0.01)
    assert (np.diff(w) < 0).all()
