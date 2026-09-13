"""Measures how much each ensemble hyperparameter actually moves the inspection
ranking -- the evidence behind slide 13 of the round-2 deck.

Run from `05-App/`:
    uv run python scripts/hyperparameter_sensitivity.py

The headline result is that `contamination` does not move the ranking at all. It sets
`offset_`, the cut-point for the binary `predict()`, and the pipeline never calls
`predict()` -- it uses the continuous scores. The parameter that does move the ranking
is `random_state`, and `n_estimators` is what damps it.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline" / "src"))
from nidhinetra_pipeline.risk import detectors  # noqa: E402

AS_OF = date(2026, 9, 4)
SAMPLE_N = 8000  # enough for a stable read, small enough to re-run live in a demo


def sample_records() -> list[dict]:
    works = pd.read_parquet(ROOT / "data" / "snapshot" / "works.parquet")
    works = works.sample(min(SAMPLE_N, len(works)), random_state=1)
    records = []
    for row in works.to_dict("records"):
        sanction = row.get("sanction_date")
        records.append({
            "work_id": row["work_id"],
            "sanctioned_amount_inr": row["sanctioned_amount_inr"],
            "expenditure_amount_inr": row["expenditure_amount_inr"],
            "sanction_date": sanction if isinstance(sanction, str) else None,
        })
    return records


def jaccard_at_k(a: dict[str, float], b: dict[str, float], k: int) -> float:
    top_a = {w for w, _ in sorted(a.items(), key=lambda kv: -kv[1])[:k]}
    top_b = {w for w, _ in sorted(b.items(), key=lambda kv: -kv[1])[:k]}
    return len(top_a & top_b) / len(top_a | top_b)


def contamination_sweep(records: list[dict]) -> None:
    print("CONTAMINATION SWEEP -- effect on the ensemble ranking")
    print(f"{'contamination':>14}{'scores identical':>19}{'Jaccard@1000':>15}{'max |diff|':>13}")
    baseline = detectors.ensemble_scores(records, AS_OF)
    original = (detectors.ISOLATION_FOREST_CONTAMINATION, detectors.LOF_CONTAMINATION)
    try:
        for value in (0.01, 0.05, 0.1, 0.25, 0.5):
            detectors.ISOLATION_FOREST_CONTAMINATION = value
            detectors.LOF_CONTAMINATION = value
            out = detectors.ensemble_scores(records, AS_OF)
            identical = all(baseline[w] == out[w] for w in baseline)
            worst = max(abs(baseline[w] - out[w]) for w in baseline)
            print(f"{value:>14}{str(identical):>19}"
                  f"{jaccard_at_k(baseline, out, 1000):>15.6f}{worst:>13.3e}")
    finally:
        detectors.ISOLATION_FOREST_CONTAMINATION, detectors.LOF_CONTAMINATION = original


def seed_and_tree_sweep(records: list[dict]) -> None:
    """The honest counterpart: what *does* move the ranking, and how n_estimators
    damps it. Uses IsolationForest directly so the seed can be varied."""
    features = detectors._feature_matrix(records, AS_OF)
    scaled = StandardScaler().fit_transform(features)
    ids = [r["work_id"] for r in records]

    def fit(n_estimators: int, seed: int) -> dict[str, float]:
        model = IsolationForest(n_estimators=n_estimators, contamination=0.1,
                                random_state=seed).fit(scaled)
        signal = -model.decision_function(scaled)
        return dict(zip(ids, signal.tolist(), strict=True))

    print("\nSEED SENSITIVITY -- agreement between two seeds, by forest size")
    print(f"{'n_estimators':>14}{'Spearman':>12}{'Jaccard@1000':>15}")
    for n_estimators in (50, 100, 200, 400, 800):
        a, b = fit(n_estimators, 42), fit(n_estimators, 99)
        rho = spearmanr(list(a.values()), list(b.values())).statistic
        print(f"{n_estimators:>14}{rho:>12.4f}{jaccard_at_k(a, b, 1000):>15.4f}")
    print(f"\n  The pipeline uses n_estimators="
          f"{detectors.ISOLATION_FOREST_N_ESTIMATORS} and a fixed random_state="
          f"{detectors.ISOLATION_FOREST_RANDOM_STATE}.")


if __name__ == "__main__":
    data = sample_records()
    print(f"records sampled: {len(data):,}\n")
    contamination_sweep(data)
    seed_and_tree_sweep(data)
