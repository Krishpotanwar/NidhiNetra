"""build_fund_flow_graph's output must validate against
contracts/fund_flow_graph.schema.json, and satisfy the referential
invariant the schema itself cannot express (every edge's source/target
must match a real node id) -- see contracts/validate.py's own cross-file
check 8 for the same rule enforced independently at the fixture level.
"""

from __future__ import annotations

from urllib.parse import quote

import jsonschema
import pytest
from nidhinetra_pipeline.graph import build_fund_flow_graph
from nidhinetra_pipeline.graph.build_graph import GraphValidationError

from .conftest import make_normalized, make_scored


def test_builds_on_the_real_fixture_and_validates_against_the_frozen_schema(
    works_fixture, scored_fixture, graph_schema
) -> None:
    graph = build_fund_flow_graph(works_fixture, scored_fixture)
    validator = jsonschema.Draft7Validator(graph_schema)
    errors = list(validator.iter_errors(graph))
    assert not errors, [str(e) for e in errors]


def test_real_fixture_build_matches_the_committed_graph_fixture(
    works_fixture, scored_fixture, graph_fixture
) -> None:
    assert build_fund_flow_graph(works_fixture, scored_fixture) == graph_fixture


def test_every_edge_endpoint_matches_a_real_node_id(works_fixture, scored_fixture) -> None:
    graph = build_fund_flow_graph(works_fixture, scored_fixture)
    node_ids = {n["id"] for n in graph["nodes"]}
    assert node_ids, "expected at least one node from the real fixture"
    for edge in graph["edges"]:
        assert edge["source"] in node_ids, edge
        assert edge["target"] in node_ids, edge


def test_real_fixture_produces_one_mp_node_per_distinct_mp_name(
    works_fixture, scored_fixture
) -> None:
    graph = build_fund_flow_graph(works_fixture, scored_fixture)
    expected_mp_count = len({w["mp_name"] for w in works_fixture})
    actual_mp_nodes = [n for n in graph["nodes"] if n["type"] == "MP"]
    assert len(actual_mp_nodes) == expected_mp_count


def test_null_implementing_agency_contributes_no_mp_agency_edge_and_does_not_crash() -> None:
    records = [
        make_normalized(
            work_id="W1",
            mp_name="Solo MP",
            implementing_agency=None,
            vendor_name=None,
        )
    ]
    graph = build_fund_flow_graph(records, [])

    # The MP node still exists...
    mp_nodes = [n for n in graph["nodes"] if n["type"] == "MP"]
    assert len(mp_nodes) == 1
    assert mp_nodes[0]["label"] == "Solo MP"

    # ...but no Agency node and no edges of any kind were created.
    assert not any(n["type"] == "Agency" for n in graph["nodes"])
    assert graph["edges"] == []


def test_agency_present_vendor_null_gives_mp_agency_edge_but_no_agency_vendor_edge() -> None:
    records = [
        make_normalized(
            work_id="W1",
            mp_name="Some MP",
            implementing_agency="Some Agency",
            vendor_name=None,
        )
    ]
    graph = build_fund_flow_graph(records, [])

    node_ids = {n["id"] for n in graph["nodes"]}
    assert "mp_some_mp" in node_ids
    assert "agency_some_agency" in node_ids
    assert not any(n["type"] == "Vendor" for n in graph["nodes"])

    assert len(graph["edges"]) == 1
    edge = graph["edges"][0]
    assert edge["source"] == "mp_some_mp"
    assert edge["target"] == "agency_some_agency"
    assert edge["work_count"] == 1
    assert edge["work_ids"] == ["W1"]


def test_vendor_present_agency_null_creates_vendor_node_but_no_edges() -> None:
    # Vendor identity comes from the source ID, independently of whether an
    # agency exists on this record. The orphan still gets a node, just no
    # edge touching it.
    records = [
        make_normalized(
            work_id="W1",
            mp_name="Some MP",
            implementing_agency=None,
            vendor_id="orphan-7",
            vendor_name="Orphan Vendor",
        )
    ]
    graph = build_fund_flow_graph(records, [])
    vendor_nodes = [n for n in graph["nodes"] if n["type"] == "Vendor"]
    assert len(vendor_nodes) == 1
    assert vendor_nodes[0]["label"] == "Orphan Vendor"
    assert graph["edges"] == []


def test_edges_aggregate_work_count_amount_and_flagged_count_across_records() -> None:
    records = [
        make_normalized(
            work_id="W1",
            mp_name="Agg MP",
            implementing_agency="Agg Agency",
            vendor_id="agg-9",
            vendor_name="Agg Vendor",
            sanctioned_amount_inr=1_000_000.0,
        ),
        make_normalized(
            work_id="W2",
            mp_name="Agg MP",
            implementing_agency="Agg Agency",
            vendor_id="agg-9",
            vendor_name="Agg Vendor",
            sanctioned_amount_inr=2_500_000.5,
        ),
    ]
    scored = [make_scored("W1", flags=["cost_outlier"]), make_scored("W2", flags=[])]

    graph = build_fund_flow_graph(records, scored)

    mp_agency = next(e for e in graph["edges"] if e["target"] == "agency_agg_agency")
    assert mp_agency["work_count"] == 2
    assert mp_agency["total_amount_inr"] == pytest.approx(3_500_000.5)
    assert mp_agency["flagged_work_count"] == 1

    agency_vendor = next(e for e in graph["edges"] if e["target"] == "vendor_agg-9")
    assert agency_vendor["work_count"] == 2
    assert agency_vendor["total_amount_inr"] == pytest.approx(3_500_000.5)
    assert agency_vendor["flagged_work_count"] == 1


def test_edge_work_ids_are_every_contributing_work_id_sorted_and_deduplicated() -> None:
    """F-02, fixed 2026-09-14: adjacency alone (sharing an agency) is not
    evidence of a real fund-flow path -- only a work_id common to both an
    MP->Agency edge and an Agency->Vendor edge is. Two MPs funding the same
    agency, which pays one shared vendor, must each carry only THEIR OWN
    work's id on their own edge -- not each other's -- even though both
    edges point at the same agency.
    """
    records = [
        make_normalized(
            work_id="W1",
            mp_name="MP One",
            implementing_agency="Shared Agency",
            vendor_id="shared-11",
            vendor_name="Shared Vendor",
        ),
        make_normalized(
            work_id="W2",
            mp_name="MP Two",
            implementing_agency="Shared Agency",
            vendor_id="shared-11",
            vendor_name="Shared Vendor",
        ),
    ]
    graph = build_fund_flow_graph(records, [])

    mp_one_edge = next(e for e in graph["edges"] if e["source"] == "mp_mp_one")
    mp_two_edge = next(e for e in graph["edges"] if e["source"] == "mp_mp_two")
    agency_vendor_edge = next(e for e in graph["edges"] if e["target"] == "vendor_shared-11")

    assert mp_one_edge["work_ids"] == ["W1"]
    assert mp_two_edge["work_ids"] == ["W2"]
    # Both W1 and W2 really do pay the shared vendor -- the agency-vendor
    # edge legitimately carries both, unlike either MP's own edge.
    assert agency_vendor_edge["work_ids"] == ["W1", "W2"]


def test_risk_weight_counts_one_per_flagged_work_touching_the_node() -> None:
    records = [
        make_normalized(
            work_id="W1",
            mp_name="RW MP",
            implementing_agency="RW Agency",
            vendor_id="risk-5",
            vendor_name="RW Vendor",
        ),
        make_normalized(
            work_id="W2",
            mp_name="RW MP",
            implementing_agency="RW Agency",
            vendor_id="risk-5",
            vendor_name="RW Vendor",
        ),
    ]
    scored = [
        make_scored("W1", flags=["cost_outlier"]),
        make_scored("W2", flags=["stalled_work"]),
    ]
    graph = build_fund_flow_graph(records, scored)

    weights = {n["id"]: n["risk_weight"] for n in graph["nodes"]}
    assert weights["mp_rw_mp"] == 2.0
    assert weights["agency_rw_agency"] == 2.0
    assert weights["vendor_risk-5"] == 2.0


def test_unflagged_and_unmatched_work_ids_do_not_raise_and_score_zero() -> None:
    records = [
        make_normalized(work_id="W1", mp_name="Quiet MP", implementing_agency="Quiet Agency"),
    ]
    # scored_records has no entry at all for W1 -- must be treated as
    # unflagged, not as an error.
    graph = build_fund_flow_graph(records, [])
    weights = {n["id"]: n["risk_weight"] for n in graph["nodes"]}
    assert weights["mp_quiet_mp"] == 0.0
    assert weights["agency_quiet_agency"] == 0.0


def test_name_node_ids_are_slugs_and_vendor_id_is_collision_free_encoded() -> None:
    records = [
        make_normalized(
            work_id="W1",
            mp_name="Dr. A.P.J. Singh",
            implementing_agency="PWD Division #7",
            vendor_id="PFMS/A B",
            vendor_name="Ganesh & Sons Pvt. Ltd.",
        )
    ]
    graph = build_fund_flow_graph(records, [])
    node_ids = {n["id"] for n in graph["nodes"]}
    assert "mp_dr_a_p_j_singh" in node_ids
    assert "agency_pwd_division_7" in node_ids
    assert "vendor_PFMS%2FA%20B" in node_ids


def test_agency_label_in_another_script_gets_a_stable_ascii_id_instead_of_failing() -> None:
    # One of the 5,867 live IA_NAME strings is Devanagari, which slugs to
    # nothing. The build must still name that agency, keep it distinct from
    # every other one, and return the same id on every run.
    sidhi = "सामाजिक न्याय एवं दिव्यांगजन सशक्तिकरण विभाग सीधी"
    rewa = "सामाजिक न्याय विभाग रीवा"
    records = [
        make_normalized(work_id="W1", implementing_agency=sidhi),
        make_normalized(work_id="W2", implementing_agency=rewa),
    ]

    graph = build_fund_flow_graph(records, [])
    rebuilt = build_fund_flow_graph(records, [])

    agency_nodes = [node for node in graph["nodes"] if node["type"] == "Agency"]
    agency_ids = {node["id"] for node in agency_nodes}
    assert agency_ids == {f"agency_{quote(sidhi, safe='')}", f"agency_{quote(rewa, safe='')}"}
    assert all(node_id.isascii() for node_id in agency_ids)
    assert agency_ids == {n["id"] for n in rebuilt["nodes"] if n["type"] == "Agency"}
    # The id is encoded so it stays ASCII and linkable; the label an officer
    # reads is still the department's own name, untouched.
    assert {node["label"] for node in agency_nodes} == {sidhi, rewa}


def test_label_with_no_letters_or_digits_still_refuses_to_invent_a_node_id() -> None:
    for unusable in ("   ", "###"):
        with pytest.raises(GraphValidationError):
            build_fund_flow_graph([make_normalized(work_id="W1", implementing_agency=unusable)], [])


def test_same_vendor_label_with_different_source_ids_stays_distinct() -> None:
    records = [
        make_normalized(work_id="W1", vendor_id="source/1", vendor_name="DINESH KUMAR"),
        make_normalized(work_id="W2", vendor_id="source 1", vendor_name="DINESH KUMAR"),
    ]

    graph = build_fund_flow_graph(records, [])

    vendor_nodes = [node for node in graph["nodes"] if node["type"] == "Vendor"]
    assert {node["id"] for node in vendor_nodes} == {
        "vendor_source%2F1",
        "vendor_source%201",
    }
    vendor_edges = [
        edge for edge in graph["edges"] if edge["target"] in {node["id"] for node in vendor_nodes}
    ]
    assert len(vendor_edges) == 2


def test_one_source_vendor_id_with_multiple_labels_builds_one_deterministic_node() -> None:
    records = [
        make_normalized(work_id="W3", vendor_id="42", vendor_name="Zeta Works"),
        make_normalized(work_id="W1", vendor_id="42", vendor_name="Alpha Works"),
        make_normalized(work_id="W2", vendor_id="42", vendor_name="Alpha Works"),
    ]

    first = build_fund_flow_graph(records, [])
    second = build_fund_flow_graph(list(reversed(records)), [])

    vendor_nodes = [node for node in first["nodes"] if node["type"] == "Vendor"]
    assert vendor_nodes == [
        {"id": "vendor_42", "type": "Vendor", "label": "Alpha Works", "risk_weight": 0.0}
    ]
    assert first == second


def test_vendor_name_without_a_source_id_never_falls_back_to_name_identity() -> None:
    graph = build_fund_flow_graph(
        [make_normalized(work_id="W1", vendor_id=None, vendor_name="Common Name")],
        [],
    )

    assert not any(node["type"] == "Vendor" for node in graph["nodes"])
    assert not any(edge["target"].startswith("vendor_") for edge in graph["edges"])


def test_build_fund_flow_graph_is_deterministic_on_the_real_fixture(
    works_fixture, scored_fixture
) -> None:
    first = build_fund_flow_graph(works_fixture, scored_fixture)
    second = build_fund_flow_graph(works_fixture, scored_fixture)
    assert first == second


def test_build_fund_flow_graph_is_deterministic_and_ordered_on_synthetic_data() -> None:
    records = [
        make_normalized(work_id="W1", mp_name="Zed MP", implementing_agency="Beta Agency"),
        make_normalized(work_id="W2", mp_name="Alpha MP", implementing_agency="Alpha Agency"),
        make_normalized(work_id="W3", mp_name="Mid MP", implementing_agency="Beta Agency"),
    ]
    first = build_fund_flow_graph(records, [])
    second = build_fund_flow_graph(records, [])
    assert first == second
    # Sorted by id: agency_* < mp_* alphabetically, and within each type,
    # alphabetical by slug.
    node_ids = [n["id"] for n in first["nodes"]]
    assert node_ids == sorted(node_ids)
