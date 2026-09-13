from __future__ import annotations

from nidhinetra_pipeline.risk.detectors import (
    cost_outlier,
    detect_agency_concentration,
    ensemble_scores,
    expenditure_mismatch,
    stalled_work,
)
from nidhinetra_pipeline.risk.peer_groups import peer_group_for

from .conftest import AS_OF, make_peer_group, make_record

# --------------------------------------------------------------------- #
# cost_outlier
# --------------------------------------------------------------------- #


def test_cost_outlier_fires_on_a_genuine_outlier() -> None:
    peers = make_peer_group(30, category="Road", state="Bihar", base_amount=1_000_000.0)
    target = make_record(
        work_id="COST-OUT", work_category="Road", state="Bihar",
        sanction_date="2023-10-01", sanctioned_amount_inr=10_000_000.0,
    )
    records = [*peers, target]
    peer = peer_group_for(target, records)
    finding = cost_outlier(target, peer)
    assert finding.fired
    assert finding.variant == "default"
    assert finding.params["multiple"] > 1


def test_cost_outlier_does_not_fire_on_ordinary_variation() -> None:
    peers = make_peer_group(30, category="Road", state="Bihar", base_amount=1_000_000.0)
    target = peers[0]
    records = peers
    peer = peer_group_for(target, records)
    finding = cost_outlier(target, peer)
    assert not finding.fired


def test_cost_outlier_does_not_fire_when_peer_group_has_no_spread() -> None:
    peers = make_peer_group(30, base_amount=1_000_000.0, spread=0.0)
    peer = peer_group_for(peers[0], peers)
    finding = cost_outlier(peers[0], peer)
    assert not finding.fired  # std == 0, cannot compute a meaningful z


# --------------------------------------------------------------------- #
# stalled_work
# --------------------------------------------------------------------- #


def test_stalled_work_fires_on_zero_spend_after_threshold_months() -> None:
    record = make_record(
        completion_status="In Progress",
        sanction_date="2023-01-01",  # >> 6 months before AS_OF (2026-09-01)
        expenditure_amount_inr=0.0,
    )
    finding = stalled_work(record, AS_OF)
    assert finding.fired
    assert finding.variant == "zero_spend"
    assert finding.params["months"] > 0


def test_stalled_work_does_not_fire_within_the_grace_period() -> None:
    record = make_record(
        completion_status="In Progress",
        sanction_date="2026-08-01",  # one month before AS_OF
        expenditure_amount_inr=0.0,
    )
    finding = stalled_work(record, AS_OF)
    assert not finding.fired


def test_stalled_work_does_not_fire_on_completed_work() -> None:
    record = make_record(
        completion_status="Completed",
        sanction_date="2020-01-01",
        expenditure_amount_inr=0.0,
    )
    finding = stalled_work(record, AS_OF)
    assert not finding.fired


def test_stalled_work_part_spend_variant() -> None:
    record = make_record(
        completion_status="In Progress",
        sanction_date="2023-01-01",
        sanctioned_amount_inr=1_000_000.0,
        expenditure_amount_inr=20_000.0,  # 2 percent spent
    )
    finding = stalled_work(record, AS_OF)
    assert finding.fired
    assert finding.variant == "part_spend"


# --------------------------------------------------------------------- #
# expenditure_mismatch
# --------------------------------------------------------------------- #


def test_expenditure_mismatch_fires_when_spend_exceeds_sanction() -> None:
    peers = make_peer_group(30, category="Road", state="Bihar")
    target = make_record(
        work_id="OVER-SANCTION", work_category="Road", state="Bihar",
        sanction_date="2023-10-01",
        sanctioned_amount_inr=1_000_000.0,
        expenditure_amount_inr=1_500_000.0,
    )
    records = [*peers, target]
    peer = peer_group_for(target, records)
    finding = expenditure_mismatch(target, peer)
    assert finding.fired
    assert finding.variant == "over_sanction"
    assert finding.params["percent_over"] > 0


def test_expenditure_mismatch_fires_on_full_spend_while_open() -> None:
    peers = make_peer_group(30, category="Road", state="Bihar")
    target = make_record(
        work_id="FULL-SPEND-OPEN", work_category="Road", state="Bihar",
        sanction_date="2023-10-01",
        sanctioned_amount_inr=1_000_000.0,
        expenditure_amount_inr=1_000_000.0,
        completion_status="In Progress",
    )
    records = [*peers, target]
    peer = peer_group_for(target, records)
    finding = expenditure_mismatch(target, peer)
    assert finding.fired
    assert finding.variant == "full_spend_open"


def test_expenditure_mismatch_does_not_fire_on_ordinary_partial_spend() -> None:
    peers = make_peer_group(30, category="Road", state="Bihar")
    target = peers[0]
    peer = peer_group_for(target, peers)
    finding = expenditure_mismatch(target, peer)
    assert not finding.fired


# --------------------------------------------------------------------- #
# agency_concentration (cross-record)
# --------------------------------------------------------------------- #


def test_agency_concentration_fires_for_an_agency_spanning_many_mps() -> None:
    concentrated = [
        make_record(
            work_id=f"CONC-{i}",
            implementing_agency="Everywhere Works Ltd",
            mp_name=f"MP {i}",
            constituency=f"Bihar Constituency {i}",
        )
        for i in range(10)
    ]
    # A pile of ordinary agencies, each serving exactly one MP, so
    # "Everywhere Works Ltd" is a genuine statistical outlier in span.
    ordinary = [
        make_record(
            work_id=f"ORD-{i}",
            implementing_agency=f"Local Agency {i}",
            mp_name=f"Other MP {i}",
            constituency=f"Bihar Constituency {100 + i}",
        )
        for i in range(20)
    ]
    findings = detect_agency_concentration([*concentrated, *ordinary])
    assert all(wid in findings for wid in (r["work_id"] for r in concentrated))
    assert findings["CONC-0"].variant in ("mps", "districts_and_mps")
    assert not any(wid in findings for wid in (r["work_id"] for r in ordinary))


def test_agency_concentration_does_not_fire_when_everyone_spans_similarly() -> None:
    records = [
        make_record(
            work_id=f"UNIFORM-{i}",
            implementing_agency=f"Agency {i // 2}",  # each agency has 2 works
            mp_name=f"MP {i}",
            constituency=f"Bihar Constituency {i}",
        )
        for i in range(20)
    ]
    findings = detect_agency_concentration(records)
    assert findings == {}


def test_agency_concentration_respects_the_absolute_floor() -> None:
    # One agency spans 2 MPs, everyone else spans 1 -- statistically
    # unusual in a population this uniform, but 2 is below
    # MIN_SPAN_FOR_CONCENTRATION and must not fire regardless.
    records = [
        make_record(work_id="A-0", implementing_agency="Agency A", mp_name="MP 0"),
        make_record(work_id="A-1", implementing_agency="Agency A", mp_name="MP 1"),
    ] + [
        make_record(
            work_id=f"SOLO-{i}", implementing_agency=f"Solo Agency {i}", mp_name=f"MP {i + 2}"
        )
        for i in range(20)
    ]
    findings = detect_agency_concentration(records)
    assert findings == {}


# --------------------------------------------------------------------- #
# ensemble_scores
# --------------------------------------------------------------------- #


def test_ensemble_scores_are_bounded_and_cover_every_work_id() -> None:
    records = make_peer_group(30, spread=50_000.0)
    scores = ensemble_scores(records, AS_OF)
    assert set(scores) == {r["work_id"] for r in records}
    assert all(0.0 <= v <= 1.0 for v in scores.values())


def test_ensemble_scores_degenerate_case_under_two_records() -> None:
    records = make_peer_group(1)
    scores = ensemble_scores(records, AS_OF)
    assert scores == {records[0]["work_id"]: 0.0}


def test_ensemble_scores_are_deterministic_across_calls() -> None:
    records = make_peer_group(40, spread=75_000.0)
    first = ensemble_scores(records, AS_OF)
    second = ensemble_scores(records, AS_OF)
    assert first == second
