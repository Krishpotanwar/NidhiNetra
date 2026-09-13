"""GET /api/works, GET /api/works/facets and GET /api/works/{work_id}
(contracts/openapi.yaml).

Both record endpoints return the *merged* normalized + scored record (all of
contract 3.1's fields plus contract 3.2's), not a bare 3.2 record. The
work-detail endpoint's own contract already demands the merge ("full
detail... merged normalized + scored record"); the list endpoint follows
the same shape for two reasons: web/lib/types.ts's InspectionRow (the type
every A5 component actually renders) is exactly this merge, spread from
NormalizedRecord and RiskScoredRecord, and state/category -- the two
filters that need those normalized fields at all -- would be unfilterable
from a bare 3.2 payload.

2026-09-11, for the redesigned Inspection List: scope, a repeatable state
filter, the flag filter and a text search are all pushed into DuckDB, and the
response meta carries the filtered quota and flag counts. The browser now
pages through the national queue instead of downloading one page and
filtering it, which is what used to make a state absent from page one
unreachable (ultra-review F05). JSON columns are decoded only for the page
actually returned.

Gap deferred to `make contracts`: the merged record has no generated
pydantic/TypeScript model to validate against yet (models.py's module
docstring). Every row here is a plain dict straight from
db.rows_as_dicts(), decoded through db.decode_scored_json().
"""

from __future__ import annotations

import contextlib
from collections import Counter
from collections.abc import Sequence
from typing import Any

import duckdb
from fastapi import APIRouter, Depends, HTTPException
from nidhinetra_pipeline.risk import rank
from nidhinetra_pipeline.risk.peer_groups import financial_year_of

from .. import db
from ..models import Envelope, WorksQuery, works_query
from ..policy import UNDER_IMPLEMENTATION, quota_for

router = APIRouter(prefix="/api/works", tags=["works"])

# scored.* lists work_id, inspection_rank, risk_score, flags, why_flagged,
# peer_group (risk_scored_record.schema.json); work_id is already covered
# by works.*, hence the explicit column list rather than `scored.*` (which
# would collide on work_id when the two result columns are zipped into one
# dict by db.rows_as_dicts()).
_MERGED_SELECT = """
    SELECT
        works.work_id, works.state, works.constituency, works.mp_name,
        works.tenure, works.implementing_agency, works.vendor_name,
        works.work_category, works.sanctioned_amount_inr,
        works.expenditure_amount_inr, works.sanction_date,
        works.completion_status, works.last_updated, works.source_rung,
        scored.inspection_rank, scored.risk_score, scored.flags,
        scored.why_flagged, scored.peer_group
    FROM works
    JOIN scored USING (work_id)
"""

# The fields an officer would type into the header search: a work ID read off
# a file, a constituency, an agency, an MP, a state or a vendor.
_SEARCH_COLUMNS = (
    "works.work_id",
    "works.constituency",
    "works.implementing_agency",
    "works.mp_name",
    "works.state",
    "works.vendor_name",
)

# flags is JSON text in scored.parquet (db.JSON_ENCODED_SCORED_COLUMNS), so
# the flag filter and counts decode it inside DuckDB.
_FLAGS_AS_LIST = "from_json(scored.flags, '[\"VARCHAR\"]')"


def _placeholders(values: Sequence[Any]) -> str:
    return ", ".join("?" for _ in values)


def _population_clause() -> tuple[str, list[Any]]:
    return (
        f"works.completion_status IN ({_placeholders(UNDER_IMPLEMENTATION)})",
        list(UNDER_IMPLEMENTATION),
    )


def _where(query: WorksQuery) -> tuple[str, list[Any]]:
    """Every filter except year, as one parameterised WHERE clause. Year has
    no column (normalized_record.schema.json has only sanction_date), so it
    is derived afterwards with peer_groups.financial_year_of(), the exact
    function the risk engine uses to key peer groups, rather than re-deriving
    that rule a second time in SQL.
    """
    clauses: list[str] = []
    params: list[Any] = []
    if query.scope == "under_implementation":
        clause, clause_params = _population_clause()
        clauses.append(clause)
        params.extend(clause_params)
    if query.states:
        clauses.append(f"works.state IN ({_placeholders(query.states)})")
        params.extend(query.states)
    if query.category:
        clauses.append("works.work_category = ?")
        params.append(query.category)
    if query.flag:
        clauses.append(f"list_contains({_FLAGS_AS_LIST}, ?)")
        params.append(query.flag)
    if query.q:
        # strpos rather than LIKE: an officer who types "%" or "_" means those
        # characters, not "match anything".
        needle = query.q.lower()
        matches = [f"strpos(lower(coalesce({c}, '')), ?) > 0" for c in _SEARCH_COLUMNS]
        clauses.append("(" + " OR ".join(matches) + ")")
        params.extend([needle] * len(_SEARCH_COLUMNS))
    return (" WHERE " + " AND ".join(clauses) if clauses else ""), params


def _ordered_population(
    con: duckdb.DuckDBPyConnection, query: WorksQuery
) -> list[dict[str, Any]]:
    """The whole filtered set in inspection_rank order, carrying only what
    the year filter, the counts and pagination need. Always sorted by
    inspection_rank: "Filters narrow the set, never change the sort"
    (contracts/openapi.yaml).
    """
    where, params = _where(query)
    rows = db.rows_as_dicts(
        con,
        "SELECT works.work_id, works.sanction_date, works.last_updated, "
        f"len({_FLAGS_AS_LIST}) > 0 AS is_flagged "
        f"FROM works JOIN scored USING (work_id){where} "
        "ORDER BY scored.inspection_rank ASC",
        params,
    )
    if query.year:
        rows = [r for r in rows if financial_year_of(r) == query.year]
    return rows


def _fetch_merged_by_ids(
    con: duckdb.DuckDBPyConnection, work_ids: list[str]
) -> list[dict[str, Any]]:
    if not work_ids:
        return []
    rows = db.rows_as_dicts(
        con,
        f"{_MERGED_SELECT} WHERE works.work_id IN ({_placeholders(work_ids)}) "
        "ORDER BY scored.inspection_rank ASC",
        list(work_ids),
    )
    return db.decode_scored_json(rows)


@router.get("")
def list_works(query: WorksQuery = Depends(works_query)) -> Envelope:  # noqa: B008
    with contextlib.closing(db.connect()) as con:
        ordered = _ordered_population(con, query)
        start = (query.page - 1) * query.page_size
        page_ids = [r["work_id"] for r in ordered[start : start + query.page_size]]
        page_rows = _fetch_merged_by_ids(con, page_ids)

    total = len(ordered)
    # The quota is a statement about the District Authority population, so
    # it is only reported when the request is scoped to that population.
    quota_n = quota_for(total) if query.scope == "under_implementation" else None
    return Envelope(
        success=True,
        data=page_rows,
        meta={
            "page": query.page,
            "page_size": query.page_size,
            "total": total,
            "total_pages": -(-total // query.page_size) if total else 0,
            "quota_n": quota_n,
            "flagged_total": sum(1 for r in ordered if r["is_flagged"]),
            "flagged_beyond_quota": (
                sum(1 for r in ordered[quota_n:] if r["is_flagged"])
                if quota_n is not None
                else None
            ),
        },
    )


@router.get("/facets")
def work_facets() -> Envelope:
    """Filter options with counts, over the whole quota population. Declared
    before /{work_id} so "facets" is never read as a work ID.

    The flag list is every detector rank.py knows, in its own order, even one
    that never fired: a filter that silently lost an option would read as the
    product having fewer detectors than it does.
    """
    population, params = _population_clause()
    with contextlib.closing(db.connect()) as con:
        states = db.rows_as_dicts(
            con,
            f"SELECT state AS value, COUNT(*) AS count FROM works WHERE {population} "
            "GROUP BY state ORDER BY state",
            params,
        )
        categories = db.rows_as_dicts(
            con,
            f"SELECT work_category AS value, COUNT(*) AS count FROM works WHERE {population} "
            "GROUP BY work_category ORDER BY work_category",
            params,
        )
        dated = db.rows_as_dicts(
            con, f"SELECT sanction_date, last_updated FROM works WHERE {population}", params
        )
        flag_rows = db.rows_as_dicts(
            con,
            f"SELECT flag, COUNT(*) AS count FROM ("
            f"  SELECT unnest({_FLAGS_AS_LIST}) AS flag"
            f"  FROM works JOIN scored USING (work_id) WHERE {population}"
            ") GROUP BY flag",
            params,
        )

    years = Counter(year for year in (financial_year_of(r) for r in dated) if year)
    flag_counts = {r["flag"]: int(r["count"]) for r in flag_rows}
    return Envelope(
        success=True,
        data={
            "states": states,
            "years": [{"value": y, "count": n} for y, n in sorted(years.items(), reverse=True)],
            "categories": categories,
            "flags": [{"value": f, "count": flag_counts.get(f, 0)} for f in rank.FLAG_WEIGHTS],
        },
    )


@router.get("/{work_id}")
def get_work(work_id: str) -> Envelope:
    with contextlib.closing(db.connect()) as con:
        rows = db.rows_as_dicts(con, _MERGED_SELECT + " WHERE works.work_id = ?", [work_id])
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No work found with id '{work_id}' in the current snapshot.",
        )
    record = db.decode_scored_json(rows)[0]
    return Envelope(success=True, data=record)


__all__ = ["router"]
