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
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends

from .. import db
from ..models import Envelope, GraphQuery, graph_query

router = APIRouter(prefix="/api/graph", tags=["graph"])


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
    filtered = _filter_graph(graph, agency=query.agency, vendor=query.vendor)
    return Envelope(success=True, data=filtered)


__all__ = ["router"]
