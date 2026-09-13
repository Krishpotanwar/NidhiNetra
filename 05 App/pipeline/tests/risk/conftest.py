"""Shared fixtures for the risk engine test suite (A2's lane only -- see
pipeline/tests/ingest and pipeline/tests/normalize for A1's).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

# .../05 App/pipeline/tests/risk/conftest.py -> parents[3] == ".../05 App"
CONTRACTS_DIR = Path(__file__).resolve().parents[3] / "contracts"

# Fixed reference date for every test that needs "months since sanction"
# style math, so tests never depend on the wall-clock day they happen to
# run on.
AS_OF = date(2026, 9, 1)


@pytest.fixture(scope="session")
def contracts_dir() -> Path:
    return CONTRACTS_DIR


@pytest.fixture(scope="session")
def works_fixture() -> list[dict[str, Any]]:
    return json.loads((CONTRACTS_DIR / "fixtures" / "works.fixture.json").read_text())


@pytest.fixture(scope="session")
def risk_scored_schema() -> dict[str, Any]:
    return json.loads((CONTRACTS_DIR / "risk_scored_record.schema.json").read_text())


@pytest.fixture(scope="session")
def strings_contract() -> dict[str, Any]:
    return json.loads((CONTRACTS_DIR / "strings.json").read_text())


@pytest.fixture
def as_of() -> date:
    return AS_OF


def make_record(**overrides: Any) -> dict[str, Any]:
    """A minimal, schema-valid normalized_record.schema.json record, with
    sane defaults any test can override. Not a pytest fixture itself (it
    takes arguments), but the building block `many_records` and individual
    tests use to construct synthetic peer groups of a chosen size.
    """
    record = {
        "work_id": "SYN-0000",
        "state": "Bihar",
        "constituency": "Bihar Constituency 1",
        "mp_name": "Test MP",
        "tenure": "2024-2029",
        "implementing_agency": "Test Agency",
        "vendor_name": "Test Vendor",
        "work_category": "Road",
        "sanctioned_amount_inr": 1_000_000.0,
        "expenditure_amount_inr": 500_000.0,
        "sanction_date": "2023-10-01",
        "completion_status": "In Progress",
        "last_updated": "2026-08-15",
        "source_rung": 5,
    }
    record.update(overrides)
    return record


def make_peer_group(
    n: int,
    *,
    category: str = "Road",
    state: str = "Bihar",
    sanction_date: str = "2023-10-01",
    base_amount: float = 1_000_000.0,
    spread: float = 20_000.0,
    id_prefix: str = "SYN-PEER",
    **shared_overrides: Any,
) -> list[dict[str, Any]]:
    """n schema-valid records sharing one (category, state, financial_year)
    peer group key, with sanctioned_amount_inr varying only slightly around
    base_amount so the group has a well-defined, small-but-nonzero spread
    (needed for a meaningful std/z-score in tests that check the group
    itself does NOT fire on ordinary variation).
    """
    records = []
    for i in range(n):
        amount = base_amount + spread * (i % 5 - 2)  # -2..+2 steps
        records.append(
            make_record(
                work_id=f"{id_prefix}-{i:04d}",
                work_category=category,
                state=state,
                sanction_date=sanction_date,
                sanctioned_amount_inr=amount,
                expenditure_amount_inr=amount * 0.5,
                mp_name=f"MP {i % 7}",
                constituency=f"{state} Constituency {i % 7}",
                **shared_overrides,
            )
        )
    return records
