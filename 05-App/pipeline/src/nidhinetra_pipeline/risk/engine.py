"""score_all: the single entry point A4 (and this package's own tests)
call.

Runs the whole risk pipeline in order -- peer groups, the three per-record
detectors, the cross-record agency/vendor concentration pass, the
IsolationForest/LOF ensemble, why_flagged rendering, and ranking -- then
validates every output record against
contracts/risk_scored_record.schema.json before returning. Fails loud
(raises ValueError) on any schema violation: this is A2's own contract
with A4, and honouring it here, in code, is what lets A4 trust the output
without re-validating it.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import jsonschema

from .detectors import (
    cost_outlier,
    detect_agency_concentration,
    ensemble_scores,
    expenditure_mismatch,
    stalled_work,
)
from .explain import render
from .peer_groups import build_peer_index, peer_group_for
from .rank import assign_ranks, compute_risk_score

# .../05-App/pipeline/src/nidhinetra_pipeline/risk/engine.py
# parents[4] == ".../05-App"
SCHEMA_PATH = (
    Path(__file__).resolve().parents[4] / "contracts" / "risk_scored_record.schema.json"
)


def score_all(records: list[dict[str, Any]], as_of: date | None = None) -> list[dict[str, Any]]:
    """records: normalized records matching contracts/normalized_record.schema.json
    (contract 3.1). as_of: the reference date for "months since sanction"
    style calculations; defaults to date.today(). Pass an explicit as_of
    for reproducible output across days (score_all's own determinism
    guarantee is about two calls with the *same* as_of, not about calendar
    days passing between them).

    Returns records matching contracts/risk_scored_record.schema.json
    (contract 3.2), sorted by inspection_rank ascending.

    Detectors run in this fixed order for every record, on the same input
    record order the caller supplies. That, plus IsolationForest's fixed
    random_state and LOF's determinism, is what makes two calls to
    score_all() on the same input produce identical output -- see the
    determinism tests in tests/risk.
    """
    if as_of is None:
        as_of = date.today()

    peer_index = build_peer_index(records)
    concentration = detect_agency_concentration(records)
    ensemble = ensemble_scores(records, as_of)

    scored: list[dict[str, Any]] = []
    for record in records:
        work_id = record["work_id"]
        # The eng review rule, enforced exactly once, here: a record whose
        # true peer group has fewer than MIN_PEER_GROUP_N members gets
        # `peer` = None, and every detector below is skipped entirely for
        # it -- not run-and-suppressed, not flagged-with-a-caveat, simply
        # never evaluated. stalled_work does not statistically need a peer
        # group to fire, but risk_scored_record.schema.json requires
        # peer_group to be non-null on *any* non-empty flags array
        # (including agency_concentration alone), so the gate applies to
        # all four flags uniformly.
        peer = peer_group_for(record, records, index=peer_index)

        flags: list[str] = []
        why_flagged: dict[str, str] = {}

        if peer is not None:
            # stalled_work takes `as_of` rather than a peer group -- it is
            # not statistically peer-relative (see its docstring) -- but
            # still only runs inside this `peer is not None` gate, per the
            # schema-wide peer_group requirement noted above.
            findings = (
                cost_outlier(record, peer),
                stalled_work(record, as_of),
                expenditure_mismatch(record, peer),
            )
            for finding in findings:
                if not finding.fired:
                    continue
                flags.append(finding.flag)
                why_flagged[finding.flag] = render(finding.flag, finding.variant, finding.params)

            conc = concentration.get(work_id)
            if conc is not None:
                flags.append("agency_concentration")
                why_flagged["agency_concentration"] = render(
                    "agency_concentration", conc.variant, conc.params
                )

        risk_score = compute_risk_score(flags, ensemble.get(work_id, 0.0))
        scored.append(
            {
                "work_id": work_id,
                "risk_score": risk_score,
                "flags": flags,
                "why_flagged": why_flagged,
                # Mandatory non-null whenever flags is non-empty, null
                # otherwise (risk_scored_record.schema.json) -- gated on
                # `flags` here, not merely on `peer is not None`, so a
                # record with a valid-but-quiet peer group (no detector
                # fired) still correctly reports peer_group = null.
                "peer_group": peer.as_contract() if (peer is not None and flags) else None,
            }
        )

    ranked = assign_ranks(scored)
    _validate(ranked)
    return ranked


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text())


def _validate(scored: list[dict[str, Any]]) -> None:
    schema = _load_schema()
    validator = jsonschema.Draft7Validator(schema)
    errors: list[str] = []
    for record in scored:
        for err in validator.iter_errors(record):
            path = ".".join(str(p) for p in err.path) or "<root>"
            errors.append(f"{record.get('work_id', '?')} ({path}): {err.message}")
    if errors:
        raise ValueError(
            "score_all produced record(s) that violate "
            "risk_scored_record.schema.json:\n" + "\n".join(errors)
        )
