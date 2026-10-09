import numpy as np
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
