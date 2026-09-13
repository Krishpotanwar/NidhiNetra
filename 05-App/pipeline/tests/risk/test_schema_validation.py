"""score_all's output must validate against
contracts/risk_scored_record.schema.json, and satisfy the cross-file
invariants contracts/validate.py also checks (dense 1..N ranks, peer_group
non-null iff flags non-empty, peer_group.n >= 30 whenever present).

score_all already validates internally and raises on any violation, so the
mere fact that it returns at all is the first assertion; this file
re-validates independently, the way A4 (an external caller) would, rather
than trusting the engine's own internal check.
"""

from __future__ import annotations

import jsonschema
from nidhinetra_pipeline.risk import score_all

from .conftest import AS_OF


def test_score_all_on_the_real_fixture_returns_one_record_per_work(works_fixture) -> None:
    scored = score_all(works_fixture, as_of=AS_OF)
    assert len(scored) == len(works_fixture)
    assert {r["work_id"] for r in scored} == {w["work_id"] for w in works_fixture}


def test_score_all_output_validates_against_the_frozen_schema(
    works_fixture, risk_scored_schema
) -> None:
    scored = score_all(works_fixture, as_of=AS_OF)
    validator = jsonschema.Draft7Validator(risk_scored_schema)
    errors = []
    for record in scored:
        errors.extend(validator.iter_errors(record))
    assert not errors, [str(e) for e in errors]


def test_score_all_ranks_run_1_to_n_with_no_gaps(works_fixture) -> None:
    scored = score_all(works_fixture, as_of=AS_OF)
    ranks = sorted(r["inspection_rank"] for r in scored)
    assert ranks == list(range(1, len(scored) + 1))


def test_score_all_peer_group_nullness_matches_flags(works_fixture) -> None:
    scored = score_all(works_fixture, as_of=AS_OF)
    for record in scored:
        if record["flags"]:
            assert record["peer_group"] is not None, record["work_id"]
            assert record["peer_group"]["n"] >= 30, record["work_id"]
            assert set(record["why_flagged"]) == set(record["flags"]), record["work_id"]
        else:
            assert record["peer_group"] is None, record["work_id"]
            assert record["why_flagged"] == {}, record["work_id"]


def test_score_all_risk_score_is_in_bounds(works_fixture) -> None:
    scored = score_all(works_fixture, as_of=AS_OF)
    for record in scored:
        assert 0.0 <= record["risk_score"] <= 100.0


def test_works_fixture_is_too_small_for_any_real_peer_group() -> None:
    # Sanity check on the fixture itself, documented so a future reader
    # does not mistake "score_all(works_fixture) flags nothing" for a bug:
    # works.fixture.json has 20 rows spread across many category/state/year
    # combinations, so no real peer group in it can reach the n >= 30
    # floor. scored.fixture.json's illustrative flags are a shape example,
    # not a literal expected output of this engine on this input.
    import json
    from pathlib import Path

    from nidhinetra_pipeline.risk.peer_groups import build_peer_index

    here = Path(__file__).resolve().parents[3] / "contracts" / "fixtures" / "works.fixture.json"
    records = json.loads(here.read_text())
    index = build_peer_index(records)
    assert all(pg.n < 30 for pg in index.values())
