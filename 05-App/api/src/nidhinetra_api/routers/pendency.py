"""GET /api/pendency (contracts/openapi.yaml, T4): the three MoSPI monthly
pendency checks over works under implementation, plus the District
Authority quota and third-party inspection figures for the same scope.

Scope-only (R3): state (repeatable), district_authority, constituency and
group_by, nothing else -- no paging, no free-text search, no flag/category/
vendor filter (those stay on /api/works). D10's reuse pattern for this
router is the entity_aliases/duplicates pair; the WHERE clause itself is
not re-derived here at all -- it reuses works._where verbatim (R3), the same
scope=under_implementation population /api/works already knows how to
filter by state, District Authority and constituency.

D4/D5: this never touches score, rank or flags, and never reports a
combined "any pendency" count -- only the three kinds, separately.
"""

from __future__ import annotations

import contextlib
import math
from typing import Annotated, Any, Literal

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query

from .. import db, policy, snapshot
from ..models import Envelope, WorksQuery
from . import works

router = APIRouter(prefix="/api/pendency", tags=["pendency"])

GroupBy = Literal["state", "district_authority", "constituency"]

_GROUP_COLUMNS: dict[str, str] = {
    "state": "works.state",
    "district_authority": "works.implementing_district_authority",
    "constituency": "works.constituency",
}

# MPLADS Guidelines 2023 clause 4.4.2: third-party inspection is compulsory
# for every work of Rs 25 lakh or more, and required for half (rounded up)
# of works between Rs 15 and 25 lakh (same clause strings.json's
# threshold_note/context_threshold already cite).
_THIRD_PARTY_FULL_INR = 2_500_000
_THIRD_PARTY_HALF_INR = 1_500_000

_AS_OF_MISSING_DETAIL = (
    "The pendency figures need a known as-of date, and the current snapshot does not have one yet."
)


def _pendency_scope_query(
    state: Annotated[list[str] | None, Query()] = None,
    district_authority: Annotated[str | None, Query(max_length=200)] = None,
    constituency: Annotated[str | None, Query(max_length=120)] = None,
) -> WorksQuery:
    states = [s.strip() for s in (state or []) if s and s.strip()]
    return WorksQuery(
        scope="under_implementation",
        states=states,
        district_authority=district_authority or None,
        constituency=constituency or None,
    )


def _kind_where(
    base_where: str, base_params: list[Any], kind: str, as_of: str
) -> tuple[str, list[Any]]:
    clause, clause_params = policy.pendency_clause(kind, as_of)
    return f"{base_where} AND ({clause})", [*base_params, *clause_params]


def _count_and_amount(
    con: duckdb.DuckDBPyConnection, con_where: str, con_params: list[Any]
) -> tuple[int, float]:
    row = db.rows_as_dicts(
        con,
        "SELECT COUNT(*) AS n, COALESCE(SUM(works.sanctioned_amount_inr), 0) AS inr "
        f"FROM works{con_where}",
        con_params,
    )[0]
    return int(row["n"]), round(float(row["inr"]), 2)


@router.get("")
def get_pendency(
    query: WorksQuery = Depends(_pendency_scope_query),  # noqa: B008
    group_by: Annotated[GroupBy | None, Query()] = None,
) -> Envelope:
    as_of = snapshot.data_as_of_date()
    if as_of is None:
        raise HTTPException(status_code=503, detail=_AS_OF_MISSING_DETAIL)

    where, params = works._where(query)

    with contextlib.closing(db.connect()) as con:
        population_n, population_inr = _count_and_amount(con, where, params)

        kinds: dict[str, Any] = {}
        for kind in policy.PENDENCY_KINDS:
            kind_where, kind_params = _kind_where(where, params, kind, as_of)
            count, sanctioned_inr = _count_and_amount(con, kind_where, kind_params)
            kind_data: dict[str, Any] = {"count": count, "sanctioned_inr": sanctioned_inr}
            if kind == "late_sanction":
                # Both-dates-present days-to-sanction over the whole scoped
                # population, not just the >45-day-late subset above --
                # confirmed against the committed snapshot (global-context.md
                # Verified numbers: median 90, not the 122 the late-only
                # subset gives).
                median_row = db.rows_as_dicts(
                    con,
                    "SELECT median(date_diff('day', CAST(works.recommendation_date AS DATE), "
                    "CAST(works.sanction_date AS DATE))) AS median_days FROM works"
                    f"{where} AND works.recommendation_date IS NOT NULL "
                    "AND works.sanction_date IS NOT NULL",
                    params,
                )[0]
                median = median_row["median_days"]
                kind_data["median_days_to_sanction"] = (
                    int(round(median)) if median is not None else None
                )
            kinds[kind] = kind_data

        da_rows = db.rows_as_dicts(
            con,
            "SELECT works.implementing_district_authority AS da, COUNT(*) AS n FROM works"
            f"{where} AND works.implementing_district_authority IS NOT NULL "
            "GROUP BY works.implementing_district_authority",
            params,
        )
        per_da_n = {row["da"]: int(row["n"]) for row in da_rows}
        district_authority_n = len(per_da_n)
        quota_sum = sum(policy.quota_by_group(per_da_n).values())

        third_party_row = db.rows_as_dicts(
            con,
            "SELECT "
            f"COALESCE(SUM(CASE WHEN works.sanctioned_amount_inr >= {_THIRD_PARTY_FULL_INR} "
            "THEN 1 ELSE 0 END), 0) AS a, "
            "COALESCE(SUM(CASE WHEN works.sanctioned_amount_inr >= "
            f"{_THIRD_PARTY_HALF_INR} AND works.sanctioned_amount_inr < {_THIRD_PARTY_FULL_INR} "
            "THEN 1 ELSE 0 END), 0) AS b "
            f"FROM works{where}",
            params,
        )[0]
        at_or_above_25_lakh = int(third_party_row["a"])
        between_15_and_25_lakh = int(third_party_row["b"])

        groups: list[dict[str, Any]] | None = None
        if group_by is not None:
            column = _GROUP_COLUMNS[group_by]
            pop_rows = db.rows_as_dicts(
                con,
                f"SELECT {column} AS group_value, COUNT(*) AS n FROM works{where} "
                f"AND {column} IS NOT NULL GROUP BY {column}",
                params,
            )
            by_group: dict[str, dict[str, Any]] = {
                row["group_value"]: {"population_n": int(row["n"])} for row in pop_rows
            }
            for kind in policy.PENDENCY_KINDS:
                kind_where, kind_params = _kind_where(where, params, kind, as_of)
                kind_rows = db.rows_as_dicts(
                    con,
                    f"SELECT {column} AS group_value, COUNT(*) AS n FROM works{kind_where} "
                    f"AND {column} IS NOT NULL GROUP BY {column}",
                    kind_params,
                )
                counts = {row["group_value"]: int(row["n"]) for row in kind_rows}
                for group_value, entry in by_group.items():
                    entry[kind] = counts.get(group_value, 0)
            groups = [
                {
                    "group": group_value,
                    "population_n": entry["population_n"],
                    "late_sanction": entry["late_sanction"],
                    "open_past_one_year": entry["open_past_one_year"],
                    "no_payment_90_days": entry["no_payment_90_days"],
                    "quota_n": policy.quota_for(entry["population_n"]),
                }
                for group_value, entry in by_group.items()
            ]
            groups.sort(key=lambda g: (-g["population_n"], g["group"]))

    return Envelope(
        success=True,
        data={
            "as_of": as_of,
            "population_n": population_n,
            "population_inr": population_inr,
            "kinds": kinds,
            "district_authority_n": district_authority_n,
            "quota_sum": quota_sum,
            "third_party": {
                "at_or_above_25_lakh": at_or_above_25_lakh,
                "between_15_and_25_lakh": between_15_and_25_lakh,
                "required_n": at_or_above_25_lakh + math.ceil(between_15_and_25_lakh / 2),
            },
            "groups": groups,
        },
    )


__all__ = ["router"]
