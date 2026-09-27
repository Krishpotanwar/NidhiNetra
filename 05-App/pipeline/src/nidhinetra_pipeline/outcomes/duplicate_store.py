"""Phase 1 Stage C: duplicate-work candidates and append-only human reviews.

Mirrors R-06's alias_store.py exactly (see that module's docstring): candidates are rebuildable
evidence, upserted by their frozen identity; reviews are appended in the same physical SQLite
file as inspection outcomes and never rewritten. This pass syncs only the artifact's identical
batches -- see the Stage C plan's Decision 1 for why near-copy pairs wait for Stage D.
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
_CANDIDATE_SCHEMA_PATH = _APP_ROOT / "contracts" / "duplicate_candidate.schema.json"
_REVIEW_SCHEMA_PATH = _APP_ROOT / "contracts" / "duplicate_review.schema.json"

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
    FROM duplicate_reviews AS review
    WHERE NOT EXISTS (
        SELECT 1
        FROM duplicate_reviews AS later
        WHERE later.supersedes = review.review_id
    )
), resolved_candidates AS (
    SELECT
        candidate.candidate_id,
        candidate.finder,
        candidate.scope,
        candidate.fingerprint_a,
        candidate.fingerprint_b,
        candidate.finder_version,
        candidate.threshold_crossing_batch,
        candidate.text,
        candidate.text_b,
        candidate.quote_a,
        candidate.quote_b,
        candidate.work_relation,
        candidate.work_ids,
        COALESCE(review.status, 'pending') AS current_status,
        review.review_id,
        review.status AS review_status,
        review.reviewed_by,
        review.reviewed_at,
        review.reviewer_note,
        review.supersedes
    FROM duplicate_candidates AS candidate
    LEFT JOIN unsuperseded_reviews AS review
        ON review.candidate_id = candidate.candidate_id
        AND review.current_order = 1
)
"""

_RESOLVED_COLUMNS = """
candidate_id, finder, scope, fingerprint_a, fingerprint_b, finder_version,
threshold_crossing_batch, text, text_b, quote_a, quote_b, work_relation, work_ids,
current_status, review_id, review_status, reviewed_by, reviewed_at, reviewer_note, supersedes
"""


class DuplicateStoreError(Exception):
    """Base class for duplicate-review-store errors."""


class DuplicateStoreCandidateValidationError(DuplicateStoreError):
    """A generated candidate violates its JSON contract.

    Named with a Store prefix, unlike R-06's plain AliasCandidateValidationError, because the
    obvious mirror name collides with nidhinetra_pipeline.duplicates.candidates's
    DuplicateCandidateValidationError from Stage A (see this plan's Decision 4).
    """


class DuplicateReviewValidationError(DuplicateStoreError):
    """Reviewer identity or note is not a valid review input."""


class UnknownDuplicateReviewStatusError(DuplicateStoreError):
    """A decision/status is not in the contract enum."""


class DuplicateCandidateNotFoundError(DuplicateStoreError):
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
        raise DuplicateStoreError(f"could not load duplicate contract at {path}: {exc}") from exc


def _valid_review_statuses() -> frozenset[str]:
    schema = _load_schema(_REVIEW_SCHEMA_PATH)
    return frozenset(schema["properties"]["status"]["enum"])


def init_db(db_path: Path | None = None) -> None:
    """Create Stage C's tables without touching inspection outcomes or the alias tables."""
    path = _db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.closing(_connect(path)) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS duplicate_candidates (
                candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
                finder TEXT NOT NULL,
                scope TEXT NOT NULL,
                fingerprint_a TEXT NOT NULL,
                fingerprint_b TEXT NOT NULL,
                finder_version TEXT NOT NULL,
                threshold_crossing_batch INTEGER NOT NULL,
                text TEXT NOT NULL,
                text_b TEXT,
                quote_a TEXT,
                quote_b TEXT,
                work_relation TEXT,
                work_ids TEXT NOT NULL,
                UNIQUE(scope, fingerprint_a, fingerprint_b, finder_version)
            );

            CREATE TABLE IF NOT EXISTS duplicate_reviews (
                review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                reviewed_by TEXT NOT NULL,
                reviewed_at TEXT NOT NULL,
                reviewer_note TEXT NOT NULL,
                supersedes INTEGER,
                FOREIGN KEY (candidate_id)
                    REFERENCES duplicate_candidates(candidate_id),
                FOREIGN KEY (supersedes)
                    REFERENCES duplicate_reviews(review_id)
            );

            CREATE INDEX IF NOT EXISTS idx_duplicate_reviews_candidate
                ON duplicate_reviews(candidate_id, review_id DESC);

            CREATE UNIQUE INDEX IF NOT EXISTS idx_duplicate_reviews_supersedes
                ON duplicate_reviews(supersedes)
                WHERE supersedes IS NOT NULL;
            """
        )
        _migrate_judged_columns(connection)
        connection.commit()


def _migrate_judged_columns(connection: sqlite3.Connection) -> None:
    """Adds Stage D-lite's near-copy columns to a table created before them. Idempotent, mirrors
    outcomes/store.py's own _migrate_f01_columns. text_b, quote_a, quote_b and work_relation are
    only ever set on a judged_same_asset_same_place candidate; identical_batch and
    district_identical_batch rows keep them NULL, exactly as before this migration ran.
    """
    columns = {row[1] for row in connection.execute("PRAGMA table_info(duplicate_candidates)")}
    for column in ("text_b", "quote_a", "quote_b", "work_relation"):
        if column not in columns:
            connection.execute(f"ALTER TABLE duplicate_candidates ADD COLUMN {column} TEXT")


def _normalized_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(candidate)
    work_ids = normalized.get("work_ids")
    if isinstance(work_ids, list) and all(isinstance(work_id, str) for work_id in work_ids):
        normalized["work_ids"] = sorted(set(work_ids))
    fingerprint_a, fingerprint_b = normalized.get("fingerprint_a"), normalized.get("fingerprint_b")
    if isinstance(fingerprint_a, str) and isinstance(fingerprint_b, str):
        normalized["fingerprint_a"], normalized["fingerprint_b"] = sorted(
            (fingerprint_a, fingerprint_b)
        )
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
        raise DuplicateStoreCandidateValidationError("; ".join(errors))
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
            INSERT INTO duplicate_candidates (
                finder, scope, fingerprint_a, fingerprint_b, finder_version,
                threshold_crossing_batch, text, text_b, quote_a, quote_b, work_relation, work_ids
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(scope, fingerprint_a, fingerprint_b, finder_version)
            DO UPDATE SET
                finder = excluded.finder,
                threshold_crossing_batch = excluded.threshold_crossing_batch,
                text = excluded.text,
                text_b = excluded.text_b,
                quote_a = excluded.quote_a,
                quote_b = excluded.quote_b,
                work_relation = excluded.work_relation,
                work_ids = excluded.work_ids
            """,
            [
                (
                    candidate["finder"],
                    candidate["scope"],
                    candidate["fingerprint_a"],
                    candidate["fingerprint_b"],
                    candidate["finder_version"],
                    int(candidate["threshold_crossing_batch"]),
                    candidate["text"],
                    candidate.get("text_b"),
                    candidate.get("quote_a"),
                    candidate.get("quote_b"),
                    candidate.get("work_relation"),
                    json.dumps(candidate["work_ids"], separators=(",", ":")),
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
        "finder": row["finder"],
        "scope": row["scope"],
        "fingerprint_a": row["fingerprint_a"],
        "fingerprint_b": row["fingerprint_b"],
        "finder_version": row["finder_version"],
        "threshold_crossing_batch": bool(row["threshold_crossing_batch"]),
        "text": row["text"],
        "text_b": row["text_b"],
        "quote_a": row["quote_a"],
        "quote_b": row["quote_b"],
        "work_relation": row["work_relation"],
        "work_ids": json.loads(row["work_ids"]),
        "status": row["current_status"],
        "current_review": current_review,
    }


def _validate_current_status(status: str | None) -> None:
    if status is None:
        return
    valid = {"pending", *_valid_review_statuses()}
    if status not in valid:
        raise UnknownDuplicateReviewStatusError(
            f"{status!r} is not a valid duplicate status. Valid values: {sorted(valid)}"
        )


# T12B.7: the review queue's "kind" filter, grouping finders into two coarser buckets. The judged
# finder name mirrors nidhinetra_pipeline.duplicates.judged_candidates.STORE_FINDER as a literal,
# not an import: that module pulls in duckdb/pandas, which this sqlite-only module should not
# depend on, the same reasoning the API router's own local _SYNCED_FINDERS follows.
_KIND_FINDERS: dict[str, tuple[str, ...]] = {
    "identical": ("identical_batch", "district_identical_batch"),
    "judged": ("judged_same_asset_same_place",),
}


def _validate_kind(kind: str | None) -> None:
    if kind is not None and kind not in _KIND_FINDERS:
        raise ValueError(
            f"{kind!r} is not a valid duplicate kind. Valid values: {sorted(_KIND_FINDERS)}"
        )


def list_candidates(
    *,
    status: str | None = None,
    kind: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db_path: Path | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Return a deterministic candidate page and its filtered total.

    `kind` narrows by finder (T12B.7): "identical" for the two synced-batch finders, "judged" for
    the Stage D-lite near-copy finder. None (the default) applies no finder clause, matching every
    kind -- unchanged behaviour for every caller that predates this filter.
    """
    _validate_current_status(status)
    _validate_kind(kind)
    if page < 1 or page_size < 1:
        raise ValueError("page and page_size must be positive")
    path = _db_path(db_path)
    init_db(path)
    conditions: list[str] = []
    params: list[Any] = []
    if status is not None:
        conditions.append("current_status = ?")
        params.append(status)
    if kind is not None:
        finders = _KIND_FINDERS[kind]
        conditions.append(f"finder IN ({', '.join('?' for _ in finders)})")
        params.extend(finders)
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
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
        raise DuplicateReviewValidationError("review timestamp must include a timezone")
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
        raise UnknownDuplicateReviewStatusError(
            f"{status!r} is not a valid duplicate-review decision. Valid values: "
            f"{sorted(_valid_review_statuses())}"
        )
    if not isinstance(reviewed_by, str) or not reviewed_by.strip():
        raise DuplicateReviewValidationError("reviewed_by must be a non-empty string")
    if not isinstance(reviewer_note, str):
        raise DuplicateReviewValidationError("reviewer_note must be a string")

    path = _db_path(db_path)
    init_db(path)
    with contextlib.closing(_connect(path)) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            exists = connection.execute(
                "SELECT 1 FROM duplicate_candidates WHERE candidate_id = ?",
                (candidate_id,),
            ).fetchone()
            if exists is None:
                raise DuplicateCandidateNotFoundError(
                    f"No duplicate candidate found with id {candidate_id}."
                )

            current = connection.execute(
                """
                SELECT review.review_id
                FROM duplicate_reviews AS review
                WHERE review.candidate_id = ?
                  AND NOT EXISTS (
                      SELECT 1
                      FROM duplicate_reviews AS later
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
                INSERT INTO duplicate_reviews (
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
            f"SELECT {', '.join(_REVIEW_COLUMNS)} FROM duplicate_reviews "
            "WHERE candidate_id = ? ORDER BY review_id ASC",
            (candidate_id,),
        ).fetchall()
    return [{column: row[column] for column in _REVIEW_COLUMNS} for row in rows]


def candidates_for_work(
    work_id: str,
    *,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Resolved candidates whose work_ids include ``work_id``, most recent first.

    Scans the whole table and filters in Python: at Finder 1/3 scale (hundreds of rows, not the
    tens of thousands a near-copy sync would add) this is simpler and more obviously correct
    than a JSON-in-SQL query, and does not depend on a particular SQLite build's JSON1 support.
    """
    path = _db_path(db_path)
    init_db(path)
    with contextlib.closing(_connect(path)) as connection:
        rows = connection.execute(
            f"{_RESOLVED_CANDIDATES_CTE} "
            f"SELECT {_RESOLVED_COLUMNS} FROM resolved_candidates ORDER BY candidate_id DESC"
        ).fetchall()
    return [_resolved_candidate(row) for row in rows if work_id in json.loads(row["work_ids"])]


def duplicate_context(
    work_id: str,
    *,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """A short summary of every synced batch this work belongs to, for the work-detail endpoint.

    Deliberately not the full resolved-candidate shape: a detail endpoint wants "you share this
    wording with 3 other works, and here they are", not the whole review-store row.
    """
    contexts = []
    for candidate in candidates_for_work(work_id, db_path=db_path):
        entry = {
            "candidate_id": candidate["candidate_id"],
            "finder": candidate["finder"],
            "threshold_crossing_batch": candidate["threshold_crossing_batch"],
            "text": candidate["text"],
            "work_count": len(candidate["work_ids"]),
            "other_work_ids": sorted(wid for wid in candidate["work_ids"] if wid != work_id),
            "status": candidate["status"],
        }
        if candidate["text_b"] is not None:
            entry["text_b"] = candidate["text_b"]
            entry["quote_a"] = candidate["quote_a"]
            entry["quote_b"] = candidate["quote_b"]
            entry["work_relation"] = candidate["work_relation"]
        contexts.append(entry)
    return contexts


__all__ = [
    "DEFAULT_DB_PATH",
    "DuplicateCandidateNotFoundError",
    "DuplicateReviewValidationError",
    "DuplicateStoreCandidateValidationError",
    "DuplicateStoreError",
    "UnknownDuplicateReviewStatusError",
    "candidates_for_work",
    "duplicate_context",
    "get_candidate",
    "get_review_history",
    "init_db",
    "list_candidates",
    "record_review",
    "upsert_candidates",
]
