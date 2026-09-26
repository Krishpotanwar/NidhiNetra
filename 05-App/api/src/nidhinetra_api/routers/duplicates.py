"""Phase 1 Stage C: duplicate-review queue and append-only review endpoint.

Syncs only the artifact's identical batches -- see the Stage C plan's Decision 1. Near-copy pairs
stay in duplicate_candidates.json until Stage D narrows them by judge answer.
"""

from __future__ import annotations

import contextlib
import json
import logging
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from nidhinetra_pipeline.duplicates.judged_candidates import build_judged_candidates
from nidhinetra_pipeline.duplicates.judged_candidates import judge_rates as compute_judge_rates
from nidhinetra_pipeline.judge import store as judge_store
from nidhinetra_pipeline.outcomes import duplicate_store
from pydantic import BaseModel, ConfigDict, Field

from .. import db
from ..models import DuplicateQuery, Envelope, duplicate_query

logger = logging.getLogger("nidhinetra_api.duplicates")

router = APIRouter(prefix="/api/duplicates", tags=["duplicates"])

_SYNCED_FINDERS = frozenset({"identical_batch", "district_identical_batch"})


class DuplicateReviewRequest(BaseModel):
    """Only human input crosses the API boundary; the server owns timing and supersession."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: str
    reviewed_by: Annotated[str, Field(min_length=1)]
    reviewer_note: str = ""


_EVIDENCE_SELECT = """
    SELECT
        works.work_id,
        works.state,
        works.constituency,
        works.mp_name,
        works.implementing_district_authority,
        works.implementing_agency,
        works.work_description,
        works.sanctioned_amount_inr,
        works.completion_status
    FROM works
"""


def sync_duplicate_candidates_from_snapshot(snapshot_dir: Path | None = None) -> int:
    """Upsert the artifact's identical batches into persistent review state.

    Reads the whole file once, at sync time, never per request; on a memory-constrained host
    this is the one place duplicate_candidates.json is fully parsed (see the Stage C plan's
    Decision 5). Older snapshots predate Stage A and have no artifact; they remain bootable with
    an empty queue, and the next successful rebuild syncs it.
    """
    duplicate_store.init_db()
    path = (snapshot_dir or db.SNAPSHOT_DIR) / "duplicate_candidates.json"
    if not path.exists():
        logger.warning(
            "Snapshot has no %s; duplicate review queue is empty until a rebuild.",
            path.name,
        )
        return 0
    artifact = json.loads(path.read_text(encoding="utf-8"))
    groups = artifact["groups"]
    finder_version = artifact["meta"]["finder_version"]
    candidates = [
        {
            "finder": batch["finder"],
            "scope": batch["scope"],
            "fingerprint_a": groups[batch["group"]]["text_fingerprint"],
            "fingerprint_b": groups[batch["group"]]["text_fingerprint"],
            "finder_version": finder_version,
            "threshold_crossing_batch": batch["threshold_crossing_batch"],
            "text": groups[batch["group"]]["text"],
            "work_ids": groups[batch["group"]]["work_ids"],
        }
        for batch in artifact["batches"]
        if batch["finder"] in _SYNCED_FINDERS
    ]
    return duplicate_store.upsert_candidates(candidates)


def sync_judged_candidates_from_judgments(
    snapshot_dir: Path | None = None,
    judgments_dir: Path | None = None,
) -> int:
    """Stage D-lite: upsert judged, discriminating-fact same_asset_same_place pairs as work-level
    review candidates (nidhinetra_pipeline.duplicates.judged_candidates).

    Widens Stage C's Decision 1 (docs/superpowers/plans/2026-09-22-phase-1-stage-c-review-store.md),
    which deferred near-copy pairs until "Stage D has narrowed them by judge answer" -- Stage B's
    completed judge run is exactly that narrowing, for same_asset_same_place. Safe when either file
    is missing (a snapshot or a judgments run that predates this pass). Does not re-validate the
    artifact against duplicate_candidates.schema.json, matching sync_duplicate_candidates_from_
    snapshot's own precedent: the artifact was already validated when Stage A's builder wrote it.
    """
    duplicate_store.init_db()
    candidates_path = (snapshot_dir or db.SNAPSHOT_DIR) / "duplicate_candidates.json"
    judgments_path = (judgments_dir or db.JUDGMENTS_DIR) / judge_store.FILENAME
    if not candidates_path.exists() or not judgments_path.exists():
        logger.warning(
            "Snapshot has no %s or no %s; the judged near-copy queue is empty until both exist.",
            candidates_path.name,
            judgments_path.name,
        )
        return 0
    artifact = json.loads(candidates_path.read_text(encoding="utf-8"))
    judgments = judge_store.read_judgments(judgments_path)
    candidates = build_judged_candidates(artifact, judgments)
    return duplicate_store.upsert_candidates(candidates)


def _judge_rates_meta(judgments_dir: Path | None = None) -> dict[str, float | int | None]:
    """The two rates the spec allows reporting for the judge's own run, plus the population they
    are of. None until a judgments file exists; read fresh every call (the file is ~1.6 MB, a
    pandas read is milliseconds -- see the Stage D-lite plan's Decision D7)."""
    path = (judgments_dir or db.JUDGMENTS_DIR) / judge_store.FILENAME
    if not path.exists():
        return {
            "judge_abstention_rate": None,
            "judge_quote_rejection_rate": None,
            "judge_pairs_total": None,
        }
    rates = compute_judge_rates(judge_store.read_judgments(path))
    return {
        "judge_abstention_rate": rates["abstention_rate"],
        "judge_quote_rejection_rate": rates["quote_rejection_rate"],
        "judge_pairs_total": rates["pairs_total"],
    }


def _evidence_by_id(work_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not work_ids:
        return {}
    placeholders = ", ".join("?" for _ in work_ids)
    with contextlib.closing(db.connect()) as connection:
        rows = db.rows_as_dicts(
            connection,
            f"{_EVIDENCE_SELECT} WHERE works.work_id IN ({placeholders})",
            work_ids,
        )
    return {row["work_id"]: row for row in rows}


@router.get("")
def list_duplicates(query: DuplicateQuery = Depends(duplicate_query)) -> Envelope:  # noqa: B008
    candidates, total = duplicate_store.list_candidates(
        status=query.status,
        page=query.page,
        page_size=query.page_size,
    )
    work_ids = sorted({work_id for candidate in candidates for work_id in candidate["work_ids"]})
    evidence_by_id = _evidence_by_id(work_ids)
    for candidate in candidates:
        candidate["evidence_works"] = [
            evidence_by_id[work_id]
            for work_id in candidate["work_ids"]
            if work_id in evidence_by_id
        ]

    return Envelope(
        success=True,
        data=candidates,
        meta={
            "page": query.page,
            "page_size": query.page_size,
            "total": total,
            "total_pages": -(-total // query.page_size) if total else 0,
            **_judge_rates_meta(),
        },
    )


@router.post("/{candidate_id}/review")
def review_duplicate(candidate_id: int, payload: DuplicateReviewRequest) -> Envelope:
    try:
        duplicate_store.record_review(
            candidate_id,
            payload.status,
            payload.reviewed_by,
            payload.reviewer_note,
        )
    except duplicate_store.UnknownDuplicateReviewStatusError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except duplicate_store.DuplicateCandidateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except duplicate_store.DuplicateReviewValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    candidate = duplicate_store.get_candidate(candidate_id)
    return Envelope(success=True, data=candidate)


__all__ = [
    "DuplicateReviewRequest",
    "router",
    "sync_duplicate_candidates_from_snapshot",
    "sync_judged_candidates_from_judgments",
]
