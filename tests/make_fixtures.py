"""Deterministically generate small fixture CSVs matching the real source formats.

Note: zillow_forecast.csv is hand-written (not generated here).
Run with: python tests/make_fixtures.py
Regenerates tests/fixtures/{zhvi_metro,zhvi_state,MORTGAGE30US,CSUSHPINSA,MSACSR,...}.csv
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

MONTH_ENDS = pd.date_range("2000-01-31", "2026-08-31", freq="ME")
DATE_COL_LABELS = [d.strftime("%Y-%m-%d") for d in MONTH_ENDS]

METROS = [
    # (RegionID, SizeRank, RegionName, StateName, start_value, monthly_drift, monthly_vol)
    (10001, 1, "New York-Newark-Jersey City, NY-NJ", "NY", 350000, 0.0025, 0.010),
    (10002, 2, "Los Angeles-Long Beach-Anaheim, CA", "CA", 400000, 0.0035, 0.014),
    (10003, 3, "Chicago, IL", "IL", 220000, 0.0015, 0.009),
    (10004, 4, "Dallas-Fort Worth, TX", "TX", 180000, 0.0040, 0.011),
    (10005, 5, "Houston, TX", "TX", 170000, 0.0020, 0.010),
    (10006, 6, "Miami-Fort Lauderdale, FL", "FL", 210000, 0.0038, 0.015),
    (10007, 7, "Detroit, MI", "MI", 120000, 0.0010, 0.013),
    (10008, 8, "Seattle, WA", "WA", 260000, 0.0042, 0.013),
    (10009, 9, "Phoenix, AZ", "AZ", 190000, 0.0030, 0.016),
    (10010, 10, "Boise City, ID", "ID", 150000, 0.0033, 0.017),
]
# Metro with leading NaNs until 2010 (newly-covered market): Boise City (last one).
NAN_UNTIL_METRO = "Boise City, ID"
NAN_UNTIL_DATE = pd.Timestamp("2010-01-31")

STATES = [
    (20001, 1, "California", 400000, 0.0035, 0.014),
    (20002, 2, "Texas", 180000, 0.0035, 0.011),
    (20003, 3, "Florida", 210000, 0.0038, 0.015),
    (20004, 4, "New York", 320000, 0.0022, 0.010),
    (20005, 5, "Michigan", 130000, 0.0012, 0.012),
]


def _simulate(rng: np.random.Generator, start_value: float, drift: float, vol: float, n: int) -> np.ndarray:
    log_returns = rng.normal(loc=drift, scale=vol, size=n - 1)
    log_path = np.concatenate([[0.0], np.cumsum(log_returns)])
    return start_value * np.exp(log_path)


def build_zhvi_metro(rng: np.random.Generator) -> pd.DataFrame:
    n = len(MONTH_ENDS)
    rows = []
    # United States (country) row: gentle blended trend.
    us_values = _simulate(rng, 200000, 0.0025, 0.006, n)
    rows.append(
        {
            "RegionID": 1,
            "SizeRank": 0,
            "RegionName": "United States",
            "RegionType": "country",
            "StateName": np.nan,
            **dict(zip(DATE_COL_LABELS, us_values)),
        }
    )
    for region_id, size_rank, name, state, start_value, drift, vol in METROS:
        values = _simulate(rng, start_value, drift, vol, n)
        row = {
            "RegionID": region_id,
            "SizeRank": size_rank,
            "RegionName": name,
            "RegionType": "msa",
            "StateName": state,
            **dict(zip(DATE_COL_LABELS, values)),
        }
        if name == NAN_UNTIL_METRO:
            for label, dt in zip(DATE_COL_LABELS, MONTH_ENDS):
                if dt < NAN_UNTIL_DATE:
                    row[label] = np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def build_zhvi_state(rng: np.random.Generator) -> pd.DataFrame:
    n = len(MONTH_ENDS)
    rows = []
    for region_id, size_rank, name, start_value, drift, vol in STATES:
        values = _simulate(rng, start_value, drift, vol, n)
        rows.append(
            {
                "RegionID": region_id,
                "SizeRank": size_rank,
                "RegionName": name,
                "RegionType": "state",
                "StateName": name,
                **dict(zip(DATE_COL_LABELS, values)),
            }
        )
    return pd.DataFrame(rows)


def build_mortgage(rng: np.random.Generator) -> pd.DataFrame:
    weeks = pd.date_range("2000-01-07", "2026-08-28", freq="W-FRI")
    n = len(weeks)
    base = 3.5 + 3.0 * np.sin(np.linspace(0, 6, n)) * 0.3 + np.linspace(0, 2.0, n)
    noise = rng.normal(0, 0.05, n)
    values = np.clip(base + noise, 2.5, 8.5)
    df = pd.DataFrame(
        {"observation_date": weeks.strftime("%Y-%m-%d"), "MORTGAGE30US": values.round(2).astype(object)}
    )
    # Sprinkle a few missing-value placeholders like the real FRED export.
    missing_idx = rng.choice(n, size=max(1, n // 200), replace=False)
    df.loc[missing_idx, "MORTGAGE30US"] = "."
    return df


def build_mortgage15() -> pd.DataFrame:
    # Own RNG so other fixtures stay byte-identical.
    rng = np.random.default_rng(15)
    weeks = pd.date_range("2025-09-05", periods=50, freq="W-FRI")
    values = 4.2 + np.linspace(0, 0.8, 50) + rng.normal(0, 0.04, 50)
    return pd.DataFrame({"observation_date": weeks.strftime("%Y-%m-%d"), "MORTGAGE15US": values.round(2)})


def build_sofr() -> pd.DataFrame:
    days = pd.bdate_range("2025-09-01", "2026-09-30")
    values = np.linspace(4.3, 3.8, len(days)).round(5)
    return pd.DataFrame({"observation_date": days.strftime("%Y-%m-%d"), "SOFR30DAYAVG": values})


def build_case_shiller(rng: np.random.Generator) -> pd.DataFrame:
    months = pd.date_range("2000-01-01", "2026-06-01", freq="MS")
    n = len(months)
    log_returns = rng.normal(loc=0.003, scale=0.008, size=n - 1)
    log_path = np.concatenate([[0.0], np.cumsum(log_returns)])
    values = 100 * np.exp(log_path)
    df = pd.DataFrame(
        {"observation_date": months.strftime("%Y-%m-%d"), "CSUSHPINSA": values.round(3)}
    )
    return df


def build_msacsr() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    months = pd.date_range("2000-01-01", "2026-07-01", freq="MS")
    vals = 5.5 + 2 * np.sin(np.linspace(0, 8, len(months))) + rng.normal(0, 0.2, len(months))
    return pd.DataFrame({"observation_date": months.strftime("%Y-%m-%d"), "MSACSR": vals.round(1)})


SUPPLY_MONTHS = pd.date_range("2018-03-31", "2026-08-31", freq="ME")


def _supply_frame(rng: np.random.Generator, draw) -> pd.DataFrame:
    labels = [d.strftime("%Y-%m-%d") for d in SUPPLY_MONTHS]
    rows = [(1, 0, "United States", "country", np.nan)] + [
        (rid, rank, name, "msa", state) for rid, rank, name, state, *_ in METROS if name != NAN_UNTIL_METRO
    ]
    return pd.DataFrame(
        [
            {"RegionID": rid, "SizeRank": rank, "RegionName": name, "RegionType": rt, "StateName": st,
             **dict(zip(labels, draw(rng, len(labels))))}
            for rid, rank, name, rt, st in rows
        ]
    )


def build_inventory(rng: np.random.Generator) -> pd.DataFrame:
    # Boise City is left out on purpose to exercise NaN tolerance.
    return _supply_frame(rng, lambda r, n: (r.uniform(5000, 20000) * np.exp(np.cumsum(r.normal(0, 0.03, n)))).round())


def build_price_cut(rng: np.random.Generator) -> pd.DataFrame:
    return _supply_frame(rng, lambda r, n: r.uniform(0.05, 0.35, n).round(4))


def build_affordability(rng: np.random.Generator, kind: str) -> pd.DataFrame:
    # US + fixture metros except Boise City. Payment is seeded apart from `rng` so income = payment*12/0.30 matches.
    labels = [d.strftime("%Y-%m-%d") for d in pd.date_range("2024-01-31", "2026-08-31", freq="ME")]
    rows = [(1, 0, "United States", "country", np.nan)] + [
        (rid, rank, name, "msa", state) for rid, rank, name, state, *_ in METROS if name != NAN_UNTIL_METRO
    ]
    out = []
    for rid, rank, name, rt, st in rows:
        pay = np.random.default_rng(rid).uniform(1000, 4000, len(labels)).round()
        vals = {"payment": pay, "income": (pay * 12 / 0.30).round(), "share": rng.uniform(0.15, 0.60, len(labels)).round(4)}[kind]
        out.append({"RegionID": rid, "SizeRank": rank, "RegionName": name, "RegionType": rt, "StateName": st,
                    **dict(zip(labels, vals))})
    return pd.DataFrame(out)


def main() -> None:
    os.makedirs(FIXTURES_DIR, exist_ok=True)
    rng = np.random.default_rng(0)

    build_zhvi_metro(rng).to_csv(os.path.join(FIXTURES_DIR, "zhvi_metro.csv"), index=False)
    build_zhvi_state(rng).to_csv(os.path.join(FIXTURES_DIR, "zhvi_state.csv"), index=False)
    build_mortgage(rng).to_csv(os.path.join(FIXTURES_DIR, "MORTGAGE30US.csv"), index=False)
    build_case_shiller(rng).to_csv(os.path.join(FIXTURES_DIR, "CSUSHPINSA.csv"), index=False)
    build_mortgage15().to_csv(os.path.join(FIXTURES_DIR, "MORTGAGE15US.csv"), index=False)
    build_sofr().to_csv(os.path.join(FIXTURES_DIR, "SOFR30DAYAVG.csv"), index=False)

    rng = np.random.default_rng(1)
    build_inventory(rng).to_csv(os.path.join(FIXTURES_DIR, "inventory_metro.csv"), index=False)
    build_price_cut(rng).to_csv(os.path.join(FIXTURES_DIR, "price_cut_metro.csv"), index=False)

    rng = np.random.default_rng(2)
    for kind in ("payment", "income", "share"):
        build_affordability(rng, kind).to_csv(os.path.join(FIXTURES_DIR, f"afford_{kind}.csv"), index=False)

    build_msacsr().to_csv(os.path.join(FIXTURES_DIR, "MSACSR.csv"), index=False)


if __name__ == "__main__":
    main()
