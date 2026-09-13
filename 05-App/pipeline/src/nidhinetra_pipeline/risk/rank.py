"""Combines per-record flag findings and the ML ensemble signal into a
single 0-100 risk_score, then produces a dense, gap-free, deterministically
tie-broken inspection_rank across the whole scored batch.
"""

from __future__ import annotations

from typing import Any

FLAG_WEIGHTS: dict[str, float] = {
    "cost_outlier": 30,
    "stalled_work": 25,
    "expenditure_mismatch": 25,
    "agency_concentration": 20,
}
# Weights are additive (see compute_risk_score), not averaged: two
# independent reasons to inspect a work are a stronger signal than one, not
# a diluted one. cost_outlier and stalled_work carry the most weight
# because they are single-record, directly-measured facts about the work
# itself; agency_concentration carries the least because it is a
# network-level pattern that implicates the agency more than any one
# specific work on its own.

FLAGS_COMPONENT_CAP = 80.0
# Leaves headroom for the ensemble component below, and stops a record
# carrying all four flags from mathematically dominating every other
# record's score by more than the ensemble signal could ever claw back.

ENSEMBLE_COMPONENT_WEIGHT = 20.0
# The ML ensemble (risk/detectors.py ensemble_scores) is a supporting
# signal, not the headline reason a work is ranked where it is -- design
# brief: "Explainability beats accuracy theatre." A record's score is
# always dominated by the flags an inspector can actually be shown in
# why_flagged; the ensemble only nudges ordering within and around them,
# and is the only source of a nonzero score for an unflagged record.


def compute_risk_score(flags: list[str], ensemble_score: float) -> float:
    """flags: the fired flag names for one record (possibly empty).
    ensemble_score: that record's IsolationForest/LOF signal, in [0, 1].
    Returns a score in [0, 100], rounded to 2 decimal places.
    """
    flags_component = min(FLAGS_COMPONENT_CAP, sum(FLAG_WEIGHTS[f] for f in flags))
    ensemble_component = ENSEMBLE_COMPONENT_WEIGHT * max(0.0, min(1.0, ensemble_score))
    return round(min(100.0, flags_component + ensemble_component), 2)


def assign_ranks(scored: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Assigns inspection_rank 1..N, N = len(scored), with no gaps.

    Tie-break rule, frozen: risk_score descending, then work_id ascending.
    work_id is guaranteed unique per record (normalized_record.schema.json
    work_id.minLength + A1's ingest dedup), so this is always a total
    order -- no two records can tie all the way down -- which is exactly
    what makes the ranking reproducible run over run on the same input
    (Execution Plan 3.2, Checkpoints CP2: ranks must not reshuffle).

    Returns a new list (does not mutate the input dicts in place beyond
    adding the inspection_rank key), sorted into rank order.
    """
    ordered = sorted(scored, key=lambda r: (-r["risk_score"], r["work_id"]))
    ranked: list[dict[str, Any]] = []
    for position, record in enumerate(ordered, start=1):
        ranked.append({**record, "inspection_rank": position})
    return ranked
