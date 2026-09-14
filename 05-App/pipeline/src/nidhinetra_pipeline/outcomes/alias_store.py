"""R-06 entity-alias candidates and append-only human reviews.

Candidates are rebuildable evidence derived from the current snapshot, but
their stable ``candidate_id`` is the anchor for non-rebuildable review
history.  Rebuilds therefore upsert candidate evidence by the frozen
identity triple and never replace or delete rows.  Reviews are appended in
the same physical SQLite file as inspection outcomes, but this sibling
module never edits ``outcomes/store.py`` or its table.
"""

from __future__ import annotations

import contextlib
import json
import sqlite3
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonschema

_APP_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DB_PATH = _APP_ROOT / "data" / "outcomes" / "outcomes.db"
_CANDIDATE_SCHEMA_PATH = _APP_ROOT / "contracts" / "entity_alias_candidate.schema.json"
_REVIEW_SCHEMA_PATH = _APP_ROOT / "contracts" / "entity_alias_review.schema.json"

_REVIEW_COLUMNS = (
    "review_id",
    "candidate_id",
    "status",
    "reviewed_by",
    "reviewed_at",
    "reviewer_note",
    "supersedes",
)

_RESOLVED_CANDIDATES_CTE = """
WITH unsuperseded_reviews AS (
    SELECT
        review.*,
        ROW_NUMBER() OVER (
            PARTITION BY review.candidate_id
            ORDER BY review.review_id DESC
        ) AS current_order
    FROM entity_alias_reviews AS review
    WHERE NOT EXISTS (
        SELECT 1
        FROM entity_alias_reviews AS later
        WHERE later.supersedes = review.review_id
    )
), resolved_candidates AS (
    SELECT
        candidate.candidate_id,
        candidate.entity_type,
        candidate.proposed_canonical_id,
        candidate.alias_label,
        candidate.reason,
        candidate.evidence_work_ids,
        COALESCE(review.status, 'pending') AS current_status,
        review.review_id,
        review.status AS review_status,
        review.reviewed_by,
        review.reviewed_at,
        review.reviewer_note,
        review.supersedes
    FROM entity_alias_candidates AS candidate
    LEFT JOIN unsuperseded_reviews AS review
        ON review.candidate_id = candidate.candidate_id
        AND review.current_order = 1
)
"""

_RESOLVED_COLUMNS = """
candidate_id, entity_type, proposed_canonical_id, alias_label, reason,
evidence_work_ids, current_status, review_id, review_status, reviewed_by,
reviewed_at, reviewer_note, supersedes
"""


class AliasStoreError(Exception):
    """Base class for alias-store errors."""


class AliasCandidateValidationError(AliasStoreError):
    """A generated candidate violates its JSON contract."""


class AliasReviewValidationError(AliasStoreError):
    """Reviewer identity or note is not a valid review input."""


class UnknownAliasReviewStatusError(AliasStoreError):
    """A decision/status is not in the contract enum."""


class AliasCandidateNotFoundError(AliasStoreError):
    """A review named a candidate that is not stored."""


def _db_path(db_path: Path | None) -> Path:
    return db_path if db_path is not None else DEFAULT_DB_PATH


def _connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _load_schema(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AliasStoreError(f"could not load alias contract at {path}: {exc}") from exc


def _valid_review_statuses() -> frozenset[str]:
    schema = _load_schema(_REVIEW_SCHEMA_PATH)
    return frozenset(schema["properties"]["status"]["enum"])


def init_db(db_path: Path | None = None) -> None:
    """Create R-06 tables without touching inspection outcomes."""
    path = _db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.closing(_connect(path)) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS entity_alias_candidates (
                candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                proposed_canonical_id TEXT NOT NULL,
                alias_label TEXT NOT NULL,
                reason TEXT NOT NULL,
                evidence_work_ids TEXT NOT NULL,
                UNIQUE(entity_type, proposed_canonical_id, alias_label)
            );

            CREATE TABLE IF NOT EXISTS entity_alias_reviews (
                review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                reviewed_by TEXT NOT NULL,
                reviewed_at TEXT NOT NULL,
                reviewer_note TEXT NOT NULL,
                supersedes INTEGER,
                FOREIGN KEY (candidate_id)
                    REFERENCES entity_alias_candidates(candidate_id),
                FOREIGN KEY (supersedes)
                    REFERENCES entity_alias_reviews(review_id)
            );

            CREATE INDEX IF NOT EXISTS idx_entity_alias_reviews_candidate
                ON entity_alias_reviews(candidate_id, review_id DESC);

            CREATE UNIQUE INDEX IF NOT EXISTS idx_entity_alias_reviews_supersedes
                ON entity_alias_reviews(supersedes)
                WHERE supersedes IS NOT NULL;
            """
        )
        connection.commit()


def _normalized_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(candidate)
    evidence = normalized.get("evidence_work_ids")
    if isinstance(evidence, list) and all(isinstance(work_id, str) for work_id in evidence):
        normalized["evidence_work_ids"] = sorted(set(evidence))
    return normalized


def _validated_candidates(
    candidates: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    schema = _load_schema(_CANDIDATE_SCHEMA_PATH)
    validator = jsonschema.Draft7Validator(schema)
    validated: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, candidate in enumerate(candidates):
        normalized = _normalized_candidate(candidate)
        candidate_errors = sorted(
            validator.iter_errors(normalized), key=lambda error: list(error.path)
        )
        for error in candidate_errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            errors.append(f"candidate {index} ({location}): {error.message}")
        validated.append(normalized)
    if errors:
        raise AliasCandidateValidationError("; ".join(errors))
    return validated


def upsert_candidates(
    candidates: Iterable[Mapping[str, Any]],
    *,
    db_path: Path | None = None,
) -> int:
    """Atomically upsert generated identity/evidence, preserving reviews."""
    validated = _validated_candidates(candidates)
    path = _db_path(db_path)
    init_db(path)
    with contextlib.closing(_connect(path)) as connection:
        connection.executemany(
            """
            INSERT INTO entity_alias_candidates (
                entity_type, proposed_canonical_id, alias_label, reason,
                evidence_work_ids
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(entity_type, proposed_canonical_id, alias_label)
            DO UPDATE SET
                reason = excluded.reason,
                evidence_work_ids = excluded.evidence_work_ids
            """,
            [
                (
                    candidate["entity_type"],
                    candidate["proposed_canonical_id"],
                    candidate["alias_label"],
                    candidate["reason"],
                    json.dumps(candidate["evidence_work_ids"], separators=(",", ":")),
                )
                for candidate in validated
            ],
        )
        connection.commit()
    return len(validated)


def _resolved_candidate(row: sqlite3.Row) -> dict[str, Any]:
    current_review = None
    if row["review_id"] is not None:
        current_review = {
            "review_id": row["review_id"],
            "candidate_id": row["candidate_id"],
            "status": row["review_status"],
            "reviewed_by": row["reviewed_by"],
            "reviewed_at": row["reviewed_at"],
            "reviewer_note": row["reviewer_note"],
            "supersedes": row["supersedes"],
        }
    return {
        "candidate_id": row["candidate_id"],
        "entity_type": row["entity_type"],
        "proposed_canonical_id": row["proposed_canonical_id"],
        "alias_label": row["alias_label"],
        "reason": row["reason"],
        "evidence_work_ids": json.loads(row["evidence_work_ids"]),
        "status": row["current_status"],
        "current_review": current_review,
    }


def _validate_current_status(status: str | None) -> None:
    if status is None:
        return
    valid = {"pending", *_valid_review_statuses()}
    if status not in valid:
        raise UnknownAliasReviewStatusError(
            f"{status!r} is not a valid alias status. Valid values: {sorted(valid)}"
        )


def list_candidates(
    *,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db_path: Path | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Return a deterministic candidate page and its filtered total."""
    _validate_current_status(status)
    if page < 1 or page_size < 1:
        raise ValueError("page and page_size must be positive")
    path = _db_path(db_path)
    init_db(path)
    where = " WHERE current_status = ?" if status is not None else ""
    params: tuple[Any, ...] = (status,) if status is not None else ()
    offset = (page - 1) * page_size
    with contextlib.closing(_connect(path)) as connection:
        total = connection.execute(
            f"{_RESOLVED_CANDIDATES_CTE} SELECT COUNT(*) FROM resolved_candidates{where}",
            params,
        ).fetchone()[0]
        rows = connection.execute(
            f"{_RESOLVED_CANDIDATES_CTE} "
            f"SELECT {_RESOLVED_COLUMNS} FROM resolved_candidates{where} "
            "ORDER BY candidate_id ASC LIMIT ? OFFSET ?",
            (*params, page_size, offset),
        ).fetchall()
    return [_resolved_candidate(row) for row in rows], total


def get_candidate(
    candidate_id: int,
    *,
    db_path: Path | None = None,
) -> dict[str, Any] | None:
    """Return one candidate with its current review, or ``None``."""
    path = _db_path(db_path)
    init_db(path)
    with contextlib.closing(_connect(path)) as connection:
        row = connection.execute(
            f"{_RESOLVED_CANDIDATES_CTE} "
            f"SELECT {_RESOLVED_COLUMNS} FROM resolved_candidates "
            "WHERE candidate_id = ?",
            (candidate_id,),
        ).fetchone()
    return _resolved_candidate(row) if row is not None else None


def _reviewed_at(now: datetime | None) -> str:
    instant = now or datetime.now(UTC)
    if instant.tzinfo is None:
        raise AliasReviewValidationError("review timestamp must include a timezone")
    return instant.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def record_review(
    candidate_id: int,
    status: str,
    reviewed_by: str,
    reviewer_note: str = "",
    *,
    now: datetime | None = None,
    db_path: Path | None = None,
) -> int:
    """Append a decision, automatically superseding the current decision."""
    if status not in _valid_review_statuses():
        raise UnknownAliasReviewStatusError(
            f"{status!r} is not a valid alias-review decision. Valid values: "
            f"{sorted(_valid_review_statuses())}"
        )
    if not isinstance(reviewed_by, str) or not reviewed_by.strip():
        raise AliasReviewValidationError("reviewed_by must be a non-empty string")
    if not isinstance(reviewer_note, str):
        raise AliasReviewValidationError("reviewer_note must be a string")

    path = _db_path(db_path)
    init_db(path)
    with contextlib.closing(_connect(path)) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            exists = connection.execute(
                "SELECT 1 FROM entity_alias_candidates WHERE candidate_id = ?",
                (candidate_id,),
            ).fetchone()
            if exists is None:
                raise AliasCandidateNotFoundError(
                    f"No entity-alias candidate found with id {candidate_id}."
                )

            current = connection.execute(
                """
                SELECT review.review_id
                FROM entity_alias_reviews AS review
                WHERE review.candidate_id = ?
                  AND NOT EXISTS (
                      SELECT 1
                      FROM entity_alias_reviews AS later
                      WHERE later.supersedes = review.review_id
                  )
                ORDER BY review.review_id DESC
                LIMIT 1
                """,
                (candidate_id,),
            ).fetchone()
            supersedes = current["review_id"] if current is not None else None
            cursor = connection.execute(
                """
                INSERT INTO entity_alias_reviews (
                    candidate_id, status, reviewed_by, reviewed_at,
                    reviewer_note, supersedes
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_id,
                    status,
                    reviewed_by.strip(),
                    _reviewed_at(now),
                    reviewer_note,
                    supersedes,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)
        except Exception:
            connection.rollback()
            raise


def get_review_history(
    candidate_id: int,
    *,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Return the complete append-only history, oldest first."""
    path = _db_path(db_path)
    init_db(path)
    with contextlib.closing(_connect(path)) as connection:
        rows = connection.execute(
            f"SELECT {', '.join(_REVIEW_COLUMNS)} FROM entity_alias_reviews "
            "WHERE candidate_id = ? ORDER BY review_id ASC",
            (candidate_id,),
        ).fetchall()
    return [{column: row[column] for column in _REVIEW_COLUMNS} for row in rows]


__all__ = [
    "AliasCandidateNotFoundError",
    "AliasCandidateValidationError",
    "AliasReviewValidationError",
    "AliasStoreError",
    "DEFAULT_DB_PATH",
    "UnknownAliasReviewStatusError",
    "get_candidate",
    "get_review_history",
    "init_db",
    "list_candidates",
    "record_review",
    "upsert_candidates",
]
