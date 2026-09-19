"""Server-side vendor concentration and cluster extraction (F-17, part b /
task T17). A line-for-line port of web/lib/vendor-concentration.ts and
web/lib/graph-data.ts's graphTotals -- those TS files are the reference this
module must match exactly, including F-02's shared-work rule (an MP is
credited to a vendor, or kept in a cluster, only when a real work_id backs
both the MP -> Agency hop and the Agency -> Vendor hop; sharing only an
agency is not a fund-flow path).

Exists so the Fund Flow page's non-deep-link view no longer has to download
and parse the whole national graph.json (about 10 MB) client-side just to
show its 25 most concentrated vendors and one cluster -- see
`docs/designs/nemotron-audit-remediation.md`'s F-17 finding and
`SIHGit/tasks/T17-F17b-server-side-concentration.md`.

`graph` throughout is graph.json's own shape: {"nodes": [...], "edges": [...]},
each node a dict with "id"/"type"/"label", each edge a dict with
"source"/"target"/"work_count"/"total_amount_inr"/"flagged_work_count"/
"work_ids" -- read directly off the JSON, not a typed model (routers/graph.py
already reads graph.json the same untyped way).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

Graph = dict[str, Any]
Node = dict[str, Any]
Edge = dict[str, Any]


def _has_shared_work(a: set[str], b: set[str]) -> bool:
    smaller, larger = (a, b) if len(a) <= len(b) else (b, a)
    return any(work_id in larger for work_id in smaller)


def vendor_concentrations(graph: Graph) -> list[dict[str, Any]]:
    """One entry per Vendor node, regardless of any threshold -- filtering is
    `matching_vendors`'s job. Mirrors allVendorConcentrations exactly,
    including the two new fields (agency_count, flagged_work_count) added
    to the TS reference alongside the ribbon-chart Fund Flow redesign this
    task ships against -- the TS file, as it stands today, is the contract.
    """
    by_id: dict[str, Node] = {n["id"]: n for n in graph["nodes"]}

    # agency id -> (mp id -> that MP's own work_ids into this agency).
    mp_work_ids_of_agency: dict[str, dict[str, set[str]]] = {}
    # vendor id -> every Agency -> Vendor edge into it.
    agency_edges_into_vendor: dict[str, list[Edge]] = {}
    for edge in graph["edges"]:
        source = by_id.get(edge["source"])
        target = by_id.get(edge["target"])
        if source and source["type"] == "MP" and target and target["type"] == "Agency":
            by_mp = mp_work_ids_of_agency.setdefault(edge["target"], {})
            by_mp[edge["source"]] = set(edge["work_ids"])
        elif source and source["type"] == "Agency":
            agency_edges_into_vendor.setdefault(edge["target"], []).append(edge)

    result: list[dict[str, Any]] = []
    for vendor in graph["nodes"]:
        if vendor["type"] != "Vendor":
            continue
        members: set[str] = set()
        agencies: set[str] = set()
        work_count = 0
        paid_inr = 0.0
        flagged_work_count = 0
        for edge in agency_edges_into_vendor.get(vendor["id"], []):
            agencies.add(edge["source"])
            work_count += edge["work_count"]
            paid_inr += edge["total_amount_inr"]
            flagged_work_count += edge["flagged_work_count"]

            agency_vendor_work_ids = set(edge["work_ids"])
            for mp_id, mp_work_ids in mp_work_ids_of_agency.get(edge["source"], {}).items():
                if _has_shared_work(mp_work_ids, agency_vendor_work_ids):
                    members.add(mp_id)

        result.append(
            {
                "vendor_id": vendor["id"],
                "vendor_label": vendor["label"],
                "member_count": len(members),
                "agency_count": len(agencies),
                "work_count": work_count,
                "sanctioned_inr": round(paid_inr, 2),
                "flagged_work_count": flagged_work_count,
            }
        )
    return result


def matching_vendors(concentrations: list[dict[str, Any]], threshold: int) -> list[dict[str, Any]]:
    """Vendors meeting `threshold`, ranked by member_count descending, ties
    broken by vendor_label ascending (Python str order, matching TS's
    localeCompare for the plain-ASCII labels this graph carries)."""
    matched = [v for v in concentrations if v["member_count"] >= threshold]
    return sorted(matched, key=lambda v: (-v["member_count"], v["vendor_label"]))


def median_member_count(vendors: list[dict[str, Any]]) -> int:
    """The middle member_count of a non-empty list, even-length lists
    averaging their two middle values, rounded **half up** -- Python's
    round() rounds half to even (banker's rounding), which silently
    disagrees with JS's Math.round on exact .5 values, so this uses
    floor(x + 0.5) instead, per the task card's own instruction.
    """
    if not vendors:
        return 0
    counts = sorted(v["member_count"] for v in vendors)
    mid = len(counts) // 2
    if len(counts) % 2 == 0:
        median = (counts[mid - 1] + counts[mid]) / 2
    else:
        median = counts[mid]
    return math.floor(median + 0.5)


def subgraph_for(graph: Graph, vendor_ids: set[str]) -> Graph:
    """The subgraph reachable from `vendor_ids`: those vendors, every agency
    with a direct edge into one of them, and every MP with a direct edge
    into one of those agencies on a work_id that agency actually used to
    reach one of `vendor_ids` -- an exact port of subgraphFor, including
    the cross-branch edge filter (F-02).
    """
    by_id: dict[str, Node] = {n["id"]: n for n in graph["nodes"]}

    # agency id -> the union of work_ids on this agency's edges into any of
    # vendor_ids specifically.
    relevant_work_ids_of_agency: dict[str, set[str]] = {}
    for edge in graph["edges"]:
        source = by_id.get(edge["source"])
        if source and source["type"] == "Agency" and edge["target"] in vendor_ids:
            relevant_work_ids_of_agency.setdefault(edge["source"], set()).update(edge["work_ids"])
    keep_agencies = set(relevant_work_ids_of_agency.keys())

    keep_mps: set[str] = set()
    for edge in graph["edges"]:
        target = by_id.get(edge["target"])
        if not target or target["type"] != "Agency" or edge["target"] not in keep_agencies:
            continue
        relevant = relevant_work_ids_of_agency.get(edge["target"], set())
        if _has_shared_work(set(edge["work_ids"]), relevant):
            keep_mps.add(edge["source"])

    keep_nodes = vendor_ids | keep_agencies | keep_mps

    def keep_edge(edge: Edge) -> bool:
        if edge["source"] not in keep_nodes or edge["target"] not in keep_nodes:
            return False
        source = by_id.get(edge["source"])
        target = by_id.get(edge["target"])
        if source and source["type"] == "MP" and target and target["type"] == "Agency":
            relevant = relevant_work_ids_of_agency.get(edge["target"])
            return bool(relevant) and _has_shared_work(set(edge["work_ids"]), relevant)
        return True

    return {
        "nodes": [n for n in graph["nodes"] if n["id"] in keep_nodes],
        "edges": [e for e in graph["edges"] if keep_edge(e)],
    }


def restrict_to_vendor_works(subgraph: Graph, facts: Mapping[str, Mapping[str, Any]]) -> Graph:
    """`subgraph` (from `subgraph_for`) with every MP -> Agency edge cut down to the works that
    agency paid to the vendor in it, so the MP side of a cluster adds up to its vendor side.

    `subgraph_for` keeps a whole MP -> Agency edge once it shares one work with the vendor's
    edges, so that edge still carries the MP's entire spend through the agency. Measured on the
    live snapshot: 7.65 Cr drawn for a vendor paid 0.72 Cr. Every work has exactly one MP, one
    agency and one vendor, so restricted to the works the agency paid the vendor, the two sides
    are equal.

    work_count, total_amount_inr and flagged_work_count are recomputed by build_graph.py's rules:
    the amount is `sanctioned_amount_inr or 0` rounded to paise, and a work is flagged when its
    scored `flags` list is non-empty. `facts` maps work_id to a row holding those two keys; a
    work id it lacks counts as Rs 0 and unflagged, as build_graph.py treats a work with no
    scored record. Agency -> Vendor edges and every node pass through unchanged, and `subgraph`
    is not modified.
    """
    by_id: dict[str, Node] = {n["id"]: n for n in subgraph["nodes"]}

    # agency id -> every work_id that agency paid to a vendor in this subgraph.
    paid_by_agency: dict[str, set[str]] = {}
    for edge in subgraph["edges"]:
        source = by_id.get(edge["source"])
        if source and source["type"] == "Agency":
            paid_by_agency.setdefault(edge["source"], set()).update(edge["work_ids"])

    def restricted(edge: Edge) -> Edge:
        source = by_id.get(edge["source"])
        target = by_id.get(edge["target"])
        if not (source and source["type"] == "MP" and target and target["type"] == "Agency"):
            return edge
        paid = paid_by_agency.get(edge["target"], set())
        work_ids = [w for w in edge["work_ids"] if w in paid]
        rows = [facts.get(w, {}) for w in work_ids]
        return {
            **edge,
            "work_ids": work_ids,
            "work_count": len(work_ids),
            "total_amount_inr": round(sum(r.get("sanctioned_amount_inr") or 0 for r in rows), 2),
            "flagged_work_count": sum(1 for r in rows if r.get("flags")),
        }

    return {"nodes": subgraph["nodes"], "edges": [restricted(e) for e in subgraph["edges"]]}


def graph_totals(graph: Graph) -> dict[str, Any]:
    """Whole-graph totals for the Fund Flow page's stat-tile row (added
    alongside the ribbon-chart redesign, kept working here since the
    non-deep-link path no longer fetches the full graph to compute them
    client-side). Mirrors web/lib/graph-data.ts's graphTotals: flow_inr
    sums only Agency -> Vendor edges, never MP -> Agency too, which would
    double-count the same sanctioned works.
    """
    by_id: dict[str, Node] = {n["id"]: n for n in graph["nodes"]}
    mp_count = agency_count = vendor_count = 0
    for node in graph["nodes"]:
        if node["type"] == "MP":
            mp_count += 1
        elif node["type"] == "Agency":
            agency_count += 1
        else:
            vendor_count += 1
    flow_inr = sum(
        edge["total_amount_inr"]
        for edge in graph["edges"]
        if (source := by_id.get(edge["source"])) and source["type"] == "Agency"
    )
    return {
        "flow_inr": round(flow_inr, 2),
        "mp_count": mp_count,
        "agency_count": agency_count,
        "vendor_count": vendor_count,
    }
