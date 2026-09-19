"""GET /api/graph (contracts/openapi.yaml). Reads data/snapshot/graph.json
(fund_flow_graph.schema.json shape) and returns a subset filtered by
`agency` and/or `vendor`.

The contract's own description just says "subset" without defining the
filter semantics, so this module fixes one concrete, defensible reading:
`agency`/`vendor` are case-insensitive substring matches against Agency /
Vendor node labels; the response is those matched nodes plus their direct
(one-hop) neighbors and the edges connecting them, which is what makes
the result a usable subgraph -- e.g. "show me this agency's MPs and
vendors" -- rather than a set of isolated, edge-less nodes. When neither
filter is given, the full graph is returned unfiltered. When a filter is
given but matches nothing, the response is an empty graph (200, not 404 --
contracts/openapi.yaml defines no 404 case for this endpoint).

F-01/F-02 legacy guard (decision D6 in the handoff): a graph.json whose edges
carry no work_ids, or whose snapshot has no implementing_district_authority
column, is never served under the current labels. The endpoint returns an
empty graph with meta.graph_status = "rebuild_required" instead, and
"current" otherwise.
"""

from __future__ import annotations

import contextlib
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from .. import db, graph_analysis
from ..models import (
    ClusterQuery,
    ConcentrationsQuery,
    Envelope,
    GraphQuery,
    cluster_query,
    concentrations_query,
    graph_query,
)

router = APIRouter(prefix="/api/graph", tags=["graph"])

# meta.graph_status values; web/lib/graph-data.ts reads them.
GRAPH_STATUS_CURRENT = "current"
GRAPH_STATUS_REBUILD_REQUIRED = "rebuild_required"


def _graph_is_legacy(graph: dict[str, Any]) -> bool:
    """True for a graph built before F-01 (its snapshot has no
    implementing_district_authority column, so its Agency nodes are District
    Authorities under the wrong name) or before F-02 (edges without work_ids
    cannot be checked for a real shared work).
    """
    if "implementing_district_authority" not in db.works_columns():
        return True
    return any("work_ids" not in edge for edge in graph.get("edges", []))


def _load_graph() -> dict[str, Any]:
    path = db.SNAPSHOT_DIR / "graph.json"
    return json.loads(path.read_text(encoding="utf-8"))


# T17/F-17b: (path, st_mtime_ns, st_size) -> (graph, vendor_concentrations, graph_totals).
# Computing vendor_concentrations over the whole national graph is the
# expensive part this task exists to stop paying for on every request; a
# rebuilt snapshot changes mtime/size, so a stale entry is never served, and
# clearing before inserting keeps exactly one entry rather than accumulating
# one per snapshot generation this process has ever seen.
_ANALYSIS_CACHE: dict[tuple[str, int, int], tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]] = {}


def _load_graph_analysis_cached() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    path = db.SNAPSHOT_DIR / "graph.json"
    stat = path.stat()
    key = (str(path), stat.st_mtime_ns, stat.st_size)
    cached = _ANALYSIS_CACHE.get(key)
    if cached is not None:
        return cached

    graph = json.loads(path.read_text(encoding="utf-8"))
    concentrations = graph_analysis.vendor_concentrations(graph)
    totals = graph_analysis.graph_totals(graph)
    _ANALYSIS_CACHE.clear()
    _ANALYSIS_CACHE[key] = (graph, concentrations, totals)
    return graph, concentrations, totals


def _matches(node: dict[str, Any], node_type: str, needle: str) -> bool:
    return node["type"] == node_type and needle in node["label"].lower()


def _filter_graph(
    graph: dict[str, Any], *, agency: str | None, vendor: str | None
) -> dict[str, Any]:
    if not agency and not vendor:
        return graph

    nodes = graph["nodes"]
    edges = graph["edges"]

    seed_ids: set[str] = set()
    if agency:
        needle = agency.lower()
        seed_ids |= {n["id"] for n in nodes if _matches(n, "Agency", needle)}
    if vendor:
        needle = vendor.lower()
        seed_ids |= {n["id"] for n in nodes if _matches(n, "Vendor", needle)}

    if not seed_ids:
        return {"nodes": [], "edges": []}

    kept_edges = [e for e in edges if e["source"] in seed_ids or e["target"] in seed_ids]
    kept_ids = set(seed_ids)
    for edge in kept_edges:
        kept_ids.add(edge["source"])
        kept_ids.add(edge["target"])
    kept_nodes = [n for n in nodes if n["id"] in kept_ids]
    return {"nodes": kept_nodes, "edges": kept_edges}


@router.get("/concentrations")
def get_concentrations(query: ConcentrationsQuery = Depends(concentrations_query)) -> Envelope:  # noqa: B008
    """T17/F-17b: the Fund Flow page's non-deep-link view. Returns only the
    top `limit` vendors and the totals it needs (matching_count over the
    WHOLE graph, not just the returned page, so the filter description
    stays honest even when more matches exist than are returned).
    """
    graph, concentrations, totals = _load_graph_analysis_cached()
    if _graph_is_legacy(graph):
        return Envelope(
            success=True,
            data={
                "vendors": [],
                "matching_count": 0,
                "total_vendor_count": 0,
                "median_member_count": 0,
                "totals": None,
            },
            meta={"graph_status": GRAPH_STATUS_REBUILD_REQUIRED},
        )
    matching = graph_analysis.matching_vendors(concentrations, query.min_members)
    return Envelope(
        success=True,
        data={
            "vendors": matching[: query.limit],
            "matching_count": len(matching),
            "total_vendor_count": len(concentrations),
            "median_member_count": graph_analysis.median_member_count(matching),
            "totals": totals,
        },
        meta={"graph_status": GRAPH_STATUS_CURRENT},
    )


def _work_facts(work_ids: list[str]) -> dict[str, dict[str, Any]]:
    """work_id -> sanctioned_amount_inr and the decoded scored flags, for exactly these works. A
    work id the snapshot does not hold is simply absent, which restrict_to_vendor_works counts as
    Rs 0 and unflagged.
    """
    if not work_ids:
        return {}
    marks = ", ".join("?" for _ in work_ids)
    with contextlib.closing(db.connect()) as con:
        rows = db.rows_as_dicts(
            con,
            "SELECT works.work_id, works.sanctioned_amount_inr, scored.flags "
            f"FROM works LEFT JOIN scored USING (work_id) WHERE works.work_id IN ({marks})",
            work_ids,
        )
    return {row["work_id"]: row for row in db.decode_scored_json(rows, columns=("flags",))}


@router.get("/cluster")
def get_cluster(query: ClusterQuery = Depends(cluster_query)) -> Envelope:  # noqa: B008
    """T17/F-17b: one vendor's own evidence-backed cluster, fetched on
    demand instead of narrowing it out of an already-downloaded national
    graph.

    Inside a cluster an MP -> Agency edge carries only the works that agency paid to this
    vendor (graph_analysis.restrict_to_vendor_works), so at every agency the MP side adds up
    to the vendor side. GET /api/graph, which the ?agency= deep link uses, still returns whole
    edges.
    """
    graph, _concentrations, _totals = _load_graph_analysis_cached()
    if _graph_is_legacy(graph):
        return Envelope(
            success=True,
            data={"nodes": [], "edges": []},
            meta={"graph_status": GRAPH_STATUS_REBUILD_REQUIRED},
        )
    vendor_ids = {n["id"] for n in graph["nodes"] if n["type"] == "Vendor"}
    if query.vendor_id not in vendor_ids:
        raise HTTPException(
            status_code=404,
            detail=f"No vendor found with id '{query.vendor_id}' in the current graph.",
        )
    subgraph = graph_analysis.subgraph_for(graph, {query.vendor_id})
    paid_work_ids = sorted(
        {w for e in subgraph["edges"] if e["target"] == query.vendor_id for w in e["work_ids"]}
    )
    cluster = graph_analysis.restrict_to_vendor_works(subgraph, _work_facts(paid_work_ids))
    return Envelope(success=True, data=cluster, meta={"graph_status": GRAPH_STATUS_CURRENT})


@router.get("")
def get_graph(query: GraphQuery = Depends(graph_query)) -> Envelope:  # noqa: B008
    graph = _load_graph()
    if _graph_is_legacy(graph):
        return Envelope(
            success=True,
            data={"nodes": [], "edges": []},
            meta={"graph_status": GRAPH_STATUS_REBUILD_REQUIRED},
        )
    filtered = _filter_graph(graph, agency=query.agency, vendor=query.vendor)
    return Envelope(success=True, data=filtered, meta={"graph_status": GRAPH_STATUS_CURRENT})


__all__ = [
    "GRAPH_STATUS_CURRENT",
    "GRAPH_STATUS_REBUILD_REQUIRED",
    "router",
]
