import numpy as np
import pandas as pd
import pytest

from housing import finance as f

RB = f.base_rates(7.0, 6.4)


def test_monthly_payment():
    assert f.monthly_payment(200000, 6, 360) == pytest.approx(1199.10, abs=0.01)
    assert f.monthly_payment(300000, 7, 180) == pytest.approx(2696.48, abs=0.01)
    assert f.monthly_payment(120000, 0, 120) == 1000


def test_schedule():
    s = f.amortization_schedule(250000, 6.5, 360)
    assert len(s) == 360
    assert abs(s["balance"].iloc[-1]) < 0.01
    assert s["principal"].sum() == pytest.approx(250000, abs=0.01)


def test_apr_equals_rate_without_fees():
    pay = np.full(360, f.monthly_payment(200000, 6, 360))
    assert f.apr(200000, pay) == pytest.approx(6.0, abs=1e-6)


def test_apr_with_fees():
    pay = np.full(360, f.monthly_payment(200000, 6, 360))
    a = f.apr(196000, pay)
    assert a > 6.0
    r = a / 1200
    assert (pay / (1 + r) ** np.arange(1, 361)).sum() == pytest.approx(196000, abs=0.01)


def test_is_jumbo():
    assert not f.is_jumbo(832_750, "conventional")
    assert f.is_jumbo(832_751, "conventional")
    assert not f.is_jumbo(2_000_000, "fha")


def test_ltv_buckets():
    assert f.ltv_pct(80, 100) == 80.0
    assert f.ltv_bucket(80.0, f.LLPA_EDGES) == 3
    assert f.ltv_bucket(80.01, f.LLPA_EDGES) == 4


def _mi(loan_type, down, term=30):
    price = 400_000
    base = price * (1 - down / 100)
    loan = base + f.upfront_fee(base, loan_type, down)
    s = f.amortization_schedule(loan, 6.5, term * 12)
    return f.mi_schedule(loan_type, base, price, term, "740-759", s), s, price


def test_conventional_mi_20_down():
    assert not _mi("conventional", 20)[0].any()


def test_conventional_pmi_cancels():
    mi, s, price = _mi("conventional", 10)
    assert mi[0] > 0
    start = (s["balance"] + s["principal"]).to_numpy()
    first = int(np.argmax(start <= 0.78 * price))
    assert first > 0 and (mi[:first] > 0).all() and not mi[first:].any()


def test_fha_bps():
    mi, s, _ = _mi("fha", 3.5)
    start = (s["balance"] + s["principal"]).to_numpy()
    assert (mi > 0).all() and np.allclose(mi * 12 / start * 1e4, 55)
    mi, s, _ = _mi("fha", 10)
    start = (s["balance"] + s["principal"]).to_numpy()
    assert (mi > 0).sum() == 132 and np.allclose(mi[:132] * 12 / start[:132] * 1e4, 50)
    mi, s, _ = _mi("fha", 10, 15)
    start = (s["balance"] + s["principal"]).to_numpy()
    assert np.allclose(mi[:132] * 12 / start[:132] * 1e4, 15)


def test_va_fee():
    assert f.upfront_fee(400000, "va", 0) == pytest.approx(400000 * 0.0215)
    assert f.upfront_fee(400000, "va", 10) == pytest.approx(400000 * 0.0125)
    assert not _mi("va", 0)[0].any()


def test_adjusted_rate():
    assert f.adjusted_rate(6.0, 15, "conventional", "620-639", 95) == 6.0
    assert f.adjusted_rate(6.0, 30, "conventional", "780+", 80) == pytest.approx(5.875)


def test_base_rates():
    assert RB[20] == pytest.approx(6.6) and RB[10] == pytest.approx(6.2)


def test_estimate():
    e = f.estimate(400_000, 20, "conventional", "740-759", "TX", 30, RB)
    assert e["piti"] == pytest.approx(e["pi"] + e["tax"] + e["ins"] + e["mi"]) and e["apr"] > e["rate"]
    with pytest.raises(ValueError):
        f.estimate(400_000, 2, "conventional", "740-759", "TX", 30, RB)
    with pytest.raises(ValueError):
        f.estimate(400_000, 100, "va", "740-759", "TX", 30, RB)


def test_dti():
    assert f.dti(2000, 500, 8000) == (25.0, 31.25)


def test_arm_fixed_period():
    s = f.arm_schedule(300000, 6.0, 3.8, 2.75, 60, (2, 1, 5))
    assert (s["rate"].iloc[:60] == 6.0).all()
    assert s["payment"].iloc[:60].to_numpy() == pytest.approx(f.monthly_payment(300000, 6, 360), abs=0.01)


def test_arm_flat_index():
    s = f.arm_schedule(300000, 6.0, 3.8, 2.75, 60, (2, 1, 5))
    assert f.round_eighth(6.55) == 6.5
    assert (s["rate"].iloc[60:] == 6.5).all()
    bal60 = f.amortization_schedule(300000, 6, 360)["balance"].iloc[59]
    assert s["payment"].iloc[60] == pytest.approx(f.monthly_payment(bal60, 6.5, 300), abs=0.01)
    assert s["interest"].sum() == pytest.approx(s["payment"].sum() - 300000, abs=0.01)


def test_arm_caps_up_5_6():
    assert f.arm_rates(5.0, 10.0, 2.75, 60, (2, 1, 5))[:6] == [5.0, 7.0, 8.0, 9.0, 10.0, 10.0]


def test_arm_caps_10_6():
    r = f.arm_rates(5.0, 10.0, 2.75, 120, (5, 1, 5))
    assert r[:3] == [5.0, 10.0, 10.0]
    assert len(r) == 1 + 240 // 6


def test_arm_floor_and_down_caps():
    assert f.arm_rates(7.0, 0.0, 2.75, 60, (2, 1, 5))[:6] == [7.0, 5.0, 4.0, 3.0, 2.75, 2.75]


def test_arm_balance_zero():
    for p in f.ARM_PLANS:
        for s in f.arm_scenarios(400000, 6.9, 3.8, 2.75, p).values():
            assert len(s) == 360
            assert abs(s["balance"].iloc[-1]) < 0.01
            assert s["principal"].sum() == pytest.approx(400000, abs=0.01)


def test_arm_worst_case():
    s = f.arm_scenarios(400000, 6.9, 3.8, 2.75, "5/6")["Caps worst case"]
    assert s["rate"].max() == pytest.approx(6.9 + 5)


def test_appreciation_params_exact():
    s = pd.Series(100 * np.exp(0.03 * np.arange(180) / 12))
    mu, sd5 = f.appreciation_params(s)
    assert mu == pytest.approx(0.03, abs=1e-12)
    assert sd5 == pytest.approx(0, abs=1e-12)


def test_appreciation_params_short():
    with pytest.raises(ValueError):
        f.appreciation_params(pd.Series(np.linspace(100, 200, 119)))
    with pytest.raises(ValueError):
        f.appreciation_params(pd.Series([np.nan] * 10 + list(np.linspace(100, 200, 119))))


def test_equity_compounding():
    d = f.equity_projection(100000, f.amortization_schedule(80000, 6, 360), 0.05, 0.0)
    assert d["value"].iloc[9] == pytest.approx(100000 * np.exp(0.5), abs=0.01)
    assert (d.value_lo == d.value).all() and (d.value == d.value_hi).all()


def test_equity_year1_forecast():
    d = f.equity_projection(100000, f.amortization_schedule(80000, 6, 360), 0.04, 0.1, (-0.02, 0.03, 0.08))
    assert [d[c].iloc[0] for c in ("value_lo", "value", "value_hi")] == pytest.approx([98000, 103000, 108000], abs=0.01)
    assert d["value"].iloc[4] == pytest.approx(103000 * np.exp(0.16), abs=0.01)
    assert d["value_lo"].iloc[4] == pytest.approx(98000 * np.exp(0.16 - f.Z80 * 0.1 * np.sqrt(4 / 5)), abs=0.01)


def test_equity_balance_subtraction():
    s = f.amortization_schedule(80000, 6, 180)
    d = f.equity_projection(100000, s, 0.03, 0.1, sell_pct=6)
    assert d["balance"].iloc[4] == s["balance"].iloc[59]
    assert (d["balance"].iloc[14:] == 0).all()
    assert np.allclose(d.equity, d.value - d.balance)
    assert np.allclose(d.net, d.value * 0.94 - d.balance, atol=0.01)


def test_equity_range_ordering():
    fixed = f.amortization_schedule(300000, 6, 360)
    arm = f.arm_schedule(300000, 6.0, 3.8, 2.75, 60, (2, 1, 5))
    assert arm["balance"].iloc[-1] < 0.01
    for sch in (fixed, arm):
        for mu, sd5, y1 in [(0.04, 0.1, (-0.02, 0.03, 0.08)), (0.0, 0.2, None), (0.02, 0.15, (0.05, 0.03, 0.08))]:
            d = f.equity_projection(400000, sch, mu, sd5, y1)
            for c in ("value", "equity", "net"):
                assert (d[c + "_lo"] <= d[c] + 1e-9).all() and (d[c] <= d[c + "_hi"] + 1e-9).all()
            assert (np.diff(d.value_hi / d.value_lo) >= -1e-12).all()


def test_affordability_table_share():
    m = pd.DataFrame({"region": ["A", "B"], "state": ["IL", "TX"], "value": [200_000.0, 900_000.0]})
    rb = f.base_rates(6.5, 5.8)
    t = f.affordability_table(m, 100_000, 20.0, rb)
    p = f.estimate(200_000, 20.0, "conventional", "740-759", "IL", 30, rb)["piti"]
    assert t["payment"].iloc[0] == pytest.approx(p)
    assert t["share"].iloc[0] == pytest.approx(p * 12 / 100_000)
    assert list(t["affordable"]) == [True, False]
    assert not f.affordability_table(m, 100_000, 20.0, rb, debts=3000)["affordable"].iloc[0]


def test_affordability_table_errors():
    m = pd.DataFrame({"region": ["A"], "state": ["IL"], "value": [200_000.0]})
    rb = f.base_rates(6.5, 5.8)
    with pytest.raises(ValueError):
        f.affordability_table(m, 0, 20.0, rb)
    with pytest.raises(ValueError):
        f.affordability_table(m, 100_000, 1.0, rb)
