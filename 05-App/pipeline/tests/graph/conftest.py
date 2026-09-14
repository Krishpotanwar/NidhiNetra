"""Shared fixtures for the graph test suite (A3's lane only -- see
pipeline/tests/normalize and pipeline/tests/risk for A1's and A2's).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

# .../05-App/pipeline/tests/graph/conftest.py -> parents[3] == ".../05-App"
CONTRACTS_DIR = Path(__file__).resolve().parents[3] / "contracts"


@pytest.fixture(scope="session")
def contracts_dir() -> Path:
    return CONTRACTS_DIR


@pytest.fixture(scope="session")
def works_fixture() -> list[dict[str, Any]]:
    return json.loads((CONTRACTS_DIR / "fixtures" / "works.fixture.json").read_text())


@pytest.fixture(scope="session")
def scored_fixture() -> list[dict[str, Any]]:
    return json.loads((CONTRACTS_DIR / "fixtures" / "scored.fixture.json").read_text())


@pytest.fixture(scope="session")
def graph_schema() -> dict[str, Any]:
    return json.loads((CONTRACTS_DIR / "fund_flow_graph.schema.json").read_text())


@pytest.fixture(scope="session")
def graph_fixture() -> dict[str, Any]:
    return json.loads((CONTRACTS_DIR / "fixtures" / "graph.fixture.json").read_text())


def make_normalized(**overrides: Any) -> dict[str, Any]:
    """A minimal, schema-valid normalized_record.schema.json record, with
    sane defaults any test can override.
    """
    record = {
        "work_id": "SYN-0000",
        "state": "Bihar",
        "constituency": "Bihar Constituency 1",
        "mp_name": "Test MP",
        "tenure": "2024-2029",
        "implementing_agency": "Test Agency",
        "vendor_id": "test-vendor-id",
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


def make_scored(work_id: str, *, flags: list[str] | None = None) -> dict[str, Any]:
    """A minimal, schema-valid risk_scored_record.schema.json record."""
    flags = flags or []
    why_flagged = {flag: f"synthetic reason for {flag}" for flag in flags}
    return {
        "work_id": work_id,
        "inspection_rank": 1,
        "risk_score": 75.0 if flags else 10.0,
        "flags": flags,
        "why_flagged": why_flagged,
        "peer_group": {"label": "Synthetic peer group", "n": 30} if flags else None,
    }
