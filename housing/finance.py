"""Pure mortgage math and reference tables. Estimates only, not loan quotes."""
from __future__ import annotations

from bisect import bisect_left

import numpy as np
import pandas as pd

CREDIT_BANDS = ["620-639", "640-659", "660-679", "680-699", "700-719", "720-739", "740-759", "760-779", "780+"]
TERMS = (30, 20, 15, 10)
MIN_DOWN_PCT = {"conventional": 3.0, "fha": 3.5, "va": 0.0}
PMI_CANCEL_LTV = 78.0
DTI_WARN = 43.0
DTI_MAX = 50.0
REF_LLPA = 0.875  # PMMS reference borrower: 740-759, LTV 75.01-80

# Source: FHFA release of 2025-11-25 (baseline conforming loan limit, 1 unit). High-cost ceiling: $1,249,125.
CONFORMING_LIMIT_2026 = 832_750
FHA_LIMIT_BASE = 726_200  # HUD Mortgagee Letter 2023-05 loan-size split

# Source: Tax Foundation, "Property Taxes by State and County" (2024 ACS, published 2026-03-16).
# Effective rate on owner-occupied homes, % of value per year.
PROPERTY_TAX_PCT = {
    "AL": .37, "AK": .94, "AZ": .48, "AR": .56, "CA": .70, "CO": .50, "CT": 1.54, "DE": .54, "DC": .60, "FL": .78,
    "GA": .79, "HI": .29, "ID": .495, "IL": 1.88, "IN": .76, "IA": 1.33, "KS": 1.21, "KY": .74, "LA": .55, "ME": .98,
    "MD": .92, "MA": 1.00, "MI": 1.19, "MN": 1.00, "MS": .58, "MO": .89, "MT": .61, "NE": 1.44, "NV": .50, "NH": 1.50,
    "NJ": 1.88, "NM": .63, "NY": 1.30, "NC": .66, "ND": .92, "OH": 1.36, "OK": .79, "OR": .81, "PA": 1.26, "RI": 1.12,
    "SC": .49, "SD": 1.00, "TN": .52, "TX": 1.40, "UT": .48, "VT": 1.51, "VA": .78, "WA": .75, "WV": .51, "WI": 1.32,
    "WY": .53,
}

# Source: NAIC 2022 via III "Facts + Statistics: Homeowners and renters insurance".
# Average HO-3 premium, $/yr. 2022 data, likely below 2026 premiums.
HOME_INS_ANNUAL = {
    "AL": 1748, "AK": 1129, "AZ": 1018, "AR": 1740, "CA": 1492, "CO": 2079, "CT": 1814, "DE": 1103, "DC": 1384,
    "FL": 2677, "GA": 1655, "HI": 1431, "ID": 1002, "IL": 1343, "IN": 1191, "IA": 1268, "KS": 1583, "KY": 1359,
    "LA": 2603, "ME": 1077, "MD": 1392, "MA": 1871, "MI": 1056, "MN": 1774, "MS": 1907, "MO": 1668, "MT": 1639,
    "NE": 1869, "NV": 948, "NH": 1188, "NJ": 1417, "NM": 1322, "NY": 1628, "NC": 1621, "ND": 1325, "OH": 995,
    "OK": 2268, "OR": 893, "PA": 1120, "RI": 2074, "SC": 1571, "SD": 1756, "TN": 1492, "TX": 2397, "UT": 937,
    "VT": 1109, "VA": 1332, "WA": 1151, "WV": 1113, "WI": 957, "WY": 1596,
}

# Approximate Fannie Mae LLPA Matrix Table 1 (purchase, effective 2023-05-01), % of loan, from memory (approximate).
# Applies to terms > 15 years only. Columns: LTV <=60, 60-70, 70-75, 75-80, 80-85, 85-90, 90-95, >95.
LLPA_EDGES = [60, 70, 75, 80, 85, 90, 95]
LLPA = {
    "780+": [0, 0, 0, .375, .375, .25, .25, .125],
    "760-779": [0, 0, .25, .625, .625, .5, .5, .25],
    "740-759": [0, .125, .375, .875, 1, .75, .625, .5],
    "720-739": [0, .25, .75, 1.25, 1.25, 1, .875, .75],
    "700-719": [0, .375, .875, 1.375, 1.5, 1.25, 1.125, .875],
    "680-699": [0, .625, 1.125, 1.75, 1.875, 1.5, 1.375, 1.125],
    "660-679": [0, .75, 1.375, 1.875, 2.125, 1.75, 1.625, 1.25],
    "640-659": [0, 1.125, 1.5, 2.25, 2.5, 2, 1.875, 1.5],
    "620-639": [.125, 1.5, 2.125, 2.75, 2.875, 2.625, 2.25, 1.75],
}

# Illustrative conventional BPMI, % of loan per year (not verified). Columns: LTV 80-85, 85-90, 90-95, 95-97.
PMI_EDGES = [85, 90, 95]
PMI_ANNUAL_PCT = {
    "780+": [.15, .20, .30, .40], "760-779": [.17, .25, .38, .52], "740-759": [.20, .30, .46, .63],
    "720-739": [.25, .38, .58, .79], "700-719": [.30, .45, .70, .94], "680-699": [.36, .56, .87, 1.18],
    "660-679": [.45, .70, 1.05, 1.40], "640-659": [.55, .85, 1.25, 1.62], "620-639": [.65, 1.00, 1.45, 1.86],
}

# FHA MIP: HUD Mortgagee Letter 2023-05, effective 2023-03-20. Upfront 1.75% of base loan, financed.
FHA_UFMIP_PCT = 1.75
# VA funding fee, first use, purchase: VA.gov, effective 2023-04-07. Financed.


def monthly_payment(principal: float, annual_rate_pct: float, n_months: int) -> float:
    r = annual_rate_pct / 1200
    if r == 0:
        return principal / n_months
    return principal * r / (1 - (1 + r) ** -n_months)


def amortization_schedule(principal: float, annual_rate_pct: float, n_months: int) -> pd.DataFrame:
    r = annual_rate_pct / 1200
    pay = monthly_payment(principal, annual_rate_pct, n_months)
    bal, rows = principal, []
    for m in range(1, n_months + 1):
        interest = bal * r
        princ = bal if m == n_months else pay - interest  # last payment absorbs rounding drift
        bal = 0.0 if m == n_months else bal - princ
        rows.append((m, princ + interest, interest, princ, bal))
    return pd.DataFrame(rows, columns=["month", "payment", "interest", "principal", "balance"])


def ltv_pct(loan: float, price: float) -> float:
    return loan / price * 100


def ltv_bucket(ltv: float, edges: list[float]) -> int:
    """Column index: first edge >= ltv (upper bounds inclusive), else len(edges)."""
    return bisect_left(edges, ltv)


def is_jumbo(base_loan: float, loan_type: str) -> bool:
    return loan_type == "conventional" and base_loan > CONFORMING_LIMIT_2026


def base_rates(r30: float, r15: float) -> dict[int, float]:
    step = (r30 - r15) * 5 / 15  # 20y interpolated, 10y extrapolated
    return {30: r30, 20: r15 + step, 15: r15, 10: r15 - step}


def adjusted_rate(base: float, term_years: int, loan_type: str, band: str, ltv: float) -> float:
    if loan_type == "conventional":
        if term_years <= 15:
            return base
        return base + (LLPA[band][ltv_bucket(ltv, LLPA_EDGES)] - REF_LLPA) * 0.25
    adder = 0.25 if band == "620-639" else 0.125 if band in ("640-659", "660-679") else 0.0
    return base - 0.25 + adder


def upfront_fee(base_loan: float, loan_type: str, down_pct: float) -> float:
    if loan_type == "fha":
        return base_loan * FHA_UFMIP_PCT / 100
    if loan_type == "va":
        return base_loan * (2.15 if down_pct < 5 else 1.5 if down_pct < 10 else 1.25) / 100
    return 0.0


def fha_annual_bps(base_loan: float, ltv: float, term_years: int) -> int:
    big = base_loan > FHA_LIMIT_BASE
    if term_years > 15:
        return (70 if ltv <= 95 else 75) if big else (50 if ltv <= 95 else 55)
    if big:
        return 15 if ltv <= 78 else 40 if ltv <= 90 else 65
    return 15 if ltv <= 90 else 40


def mi_schedule(loan_type: str, base_loan: float, price: float, term_years: int, band: str,
                schedule: pd.DataFrame) -> np.ndarray:
    """Monthly mortgage insurance ($) for each month of `schedule`."""
    n = len(schedule)
    start_bal = (schedule["balance"] + schedule["principal"]).to_numpy()
    ltv = ltv_pct(base_loan, price)
    if loan_type == "conventional" and ltv > 80:
        pct = PMI_ANNUAL_PCT[band][min(ltv_bucket(ltv, PMI_EDGES), 3)]
        return np.where(start_bal > PMI_CANCEL_LTV / 100 * price, pct / 100 * base_loan / 12, 0.0)
    if loan_type == "fha":
        # ponytail: MIP on monthly balance; HUD uses annual average balance — within a few $
        out = fha_annual_bps(base_loan, ltv, term_years) / 1e4 * start_bal / 12
        out[(132 if ltv <= 90 else n):] = 0.0
        return out
    return np.zeros(n)


def apr(amount_financed: float, payments: np.ndarray) -> float:
    t = np.arange(1, len(payments) + 1)
    lo, hi = 0.0, 0.05
    while hi - lo > 1e-10:
        mid = (lo + hi) / 2
        if (payments / (1 + mid) ** t).sum() > amount_financed:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2 * 1200


def estimate(price: float, down_pct: float, loan_type: str, band: str, state: str, term_years: int,
             r_base: dict[int, float], fees_pct: float = 1.0, tax_pct: float | None = None,
             ins_annual: float | None = None) -> dict:
    if down_pct >= 100:
        raise ValueError("Down payment must be below 100% of the price.")
    if down_pct < MIN_DOWN_PCT[loan_type]:
        raise ValueError(f"Minimum down payment for a {loan_type.upper()} loan is {MIN_DOWN_PCT[loan_type]}%.")
    tax_pct = PROPERTY_TAX_PCT[state] if tax_pct is None else tax_pct
    ins_annual = HOME_INS_ANNUAL[state] if ins_annual is None else ins_annual
    base_loan = price * (1 - down_pct / 100)
    ltv = ltv_pct(base_loan, price)
    rate = adjusted_rate(r_base[term_years], term_years, loan_type, band, ltv)
    upfront = upfront_fee(base_loan, loan_type, down_pct)
    loan = base_loan + upfront
    schedule = amortization_schedule(loan, rate, term_years * 12)
    mi = mi_schedule(loan_type, base_loan, price, term_years, band, schedule)
    pi = monthly_payment(loan, rate, term_years * 12)
    tax, ins = price * tax_pct / 1200, ins_annual / 12
    return {
        "term": term_years, "rate": rate, "loan": loan, "pi": pi, "tax": tax, "ins": ins, "mi": float(mi[0]),
        "piti": pi + tax + ins + float(mi[0]),
        "apr": apr(base_loan * (1 - fees_pct / 100), pi + mi),
        "total_interest": float(schedule["interest"].sum()), "ltv": ltv,
        "jumbo": is_jumbo(base_loan, loan_type), "upfront": upfront, "schedule": schedule,
    }


def dti(piti: float, debts: float, income: float) -> tuple[float, float]:
    return piti / income * 100, (piti + debts) / income * 100
