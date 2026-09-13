from __future__ import annotations

from nidhinetra_pipeline.risk.peer_groups import (
    build_peer_index,
    financial_year_of,
    peer_group_for,
    peer_group_key,
)

from .conftest import make_peer_group, make_record


def test_financial_year_prefers_sanction_date() -> None:
    # April onward -> that calendar year starts the FY.
    assert financial_year_of(make_record(sanction_date="2023-04-01")) == "2023-24"
    assert financial_year_of(make_record(sanction_date="2023-12-31")) == "2023-24"
    # January-March -> still the FY that started the previous April.
    assert financial_year_of(make_record(sanction_date="2024-03-31")) == "2023-24"
    assert financial_year_of(make_record(sanction_date="2024-01-01")) == "2023-24"


def test_financial_year_falls_back_to_last_updated_when_sanction_date_missing() -> None:
    record = make_record(sanction_date=None, last_updated="2026-08-15")
    assert financial_year_of(record) == "2026-27"


def test_peer_group_key_requires_category_and_state() -> None:
    assert peer_group_key(make_record(work_category="", state="Bihar")) is None
    assert peer_group_key(make_record(work_category="Road", state="")) is None
    assert peer_group_key(make_record(work_category="Road", state="Bihar")) is not None


def test_peer_group_label_order_is_category_state_year() -> None:
    records = make_peer_group(30, category="Road", state="Bihar", sanction_date="2023-10-01")
    index = build_peer_index(records)
    key = ("Road", "Bihar", "2023-24")
    assert key in index
    assert index[key].label == "Road works, Bihar, 2023-24"


def test_peer_group_for_returns_none_below_floor_and_group_above_floor() -> None:
    records = make_peer_group(30, category="Drinking Water", state="Assam")
    target = records[0]
    assert peer_group_for(target, records).n == 30

    records_small = make_peer_group(10, category="Drinking Water", state="Assam")
    target_small = records_small[0]
    assert peer_group_for(target_small, records_small) is None


def test_peer_group_stats_are_sane() -> None:
    records = make_peer_group(
        30, category="Road", state="Bihar", base_amount=1_000_000.0, spread=0.0
    )
    # spread=0 -> every record costs exactly the same.
    pg = peer_group_for(records[0], records)
    assert pg is not None
    assert pg.median_cost == 1_000_000.0
    assert pg.mean_cost == 1_000_000.0
    assert pg.std_cost == 0.0
