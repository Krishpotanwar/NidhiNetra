"""Tests for normalize/normalize.py."""

from __future__ import annotations

import copy
from datetime import date

import pytest
from nidhinetra_pipeline.normalize.normalize import (
    SCHEMA_PATH,
    NormalizeValidationError,
    normalize_records,
)

VALID_RAW_RECORD = {
    "work_id": "MPLADS-TEST-0001",
    "state": "Bihar",
    "constituency": "Bihar Constituency 1",
    "mp_name": "Test MP",
    "tenure": "2024-2029",
    "implementing_agency": "PWD Division 1",
    "vendor_id": "vendor-42",
    "vendor_name": "Test Vendor Pvt Ltd",
    "work_category": "Road",
    "sanctioned_amount_inr": 1000000.0,
    "expenditure_amount_inr": 500000.0,
    "sanction_date": "2024-01-01",
    "completion_status": "In Progress",
    "last_updated": "2026-08-01",
}


def test_schema_path_exists():
    assert SCHEMA_PATH.exists(), f"expected schema at {SCHEMA_PATH}"
    assert SCHEMA_PATH.name == "normalized_record.schema.json"


def test_normalize_happy_path_stamps_source_rung():
    result = normalize_records([VALID_RAW_RECORD], source_rung=1)

    assert len(result) == 1
    record = result[0]
    assert record["work_id"] == "MPLADS-TEST-0001"
    assert record["vendor_id"] == "vendor-42"
    assert record["source_rung"] == 1


def test_normalize_source_rung_overrides_whatever_raw_row_carried():
    raw = dict(VALID_RAW_RECORD)
    raw["source_rung"] = 99  # must never leak through; caller's rung is authoritative

    result = normalize_records([raw], source_rung=3)

    assert result[0]["source_rung"] == 3


def test_normalize_multiple_valid_records():
    raw_2 = dict(VALID_RAW_RECORD, work_id="MPLADS-TEST-0002")
    result = normalize_records([VALID_RAW_RECORD, raw_2], source_rung=5)

    assert [r["work_id"] for r in result] == ["MPLADS-TEST-0001", "MPLADS-TEST-0002"]
    assert all(r["source_rung"] == 5 for r in result)


def test_normalize_defaults_expenditure_to_zero_when_missing():
    raw = dict(VALID_RAW_RECORD)
    del raw["expenditure_amount_inr"]

    result = normalize_records([raw], source_rung=5)

    assert result[0]["expenditure_amount_inr"] == 0


def test_normalize_defaults_last_updated_to_today_when_missing():
    raw = dict(VALID_RAW_RECORD)
    del raw["last_updated"]

    result = normalize_records([raw], source_rung=5)

    assert result[0]["last_updated"] == date.today().isoformat()


def test_normalize_allows_null_implementing_agency_and_vendor_identity():
    raw = dict(
        VALID_RAW_RECORD,
        implementing_agency=None,
        vendor_id=None,
        vendor_name=None,
    )

    result = normalize_records([raw], source_rung=5)

    assert result[0]["implementing_agency"] is None
    assert result[0]["vendor_id"] is None
    assert result[0]["vendor_name"] is None


def test_normalize_maps_a_missing_vendor_id_to_explicit_null_for_old_caches():
    raw = dict(VALID_RAW_RECORD)
    del raw["vendor_id"]

    result = normalize_records([raw], source_rung=5)

    assert "vendor_id" in result[0]
    assert result[0]["vendor_id"] is None


# --------------------------------------------------------------------------
# Rejections -- the load-bearing behavior: never silently emit invalid records
# --------------------------------------------------------------------------


def test_normalize_rejects_record_missing_required_field_work_id():
    raw = dict(VALID_RAW_RECORD)
    del raw["work_id"]

    with pytest.raises(NormalizeValidationError, match="work_id"):
        normalize_records([raw], source_rung=5)


def test_normalize_rejects_record_missing_required_field_state():
    raw = dict(VALID_RAW_RECORD)
    del raw["state"]

    with pytest.raises(NormalizeValidationError):
        normalize_records([raw], source_rung=5)


def test_normalize_rejects_record_missing_sanctioned_amount():
    raw = dict(VALID_RAW_RECORD)
    del raw["sanctioned_amount_inr"]

    with pytest.raises(NormalizeValidationError, match="sanctioned_amount_inr"):
        normalize_records([raw], source_rung=5)


def test_normalize_rejects_invalid_work_category_enum():
    raw = dict(VALID_RAW_RECORD, work_category="Not A Real Category")

    with pytest.raises(NormalizeValidationError):
        normalize_records([raw], source_rung=5)


def test_normalize_rejects_invalid_tenure_pattern():
    raw = dict(VALID_RAW_RECORD, tenure="not-a-tenure")

    with pytest.raises(NormalizeValidationError):
        normalize_records([raw], source_rung=5)


def test_normalize_rejects_negative_sanctioned_amount():
    raw = dict(VALID_RAW_RECORD, sanctioned_amount_inr=-500.0)

    with pytest.raises(NormalizeValidationError):
        normalize_records([raw], source_rung=5)


def test_normalize_rejects_out_of_range_source_rung():
    with pytest.raises(NormalizeValidationError):
        normalize_records([VALID_RAW_RECORD], source_rung=6)

    with pytest.raises(NormalizeValidationError):
        normalize_records([VALID_RAW_RECORD], source_rung=0)


def test_normalize_rejects_non_dict_row():
    with pytest.raises(NormalizeValidationError):
        normalize_records(["not a dict"], source_rung=5)


def test_normalize_is_all_or_nothing_across_a_batch():
    """One bad record in a batch must fail the whole call -- no partial,
    invalid list is ever returned to the caller.
    """
    bad = dict(VALID_RAW_RECORD)
    del bad["work_id"]
    good = dict(VALID_RAW_RECORD, work_id="MPLADS-TEST-0002")

    with pytest.raises(NormalizeValidationError):
        normalize_records([good, bad], source_rung=5)


def test_normalize_does_not_mutate_input_records():
    original = copy.deepcopy(VALID_RAW_RECORD)
    normalize_records([VALID_RAW_RECORD], source_rung=5)

    assert VALID_RAW_RECORD == original
