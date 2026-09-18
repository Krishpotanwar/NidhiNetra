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

cutoff_rank_at_time / population_n_at_time / inspection_rank_at_time
together freeze a work's rank against a genuinely comparable population and
cutoff, because two separate mismatches would otherwise corrupt any later
precision-at-quota calculation:

- inspection_rank (rank.py, all 79,068 works, completed and recommended
  included, Checkpoints CP2) is drawn from a different, larger population
  than any quota cutoff, which only ever covers works under implementation
  (2026-09-05 outside-voice finding). Freezing the raw global rank next to
  an under-implementation-scoped cutoff, as this endpoint did until
  2026-09-13, made the two numbers reproducible but still not comparable --
  a work ranked, say, 5000th nationally could still be the single
  highest-priority under-implementation work in its own district.
- Clause 4.5.2 is a per-District-Authority obligation, not a national one
  (F-03, nemotronreview.md): a district with zero of its own works
  inspected this year is a real compliance gap even when the national
  aggregate looks satisfied by some other district's surplus.

_district_population_and_rank() below fixes both at once (2026-09-14):
population_n_at_time and cutoff_rank_at_time are this work's own District
Authority's (works.implementing_district_authority since F-01) under-implementation
population and policy.quota_for() of it, not the national ones, and
inspection_rank_at_time is this work's rank strictly within that same
district-scoped population, re-deriving rank.py's own tie-break (risk_score
descending, work_id ascending) in SQL rather than reading the unrelated global
scored.inspection_rank value. The two figures are now drawn from the same
population by construction, so inspection_rank_at_time <= cutoff_rank_at_time
(the Reports page's within_quota check, _group_summary below) is finally a
true apples-to-apples comparison.

The denormalized context fields exist because of a second outside-voice
finding, same session: work_id "stability across pulls" is asserted in
ingest/mplads_adapter.py, never observed (there has been exactly one real
pull). If the portal ever re-issues WORK_RECOMMENDATION_DTL_IDs, an outcome
would otherwise orphan silently on the next re-pull with no way to
hand-rematch it to the work it was about.

in_control_sample, the comparison-group flag, is also server-owned (F-09,
fixed with Next Step 6): _server_control_assignment() decides it, and a
client-sent value is ignored. Until the R-05 assignment registry exists, every
outcome joins the ranked group.
"""

from __future__ import annotations

import contextlib
import math
from datetime import date, datetime, timedelta, timezone
from typing import Any

import duckdb
from fastapi import APIRouter, HTTPException
from nidhinetra_pipeline.outcomes import store
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .. import db
from ..models import Envelope
from ..policy import UNDER_IMPLEMENTATION, quota_for

router = APIRouter(prefix="/api/inspections", tags=["inspections"])

# India has no daylight saving, so a fixed +05:30 offset is exact and needs no
# timezone database. "Today" for an inspection date is the officer's date.
_IST = timezone(timedelta(hours=5, minutes=30))

_CONTEXT_SELECT = """
    SELECT
        works.state, works.constituency, works.implementing_district_authority,
        works.implementing_agency, works.work_category,
        works.sanctioned_amount_inr, scored.risk_score
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

    F-10 (nemotronreview.md): strict input even in demo mode. Whitespace is
    trimmed, sizes are capped, inspected_on must be a real date no later than
    today in India, and supersedes must be a positive id. Violations are 422s
    through main.py's envelope handler.
    """

    # F-09: a client may not choose the comparison group. Unknown fields,
    # including an old frontend's in_control_sample, are ignored rather than
    # rejected, so that frontend keeps working while the server decides.
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    work_id: str = Field(min_length=1, max_length=64)
    inspected_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    outcome: str
    notes: str = Field(default="", max_length=2000)
    inspector_id: str = Field(min_length=1, max_length=40)
    supersedes: int | None = Field(default=None, ge=1)

    @field_validator("inspected_on")
    @classmethod
    def _a_real_date_not_in_the_future(cls, value: str) -> str:
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("inspected_on must be a real calendar date (YYYY-MM-DD)") from exc
        if parsed > datetime.now(_IST).date():
            raise ValueError("inspected_on cannot be later than today (India time)")
        return value


def _server_control_assignment(work_id: str) -> bool:
    """F-09 (nemotronreview.md): whether this work belongs to a pre-assigned
    random comparison sample is decided here, by the server, and is never
    accepted from the client. No assignment registry exists yet (R-05, in the
    design backlog), so no work is a comparison-sample assignment and every
    recorded outcome joins the ranked group. Tests monkeypatch this function to
    exercise the spot-check grouping; R-05 replaces its body.
    """
    return False


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


def _district_population_and_rank(
    con: duckdb.DuckDBPyConnection,
    district_authority: str | None,
    risk_score: float,
    work_id: str,
) -> tuple[int, int, int]:
    """This work's District Authority's under-implementation population,
    this work's rank strictly within that population, and that district's
    own quota (F-03/F-04, 2026-09-14 -- see the module docstring). Recording
    an outcome does not require the work itself to be under implementation
    (an officer may verify a Completed work too), so district_rank is
    computed as "where this work WOULD fall" among its district's
    under-implementation peers by risk_score, rather than left undefined for
    a work outside that population.

    F-01: grouped by works.implementing_district_authority (IDA_NAME). Until
    F-01 the grouping used works.implementing_agency, which held IDA_NAME
    values at the time; that column now means the executing agency.

    district_authority is compared with an explicit IS NULL branch, not a
    parameterised `= ?`, because SQL's `NULL = NULL` is UNKNOWN, not true --
    a plain `=?` would silently and wrongly report population 0 for every
    work with a null authority instead of grouping them together.
    """
    if district_authority is None:
        agency_clause, agency_params = "works.implementing_district_authority IS NULL", []
    else:
        agency_clause, agency_params = (
            "works.implementing_district_authority = ?",
            [district_authority],
        )
    placeholders = ", ".join("?" for _ in UNDER_IMPLEMENTATION)

    population_rows = db.rows_as_dicts(
        con,
        f"SELECT COUNT(*) AS n FROM works "
        f"WHERE {agency_clause} AND completion_status IN ({placeholders})",
        [*agency_params, *UNDER_IMPLEMENTATION],
    )
    population_n = population_rows[0]["n"]

    # Same tie-break as rank.py's assign_ranks (risk_score descending,
    # work_id ascending), re-applied here rather than imported: that
    # function ranks a Python list already in memory, and re-running it over
    # every under-implementation work on every POST would be real, avoidable
    # work this single COUNT already does inside DuckDB.
    better_rows = db.rows_as_dicts(
        con,
        f"SELECT COUNT(*) AS n FROM works JOIN scored USING (work_id) "
        f"WHERE {agency_clause} AND works.completion_status IN ({placeholders}) "
        "AND (scored.risk_score > ? OR (scored.risk_score = ? AND works.work_id < ?))",
        [*agency_params, *UNDER_IMPLEMENTATION, risk_score, risk_score, work_id],
    )
    district_rank = better_rows[0]["n"] + 1

    # policy.quota_for owns the ceiling rule and the zero-population special
    # case (found live 2026-09-02: without it, a population of 0 renders a
    # nonsensical "at least 1 of 0 works").
    return population_n, district_rank, quota_for(population_n)


@router.post("")
def record_inspection(payload: InspectionOutcomeRequest) -> Envelope:
    with contextlib.closing(db.connect()) as con:
        context = _lookup_work_context(con, payload.work_id)
        population_n_at_time, inspection_rank_at_time, cutoff_rank_at_time = (
            _district_population_and_rank(
                con,
                context["implementing_district_authority"],
                context["risk_score"],
                payload.work_id,
            )
        )

    in_control_sample = _server_control_assignment(payload.work_id)
    try:
        outcome_id = store.record_outcome(
            work_id=payload.work_id,
            inspected_on=payload.inspected_on,
            outcome=payload.outcome,
            notes=payload.notes,
            inspector_id=payload.inspector_id,
            state=context["state"],
            constituency=context["constituency"],
            implementing_district_authority=context["implementing_district_authority"],
            implementing_agency=context["implementing_agency"],
            work_category=context["work_category"],
            sanctioned_amount_inr=context["sanctioned_amount_inr"],
            inspection_rank_at_time=inspection_rank_at_time,
            risk_score_at_time=context["risk_score"],
            cutoff_rank_at_time=cutoff_rank_at_time,
            population_n_at_time=population_n_at_time,
            in_control_sample=in_control_sample,
            supersedes=payload.supersedes,
        )
    except store.UnknownOutcomeEnumError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except store.DuplicateOutcomeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except store.InvalidSupersedesError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except store.AlreadySupersededError as exc:
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
            "inspection_rank_at_time": inspection_rank_at_time,
            "risk_score_at_time": context["risk_score"],
            "cutoff_rank_at_time": cutoff_rank_at_time,
            "population_n_at_time": population_n_at_time,
            "in_control_sample": in_control_sample,
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
