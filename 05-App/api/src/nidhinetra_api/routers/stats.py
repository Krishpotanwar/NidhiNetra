"""GET /api/stats/summary (contracts/openapi.yaml): the four summary-strip
figures plus data_as_of.

Scoped to the "works under implementation" population -- completion_status
in (Sanctioned, In Progress) -- matching web/lib/data.ts's
isUnderImplementation exactly (04 Prototype/Logbook.md, 2026-08-31: "Works
under implementation = sanctioned minus completed"). This is a deliberate
choice, not the only reading of contracts/openapi.yaml's terse field list:
scoping every figure to the same population the table above them shows is
what keeps the summary strip and the table from ever silently disagreeing.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter

from .. import db, snapshot
from ..models import Envelope
from ..policy import UNDER_IMPLEMENTATION

router = APIRouter(prefix="/api/stats", tags=["stats"])


_SUMMARY_SELECT = """
    SELECT
        works.completion_status, works.state, works.constituency,
        works.sanctioned_amount_inr,
        works.expenditure_amount_inr, works.sanction_date, works.last_updated,
        scored.flags
    FROM works
    JOIN scored USING (work_id)
"""


def _months_between(from_iso: str, to_iso: str) -> int:
    """Whole calendar months from `from_iso` to `to_iso`, both YYYY-MM-DD.
    Matches web/lib/data.ts's monthsBetween exactly (year/month diff, not a
    day-granular count), so "idle beyond 12 months" means the same thing on
    both sides once A6 wires the frontend to this endpoint.
    """
    f = date.fromisoformat(from_iso)
    t = date.fromisoformat(to_iso)
    return (t.year - f.year) * 12 + (t.month - f.month)


@router.get("/summary")
def get_summary() -> Envelope:
    con = db.connect()
    rows = db.rows_as_dicts(con, _SUMMARY_SELECT)
    rows = db.decode_scored_json(rows, columns=("flags",))

    under_impl = [r for r in rows if r["completion_status"] in UNDER_IMPLEMENTATION]
    flagged = [r for r in under_impl if r["flags"]]

    # "As of" reference for the 12-month idle check: the freshest
    # last_updated across the whole snapshot, same as getAsOfDate() in
    # web/lib/data.ts. Deliberately not manifest.data_as_of -- that is the
    # snapshot's own generation timestamp, reported separately below, not
    # a claim about how current any individual record's data is.
    as_of_ref = max((r["last_updated"] for r in rows), default=None)

    idle = [
        r
        for r in under_impl
        if r["expenditure_amount_inr"] == 0
        and r["sanction_date"] is not None
        and as_of_ref is not None
        and _months_between(r["sanction_date"], as_of_ref) > 12
    ]

    manifest = snapshot.read_manifest()
    data_as_of = manifest["data_as_of"] if manifest else None

    data: dict[str, Any] = {
        "works_under_implementation": len(under_impl),
        "flagged_count": len(flagged),
        "total_flagged_amount_inr": round(
            sum(r["sanctioned_amount_inr"] for r in flagged), 2
        ),
        "idle_beyond_12_months_amount_inr": round(
            sum(r["sanctioned_amount_inr"] for r in idle), 2
        ),
        # The three below exist so the summary strip's context lines ("N of M
        # works", "X%") can be rendered from whole-dataset truth. Added
        # 2026-09-04: the frontend previously derived every figure from the
        # page of rows it had fetched, which was correct while the CP0
        # fixture's 20 rows fitted in one page and became a false statement
        # the moment rung 1 landed 79,068 -- the strip read "200 works under
        # implementation, 200 flagged, 100%" against a real 44,810 and
        # 18,093. A summary computed over a page is not a summary.
        "total_works_all_statuses": len(rows),
        "idle_work_count": len(idle),
        "total_sanctioned_under_implementation_inr": round(
            sum(r["sanctioned_amount_inr"] for r in under_impl), 2
        ),
        # Coverage behind the Dashboard's first figure, over the same
        # population as works_under_implementation. Added 2026-09-11.
        "state_count": len({r["state"] for r in under_impl}),
        "constituency_count": len({r["constituency"] for r in under_impl}),
        "data_as_of": data_as_of,
    }
    return Envelope(success=True, data=data)


__all__ = ["UNDER_IMPLEMENTATION", "router"]
