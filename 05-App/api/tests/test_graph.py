"""GET /api/graph: 200 with the full fund-flow graph unfiltered, and a
narrower, referentially-consistent subgraph when filtered.
"""

from __future__ import annotations

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
