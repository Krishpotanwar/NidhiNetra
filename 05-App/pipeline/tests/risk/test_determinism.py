"""score_all() must produce identical output across repeated calls on the
same input. This is what makes the "dated snapshot" product decision
meaningful (README, Execution Plan 3.2, Checkpoints CP2): if ranks are not
reproducible, nothing downstream (the API, the frontend, an inspector's
printed list) can trust them.

Covers both the real fixture (mostly-unflagged, small batch) and a larger
synthetic batch big enough to exercise real peer groups and the
IsolationForest/LOF ensemble, since determinism there depends on
detectors.py's fixed random_state -- a bug that only shows up with n >= 2
records would not be caught by the fixture alone.
"""

from __future__ import annotations

from nidhinetra_pipeline.risk import score_all

from .conftest import AS_OF, make_peer_group


def test_score_all_is_deterministic_on_the_real_fixture(works_fixture) -> None:
    first = score_all(works_fixture, as_of=AS_OF)
    second = score_all(works_fixture, as_of=AS_OF)
    assert first == second


def test_score_all_is_deterministic_on_a_larger_synthetic_batch() -> None:
    records = [
        *make_peer_group(
            35, category="Road", state="Bihar", base_amount=1_000_000.0, spread=40_000.0
        ),
        *make_peer_group(
            32, category="Health", state="Odisha", base_amount=2_000_000.0, spread=60_000.0,
            id_prefix="SYN-PEER-HEALTH",
        ),
    ]
    first = score_all(records, as_of=AS_OF)
    second = score_all(records, as_of=AS_OF)
    assert first == second

    # Also confirm ranks are stable, not merely the flag/score payload --
    # the exact failure mode the eng review flagged for IsolationForest
    # without a fixed random_state.
    first_order = [r["work_id"] for r in first]
    second_order = [r["work_id"] for r in second]
    assert first_order == second_order
