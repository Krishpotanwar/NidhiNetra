"""Parity tests for graph_analysis.py, the Python port of
web/lib/vendor-concentration.ts (T17/F-17b). Every case here is a direct
port of vendor-concentration.test.ts's cases, same graphs, same expected
numbers -- the TS file is the reference this port must match exactly.
"""

from __future__ import annotations

from nidhinetra_api import graph_analysis as ga


def node(node_id: str, node_type: str, label: str | None = None) -> dict:
    return {"id": node_id, "type": node_type, "label": label or node_id, "risk_weight": 0}


def edge(source: str, target: str, work_ids: list[str], **overrides) -> dict:
    base = {
        "source": source,
        "target": target,
        "work_count": len(work_ids),
        "total_amount_inr": 0,
        "flagged_work_count": 0,
        "work_ids": work_ids,
    }
    base.update(overrides)
    return base


class TestVendorConcentrations:
    """F-02: two unrelated works sharing only an agency cannot form a path."""

    def test_does_not_credit_an_mp_sharing_only_an_agency_not_a_work(self):
        graph = {
            "nodes": [node("mp_a", "MP"), node("mp_b", "MP"), node("agency_shared", "Agency"), node("vendor_v1", "Vendor")],
            "edges": [
                edge("mp_a", "agency_shared", ["W1"]),
                edge("mp_b", "agency_shared", ["W2"]),
                edge("agency_shared", "vendor_v1", ["W1"]),
            ],
        }

        [v1] = [v for v in ga.vendor_concentrations(graph) if v["vendor_id"] == "vendor_v1"]

        assert v1["member_count"] == 1

    def test_credits_an_mp_when_a_real_work_id_backs_both_hops(self):
        graph = {
            "nodes": [node("mp_a", "MP"), node("agency_shared", "Agency"), node("vendor_v1", "Vendor")],
            "edges": [edge("mp_a", "agency_shared", ["W1"]), edge("agency_shared", "vendor_v1", ["W1"])],
        }

        [v1] = ga.vendor_concentrations(graph)

        assert v1["member_count"] == 1

    def test_credits_each_qualifying_mp_independently(self):
        graph = {
            "nodes": [
                node("mp_a", "MP"),
                node("mp_b", "MP"),
                node("agency_shared", "Agency"),
                node("vendor_v1", "Vendor"),
            ],
            "edges": [
                edge("mp_a", "agency_shared", ["W1"]),
                edge("mp_b", "agency_shared", ["W2"]),
                edge("agency_shared", "vendor_v1", ["W1", "W2"]),
            ],
        }

        [v1] = ga.vendor_concentrations(graph)

        assert v1["member_count"] == 2

    def test_sums_work_count_and_sanctioned_inr_over_every_agency_vendor_edge(self):
        graph = {
            "nodes": [node("mp_a", "MP"), node("agency_shared", "Agency"), node("vendor_v1", "Vendor")],
            "edges": [
                edge("mp_a", "agency_shared", ["W1"]),
                edge("agency_shared", "vendor_v1", ["W1"], work_count=1, total_amount_inr=500_000),
            ],
        }

        [v1] = ga.vendor_concentrations(graph)

        assert v1["work_count"] == 1
        assert v1["sanctioned_inr"] == 500_000

    def test_counts_distinct_agencies_and_sums_flagged_work_count(self):
        graph = {
            "nodes": [
                node("mp_a", "MP"),
                node("agency_1", "Agency"),
                node("agency_2", "Agency"),
                node("vendor_v1", "Vendor"),
            ],
            "edges": [
                edge("mp_a", "agency_1", ["W1"]),
                edge("mp_a", "agency_2", ["W2"]),
                edge("agency_1", "vendor_v1", ["W1"], flagged_work_count=1),
                edge("agency_2", "vendor_v1", ["W2"], flagged_work_count=0),
            ],
        }

        [v1] = ga.vendor_concentrations(graph)

        assert v1["agency_count"] == 2
        assert v1["flagged_work_count"] == 1


class TestMatchingVendors:
    def test_filters_by_threshold_and_sorts_by_member_count_desc_then_label(self):
        concentrations = [
            {"vendor_id": "v1", "vendor_label": "Zed", "member_count": 3},
            {"vendor_id": "v2", "vendor_label": "Alpha", "member_count": 3},
            {"vendor_id": "v3", "vendor_label": "Beta", "member_count": 1},
        ]

        matched = ga.matching_vendors(concentrations, threshold=2)

        assert [v["vendor_id"] for v in matched] == ["v2", "v1"]


class TestMedianMemberCount:
    def test_odd_length(self):
        vendors = [{"member_count": n} for n in (5, 1, 3)]
        assert ga.median_member_count(vendors) == 3

    def test_even_length_rounds_half_up(self):
        vendors = [{"member_count": n} for n in (1, 2)]
        assert ga.median_member_count(vendors) == 2

        vendors = [{"member_count": n} for n in (1, 2, 3, 4)]
        assert ga.median_member_count(vendors) == 3

    def test_empty_is_zero(self):
        assert ga.median_member_count([]) == 0


class TestSubgraphFor:
    def test_excludes_an_mp_sharing_only_the_agency_not_a_work(self):
        graph = {
            "nodes": [
                node("mp_a", "MP"),
                node("mp_b", "MP"),
                node("agency_shared", "Agency"),
                node("vendor_v1", "Vendor"),
            ],
            "edges": [
                edge("mp_a", "agency_shared", ["W1"]),
                edge("mp_b", "agency_shared", ["W2"]),
                edge("agency_shared", "vendor_v1", ["W1"]),
            ],
        }

        sub = ga.subgraph_for(graph, {"vendor_v1"})
        kept_ids = {n["id"] for n in sub["nodes"]}

        assert "mp_a" in kept_ids
        assert "mp_b" not in kept_ids
        assert "agency_shared" in kept_ids

    def test_keeps_an_agencys_other_vendor_relationships_out(self):
        graph = {
            "nodes": [
                node("mp_a", "MP"),
                node("mp_c", "MP"),
                node("agency_shared", "Agency"),
                node("vendor_v1", "Vendor"),
                node("vendor_v2", "Vendor"),
            ],
            "edges": [
                edge("mp_a", "agency_shared", ["W1"]),
                edge("mp_c", "agency_shared", ["W3"]),
                edge("agency_shared", "vendor_v1", ["W1"]),
                edge("agency_shared", "vendor_v2", ["W3"]),
            ],
        }

        sub = ga.subgraph_for(graph, {"vendor_v1"})
        kept_ids = {n["id"] for n in sub["nodes"]}

        assert "mp_a" in kept_ids
        assert "mp_c" not in kept_ids
        assert "vendor_v2" not in kept_ids

    def test_excludes_a_cross_branch_mp_edge_with_no_work_in_common(self):
        graph = {
            "nodes": [
                node("mp_a", "MP"),
                node("agency_a", "Agency"),
                node("agency_b", "Agency"),
                node("vendor_v1", "Vendor"),
            ],
            "edges": [
                edge("mp_a", "agency_a", ["W1"]),
                edge("agency_a", "vendor_v1", ["W1"]),
                edge("mp_a", "agency_b", ["W3"]),
                edge("agency_b", "vendor_v1", ["W2"]),
            ],
        }

        sub = ga.subgraph_for(graph, {"vendor_v1"})
        sub_edge_pairs = {(e["source"], e["target"], tuple(e["work_ids"])) for e in sub["edges"]}

        assert ("mp_a", "agency_a", ("W1",)) in sub_edge_pairs
        assert ("mp_a", "agency_b", ("W3",)) not in sub_edge_pairs


class TestGraphTotals:
    def test_counts_nodes_by_type_and_sums_only_agency_vendor_edges(self):
        graph = {
            "nodes": [node("mp-1", "MP"), node("agency-1", "Agency"), node("vendor-1", "Vendor")],
            "edges": [
                edge("mp-1", "agency-1", ["W1"], total_amount_inr=1_000_000),
                edge("agency-1", "vendor-1", ["W1"], total_amount_inr=700_000),
            ],
        }

        totals = ga.graph_totals(graph)

        assert totals == {"flow_inr": 700_000, "mp_count": 1, "agency_count": 1, "vendor_count": 1}
