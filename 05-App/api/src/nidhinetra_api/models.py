"""Pydantic models for the house response envelope and query params.

Deliberately does NOT define models for the record shapes themselves
(NormalizedRecord, RiskScoredRecord, FundFlowGraph) -- see the module
docstring on that gap in `routers/works.py`. `make contracts` (the
datamodel-codegen target in the root Makefile) is meant to generate those
into `generated/` from contracts/*.schema.json, and it has not been run
yet. Wiring `make contracts` output in is follow-up work, not something
to block this pass on; see the final report for the explicit call-out.
Until then, every record in an envelope's `data` is a plain dict read
straight out of DuckDB (`rows_as_dicts()` in db.py), typed here as `Any`.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import Query
from pydantic import BaseModel, Field


class Envelope(BaseModel):
    """The house response envelope (coding-style rules): every endpoint,
    success or error, returns exactly this shape. `data` is nullable on
    error, `error` is nullable on success, `meta` carries pagination info
    (or is omitted) and is nullable whenever there is nothing to report.
    """

    success: bool
    data: Any = None
    error: str | None = None
    meta: dict[str, Any] | None = None


WorksScope = Literal["all", "under_implementation"]


class WorksQuery(BaseModel):
    """Query params for GET /api/works. Filters narrow the result set;
    they never change the sort -- inspection_rank ascending is not one of
    these fields because it is not optional (contracts/openapi.yaml).

    2026-09-11: `states` is repeatable (the Inspection List's state filter is
    multi-select), `q` is a plain-text search, and `scope` restricts the set
    to the District Authority quota population. `scope` defaults to "all" so
    every existing caller keeps its old behaviour.
    """

    states: list[str] = Field(default_factory=list)
    year: str | None = None
    category: str | None = None
    flag: str | None = None
    vendor_id: str | None = None
    q: str | None = None
    scope: WorksScope = "all"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


def works_query(
    state: Annotated[list[str] | None, Query()] = None,
    year: str | None = None,
    category: str | None = None,
    flag: str | None = None,
    vendor_id: Annotated[str | None, Query(max_length=64)] = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    scope: Annotated[WorksScope, Query()] = "all",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> WorksQuery:
    """FastAPI dependency: builds WorksQuery from individual query params
    (rather than depending on FastAPI's pydantic-model-as-query-params
    support, which is version-sensitive) so validation errors (e.g.
    page_size=500, scope=everything) come back as FastAPI's normal 422,
    caught by the envelope-shaping handler in main.py. Blank values are
    dropped here, so "state=&q=  " means no filter rather than a filter
    that matches nothing.
    """
    states = [s.strip() for s in (state or []) if s and s.strip()]
    search = q.strip() if q and q.strip() else None
    return WorksQuery(
        states=states,
        year=year or None,
        category=category or None,
        flag=flag or None,
        vendor_id=vendor_id or None,
        q=search,
        scope=scope,
        page=page,
        page_size=page_size,
    )


class GraphQuery(BaseModel):
    """Query params for GET /api/graph."""

    agency: str | None = None
    vendor: str | None = None


def graph_query(
    agency: Annotated[str | None, Query(max_length=120)] = None,
    vendor: Annotated[str | None, Query(max_length=120)] = None,
) -> GraphQuery:
    return GraphQuery(agency=agency, vendor=vendor)


AliasStatus = Literal["pending", "confirmed_merge", "rejected_distinct"]


class AliasQuery(BaseModel):
    """Pagination and current-status filter for the R-06 review queue."""

    status: AliasStatus = "pending"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


def alias_query(
    status: Annotated[AliasStatus, Query()] = "pending",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> AliasQuery:
    return AliasQuery(status=status, page=page, page_size=page_size)


__all__ = [
    "AliasQuery",
    "AliasStatus",
    "Envelope",
    "GraphQuery",
    "WorksQuery",
    "WorksScope",
    "alias_query",
    "graph_query",
    "works_query",
]
