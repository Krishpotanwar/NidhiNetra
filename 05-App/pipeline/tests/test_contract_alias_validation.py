"""R-06 cross-file validation for the alias-candidate fixture."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = APP_ROOT / "contracts"

_VALIDATE_SPEC = importlib.util.spec_from_file_location(
    "nidhinetra_contract_validate", CONTRACTS / "validate.py"
)
assert _VALIDATE_SPEC is not None and _VALIDATE_SPEC.loader is not None
_VALIDATE_MODULE = importlib.util.module_from_spec(_VALIDATE_SPEC)
_VALIDATE_SPEC.loader.exec_module(_VALIDATE_MODULE)
validate_all = _VALIDATE_MODULE.validate_all


def test_alias_candidate_evidence_must_name_a_real_fixture_work(tmp_path: Path) -> None:
    aliases = [
        {
            "entity_type": "vendor",
            "proposed_canonical_id": "SYNTH-V001",
            "alias_label": "Rajdhani Civil Works",
            "reason": "identifier_has_multiple_labels",
            "evidence_work_ids": ["NOT-A-REAL-WORK"],
        }
    ]
    aliases_path = tmp_path / "aliases.json"
    aliases_path.write_text(json.dumps(aliases), encoding="utf-8")

    errors = validate_all(
        CONTRACTS / "fixtures" / "works.fixture.json",
        CONTRACTS / "fixtures" / "scored.fixture.json",
        CONTRACTS / "fixtures" / "graph.fixture.json",
        aliases_path,
    )

    assert any("NOT-A-REAL-WORK" in error and "alias candidate" in error for error in errors)


def test_committed_alias_fixture_passes_cross_file_validation() -> None:
    assert (
        validate_all(
            CONTRACTS / "fixtures" / "works.fixture.json",
            CONTRACTS / "fixtures" / "scored.fixture.json",
            CONTRACTS / "fixtures" / "graph.fixture.json",
            CONTRACTS / "fixtures" / "alias_candidates.fixture.json",
        )
        == []
    )
