from __future__ import annotations

from nidhinetra_pipeline.risk.rank import assign_ranks, compute_risk_score


def test_compute_risk_score_is_bounded() -> None:
    assert compute_risk_score([], 0.0) == 0.0
    assert compute_risk_score([], 1.0) == 20.0
    all_flags = ["cost_outlier", "stalled_work", "expenditure_mismatch", "agency_concentration"]
    assert compute_risk_score(all_flags, 1.0) == 100.0


def test_compute_risk_score_is_monotonic_in_flag_count() -> None:
    one = compute_risk_score(["cost_outlier"], 0.0)
    two = compute_risk_score(["cost_outlier", "stalled_work"], 0.0)
    assert two > one


def test_assign_ranks_is_dense_1_to_n_with_no_gaps() -> None:
    scored = [
        {"work_id": f"W{i}", "risk_score": float(i)} for i in range(50)
    ]
    ranked = assign_ranks(scored)
    ranks = sorted(r["inspection_rank"] for r in ranked)
    assert ranks == list(range(1, 51))


def test_assign_ranks_orders_by_score_descending() -> None:
    scored = [
        {"work_id": "LOW", "risk_score": 10.0},
        {"work_id": "HIGH", "risk_score": 90.0},
        {"work_id": "MID", "risk_score": 50.0},
    ]
    ranked = assign_ranks(scored)
    by_id = {r["work_id"]: r["inspection_rank"] for r in ranked}
    assert by_id["HIGH"] == 1
    assert by_id["MID"] == 2
    assert by_id["LOW"] == 3


def test_assign_ranks_tie_break_is_work_id_ascending() -> None:
    scored = [
        {"work_id": "ZEBRA", "risk_score": 50.0},
        {"work_id": "APPLE", "risk_score": 50.0},
        {"work_id": "MANGO", "risk_score": 50.0},
    ]
    ranked = assign_ranks(scored)
    by_id = {r["work_id"]: r["inspection_rank"] for r in ranked}
    assert by_id["APPLE"] == 1
    assert by_id["MANGO"] == 2
    assert by_id["ZEBRA"] == 3


def test_assign_ranks_tie_break_is_reproducible() -> None:
    scored = [{"work_id": f"W{i}", "risk_score": 50.0} for i in range(20)]
    first = assign_ranks(scored)
    second = assign_ranks(scored)
    assert [r["work_id"] for r in first] == [r["work_id"] for r in second]
