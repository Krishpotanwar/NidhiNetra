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

import json
from typing import Any

from fastapi import APIRouter, Depends

from .. import db
from ..models import Envelope, GraphQuery, graph_query

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
