"""POST /api/inspections (Checkpoints CP8, contracts/inspection_outcome.schema.json).

The one write endpoint in an API that has otherwise never accepted state
from a client -- everything else here is a read over data/snapshot/*.parquet,
fully rebuildable. An inspection outcome is not: it is a human judgement
that exists nowhere else, so it is persisted through
nidhinetra_pipeline.outcomes.store (a separate SQLite file build_snapshot()
never touches), not through this API's own snapshot/DuckDB layer at all.

inspection_rank_at_time, risk_score_at_time, cutoff_rank_at_time,
population_n_at_time, and the denormalized context fields (state,
constituency, implementing_agency, work_category, sanctioned_amount_inr)
are all looked up here, from the CURRENT snapshot, at the moment this
request is handled -- never accepted from the request body. Ranks reshuffle
between pulls (Checkpoints CP1), so trusting a client-supplied rank would
let a stale or spoofed value corrupt precision-at-quota later; looking it
up server-side and freezing it into the stored row is what makes that
figure honest.

cutoff_rank_at_time / population_n_at_time exist because of a 2026-09-05
outside-voice finding: inspection_rank is drawn from ALL 79,068 works
(rank.py has no completion_status filter) but the 10 percent quota cutoff is
drawn from only the 44,810 works under implementation (routers/stats.py,
web/lib/data.ts) -- two different populations, only comparable if a row
freezes both at once. _lookup_work_context() below mirrors stats.py's
UNDER_IMPLEMENTATION population and data.ts's getQuotaFigures formula
exactly, so this endpoint's frozen cutoff can never drift from what the
quota meter shows on screen the same moment.

The denormalized context fields exist because of a second outside-voice
finding, same session: work_id "stability across pulls" is asserted in
ingest/mplads_adapter.py, never observed (there has been exactly one real
pull). If the portal ever re-issues WORK_RECOMMENDATION_DTL_IDs, an outcome
would otherwise orphan silently on the next re-pull with no way to
hand-rematch it to the work it was about.
"""

from __future__ import annotations

import math
from typing import Any

import duckdb
from fastapi import APIRouter, HTTPException
from nidhinetra_pipeline.outcomes import store
from pydantic import BaseModel

from .. import db
from ..models import Envelope
from ..policy import UNDER_IMPLEMENTATION, quota_for

router = APIRouter(prefix="/api/inspections", tags=["inspections"])

_CONTEXT_SELECT = """
    SELECT
        works.state, works.constituency, works.implementing_agency,
        works.work_category, works.sanctioned_amount_inr,
        scored.inspection_rank, scored.risk_score
    FROM works
    JOIN scored USING (work_id)
    WHERE works.work_id = ?
"""


class InspectionOutcomeRequest(BaseModel):
    """Plain pydantic model, not yet generated from
    contracts/inspection_outcome.schema.json -- the same deferred-codegen
    gap models.py's own docstring already names for the other three
    contracts (`make contracts` has not been run for this one either).
    `outcome` is deliberately typed `str`, not a hardcoded Literal of the
    six values: the schema file is the single source of truth for the
    enum, and store.record_outcome validates against it directly, so a
    future enum edit can't drift between two hand-maintained copies.
    """

    work_id: str
    inspected_on: str
    outcome: str
    notes: str = ""
    inspector_id: str
    in_control_sample: bool = False
    supersedes: int | None = None


def _lookup_work_context(con: duckdb.DuckDBPyConnection, work_id: str) -> dict[str, object]:
    """Everything this endpoint needs to know about one work, in one round
    trip: the denormalized context fields (state/constituency/agency/
    category/sanctioned_amount) plus the current rank and score. Raises
    404 for an unknown work_id -- the only validation this endpoint does
    against the request body itself.
    """
    rows = db.rows_as_dicts(con, _CONTEXT_SELECT, [work_id])
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No work found with id '{work_id}' in the current snapshot.",
        )
    return rows[0]


def _population_and_cutoff(con: duckdb.DuckDBPyConnection) -> tuple[int, int]:
    placeholders = ", ".join("?" for _ in UNDER_IMPLEMENTATION)
    rows = db.rows_as_dicts(
        con,
        f"SELECT COUNT(*) AS n FROM works WHERE completion_status IN ({placeholders})",
        list(UNDER_IMPLEMENTATION),
    )
    population_n = rows[0]["n"]
    # policy.quota_for owns the ceiling rule and the zero-population special
    # case (found live 2026-09-02: without it, a population of 0 renders a
    # nonsensical "at least 1 of 0 works").
    return population_n, quota_for(population_n)


@router.post("")
def record_inspection(payload: InspectionOutcomeRequest) -> Envelope:
    con = db.connect()
    context = _lookup_work_context(con, payload.work_id)
    population_n_at_time, cutoff_rank_at_time = _population_and_cutoff(con)

    try:
        outcome_id = store.record_outcome(
            work_id=payload.work_id,
            inspected_on=payload.inspected_on,
            outcome=payload.outcome,
            notes=payload.notes,
            inspector_id=payload.inspector_id,
            state=context["state"],
            constituency=context["constituency"],
            implementing_agency=context["implementing_agency"],
            work_category=context["work_category"],
            sanctioned_amount_inr=context["sanctioned_amount_inr"],
            inspection_rank_at_time=context["inspection_rank"],
            risk_score_at_time=context["risk_score"],
            cutoff_rank_at_time=cutoff_rank_at_time,
            population_n_at_time=population_n_at_time,
            in_control_sample=payload.in_control_sample,
            supersedes=payload.supersedes,
        )
    except store.UnknownOutcomeEnumError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except store.DuplicateOutcomeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return Envelope(
        success=True,
        data={
            "outcome_id": outcome_id,
            "work_id": payload.work_id,
            "inspected_on": payload.inspected_on,
            "outcome": payload.outcome,
            "notes": payload.notes,
            "inspector_id": payload.inspector_id,
            "inspection_rank_at_time": context["inspection_rank"],
            "risk_score_at_time": context["risk_score"],
            "cutoff_rank_at_time": cutoff_rank_at_time,
            "population_n_at_time": population_n_at_time,
            "in_control_sample": payload.in_control_sample,
            "supersedes": payload.supersedes,
        },
    )


# Reports page (2026-09-11). An issue rate is only shown for a group once it
# has this many inspections that actually reached the work; below that the
# rate is null and the page says how many more are needed. Thirty is the usual
# floor for a normal-approximation proportion, and the Wilson interval below
# stays honest well under it, so this errs on the side of saying nothing.
MIN_REACHED_PER_GROUP = 30

# Two-sided 95 percent normal quantile, for the Wilson score interval.
WILSON_Z = 1.959963984540054


def _wilson_interval(issues: int, n: int) -> tuple[float, float]:
    """Wilson score interval for issues out of n. Chosen over the plain
    normal interval because it never leaves [0, 1] and behaves at small n,
    which is exactly where an early inspection programme lives.
    """
    p = issues / n
    z2 = WILSON_Z * WILSON_Z
    denominator = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denominator
    margin = WILSON_Z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denominator
    return max(0.0, centre - margin), min(1.0, centre + margin)


def _group_summary(
    outcomes: list[dict[str, Any]], mapping: dict[str, bool | None]
) -> dict[str, Any]:
    """Counts for one group (the ranked list, or officer-marked spot-checks).
    "Reached the work" excludes outcomes the frozen _issue_mapping marks
    inconclusive (agency_unresponsive): no inspection of the work happened,
    so it belongs in neither the numerator nor the denominator.
    """
    reached = [o for o in outcomes if mapping.get(o["outcome"]) is not None]
    issues = sum(1 for o in reached if mapping[o["outcome"]])
    rate = None
    if reached and len(reached) >= MIN_REACHED_PER_GROUP:
        low, high = _wilson_interval(issues, len(reached))
        rate = {"value": issues / len(reached), "low": low, "high": high}
    return {
        "n": len(outcomes),
        "reached_work": len(reached),
        "issues": issues,
        "within_quota": sum(
            1 for o in outcomes if o["inspection_rank_at_time"] <= o["cutoff_rank_at_time"]
        ),
        "issue_rate": rate,
    }


@router.get("")
def list_inspections() -> Envelope:
    """Every recorded outcome, newest first, plus per-group counts for the
    Reports page. An outcome that a later entry explicitly supersedes is
    still listed (the record is append-only) but is flagged and left out of
    every count, so an amended inspection is never counted twice.
    """
    outcomes = sorted(store.list_all_outcomes(), key=lambda o: o["outcome_id"], reverse=True)
    superseded_ids = {o["supersedes"] for o in outcomes if o["supersedes"] is not None}
    for outcome in outcomes:
        outcome["superseded"] = outcome["outcome_id"] in superseded_ids
    current = [o for o in outcomes if not o["superseded"]]

    mapping = store.issue_mapping()
    ranked = _group_summary([o for o in current if not o["in_control_sample"]], mapping)
    spot_check = _group_summary([o for o in current if o["in_control_sample"]], mapping)
    return Envelope(
        success=True,
        data={
            "outcomes": outcomes,
            "summary": {
                "total": len(current),
                "ranked": ranked,
                "spot_check": spot_check,
                "min_reached_per_group": MIN_REACHED_PER_GROUP,
                "comparison_ready": (
                    ranked["issue_rate"] is not None and spot_check["issue_rate"] is not None
                ),
            },
        },
    )


__all__ = ["MIN_REACHED_PER_GROUP", "router"]
