"""find_concentration_clusters is the "money network" analysis from part 7
of Understanding NidhiNetra.html. These tests cover both directions
Checkpoints CP3 cares about: it must actually fire on a graph with a
genuine, deliberately-built outlier, and it must not manufacture a result
on a graph that has none -- including on the real CP0 fixture, which is
far too small to contain a genuine national-scale pattern.
"""

from __future__ import annotations

from nidhinetra_pipeline.graph import build_fund_flow_graph, find_concentration_clusters


def _agency_node(n: int) -> dict:
    return {"id": f"agency_{n}", "type": "Agency", "label": f"Agency {n}", "risk_weight": 0.0}


def _mp_node(n: int) -> dict:
    return {"id": f"mp_{n}", "type": "MP", "label": f"MP {n}", "risk_weight": 0.0}


def _edge(mp_id: str, agency_id: str, work_count: int) -> dict:
    return {
        "source": mp_id,
        "target": agency_id,
        "work_count": work_count,
        "total_amount_inr": 1_000_000.0 * work_count,
        "flagged_work_count": 0,
    }


def _build_outlier_graph() -> dict:
    """10 ordinary agencies, each tied to exactly one MP via work_count=5
    (clearing the default min_work_count floor). One concentration agency
    tied to 20 distinct MPs, one work each (work_count=20, also clearing
    the floor). distinct_mp_count values: [1]*10 + [20] -> mean ~2.73,
    stdev ~5.73, outlier z ~3.0, comfortably above the 2.0 threshold.
    """
    nodes: list[dict] = []
    edges: list[dict] = []
    mp_counter = 0

    for agency_n in range(10):
        mp_counter += 1
        mp = _mp_node(mp_counter)
        agency = _agency_node(agency_n)
        nodes.extend([mp, agency])
        edges.append(_edge(mp["id"], agency["id"], work_count=5))

    concentrated_agency = _agency_node("concentrated")
    nodes.append(concentrated_agency)
    for _ in range(20):
        mp_counter += 1
        mp = _mp_node(mp_counter)
        nodes.append(mp)
        edges.append(_edge(mp["id"], concentrated_agency["id"], work_count=1))

    return {"nodes": nodes, "edges": edges}


def test_finds_the_deliberately_planted_outlier_agency() -> None:
    graph = _build_outlier_graph()
    clusters = find_concentration_clusters(graph, min_work_count=5)

    flagged_ids = {c["node_id"] for c in clusters}
    assert "agency_concentrated" in flagged_ids

    outlier = next(c for c in clusters if c["node_id"] == "agency_concentrated")
    assert "20 distinct MPs" in outlier["reason"]
    assert outlier["label"] == "Agency concentrated"

    # None of the ten ordinary agencies (distinct_mp_count == 1 each)
    # should also clear the bar.
    assert flagged_ids == {"agency_concentrated"}


def test_no_genuine_outlier_returns_empty_list_rather_than_forcing_one() -> None:
    # Eight agencies, mild natural variation (2 or 3 distinct MPs each),
    # all comfortably clearing min_work_count -- but no agency stands out
    # by 2+ standard deviations.
    nodes: list[dict] = []
    edges: list[dict] = []
    mp_counter = 0
    distinct_counts = [2, 3, 2, 3, 2, 3, 2, 3]

    for agency_n, count in enumerate(distinct_counts):
        agency = _agency_node(agency_n)
        nodes.append(agency)
        for _ in range(count):
            mp_counter += 1
            mp = _mp_node(mp_counter)
            nodes.append(mp)
            edges.append(_edge(mp["id"], agency["id"], work_count=3))

    graph = {"nodes": nodes, "edges": edges}
    clusters = find_concentration_clusters(graph, min_work_count=5)
    assert clusters == []


def test_identically_connected_agencies_yield_empty_list_not_a_division_error() -> None:
    # Every agency connected to exactly the same number of distinct MPs:
    # stdev is 0, so there is no spread to be an outlier against. Must not
    # raise (ZeroDivisionError / StatisticsError) and must not flag
    # anything.
    nodes: list[dict] = []
    edges: list[dict] = []
    mp_counter = 0

    for agency_n in range(6):
        agency = _agency_node(agency_n)
        nodes.append(agency)
        for _ in range(3):
            mp_counter += 1
            mp = _mp_node(mp_counter)
            nodes.append(mp)
            edges.append(_edge(mp["id"], agency["id"], work_count=5))

    graph = {"nodes": nodes, "edges": edges}
    clusters = find_concentration_clusters(graph, min_work_count=5)
    assert clusters == []


def test_high_degree_node_below_min_work_count_is_not_eligible() -> None:
    # An agency connected to many distinct MPs but via low-volume edges
    # (total work_count below the floor) must not be treated as a
    # candidate at all -- it should not appear in the output, and it
    # should not pollute the mean/stdev used to judge the other agencies.
    nodes: list[dict] = []
    edges: list[dict] = []
    mp_counter = 0

    # Five ordinary, eligible agencies with identical distinct_mp_count.
    for agency_n in range(5):
        agency = _agency_node(agency_n)
        nodes.append(agency)
        for _ in range(2):
            mp_counter += 1
            mp = _mp_node(mp_counter)
            nodes.append(mp)
            edges.append(_edge(mp["id"], agency["id"], work_count=5))

    # One agency touching 10 distinct MPs, but each edge has work_count=1,
    # so its total work_count (10) still happens to clear a *low* floor --
    # push it below the floor explicitly with a stricter min_work_count.
    thin_agency = _agency_node("thin")
    nodes.append(thin_agency)
    for _ in range(10):
        mp_counter += 1
        mp = _mp_node(mp_counter)
        nodes.append(mp)
        edges.append(_edge(mp["id"], thin_agency["id"], work_count=1))

    graph = {"nodes": nodes, "edges": edges}
    clusters = find_concentration_clusters(graph, min_work_count=11)
    assert clusters == []


def test_fewer_than_two_eligible_nodes_of_a_type_yields_empty_list() -> None:
    # A single agency has nothing to be compared against.
    graph = {
        "nodes": [_mp_node(1), _agency_node(1)],
        "edges": [_edge("mp_1", "agency_1", work_count=10)],
    }
    assert find_concentration_clusters(graph, min_work_count=5) == []


def test_real_cp0_fixture_finds_nothing_genuine_at_this_scale(
    works_fixture, scored_fixture
) -> None:
    # Documented, expected behaviour per Checkpoints CP3 and Design Review
    # - Data Spike First.md's P4: 20 rows across many states is far too
    # small to contain a genuine national-scale concentration pattern.
    # The function must say so honestly (empty list), not lower the
    # threshold to manufacture something to show.
    graph = build_fund_flow_graph(works_fixture, scored_fixture)
    assert find_concentration_clusters(graph) == []
    # Also true even with an aggressive min_work_count of 1 -- confirms
    # the honesty holds regardless of the eligibility floor, not because
    # the floor happens to exclude everything.
    assert find_concentration_clusters(graph, min_work_count=1) == []
