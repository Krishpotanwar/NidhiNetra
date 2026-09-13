"""THE CRITICAL TEST for this codebase, per the eng review that produced the
peer-group-n-30 rule (Execution Plan 3.2, Checkpoints CP2,
risk_scored_record.schema.json peer_group.n minimum).

A work whose true peer group has fewer than 30 comparable works must NEVER
be flagged, no matter how statistically extreme its numbers are. Not
flagged weakly, not flagged with a caveat -- excluded from flagging
entirely, with peer_group left null. This file asserts that holds even
when every other signal (cost, stalled spend, expenditure ratio, agency
footprint) is pushed to an extreme that would fire every detector if the
peer group were large enough.
"""

from __future__ import annotations

from nidhinetra_pipeline.risk import score_all
from nidhinetra_pipeline.risk.peer_groups import MIN_PEER_GROUP_N, peer_group_for

from .conftest import AS_OF, make_peer_group, make_record


def test_min_peer_group_n_is_30() -> None:
    # Pin the constant itself: if this ever drifts, every test in this
    # file is silently testing the wrong number.
    assert MIN_PEER_GROUP_N == 30


def test_tiny_peer_group_is_never_flagged_even_at_extreme_cost() -> None:
    # A peer group of exactly 3 -- the scenario named explicitly in this
    # agent's brief. Costs are ordinary and tightly clustered.
    peers = make_peer_group(3, category="Health", state="Sikkim", base_amount=1_000_000.0)
    extreme = make_record(
        work_id="SYN-EXTREME-COST",
        work_category="Health",
        state="Sikkim",
        sanction_date="2023-10-01",
        # 50x the peer median. If this peer group were >= 30, this would
        # trivially clear the z > 2.5 cost_outlier threshold.
        sanctioned_amount_inr=50_000_000.0,
        expenditure_amount_inr=0.0,
        completion_status="In Progress",
    )
    records = [*peers, extreme]

    peer = peer_group_for(extreme, records)
    assert peer is None, "peer group of 3 must be treated as absent, not merely small"

    scored = score_all(records, as_of=AS_OF)
    result = next(r for r in scored if r["work_id"] == "SYN-EXTREME-COST")

    assert result["flags"] == []
    assert result["why_flagged"] == {}
    assert result["peer_group"] is None


def test_peer_group_of_29_is_still_never_flagged() -> None:
    # One below the floor -- the boundary the schema and this rule are
    # actually drawn at, not just "obviously tiny".
    peers = make_peer_group(28, category="School", state="Goa", base_amount=800_000.0)
    extreme = make_record(
        work_id="SYN-BOUNDARY-29",
        work_category="School",
        state="Goa",
        sanction_date="2023-10-01",
        sanctioned_amount_inr=40_000_000.0,
        expenditure_amount_inr=0.0,
        completion_status="Sanctioned",
    )
    records = [*peers, extreme]  # 28 peers + this record = 29 total in the group

    assert peer_group_for(extreme, records) is None

    scored = score_all(records, as_of=AS_OF)
    result = next(r for r in scored if r["work_id"] == "SYN-BOUNDARY-29")
    assert result["flags"] == []
    assert result["peer_group"] is None


def test_peer_group_of_30_is_eligible_to_be_flagged() -> None:
    # Exactly the floor, on the other side: this is the smallest group the
    # rule allows to be flagged at all, so a genuine outlier here SHOULD
    # fire -- proving the gate is a floor, not a blanket suppression.
    peers = make_peer_group(29, category="Electricity", state="Manipur", base_amount=900_000.0)
    extreme = make_record(
        work_id="SYN-BOUNDARY-30",
        work_category="Electricity",
        state="Manipur",
        sanction_date="2023-10-01",
        sanctioned_amount_inr=45_000_000.0,
        expenditure_amount_inr=0.0,
        completion_status="Sanctioned",
    )
    records = [*peers, extreme]  # 29 peers + this record = 30 total

    peer = peer_group_for(extreme, records)
    assert peer is not None
    assert peer.n == 30

    scored = score_all(records, as_of=AS_OF)
    result = next(r for r in scored if r["work_id"] == "SYN-BOUNDARY-30")
    assert "cost_outlier" in result["flags"]
    assert result["peer_group"] is not None
    assert result["peer_group"]["n"] >= MIN_PEER_GROUP_N


def test_small_peer_group_is_never_widened_to_reach_30() -> None:
    # A small, specific group (Health works in one state/year) must not be
    # rescued by folding in a broader category. peer_group_for has no
    # widening path at all -- this test asserts the *key* used stays fully
    # specific (category, state, year), not that widening was attempted
    # and failed.
    from nidhinetra_pipeline.risk.peer_groups import peer_group_key

    record = make_record(work_category="Health", state="Sikkim", sanction_date="2023-10-01")
    key = peer_group_key(record)
    assert key == ("Health", "Sikkim", "2023-24")
    # The key is exactly this triple -- there is no broader-category
    # fallback key this function could ever produce instead.
