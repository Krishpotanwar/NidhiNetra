"""GET /api/graph: 200 with the full fund-flow graph unfiltered, and a
narrower, referentially-consistent subgraph when filtered.
"""

from __future__ import annotations


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
