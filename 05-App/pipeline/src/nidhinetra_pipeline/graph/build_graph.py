"""Builds the fund-flow graph (Execution Plan section 3.3,
contracts/fund_flow_graph.schema.json) from A1's normalized records and
A2's risk-scored records.

`build_fund_flow_graph()` is the single entry point A4 calls -- its
signature is frozen and A4 builds against it without seeing this file.
Every output is validated against the frozen JSON Schema (loaded by
relative path, never hand-copied) before it is returned, matching the
pattern in normalize/normalize.py and risk/engine.py so all three
validators look and feel the same.

`find_concentration_clusters()` is the "money network" analysis from part
7 of Understanding NidhiNetra.html: one agency or vendor appearing across
an unusual number of MPs is the classic tell, but it is only a meaningful
signal at a scale this 20-row CP0 fixture does not reach (see P4 in
Design Review - Data Spike First.md). It is written to say so plainly --
returning an empty list rather than manufacturing a low-confidence result
-- when the data does not support a claim.
"""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import quote

import jsonschema

# pipeline/src/nidhinetra_pipeline/graph/build_graph.py -> parents[4] is "05-App/"
_APP_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_PATH = _APP_ROOT / "contracts" / "fund_flow_graph.schema.json"

_TYPE_PREFIX = {"MP": "mp", "Agency": "agency", "Vendor": "vendor"}

# find_concentration_clusters: a node clears the threshold when its
# distinct-MP count is more than this many standard deviations above the
# mean of its own type's eligible pool. 2.0 is roughly the top ~2.5% tail
# of a normal distribution -- deliberately strict, because a small,
# hand-curated fixture graph makes it easy to manufacture a false positive
# with a looser bar. Documented here rather than buried in the function so
# a reader doesn't have to hunt for the one number that decides everything.
_CONCENTRATION_Z_THRESHOLD = 2.0


class GraphValidationError(Exception):
    """Raised when build_fund_flow_graph's own output fails to validate
    against contracts/fund_flow_graph.schema.json, or violates the
    referential rule the schema itself does not enforce (every edge's
    source/target must match a real node id). The function never returns
    a partial or invalid graph -- it raises instead.
    """


def _load_schema() -> dict[str, Any]:
    if not SCHEMA_PATH.exists():
        raise GraphValidationError(
            f"schema file not found at {SCHEMA_PATH}. This module loads it by "
            "relative path from contracts/ and never hand-copies the shape."
        )
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(label: str) -> str:
    """Lowercase, collapse every run of non-alphanumeric characters to a
    single underscore, strip leading/trailing underscores. Deterministic:
    the same label always produces the same slug, which is what lets the
    frontend cache or link against these ids across runs.

    A label written in another script has no ASCII alphanumerics to slug at
    all: one of the 5,867 live IA_NAME strings is Devanagari
    ("सामाजिक न्याय एवं दिव्यांगजन सशक्तिकरण विभाग सीधी"). Percent encoding it
    keeps the id ASCII, deterministic and distinct from every other label --
    the same reasoning `_vendor_node_id()` already documents -- rather than
    failing an entire national build over one department's script. A label
    that is blank, or ASCII punctuation with no letters or digits, still
    raises: that is missing or unusable data, not a spelling this function
    cannot handle.
    """
    stripped = label.strip()
    slug = _SLUG_RE.sub("_", stripped.lower()).strip("_")
    if slug:
        return slug
    if stripped and not stripped.isascii():
        return quote(stripped, safe="")
    raise GraphValidationError(
        f"cannot build a stable node id from blank/unslugifiable label {label!r}"
    )


def _node_id(node_type: str, label: str) -> str:
    return f"{_TYPE_PREFIX[node_type]}_{_slugify(label)}"


def _vendor_node_id(vendor_id: str) -> str:
    """Encode a source identifier without collapsing distinct identities.

    `_slugify()` is appropriate for display labels, but it deliberately
    folds case and punctuation. Applying it to a source ID could therefore
    recreate R-06's false merge under a different spelling. Percent
    encoding is stdlib-only, deterministic and reversible.
    """
    return f"{_TYPE_PREFIX['Vendor']}_{quote(vendor_id, safe='')}"


def _modal_label(counts: dict[str, int]) -> str:
    top = max(counts.values())
    return sorted(label for label, count in counts.items() if count == top)[0]


def _new_edge_agg() -> dict[str, Any]:
    return {"work_count": 0, "total_amount_inr": 0.0, "flagged_work_count": 0, "work_ids": set()}


def build_fund_flow_graph(
    normalized_records: list[dict],
    scored_records: list[dict],
) -> dict:
    """Returns a dict matching contracts/fund_flow_graph.schema.json exactly.

    Nodes: one per distinct mp_name, one per distinct implementing_agency (IA_NAME,
    the executing agency; F-01) (records where it is null contribute no Agency
    node), one per distinct
    source vendor_id with vendor_name used only as its display label
    (records where either is null contribute no Vendor node). MP and Agency
    ids are stable deterministic slugs; Vendor ids use collision-free source
    identifier encoding so two IDs sharing a common name remain distinct.

    Edges: MP -> Agency and Agency -> Vendor, each aggregating work_count,
    total_amount_inr (sum of sanctioned_amount_inr across every
    contributing record), flagged_work_count, and work_ids (every work_id
    backing that edge) across every normalized record connecting that
    pair. A leg is skipped entirely when the relevant field is null: a
    record with an agency but no vendor contributes only the MP->Agency
    edge; a record with no agency contributes neither edge (but its MP
    and, if present, Vendor node are still created).

    work_ids exists because adjacency alone is not evidence of a real fund
    flow (F-02, nemotronreview.md, fixed 2026-09-14): an MP->Agency edge
    and an Agency->Vendor edge sharing an agency does not mean any money
    from that MP ever reached that vendor -- the agency may pay the vendor
    entirely out of a different MP's works. Only a work_id present in BOTH
    edges' work_ids proves a real path; consumers (web/lib/vendor-
    concentration.ts) must check that intersection rather than inferring a
    path from source/target adjacency.

    A record counts as flagged -- for both edge flagged_work_count and
    node risk_weight -- if its matching scored_record (matched by
    work_id) has a non-empty `flags` array. A work_id with no matching
    scored_record is treated as unflagged, not as an error: scoring and
    graph-building are independent stages and a work missing from
    scored_records should not crash the graph.

    risk_weight on a node is the count of distinct flagged works touching
    it: 1.0 for every flagged record whose MP/Agency/Vendor this node is,
    summed.
    """
    flagged_work_ids = {record["work_id"] for record in scored_records if record.get("flags")}

    # node id -> (type, label). A plain dict preserves first-seen order,
    # but the final node list is sorted by id anyway for determinism that
    # does not depend on input record order.
    node_meta: dict[str, tuple[str, str]] = {}
    risk_weight: dict[str, float] = defaultdict(float)
    vendor_labels: dict[str, Counter[str]] = defaultdict(Counter)

    mp_agency_edges: dict[tuple[str, str], dict[str, Any]] = {}
    agency_vendor_edges: dict[tuple[str, str], dict[str, Any]] = {}

    for record in normalized_records:
        work_id = record["work_id"]
        is_flagged = work_id in flagged_work_ids
        amount = record.get("sanctioned_amount_inr") or 0

        mp_id = _node_id("MP", record["mp_name"])
        node_meta.setdefault(mp_id, ("MP", record["mp_name"]))
        if is_flagged:
            risk_weight[mp_id] += 1.0

        agency_name = record.get("implementing_agency")
        agency_id: str | None = None
        if agency_name:
            agency_id = _node_id("Agency", agency_name)
            node_meta.setdefault(agency_id, ("Agency", agency_name))
            if is_flagged:
                risk_weight[agency_id] += 1.0

            edge = mp_agency_edges.setdefault((mp_id, agency_id), _new_edge_agg())
            edge["work_count"] += 1
            edge["total_amount_inr"] += amount
            edge["work_ids"].add(work_id)
            if is_flagged:
                edge["flagged_work_count"] += 1

        vendor_name = record.get("vendor_name")
        source_vendor_id = record.get("vendor_id")
        vendor_node_id: str | None = None
        if vendor_name and source_vendor_id:
            vendor_node_id = _vendor_node_id(source_vendor_id)
            vendor_labels[vendor_node_id][vendor_name] += 1
            if is_flagged:
                risk_weight[vendor_node_id] += 1.0

        if agency_id is not None and vendor_node_id is not None:
            edge = agency_vendor_edges.setdefault((agency_id, vendor_node_id), _new_edge_agg())
            edge["work_count"] += 1
            edge["total_amount_inr"] += amount
            edge["work_ids"].add(work_id)
            if is_flagged:
                edge["flagged_work_count"] += 1

    for vendor_node_id, labels in vendor_labels.items():
        node_meta[vendor_node_id] = ("Vendor", _modal_label(labels))

    nodes = [
        {
            "id": node_id,
            "type": node_type,
            "label": label,
            "risk_weight": risk_weight.get(node_id, 0.0),
        }
        for node_id, (node_type, label) in sorted(node_meta.items())
    ]

    edges: list[dict[str, Any]] = []
    for (source, target), agg in sorted(mp_agency_edges.items()):
        edges.append({"source": source, "target": target, **_rounded(agg)})
    for (source, target), agg in sorted(agency_vendor_edges.items()):
        edges.append({"source": source, "target": target, **_rounded(agg)})

    graph = {"nodes": nodes, "edges": edges}
    _validate(graph)
    return graph


def _rounded(agg: dict[str, Any]) -> dict[str, Any]:
    # Round to paise (2 decimal places) for a clean, currency-appropriate
    # output. Summation order is fixed by normalized_records' own order,
    # so this is deterministic across repeated calls regardless of
    # rounding -- the rounding is purely for readability. work_ids is
    # built as a set (insertion order is irrelevant and work_id is unique
    # per record, so no dedup ambiguity) and sorted here for the same
    # determinism guarantee as everything else this function returns.
    return {
        "work_count": agg["work_count"],
        "total_amount_inr": round(agg["total_amount_inr"], 2),
        "flagged_work_count": agg["flagged_work_count"],
        "work_ids": sorted(agg["work_ids"]),
    }


def _validate(graph: dict[str, Any]) -> None:
    schema = _load_schema()
    validator = jsonschema.Draft7Validator(schema)
    errors = [
        f"({'.'.join(str(p) for p in err.path) or '<root>'}): {err.message}"
        for err in validator.iter_errors(graph)
    ]

    # The schema itself does not (and per its own description, cannot via
    # JSON Schema alone) enforce that every edge references a real node --
    # that referential rule is this module's own responsibility, the same
    # way contracts/validate.py checks it independently at the cross-file
    # level.
    node_ids = {n["id"] for n in graph.get("nodes", [])}
    for edge in graph.get("edges", []):
        if edge.get("source") not in node_ids:
            errors.append(f"edge source {edge.get('source')!r} matches no node id")
        if edge.get("target") not in node_ids:
            errors.append(f"edge target {edge.get('target')!r} matches no node id")

    if errors:
        raise GraphValidationError(
            "build_fund_flow_graph produced output that violates "
            "fund_flow_graph.schema.json:\n" + "\n".join(errors)
        )


def find_concentration_clusters(graph: dict, min_work_count: int = 5) -> list[dict]:
    """Identifies agencies or vendors connected to an unusually high
    number of distinct MPs, the "money network" pattern from part 7 of
    Understanding NidhiNetra.html: "one contractor or agency showing up
    across far more MPs and districts than is normal." (The graph carries
    no separate district node -- an MP's constituency stands in for
    district here.)

    Method (z-score over distinct-MP count, chosen over a plain percentile
    cut because it naturally requires *some* spread in the data before it
    will call anything an outlier -- see the zero-stdev short-circuit
    below):

    1. For every Agency node, distinct_mp_count is the number of distinct
       MPs with a direct MP->Agency edge into it.
    2. For every Vendor node, distinct_mp_count is the number of distinct
       MPs reachable one hop further back: the union of the MPs feeding
       every Agency the vendor has an Agency->Vendor edge from. A vendor
       working for many MPs through one agency, or a few MPs through many
       agencies, both count.
    3. A node is only eligible for comparison if its total work_count
       (summed across every edge touching it) is at least
       `min_work_count` -- this stops a single one-off record from
       generating a spurious "outlier" out of pure small-sample noise.
    4. Agencies are compared only to other eligible Agencies, and Vendors
       only to other eligible Vendors -- the two roles have structurally
       different degree distributions and are not comparable to each
       other. Within a type's eligible pool, a node clears the threshold
       when its z-score exceeds `_CONCENTRATION_Z_THRESHOLD` (2.0).
    5. If a type has fewer than 2 eligible nodes, or its eligible pool's
       standard deviation is 0 (every node identically connected -- there
       is no spread to be an outlier against), that type contributes no
       candidates at all. This is deliberate: on a small fixture, the
       honest answer is very often "nothing clears the bar," and this
       function is written to say that rather than lower the threshold
       until something does (Checkpoints CP3).

    Returns a list of {"node_id", "label", "reason"} sorted by node_id for
    determinism, or an empty list when nothing clears the threshold.
    """
    nodes_by_id = {n["id"]: n for n in graph.get("nodes", [])}
    edges = graph.get("edges", [])

    # agency_id -> set of MP ids with a direct edge into it
    agency_mps: dict[str, set[str]] = defaultdict(set)
    # vendor_id -> set of Agency ids with a direct edge into it
    vendor_agencies: dict[str, set[str]] = defaultdict(set)
    work_count_by_node: dict[str, int] = defaultdict(int)

    for edge in edges:
        source, target = edge.get("source"), edge.get("target")
        work_count = edge.get("work_count", 0)
        work_count_by_node[source] += work_count
        work_count_by_node[target] += work_count

        source_type = nodes_by_id.get(source, {}).get("type")
        target_type = nodes_by_id.get(target, {}).get("type")
        if source_type == "MP" and target_type == "Agency":
            agency_mps[target].add(source)
        elif source_type == "Agency" and target_type == "Vendor":
            vendor_agencies[target].add(source)

    def distinct_mp_count(node_id: str, node_type: str) -> int:
        if node_type == "Agency":
            return len(agency_mps.get(node_id, set()))
        if node_type == "Vendor":
            mps: set[str] = set()
            for agency_id in vendor_agencies.get(node_id, set()):
                mps |= agency_mps.get(agency_id, set())
            return len(mps)
        return 0

    candidates: list[dict[str, str]] = []
    for node_type in ("Agency", "Vendor"):
        eligible = [
            node
            for node in nodes_by_id.values()
            if node["type"] == node_type and work_count_by_node.get(node["id"], 0) >= min_work_count
        ]
        if len(eligible) < 2:
            continue

        counts = {node["id"]: distinct_mp_count(node["id"], node_type) for node in eligible}
        values = list(counts.values())
        mean = statistics.mean(values)
        try:
            stdev = statistics.stdev(values)
        except statistics.StatisticsError:
            stdev = 0.0
        if stdev == 0:
            continue

        for node in eligible:
            count = counts[node["id"]]
            z = (count - mean) / stdev
            if z > _CONCENTRATION_Z_THRESHOLD:
                candidates.append(
                    {
                        "node_id": node["id"],
                        "label": node["label"],
                        "reason": (
                            f"{node['label']} is connected to {count} distinct MPs, "
                            f"{z:.1f} standard deviations above the average of "
                            f"{mean:.1f} among {node_type.lower()}s with at least "
                            f"{min_work_count} works recorded."
                        ),
                    }
                )

    candidates.sort(key=lambda c: c["node_id"])
    return candidates


__all__ = [
    "GraphValidationError",
    "SCHEMA_PATH",
    "build_fund_flow_graph",
    "find_concentration_clusters",
]
