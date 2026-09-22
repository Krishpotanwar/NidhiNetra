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
]
