"""R-06 entity-alias review queue and append-only review endpoint."""

from __future__ import annotations

import contextlib
import json
import logging
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from nidhinetra_pipeline.outcomes import alias_store
from pydantic import BaseModel, ConfigDict, Field

from .. import db
from ..models import AliasQuery, Envelope, alias_query

logger = logging.getLogger("nidhinetra_api.entity_aliases")

router = APIRouter(prefix="/api/entity-aliases", tags=["entity-aliases"])


class AliasReviewRequest(BaseModel):
    """Only human input crosses the API boundary.

    ``reviewed_at`` and ``supersedes`` are deliberately absent and extra
    fields are rejected: the server owns both pieces of review history.
    """

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
        works.implementing_agency,
        works.vendor_id,
        works.vendor_name,
        works.work_category,
        works.sanctioned_amount_inr,
        works.completion_status
    FROM works
"""


def sync_alias_candidates_from_snapshot(snapshot_dir: Path | None = None) -> int:
    """Upsert the current rebuildable artifact into persistent review state.

    Older committed snapshots predate R-06 and have no alias artifact. They
    remain bootable with an empty queue; the next successful rebuild will
    create and sync the file.
    """
    alias_store.init_db()
    path = (snapshot_dir or db.SNAPSHOT_DIR) / "alias_candidates.json"
    if not path.exists():
        logger.warning(
            "Snapshot has no %s; entity-alias review queue is empty until a rebuild.",
            path.name,
        )
        return 0
    candidates = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(candidates, list):
        raise alias_store.AliasCandidateValidationError(
            f"{path} must contain a top-level candidate array"
        )
    return alias_store.upsert_candidates(candidates)


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
def list_entity_aliases(query: AliasQuery = Depends(alias_query)) -> Envelope:  # noqa: B008
    candidates, total = alias_store.list_candidates(
        status=query.status,
        page=query.page,
        page_size=query.page_size,
    )
    work_ids = sorted(
        {work_id for candidate in candidates for work_id in candidate["evidence_work_ids"]}
    )
    evidence_by_id = _evidence_by_id(work_ids)
    for candidate in candidates:
        candidate["evidence_works"] = [
            evidence_by_id[work_id]
            for work_id in candidate["evidence_work_ids"]
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
def review_entity_alias(candidate_id: int, payload: AliasReviewRequest) -> Envelope:
    try:
        alias_store.record_review(
            candidate_id,
            payload.status,
            payload.reviewed_by,
            payload.reviewer_note,
        )
    except alias_store.UnknownAliasReviewStatusError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except alias_store.AliasCandidateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except alias_store.AliasReviewValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    candidate = alias_store.get_candidate(candidate_id)
    return Envelope(success=True, data=candidate)


__all__ = [
    "AliasReviewRequest",
    "router",
    "sync_alias_candidates_from_snapshot",
]
