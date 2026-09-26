"""Tests for Task 8 Part A's offline early-warning model (early_warning.py).

Synthetic frames only -- never the real parquet (global-context.md rule). One reusable helper
(`_cohort_rows`) builds a cohort segment whose label is a smoothed function of
`implementing_agency`'s assigned rate: setting every agency's rate to 0.5 gives pure noise (no
feature carries real signal); a skewed, imbalanced pair of rates gives a clean, easily-separable
"shipped" scenario. Both are seeded and large enough (thousands of rows) to be stable.
"""

from __future__ import annotations

import json
import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
from nidhinetra_pipeline import early_warning as ew

AS_OF = date(2026, 9, 4)
# Task 8's brief: for as_of 2026-09-04 these are the exact windows.
START, CUTOFF, END = date(2024, 7, 4), date(2025, 1, 4), date(2025, 4, 4)

STATE_POOL = ["Bihar", "Odisha"]
CATEGORY_POOL = ["Road", "School"]


def _cohort_rows(
    rng: np.random.Generator,
    n: int,
    window_start: date,
    window_end: date,
    agency_rate: dict[str, float],
    agency_weight: dict[str, float],
    prefix: str,
) -> list[dict]:
    agencies = list(agency_rate)
    weights = np.array([agency_weight[a] for a in agencies], dtype=float)
    weights = weights / weights.sum()
    span_days = max((window_end - window_start).days, 0)
    rows = []
    for i in range(n):
        agency = str(rng.choice(agencies, p=weights))
        y = int(rng.random() < agency_rate[agency])
        sd = window_start + timedelta(days=int(rng.integers(0, span_days + 1)))
        rows.append(
            {
                "work_id": f"{prefix}-{i:06d}",
                "state": STATE_POOL[i % len(STATE_POOL)],
                "work_category": CATEGORY_POOL[i % len(CATEGORY_POOL)],
                "implementing_agency": agency,
                "sanctioned_amount_inr": float(rng.integers(200_000, 5_000_000)),
                "expenditure_amount_inr": float(rng.integers(0, 2_000_000)),
                "sanction_date": sd.isoformat(),
                "completion_status": "Completed" if y == 0 else "In Progress",
            }
        )
    return rows


def _cohort(rng: np.random.Generator, agency_rate: dict, agency_weight: dict) -> pd.DataFrame:
    train_end = CUTOFF - timedelta(days=1)
    rows = _cohort_rows(rng, 2000, START, train_end, agency_rate, agency_weight, "TRAIN")
    rows += _cohort_rows(rng, 2000, CUTOFF, END, agency_rate, agency_weight, "TEST")
    return pd.DataFrame(rows)


def _noise_works() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    agency_rate = {f"Agency {c}": 0.5 for c in "ABCD"}
    agency_weight = dict.fromkeys(agency_rate, 1.0)
    return _cohort(rng, agency_rate, agency_weight)


def _agency_driven_works() -> tuple[pd.DataFrame, set[str], set[str]]:
    """A cohort where the label is almost entirely determined by implementing_agency, plus a
    "young" population (sanctioned within the last year) to score. Returns
    (works, young_ids, completed_young_ids) so tests can check the watch-set invariants.
    """
    rng = np.random.default_rng(1)
    agency_rate = {"Agency Alpha": 0.95, "Agency Beta": 0.10}
    agency_weight = {"Agency Alpha": 0.15, "Agency Beta": 0.85}
    frame = _cohort(rng, agency_rate, agency_weight)

    agencies = list(agency_rate)
    weights = np.array([agency_weight[a] for a in agencies], dtype=float)
    weights = weights / weights.sum()

    young_rows = []
    young_ids: set[str] = set()
    for i in range(1000):
        agency = str(rng.choice(agencies, p=weights))
        sd = AS_OF - timedelta(days=int(rng.integers(0, 366)))
        work_id = f"YOUNG-{i:06d}"
        young_ids.add(work_id)
        young_rows.append(
            {
                "work_id": work_id,
                "state": STATE_POOL[i % len(STATE_POOL)],
                "work_category": CATEGORY_POOL[i % len(CATEGORY_POOL)],
                "implementing_agency": agency,
                "sanctioned_amount_inr": float(rng.integers(200_000, 5_000_000)),
                "expenditure_amount_inr": float(rng.integers(0, 2_000_000)),
                "sanction_date": sd.isoformat(),
                "completion_status": "Sanctioned" if i % 2 == 0 else "In Progress",
            }
        )

    completed_ids: set[str] = set()
    for i in range(150):
        sd = AS_OF - timedelta(days=int(rng.integers(0, 366)))
        work_id = f"YOUNG-DONE-{i:06d}"
        completed_ids.add(work_id)
        young_rows.append(
            {
                "work_id": work_id,
                "state": STATE_POOL[i % len(STATE_POOL)],
                "work_category": CATEGORY_POOL[i % len(CATEGORY_POOL)],
                # Even the high-risk agency must not put a completed work on the watch list.
                "implementing_agency": "Agency Alpha",
                "sanctioned_amount_inr": float(rng.integers(200_000, 5_000_000)),
                "expenditure_amount_inr": float(rng.integers(0, 2_000_000)),
                "sanction_date": sd.isoformat(),
                "completion_status": "Completed",
            }
        )

    works = pd.concat([frame, pd.DataFrame(young_rows)], ignore_index=True)
    return works, young_ids, completed_ids


def test_windows_for_2026_09_04():
    works, _, _ = _agency_driven_works()

    artifact = ew.build(works, AS_OF)

    assert artifact["cohort"]["start"] == START.isoformat()
    assert artifact["cohort"]["train_cutoff"] == CUTOFF.isoformat()
    assert artifact["cohort"]["end"] == END.isoformat()


def test_build_is_deterministic():
    works, _, _ = _agency_driven_works()

    first = ew.build(works.copy(), AS_OF)
    second = ew.build(works.copy(), AS_OF)

    assert first == second


def test_pure_noise_labels_do_not_ship():
    artifact = ew.build(_noise_works(), AS_OF)

    assert artifact["status"] == "not_shipped"
    assert artifact["watch"] == []
    assert artifact["scored_n"] == 0
    assert artifact["watch_n"] == 0
    assert artifact["metrics"]["roc_auc"] < ew.MIN_TEST_AUC or (
        artifact["metrics"]["lift_at_10"] < ew.MIN_TEST_LIFT
    )


def test_agency_driven_labels_ship_with_a_ranked_watch_list():
    works, young_ids, completed_ids = _agency_driven_works()

    artifact = ew.build(works, AS_OF)

    assert artifact["status"] == "shipped"
    assert artifact["metrics"]["roc_auc"] > 0.8
    assert artifact["scored_n"] == len(young_ids)
    assert artifact["watch_n"] == math.ceil(ew.WATCH_SHARE * len(young_ids))
    assert len(artifact["watch"]) == artifact["watch_n"]
    watch_set = set(artifact["watch"])
    assert watch_set <= young_ids
    assert watch_set.isdisjoint(completed_ids)


def test_expenditure_amount_does_not_affect_the_output():
    works, _, _ = _agency_driven_works()
    baseline = ew.build(works.copy(), AS_OF)

    changed = works.copy()
    changed["expenditure_amount_inr"] = changed["expenditure_amount_inr"] + 999_999.0

    assert ew.build(changed, AS_OF) == baseline


def test_artifact_is_always_json_safe():
    shipped_works, _, _ = _agency_driven_works()

    json.dumps(ew.build(shipped_works, AS_OF), allow_nan=False)
    json.dumps(ew.build(_noise_works(), AS_OF), allow_nan=False)
