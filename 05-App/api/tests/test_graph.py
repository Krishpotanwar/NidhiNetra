"""GET /api/graph: 200 with the full fund-flow graph unfiltered, and a
narrower, referentially-consistent subgraph when filtered.

Also GET /api/graph/concentrations and GET /api/graph/cluster (T17/F-17b):
the server-computed replacements for downloading the whole graph just to
rank vendors and narrow to one cluster client-side.
"""

from __future__ import annotations

import pytest
from nidhinetra_api import graph_analysis
from nidhinetra_api.routers import graph as graph_router


def test_get_graph_200_unfiltered(client):
    body = client.get("/api/graph").json()

    assert body["success"] is True
    graph = body["data"]
    assert graph["nodes"]
    assert graph["edges"]
    node_ids = {n["id"] for n in graph["nodes"]}
    for edge in graph["edges"]:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids


def test_get_graph_filtered_by_agency_returns_a_referentially_consistent_subset(client):
    full = client.get("/api/graph").json()["data"]
    agency_node = next(n for n in full["nodes"] if n["type"] == "Agency")
    needle = agency_node["label"].split()[0]

    body = client.get("/api/graph", params={"agency": needle}).json()
    graph = body["data"]

    assert body["success"] is True
    assert len(graph["nodes"]) <= len(full["nodes"])
    node_ids = {n["id"] for n in graph["nodes"]}
    assert agency_node["id"] in node_ids
    for edge in graph["edges"]:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids


def test_get_graph_filtered_by_nonmatching_agency_returns_empty(client):
    body = client.get("/api/graph", params={"agency": "no-such-agency-xyz"}).json()

    assert body["success"] is True
    assert body["data"] == {"nodes": [], "edges": []}


def test_current_graph_reports_its_status(client):
    body = client.get("/api/graph").json()
    assert body["meta"] == {"graph_status": "current"}


def test_graph_without_edge_evidence_is_held_back(client, monkeypatch):
    """F-02 legacy: edges without work_ids cannot be checked for a shared work."""
    legacy = {
        "nodes": [
            {"id": "mp_a", "type": "MP", "label": "A", "risk_weight": 0.0},
            {"id": "agency_b", "type": "Agency", "label": "B", "risk_weight": 0.0},
        ],
        "edges": [
            {
                "source": "mp_a",
                "target": "agency_b",
                "work_count": 1,
                "total_amount_inr": 1.0,
                "flagged_work_count": 0,
            }
        ],
    }
    monkeypatch.setattr(graph_router, "_load_graph", lambda: legacy)

    body = client.get("/api/graph").json()

    assert body["success"] is True
    assert body["data"] == {"nodes": [], "edges": []}
    assert body["meta"] == {"graph_status": "rebuild_required"}


def test_graph_from_a_pre_f01_snapshot_is_held_back(client, monkeypatch):
    """F-01 legacy: its Agency nodes are District Authorities under the wrong name."""
    monkeypatch.setattr(
        graph_router.db,
        "works_columns",
        lambda snapshot_dir=None: {"work_id", "implementing_agency"},
    )

    body = client.get("/api/graph").json()

    assert body["data"] == {"nodes": [], "edges": []}
    assert body["meta"] == {"graph_status": "rebuild_required"}


def test_concentrations_returns_the_expected_shape(client):
    body = client.get("/api/graph/concentrations").json()

    assert body["success"] is True
    assert body["meta"] == {"graph_status": "current"}
    data = body["data"]
    assert set(data.keys()) == {"vendors", "matching_count", "total_vendor_count", "median_member_count", "totals"}
    assert data["total_vendor_count"] > 0
    assert set(data["totals"].keys()) == {"flow_inr", "mp_count", "agency_count", "vendor_count"}
    for vendor in data["vendors"]:
        assert set(vendor.keys()) == {
            "vendor_id",
            "vendor_label",
            "member_count",
            "agency_count",
            "work_count",
            "sanctioned_inr",
            "flagged_work_count",
        }


def test_concentrations_returns_only_the_requested_limit_but_reports_the_true_matching_count(client):
    body = client.get("/api/graph/concentrations", params={"min_members": 1, "limit": 1}).json()
    data = body["data"]

    assert len(data["vendors"]) <= 1
    assert data["matching_count"] >= len(data["vendors"])


def test_concentrations_min_members_bounds(client):
    assert client.get("/api/graph/concentrations", params={"min_members": 0}).status_code == 422
    assert client.get("/api/graph/concentrations", params={"min_members": 101}).status_code == 422


def test_concentrations_limit_bounds(client):
    assert client.get("/api/graph/concentrations", params={"limit": 0}).status_code == 422
    assert client.get("/api/graph/concentrations", params={"limit": 101}).status_code == 422


def test_concentrations_does_not_recompute_on_a_second_call(client, monkeypatch):
    graph_router._ANALYSIS_CACHE.clear()
    calls = 0
    real = graph_analysis.vendor_concentrations

    def counting(*args, **kwargs):
        nonlocal calls
        calls += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(graph_analysis, "vendor_concentrations", counting)

    client.get("/api/graph/concentrations")
    client.get("/api/graph/concentrations")

    assert calls == 1


def test_concentrations_rebuild_required_for_a_legacy_graph(monkeypatch, client):
    legacy = {"nodes": [], "edges": [{"source": "a", "target": "b"}]}
    monkeypatch.setattr(graph_router, "_load_graph_analysis_cached", lambda: (legacy, [], {}))

    body = client.get("/api/graph/concentrations").json()

    assert body["success"] is True
    assert body["data"]["vendors"] == []
    assert body["meta"] == {"graph_status": "rebuild_required"}


def test_cluster_returns_a_subgraph_for_a_real_vendor_id(client):
    full = client.get("/api/graph").json()["data"]
    vendor_node = next(n for n in full["nodes"] if n["type"] == "Vendor")

    body = client.get("/api/graph/cluster", params={"vendor_id": vendor_node["id"]}).json()

    assert body["success"] is True
    node_ids = {n["id"] for n in body["data"]["nodes"]}
    assert vendor_node["id"] in node_ids


def test_cluster_404_for_an_unknown_vendor_id(client):
    response = client.get("/api/graph/cluster", params={"vendor_id": "vendor_does-not-exist"})

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]


def test_cluster_rebuild_required_for_a_legacy_graph(monkeypatch, client):
    legacy = {"nodes": [], "edges": [{"source": "a", "target": "b"}]}
    monkeypatch.setattr(graph_router, "_load_graph_analysis_cached", lambda: (legacy, [], {}))

    body = client.get("/api/graph/cluster", params={"vendor_id": "vendor_x"}).json()

    assert body["success"] is True
    assert body["data"] == {"nodes": [], "edges": []}
    assert body["meta"] == {"graph_status": "rebuild_required"}


def _cluster(client, vendor_id: str) -> dict:
    return client.get("/api/graph/cluster", params={"vendor_id": vendor_id}).json()["data"]


def test_cluster_mp_edges_carry_only_the_works_paid_to_this_vendor(client, works_fixture):
    # In the fixture, rajesh_oraon recommended both MPLADS-FX-0001 (paid to vendor V001) and
    # MPLADS-FX-0008 (paid to V004) through one agency. V004's cluster must show only the second.
    cluster = _cluster(client, "vendor_SYNTH-V004")

    [mp_edge] = [
        e
        for e in cluster["edges"]
        if e["source"] == "mp_rajesh_oraon" and e["target"] == "agency_zilla_parishad_works_dept"
    ]
    sanctioned = {w["work_id"]: w["sanctioned_amount_inr"] for w in works_fixture}
    assert mp_edge["work_ids"] == ["MPLADS-FX-0008"]
    assert mp_edge["work_count"] == 1
    assert mp_edge["total_amount_inr"] == pytest.approx(sanctioned["MPLADS-FX-0008"])


def test_cluster_balances_at_every_agency(client):
    nodes = client.get("/api/graph").json()["data"]["nodes"]
    vendor_ids = [n["id"] for n in nodes if n["type"] == "Vendor"]
    assert vendor_ids

    for vendor_id in vendor_ids:
        cluster = _cluster(client, vendor_id)
        kind = {n["id"]: n["type"] for n in cluster["nodes"]}
        for agency in (n["id"] for n in cluster["nodes"] if n["type"] == "Agency"):
            paid = [e for e in cluster["edges"] if e["source"] == agency]
            mine = [
                e for e in cluster["edges"] if e["target"] == agency and kind[e["source"]] == "MP"
            ]
            # The MP edges are subsets of what the agency paid this vendor, and together cover it.
            assert {w for e in mine for w in e["work_ids"]} == {
                w for e in paid for w in e["work_ids"]
            }
            assert sum(e["work_count"] for e in mine) == sum(e["work_count"] for e in paid)
            assert sum(e["total_amount_inr"] for e in mine) == pytest.approx(
                sum(e["total_amount_inr"] for e in paid), abs=0.01
            )


def test_cluster_for_a_vendor_no_agency_paid_is_just_that_vendor(monkeypatch, client):
    lone = {
        "nodes": [{"id": "vendor_lone", "type": "Vendor", "label": "L", "risk_weight": 0}],
        "edges": [],
    }
    monkeypatch.setattr(graph_router, "_load_graph_analysis_cached", lambda: (lone, [], {}))

    body = client.get("/api/graph/cluster", params={"vendor_id": "vendor_lone"}).json()

    assert body["success"] is True
    assert body["data"] == lone
    assert body["meta"] == {"graph_status": "current"}
