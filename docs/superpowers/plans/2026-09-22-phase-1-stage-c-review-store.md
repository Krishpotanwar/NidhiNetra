# Phase 1 Stage C, Part 1: The Duplicate Review Store Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give officers a durable place to say "these are the same" or "these are different" about the works Stage A found sharing an identical description, without losing that decision on the next rebuild, and without waiting for Stage B's model.

**Architecture:** One new pipeline module, `outcomes/duplicate_store.py`, sibling to `outcomes/alias_store.py` in the same `outcomes.db`, built by copying R-06's already-shipped, already-tested pattern almost line for line. One new API router, `routers/duplicates.py`, sibling to `routers/entity_aliases.py`. Two new contracts. `works.py`'s work-detail endpoint gains a `duplicate_context` field.

**Tech Stack:** Python 3.13, `uv`, pytest, FastAPI, pydantic, jsonschema, sqlite3 (stdlib), DuckDB (already a dependency, used for the works read path). No new dependency.

**Spec:** `docs/superpowers/specs/2026-09-17-foundation-and-duplicate-works-design.md`, "Phase 1, Stage C: the review surface". Read that section first. This plan's input is Stage A's committed artifact: `data/snapshot/duplicate_candidates.json` (`docs/superpowers/plans/2026-09-21-phase-1-stage-a-candidates.md`).

## Scope of this part

The spec's Stage C paragraph describes a review store, an API, a detail-panel section, an inline queue on the Inspection List page, and a `strings.json` block. **This plan builds the store and the API only.** The web UI (the queue component, the detail-panel section, the page mount, the empty state, the copy block) is real, spec'd work that is not in this plan — see "Not in this plan" below. Splitting here is deliberate: the store is what starts capturing durable officer decisions, which is the actual precondition for Phase 4 training data; the UI is what makes that usable by a real officer, and deserves its own focused pass rather than being rushed alongside a new backend subsystem.

**Decision 1: this pass syncs only the artifact's identical batches (`identical_batch`, `district_identical_batch`), not near-copy pairs.** The artifact's 39,123 near-copy pairs need a model's opinion to be worth an officer's time (spec: "queue noise, not cost, decides how wide the net is; Stage D sets that"). The 1,180 identical batches need no model — identical text is identical text — and 271 of them already cross the MPLADS clause 4.4.2 inspection threshold today. Syncing pairs is future work, once Stage D has narrowed them by judge answer. Cost if wrong: a second sync path is added later; nothing already built has to change, because the store's schema already carries two fingerprint columns (Decision 2) in anticipation of it.

**Decision 2: the store's identity is `(scope, fingerprint_a, fingerprint_b, finder_version)`, with `fingerprint_a == fingerprint_b` for a batch.** The spec's own words for Stage C's identity are "unique on scope plus both text fingerprints plus finder version" — written with pairs in mind. A batch has only one group, so this plan sets both fingerprint columns to that group's `text_fingerprint`, sorted (a harmless no-op today, and correct once pairs are added: the store always sorts the pair before storing). This keeps today's schema exactly the one the spec describes, so adding pairs later is a code change, not a migration.

**Decision 3: `duplicate_store.py` does not carry through the artifact's own `candidate_id`.** Stage A's `candidate_id` is `sha256(FINDER_VERSION | ...)`-derived and is the subject of Stage A's still-open Decision 10 (whether `FINDER_VERSION` belongs in that hash). R-06 has no analogous upstream id to carry through — `alias_candidates.json` items are identified purely by their natural key — and this store follows that precedent: its own identity is `(scope, fingerprint_a, fingerprint_b, finder_version)`, computed directly, never the artifact's `candidate_id` string. This sidesteps Decision 10 entirely: nothing here breaks or needs to change if that decision is ever made either way.

**Decision 4: the sync step's error class is renamed from the R-06 mirror's obvious name.** Copying R-06's naming literally would produce `nidhinetra_pipeline.outcomes.duplicate_store.DuplicateCandidateValidationError` — which collides by name (not import path, but a real hazard for a future `from ... import *` or a two-import file) with the already-shipped `nidhinetra_pipeline.duplicates.candidates.DuplicateCandidateValidationError` from Stage A. This plan names it `DuplicateStoreCandidateValidationError` instead; every other error class mirrors R-06's naming exactly, because none of the others collide.

**Decision 5: the sync step reads the whole 23.6 MB artifact once, at sync time, in memory.** Stage A's Decision 9 warned against `json.load`-ing the full artifact at API start-up on a memory-constrained host, and suggested DuckDB's `read_json` as the fix. This plan does not build that: querying nested JSON (a `groups` object keyed by id, `batches` referencing it) correctly with DuckDB needs testing against a real constrained host to trust, which this VM cannot do. This plan does the simple, correct thing — parse the file once, keep no reference to it past the sync function's own scope — and documents the known risk in the sync function's docstring rather than silently dropping it. Cost if wrong: on a host with too little RAM, sync fails loudly (`MemoryError` or the process is killed) rather than corrupting anything; nothing is written until the whole batch validates. If this becomes a real problem, Decision 9's DuckDB path is the fix, unchanged by anything in this plan.

**Decision 6: review status codes are `confirmed_same` and `rejected_different`.** The spec names the officer-facing button copy ("These are the same" / "These are different") and says "Duplicate" never appears as a verdict; it does not name the internal codes. These two follow the button copy directly and read unambiguously in a log or a query, the same way R-06's `confirmed_merge` / `rejected_distinct` do.

## Global Constraints

- **Never push.** Commit locally on `codex/finish-nidhinetra`; the user pushes after review.
- **`data/` is off limits for writes.** Every test uses `tmp_path` (mirroring `isolated_outcomes_db`); nothing in this plan writes `data/outcomes/outcomes.db` or touches `data/snapshot/`.
- **No score change.** Nothing here imports `risk/`, touches `build_snapshot.py`, or changes anything scored.
- **No user-visible text added.** `contracts/strings.json` is not touched by this plan; there is no UI yet to show anything.
- **`store.py` (inspection outcomes) is never modified.** `duplicate_store.py` is a sibling in the same physical SQLite file, exactly like `alias_store.py`.
- **No new dependency.**
- ruff: `line-length = 100`, rules `E,F,I,UP,B`. Run `uvx ruff format` and `uvx ruff check` on the files a task changes, and only those.
- Gates before each commit: the task's own tests; the last task also runs `pytest pipeline/tests -q`, `pytest api/tests -q` and `make validate`.
- Every command block starts from the repository root, and a block that needs `05-App` runs in a subshell, `(cd 05-App && ...)`. In the Linux VM, `uv`/`uvx` need `. ~/.cache/nidhinetra-vm/env.sh` first, and the working forms are `uv run --package nidhinetra-pipeline ...` / `uv run --package nidhinetra-api ...`. Commit with one-off `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_NAME`, `GIT_COMMITTER_EMAIL` matching the repository's history; never write git config.

## Vocabulary

- **Candidate** (in this store): one row of `duplicate_candidates` — one synced identical batch, identified by `(scope, fingerprint_a, fingerprint_b, finder_version)`.
- **Review**: one append-only row of `duplicate_reviews`, `confirmed_same` or `rejected_different`, self-reported `reviewed_by`, with a `supersedes` column pointing at the review it corrects.
- **Sync**: reading the committed artifact and upserting its identical batches into the store, preserving any existing review.

## Task 1: The two contracts

**Files:**
- Create: `05-App/contracts/duplicate_candidate.schema.json`
- Create: `05-App/contracts/duplicate_review.schema.json`

- [ ] **Step 1: Write `duplicate_candidate.schema.json`**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://nidhinetra.local/contracts/duplicate_candidate.schema.json",
  "title": "DuplicateCandidate",
  "description": "Phase 1 Stage C review candidate, synced from an identical batch in duplicate_candidates.json. Review decisions do not change Stage A's artifact.",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "finder",
    "scope",
    "fingerprint_a",
    "fingerprint_b",
    "finder_version",
    "threshold_crossing_batch",
    "text",
    "work_ids"
  ],
  "properties": {
    "finder": {
      "type": "string",
      "enum": ["identical_batch", "district_identical_batch"]
    },
    "scope": {
      "type": "string",
      "minLength": 1
    },
    "fingerprint_a": {
      "type": "string",
      "pattern": "^[0-9a-f]{16}$"
    },
    "fingerprint_b": {
      "type": "string",
      "pattern": "^[0-9a-f]{16}$"
    },
    "finder_version": {
      "type": "string",
      "minLength": 1
    },
    "threshold_crossing_batch": {
      "type": "boolean",
      "description": "True when every work in the batch is below Rs 15 lakh and the group total is Rs 25 lakh or more (MPLADS Guidelines 2023, clause 4.4.2)."
    },
    "text": {
      "type": "string",
      "minLength": 1,
      "description": "The shared description, as published, spacing tidied."
    },
    "work_ids": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "minItems": 2,
      "uniqueItems": true
    }
  }
}
```

- [ ] **Step 2: Write `duplicate_review.schema.json`**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://nidhinetra.local/contracts/duplicate_review.schema.json",
  "title": "DuplicateReview",
  "description": "Phase 1 Stage C append-only human review of a duplicate candidate. reviewed_at and supersedes are assigned by the server; a later decision appends a row that supersedes the current one rather than overwriting history.",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "review_id",
    "candidate_id",
    "status",
    "reviewed_by",
    "reviewed_at",
    "reviewer_note",
    "supersedes"
  ],
  "properties": {
    "review_id": {
      "type": "integer",
      "minimum": 1,
      "description": "Server-assigned append-only review identity."
    },
    "candidate_id": {
      "type": "integer",
      "minimum": 1,
      "description": "References duplicate_candidates.candidate_id."
    },
    "status": {
      "type": "string",
      "enum": ["confirmed_same", "rejected_different"],
      "description": "Stored decision code. Officer-facing action copy lives in strings.json. 'Duplicate' never appears as a verdict."
    },
    "reviewed_by": {
      "type": "string",
      "minLength": 1,
      "description": "Self-reported reviewer name or initials; this prototype has no authentication."
    },
    "reviewed_at": {
      "type": "string",
      "format": "date-time",
      "description": "UTC timestamp assigned by the server, never accepted from the client."
    },
    "reviewer_note": {
      "type": "string",
      "description": "Optional officer note, always present and possibly empty."
    },
    "supersedes": {
      "type": ["integer", "null"],
      "minimum": 1,
      "description": "The previously-current review amended by this row, or null for the first review."
    }
  }
}
```

- [ ] **Step 3: Check both schemas are valid Draft-07**

```bash
(cd 05-App && uv run --package nidhinetra-pipeline python -c "
import json, jsonschema
for name in ('duplicate_candidate', 'duplicate_review'):
    schema = json.loads(open(f'contracts/{name}.schema.json').read())
    jsonschema.Draft7Validator.check_schema(schema)
    print(name, 'ok')
")
```
Expected: `duplicate_candidate ok` then `duplicate_review ok`.

- [ ] **Step 4: Commit**

```bash
git add 05-App/contracts/duplicate_candidate.schema.json 05-App/contracts/duplicate_review.schema.json
git commit -m "feat(contracts): the duplicate-review candidate and review schemas (Phase 1 Stage C, 1/5)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

## Task 2: `duplicate_store.py`

**Files:**
- Create: `05-App/pipeline/src/nidhinetra_pipeline/outcomes/duplicate_store.py`
- Create: `05-App/pipeline/tests/outcomes/test_duplicate_store.py`

**Interfaces:**
- Consumes: nothing new (stdlib `sqlite3`, `jsonschema`).
- Produces: `DEFAULT_DB_PATH`; `DuplicateStoreError`, `DuplicateStoreCandidateValidationError`, `DuplicateReviewValidationError`, `UnknownDuplicateReviewStatusError`, `DuplicateCandidateNotFoundError`; `init_db(db_path=None)`; `upsert_candidates(candidates, *, db_path=None) -> int`; `list_candidates(*, status=None, page=1, page_size=50, db_path=None) -> tuple[list[dict], int]`; `get_candidate(candidate_id, *, db_path=None) -> dict | None`; `record_review(candidate_id, status, reviewed_by, reviewer_note="", *, now=None, db_path=None) -> int`; `get_review_history(candidate_id, *, db_path=None) -> list[dict]`; `candidates_for_work(work_id, *, db_path=None) -> list[dict]`; `duplicate_context(work_id, *, db_path=None) -> list[dict]`.

- [ ] **Step 1: Write the failing tests**

Create `05-App/pipeline/tests/outcomes/test_duplicate_store.py`:

```python
"""Phase 1 Stage C: duplicate-review candidates and append-only review history."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from nidhinetra_pipeline.outcomes import duplicate_store
from nidhinetra_pipeline.outcomes import store as outcomes_store


def _candidate(
    scope: str = "C1",
    fingerprint: str = "1111111111111111",
    *,
    finder: str = "identical_batch",
    finder_version: str = "candidate_generation_v0",
    threshold_crossing_batch: bool = False,
    text: str = "PCC Road, near Ram House",
    work_ids: list[str] | None = None,
) -> dict[str, object]:
    return {
        "finder": finder,
        "scope": scope,
        "fingerprint_a": fingerprint,
        "fingerprint_b": fingerprint,
        "finder_version": finder_version,
        "threshold_crossing_batch": threshold_crossing_batch,
        "text": text,
        "work_ids": work_ids or ["W2", "W1"],
    }


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "outcomes" / "outcomes.db"


def test_init_db_coexists_with_inspection_outcomes_and_is_idempotent(db_path: Path) -> None:
    outcomes_store.init_db(db_path)
    duplicate_store.init_db(db_path)
    duplicate_store.init_db(db_path)

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert "inspection_outcomes" in tables
    assert "duplicate_candidates" in tables
    assert "duplicate_reviews" in tables


def test_new_candidate_is_pending_and_work_ids_are_sorted_and_deduplicated(
    db_path: Path,
) -> None:
    assert (
        duplicate_store.upsert_candidates(
            [_candidate(work_ids=["W2", "W1", "W2"])], db_path=db_path
        )
        == 1
    )

    rows, total = duplicate_store.list_candidates(status="pending", db_path=db_path)

    assert total == 1
    assert rows[0]["candidate_id"] > 0
    assert rows[0]["status"] == "pending"
    assert rows[0]["current_review"] is None
    assert rows[0]["work_ids"] == ["W1", "W2"]
    assert rows[0]["threshold_crossing_batch"] is False


def test_fingerprints_are_stored_sorted_even_if_given_reversed(db_path: Path) -> None:
    candidate = _candidate()
    candidate["fingerprint_a"], candidate["fingerprint_b"] = "2222222222222222", "1111111111111111"

    duplicate_store.upsert_candidates([candidate], db_path=db_path)

    rows, _ = duplicate_store.list_candidates(db_path=db_path)
    assert (rows[0]["fingerprint_a"], rows[0]["fingerprint_b"]) == (
        "1111111111111111",
        "2222222222222222",
    )


def test_upsert_preserves_candidate_id_and_review_while_refreshing_evidence(
    db_path: Path,
) -> None:
    duplicate_store.upsert_candidates([_candidate()], db_path=db_path)
    original = duplicate_store.list_candidates(db_path=db_path)[0][0]
    review_id = duplicate_store.record_review(
        original["candidate_id"],
        "confirmed_same",
        "RK",
        "Checked both work orders.",
        db_path=db_path,
    )

    duplicate_store.upsert_candidates(
        [_candidate(threshold_crossing_batch=True, work_ids=["W9", "W3", "W1"])],
        db_path=db_path,
    )

    current = duplicate_store.get_candidate(original["candidate_id"], db_path=db_path)
    assert current is not None
    assert current["candidate_id"] == original["candidate_id"]
    assert current["threshold_crossing_batch"] is True
    assert current["work_ids"] == ["W1", "W3", "W9"]
    assert current["status"] == "confirmed_same"
    assert current["current_review"]["review_id"] == review_id
    assert len(duplicate_store.get_review_history(original["candidate_id"], db_path=db_path)) == 1


def test_bulk_upsert_is_atomic_when_one_candidate_is_invalid(db_path: Path) -> None:
    invalid = _candidate(work_ids=["only-one"])

    with pytest.raises(duplicate_store.DuplicateStoreCandidateValidationError):
        duplicate_store.upsert_candidates([_candidate(), invalid], db_path=db_path)

    rows, total = duplicate_store.list_candidates(db_path=db_path)
    assert rows == []
    assert total == 0


def test_invalid_review_status_and_unknown_candidate_write_nothing(db_path: Path) -> None:
    duplicate_store.upsert_candidates([_candidate()], db_path=db_path)
    candidate_id = duplicate_store.list_candidates(db_path=db_path)[0][0]["candidate_id"]

    with pytest.raises(duplicate_store.UnknownDuplicateReviewStatusError):
        duplicate_store.record_review(candidate_id, "duplicate", "RK", db_path=db_path)
    with pytest.raises(duplicate_store.DuplicateCandidateNotFoundError):
        duplicate_store.record_review(999_999, "confirmed_same", "RK", db_path=db_path)

    assert duplicate_store.get_review_history(candidate_id, db_path=db_path) == []


def test_later_review_is_append_only_and_automatically_supersedes_current(
    db_path: Path,
) -> None:
    duplicate_store.upsert_candidates([_candidate()], db_path=db_path)
    candidate_id = duplicate_store.list_candidates(db_path=db_path)[0][0]["candidate_id"]
    first_time = datetime(2026, 9, 22, 8, 30, tzinfo=UTC)
    second_time = datetime(2026, 9, 22, 9, 45, tzinfo=UTC)

    first_id = duplicate_store.record_review(
        candidate_id, "confirmed_same", "RK", "Same wording.", now=first_time, db_path=db_path
    )
    second_id = duplicate_store.record_review(
        candidate_id,
        "rejected_different",
        "AB",
        "Two separate installations, checked on site.",
        now=second_time,
        db_path=db_path,
    )

    history = duplicate_store.get_review_history(candidate_id, db_path=db_path)
    assert [row["review_id"] for row in history] == [first_id, second_id]
    assert history[0]["supersedes"] is None
    assert history[0]["reviewed_at"] == "2026-09-22T08:30:00Z"
    assert history[1]["supersedes"] == first_id

    current = duplicate_store.get_candidate(candidate_id, db_path=db_path)
    assert current is not None
    assert current["status"] == "rejected_different"
    assert current["current_review"]["review_id"] == second_id


def test_status_filter_and_pagination_use_current_review_only(db_path: Path) -> None:
    duplicate_store.upsert_candidates(
        [
            _candidate("C1", "1111111111111111"),
            _candidate("C2", "2222222222222222"),
            _candidate("C3", "3333333333333333"),
        ],
        db_path=db_path,
    )
    all_rows, _ = duplicate_store.list_candidates(status=None, db_path=db_path)
    ids = {row["scope"]: row["candidate_id"] for row in all_rows}
    duplicate_store.record_review(ids["C1"], "confirmed_same", "RK", db_path=db_path)
    duplicate_store.record_review(ids["C2"], "rejected_different", "RK", db_path=db_path)

    pending, pending_total = duplicate_store.list_candidates(
        status="pending", page=1, page_size=1, db_path=db_path
    )
    confirmed, confirmed_total = duplicate_store.list_candidates(
        status="confirmed_same", db_path=db_path
    )
    rejected, rejected_total = duplicate_store.list_candidates(
        status="rejected_different", db_path=db_path
    )

    assert pending_total == 1
    assert [row["scope"] for row in pending] == ["C3"]
    assert confirmed_total == 1
    assert [row["scope"] for row in confirmed] == ["C1"]
    assert rejected_total == 1
    assert [row["scope"] for row in rejected] == ["C2"]


def test_candidates_for_work_finds_every_batch_that_includes_it(db_path: Path) -> None:
    duplicate_store.upsert_candidates(
        [
            _candidate("C1", "1111111111111111", work_ids=["W1", "W2"]),
            _candidate("C2", "2222222222222222", work_ids=["W2", "W3"]),
            _candidate("C3", "3333333333333333", work_ids=["W4", "W5"]),
        ],
        db_path=db_path,
    )

    found = duplicate_store.candidates_for_work("W2", db_path=db_path)

    assert {row["scope"] for row in found} == {"C1", "C2"}
    assert duplicate_store.candidates_for_work("W9", db_path=db_path) == []


def test_duplicate_context_summarizes_without_the_work_itself(db_path: Path) -> None:
    duplicate_store.upsert_candidates(
        [_candidate("C1", "1111111111111111", threshold_crossing_batch=True, work_ids=["W1", "W2", "W3"])],
        db_path=db_path,
    )
    candidate_id = duplicate_store.list_candidates(db_path=db_path)[0][0]["candidate_id"]
    duplicate_store.record_review(candidate_id, "confirmed_same", "RK", db_path=db_path)

    context = duplicate_store.duplicate_context("W2", db_path=db_path)

    assert context == [
        {
            "candidate_id": candidate_id,
            "finder": "identical_batch",
            "threshold_crossing_batch": True,
            "text": "PCC Road, near Ram House",
            "work_count": 3,
            "other_work_ids": ["W1", "W3"],
            "status": "confirmed_same",
        }
    ]
    assert duplicate_store.duplicate_context("W9", db_path=db_path) == []
```

- [ ] **Step 2: Run it and watch it fail**

```bash
(cd 05-App && uv run pytest pipeline/tests/outcomes/test_duplicate_store.py -q)
```
Expected: `No module named 'nidhinetra_pipeline.outcomes.duplicate_store'`

- [ ] **Step 3: Write the module**

Create `05-App/pipeline/src/nidhinetra_pipeline/outcomes/duplicate_store.py`:

```python
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
threshold_crossing_batch, text, work_ids, current_status, review_id, review_status,
reviewed_by, reviewed_at, reviewer_note, supersedes
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
        connection.commit()


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
                threshold_crossing_batch, text, work_ids
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(scope, fingerprint_a, fingerprint_b, finder_version)
            DO UPDATE SET
                finder = excluded.finder,
                threshold_crossing_batch = excluded.threshold_crossing_batch,
                text = excluded.text,
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
    return [
        _resolved_candidate(row) for row in rows if work_id in json.loads(row["work_ids"])
    ]


def duplicate_context(
    work_id: str,
    *,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """A short summary of every synced batch this work belongs to, for the work-detail endpoint.

    Deliberately not the full resolved-candidate shape: a detail endpoint wants "you share this
    wording with 3 other works, and here they are", not the whole review-store row.
    """
    return [
        {
            "candidate_id": candidate["candidate_id"],
            "finder": candidate["finder"],
            "threshold_crossing_batch": candidate["threshold_crossing_batch"],
            "text": candidate["text"],
            "work_count": len(candidate["work_ids"]),
            "other_work_ids": sorted(wid for wid in candidate["work_ids"] if wid != work_id),
            "status": candidate["status"],
        }
        for candidate in candidates_for_work(work_id, db_path=db_path)
    ]


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
```

- [ ] **Step 4: Run the tests**

```bash
(cd 05-App && uv run pytest pipeline/tests/outcomes/test_duplicate_store.py -q)
```
Expected: `10 passed`

- [ ] **Step 5: Lint**

```bash
(cd 05-App && uvx ruff format --check pipeline/src/nidhinetra_pipeline/outcomes/duplicate_store.py pipeline/tests/outcomes/test_duplicate_store.py && uvx ruff check pipeline/src/nidhinetra_pipeline/outcomes/duplicate_store.py pipeline/tests/outcomes/test_duplicate_store.py)
```
Expected: `2 files already formatted` then `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add 05-App/pipeline/src/nidhinetra_pipeline/outcomes/duplicate_store.py 05-App/pipeline/tests/outcomes/test_duplicate_store.py
git commit -m "feat(outcomes): duplicate_store, R-06's pattern mirrored for identical batches (Phase 1 Stage C, 2/5)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

## Task 3: The `duplicates` API router

**Files:**
- Create: `05-App/api/src/nidhinetra_api/routers/duplicates.py`
- Create: `05-App/api/tests/test_duplicates.py`

**Interfaces:**
- Consumes: `duplicate_store` (Task 2); `db.connect`, `db.rows_as_dicts`, `db.SNAPSHOT_DIR` from `nidhinetra_api.db`; `Envelope` from `nidhinetra_api.models`.
- Produces: `router` (prefix `/api/duplicates`); `sync_duplicate_candidates_from_snapshot(snapshot_dir=None) -> int`; `DuplicateReviewRequest`; a query dependency `DuplicateQuery`/`duplicate_query` added to `nidhinetra_api.models` (mirrors `AliasQuery`/`alias_query`).

- [ ] **Step 1: Add the query model**

In `05-App/api/src/nidhinetra_api/models.py`, immediately after the existing `alias_query` function (before its blank lines and the `__all__` list), add:

```python
DuplicateStatus = Literal["pending", "confirmed_same", "rejected_different"]


class DuplicateQuery(BaseModel):
    """Pagination and current-status filter for the Phase 1 Stage C review queue."""

    status: DuplicateStatus = "pending"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


def duplicate_query(
    status: Annotated[DuplicateStatus, Query()] = "pending",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> DuplicateQuery:
    return DuplicateQuery(status=status, page=page, page_size=page_size)
```

Note: `AliasStatus` (checked with `grep -n "AliasStatus" 05-App/api/src/nidhinetra_api/models.py` before writing this) turned out to be a plain `Literal`, not an `Enum` — the code block above matches that. Add `"DuplicateQuery"`, `"DuplicateStatus"`, and `"duplicate_query"` to `models.py`'s `__all__` list, in alphabetical order alongside the existing entries.

- [ ] **Step 2: Write the failing tests**

Create `05-App/api/tests/test_duplicates.py`:

```python
"""Phase 1 Stage C: duplicate-review queue API and batched evidence resolution."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from nidhinetra_api import db
from nidhinetra_api.routers import duplicates
from nidhinetra_pipeline.outcomes import duplicate_store


def _candidate(
    scope: str,
    fingerprint: str,
    work_ids: list[str],
    *,
    finder: str = "identical_batch",
    threshold_crossing_batch: bool = False,
    text: str = "PCC Road, near Ram House",
) -> dict[str, object]:
    return {
        "finder": finder,
        "scope": scope,
        "fingerprint_a": fingerprint,
        "fingerprint_b": fingerprint,
        "finder_version": "candidate_generation_v0",
        "threshold_crossing_batch": threshold_crossing_batch,
        "text": text,
        "work_ids": work_ids,
    }


@pytest.fixture()
def duplicates_client(client: TestClient, isolated_outcomes_db: Path) -> TestClient:
    """Start the real app, then clear only the per-test duplicate tables."""
    duplicate_store.init_db(isolated_outcomes_db)
    with sqlite3.connect(isolated_outcomes_db) as connection:
        connection.execute("DELETE FROM duplicate_reviews")
        connection.execute("DELETE FROM duplicate_candidates")
        connection.commit()
    return client


def _seed(candidates: list[dict[str, object]]) -> list[dict[str, Any]]:
    duplicate_store.upsert_candidates(candidates)
    return duplicate_store.list_candidates(status=None)[0]


def test_pending_queue_has_house_envelope_and_pagination(duplicates_client: TestClient) -> None:
    _seed(
        [
            _candidate("C1", "1111111111111111", ["MPLADS-FX-0001", "MPLADS-FX-0002"]),
            _candidate("C2", "2222222222222222", ["MPLADS-FX-0003", "MPLADS-FX-0004"]),
            _candidate("C3", "3333333333333333", ["MPLADS-FX-0005", "MPLADS-FX-0006"]),
        ]
    )

    response = duplicates_client.get(
        "/api/duplicates", params={"status": "pending", "page": 2, "page_size": 2}
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"success", "data", "error", "meta"}
    assert body["success"] is True
    assert [row["scope"] for row in body["data"]] == ["C3"]
    assert body["meta"] == {"page": 2, "page_size": 2, "total": 3, "total_pages": 2}


def test_status_filters_use_only_the_current_review(duplicates_client: TestClient) -> None:
    candidates = _seed(
        [
            _candidate("C1", "1111111111111111", ["MPLADS-FX-0001", "MPLADS-FX-0002"]),
            _candidate("C2", "2222222222222222", ["MPLADS-FX-0003", "MPLADS-FX-0004"]),
            _candidate("C3", "3333333333333333", ["MPLADS-FX-0005", "MPLADS-FX-0006"]),
        ]
    )
    ids = {row["scope"]: row["candidate_id"] for row in candidates}
    duplicate_store.record_review(ids["C1"], "confirmed_same", "RK")
    duplicate_store.record_review(ids["C2"], "rejected_different", "RK")

    pending = duplicates_client.get("/api/duplicates", params={"status": "pending"}).json()
    confirmed = duplicates_client.get(
        "/api/duplicates", params={"status": "confirmed_same"}
    ).json()
    rejected = duplicates_client.get(
        "/api/duplicates", params={"status": "rejected_different"}
    ).json()

    assert [row["scope"] for row in pending["data"]] == ["C3"]
    assert [row["scope"] for row in confirmed["data"]] == ["C1"]
    assert confirmed["data"][0]["current_review"]["reviewed_by"] == "RK"
    assert [row["scope"] for row in rejected["data"]] == ["C2"]


def test_page_evidence_is_resolved_with_one_batched_duckdb_query(
    duplicates_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    works = duplicates_client.get("/api/works", params={"page_size": 3}).json()["data"]
    work_ids = [row["work_id"] for row in works]
    _seed(
        [
            _candidate("C1", "1111111111111111", [work_ids[1], work_ids[0]]),
            _candidate("C2", "2222222222222222", [work_ids[1], work_ids[2]]),
        ]
    )
    calls: list[tuple[str, list[Any]]] = []
    real_rows_as_dicts = db.rows_as_dicts

    def recording_rows_as_dicts(con, sql: str, params: list[Any] | None = None):
        calls.append((sql, params or []))
        return real_rows_as_dicts(con, sql, params)

    monkeypatch.setattr(duplicates.db, "rows_as_dicts", recording_rows_as_dicts)

    body = duplicates_client.get("/api/duplicates", params={"status": "pending"}).json()

    evidence_queries = [call for call in calls if "works.work_id IN" in call[0]]
    assert len(evidence_queries) == 1
    assert set(evidence_queries[0][1]) == set(work_ids)
    by_id = {row["scope"]: row for row in body["data"]}
    assert [work["work_id"] for work in by_id["C1"]["evidence_works"]] == sorted(
        [work_ids[0], work_ids[1]]
    )
    assert all("work_description" in work for row in body["data"] for work in row["evidence_works"])


def test_review_post_assigns_history_fields_and_correction_supersedes(
    duplicates_client: TestClient,
) -> None:
    (candidate,) = _seed([_candidate("C1", "1111111111111111", ["MPLADS-FX-0001", "MPLADS-FX-0002"])])

    first = duplicates_client.post(
        f"/api/duplicates/{candidate['candidate_id']}/review",
        json={"status": "confirmed_same", "reviewed_by": "RK", "reviewer_note": "Checked."},
    )
    assert first.status_code == 200
    first_review = first.json()["data"]["current_review"]
    assert first_review["status"] == "confirmed_same"
    assert first_review["reviewed_at"].endswith("Z")
    assert first_review["supersedes"] is None

    second = duplicates_client.post(
        f"/api/duplicates/{candidate['candidate_id']}/review",
        json={"status": "rejected_different", "reviewed_by": "AB", "reviewer_note": "Corrected."},
    )
    assert second.status_code == 200
    second_review = second.json()["data"]["current_review"]
    assert second_review["supersedes"] == first_review["review_id"]
    assert len(duplicate_store.get_review_history(candidate["candidate_id"])) == 2


@pytest.mark.parametrize(
    ("path", "json_body", "expected_status"),
    [
        ("/api/duplicates/999999/review", {"status": "confirmed_same", "reviewed_by": "RK"}, 404),
        ("/api/duplicates/{id}/review", {"status": "duplicate", "reviewed_by": "RK"}, 400),
        ("/api/duplicates/{id}/review", {"status": "confirmed_same"}, 422),
        ("/api/duplicates/{id}/review", {"status": "confirmed_same", "reviewed_by": ""}, 422),
        (
            "/api/duplicates/{id}/review",
            {"status": "confirmed_same", "reviewed_by": "RK", "supersedes": 4},
            422,
        ),
    ],
)
def test_review_validation_errors_use_house_envelope(
    duplicates_client: TestClient,
    path: str,
    json_body: dict[str, object],
    expected_status: int,
) -> None:
    (candidate,) = _seed([_candidate("C1", "1111111111111111", ["MPLADS-FX-0001", "MPLADS-FX-0002"])])
    path = path.format(id=candidate["candidate_id"])

    response = duplicates_client.post(path, json=json_body)

    assert response.status_code == expected_status
    assert response.json()["success"] is False


@pytest.mark.parametrize(
    "params",
    [{"status": "duplicate"}, {"page": 0}, {"page_size": 201}],
)
def test_list_query_validation_is_422(duplicates_client: TestClient, params: dict[str, object]) -> None:
    response = duplicates_client.get("/api/duplicates", params=params)
    assert response.status_code == 422
    assert response.json()["success"] is False


def test_sync_upserts_only_identical_batches_and_missing_artifact_is_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    snapshot_dir = tmp_path / "snapshot"
    snapshot_dir.mkdir()
    monkeypatch.setattr(duplicates.db, "SNAPSHOT_DIR", snapshot_dir)

    assert duplicates.sync_duplicate_candidates_from_snapshot() == 0
    assert "duplicate_candidates.json" in caplog.text

    artifact = {
        "meta": {"finder_version": "candidate_generation_v0"},
        "groups": {
            "aaaaaaaaaaaaaaaa": {
                "text_fingerprint": "aaaaaaaaaaaaaaaa",
                "text": "PCC Road, near Ram House",
                "work_ids": ["MPLADS-FX-0001", "MPLADS-FX-0002"],
            },
            "bbbbbbbbbbbbbbbb": {
                "text_fingerprint": "bbbbbbbbbbbbbbbb",
                "text": "Solar street lights",
                "work_ids": ["MPLADS-FX-0003", "MPLADS-FX-0004"],
            },
        },
        "batches": [
            {
                "finder": "identical_batch",
                "scope": "C1",
                "group": "aaaaaaaaaaaaaaaa",
                "threshold_crossing_batch": True,
            }
        ],
        "pairs": [
            {
                "finder": "near_copy",
                "scope": "C1",
                "a": "aaaaaaaaaaaaaaaa",
                "b": "bbbbbbbbbbbbbbbb",
            }
        ],
    }
    (snapshot_dir / "duplicate_candidates.json").write_text(json.dumps(artifact), encoding="utf-8")

    assert duplicates.sync_duplicate_candidates_from_snapshot() == 1
    rows, total = duplicate_store.list_candidates(status="pending")
    assert total == 1
    assert rows[0]["scope"] == "C1"
    assert rows[0]["threshold_crossing_batch"] is True
```

- [ ] **Step 3: Run it and watch it fail**

```bash
(cd 05-App && uv run pytest api/tests/test_duplicates.py -q)
```
Expected: `No module named 'nidhinetra_api.routers.duplicates'`

- [ ] **Step 4: Write the module**

Create `05-App/api/src/nidhinetra_api/routers/duplicates.py`:

```python
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
```

- [ ] **Step 5: Run the tests**

```bash
(cd 05-App && uv run pytest api/tests/test_duplicates.py -q)
```
Expected: `13 passed` (parametrized cases count individually: 5 in the validation-error test, 3 in the query-validation test, 5 unparametrized). This also needs the router wired into `main.py` (this plan's Task 4 Step 4) to get real HTTP routes rather than a 404 from every request -- pull that step forward to here rather than leaving these tests red until Task 4.

- [ ] **Step 6: Lint**

```bash
(cd 05-App && uvx ruff format --check api/src/nidhinetra_api/models.py api/src/nidhinetra_api/routers/duplicates.py api/tests/test_duplicates.py && uvx ruff check api/src/nidhinetra_api/models.py api/src/nidhinetra_api/routers/duplicates.py api/tests/test_duplicates.py)
```
Expected: `3 files already formatted` then `All checks passed!`

- [ ] **Step 7: Commit**

```bash
git add 05-App/api/src/nidhinetra_api/models.py 05-App/api/src/nidhinetra_api/routers/duplicates.py 05-App/api/tests/test_duplicates.py
git commit -m "feat(api): the duplicates review-queue router, mirrored from entity-aliases (Phase 1 Stage C, 3/5)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

## Task 4: `duplicate_context` onto work detail

**Already done in Task 3** (pulled forward there because Task 3's own tests needed it to run safely — see that commit's message): the `conftest.py` isolation fix, and the `main.py` wiring (import, lifespan sync call, `include_router`). This task is now only the `works.py` change and its test.

**Files:**
- Modify: `05-App/api/src/nidhinetra_api/routers/works.py`
- Modify: `05-App/api/tests/test_works.py` (find its existing detail-endpoint test file; if the work-detail tests live elsewhere, add there instead — check with `grep -rn "def get_work\|/api/works/{" 05-App/api/tests`)

**Interfaces:**
- Consumes: `duplicate_store.duplicate_context` (Task 2).
- Produces: `GET /api/works/{work_id}` responses gain a `duplicate_context` key.

- [ ] **Step 1: Write the failing test**

Find the work-detail test file:
```bash
grep -rln 'def test.*get_work\|"/api/works/' 05-App/api/tests
```
In that file, add (adjust the import at the top of the file to include `from nidhinetra_pipeline.outcomes import duplicate_store` if it is not already imported):

```python
def test_work_detail_carries_duplicate_context(client: TestClient) -> None:
    first_page = client.get("/api/works", params={"page_size": 1}).json()["data"]
    work_id = first_page[0]["work_id"]

    duplicate_store.upsert_candidates(
        [
            {
                "finder": "identical_batch",
                "scope": "C1",
                "fingerprint_a": "1111111111111111",
                "fingerprint_b": "1111111111111111",
                "finder_version": "candidate_generation_v0",
                "threshold_crossing_batch": True,
                "text": "PCC Road, near Ram House",
                "work_ids": [work_id, "MPLADS-FX-0099"],
            }
        ]
    )

    response = client.get(f"/api/works/{work_id}")

    assert response.status_code == 200
    context = response.json()["data"]["duplicate_context"]
    assert context == [
        {
            "candidate_id": context[0]["candidate_id"],
            "finder": "identical_batch",
            "threshold_crossing_batch": True,
            "text": "PCC Road, near Ram House",
            "work_count": 2,
            "other_work_ids": ["MPLADS-FX-0099"],
            "status": "pending",
        }
    ]


def test_work_detail_duplicate_context_is_empty_list_when_there_is_none(
    client: TestClient,
) -> None:
    first_page = client.get("/api/works", params={"page_size": 1}).json()["data"]
    work_id = first_page[0]["work_id"]

    response = client.get(f"/api/works/{work_id}")

    assert response.json()["data"]["duplicate_context"] == []
```

- [ ] **Step 2: Run it and watch it fail**

```bash
(cd 05-App && uv run pytest api/tests -k duplicate_context -q)
```
Expected: `KeyError: 'duplicate_context'`

- [ ] **Step 3: Add `duplicate_context` to the work-detail endpoint**

In `05-App/api/src/nidhinetra_api/routers/works.py`, add the import:
```python
from nidhinetra_pipeline.outcomes import duplicate_store
```
(alongside this file's other imports, in import-sort order)

Change `get_work`:
```python
@router.get("/{work_id}")
def get_work(work_id: Annotated[str, Path(min_length=1, max_length=64)]) -> Envelope:
    with contextlib.closing(db.connect()) as con:
        rows = db.rows_as_dicts(con, _MERGED_SELECT + " WHERE works.work_id = ?", [work_id])
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No work found with id '{work_id}' in the current snapshot.",
        )
    record = db.decode_scored_json(rows)[0]
    record["duplicate_context"] = duplicate_store.duplicate_context(work_id)
    return Envelope(success=True, data=record)
```

- [ ] **Step 4: Run the tests**

```bash
(cd 05-App && uv run pytest api/tests -q)
```
Expected: `178 passed` (176 after Task 3, plus the two new tests)

- [ ] **Step 5: Lint**

```bash
(cd 05-App && uvx ruff format --check api/src/nidhinetra_api/routers/works.py && uvx ruff check api/src/nidhinetra_api/routers/works.py)
```
Expected: `1 file already formatted` then `All checks passed!` (plus whichever test file Step 1 landed the new tests in)

- [ ] **Step 6: Commit**

```bash
git add 05-App/api/src/nidhinetra_api/routers/works.py 05-App/api/tests/test_works.py
git commit -m "feat(api): add duplicate_context to the work-detail endpoint (Phase 1 Stage C, 4/5)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```
(If the detail test landed in a different file than `test_works.py`, `git add` that file instead.)

## Task 5: `validate.py`, the whole-repo gates, and a real sync

**Files:**
- Modify: `05-App/contracts/validate.py`

**Interfaces:**
- Consumes: the two new schemas (Task 1).
- Produces: `validate.py` checks fixture-adjacent negative cases for both new contracts, mirroring its existing alias self-test.

- [ ] **Step 1: Read `validate.py`'s alias self-test (Self-test 4) fully**

```bash
grep -n "Self-test 4" -A 30 05-App/contracts/validate.py
```
This plan does not fixture-validate `duplicate_candidates.json` itself (Stage A's own builder already validates that artifact against its own schema on every write — see `duplicates/candidates.py`'s `validate_duplicate_candidates`). What this step adds is a schema self-test for the *review-store* shapes this plan just introduced: a hand-built minimal candidate and review object, checked against `duplicate_candidate.schema.json` and `duplicate_review.schema.json`, plus one broken case each that must be rejected. Read the existing Self-test 4 fully before writing this, and match its structure (a `with tempfile.TemporaryDirectory()` block, a PASS/FAIL print, a non-zero exit on failure) exactly.

- [ ] **Step 2: Add Self-test 6**

Add, after the last existing self-test and before the summary print (`grep -n "All self-tests passed" 05-App/contracts/validate.py` to find the exact insertion point), a new self-test that:
1. Loads `duplicate_candidate.schema.json` and `duplicate_review.schema.json`.
2. Validates one well-formed example of each (reuse the two JSON bodies from Task 1's Step 3 command, trimmed to one candidate and one review) and asserts no errors.
3. Validates one broken example of each — a candidate with `work_ids: ["only-one"]` (violates `minItems: 2`), and a review with `status: "duplicate"` (not in the enum) — and asserts the validator raises.
4. Prints `PASS` or `FAIL` in the same style as the file's other self-tests, and contributes to the script's overall exit code exactly as the existing self-tests do.

Do not touch `validate_all`'s cross-file checks (Self-tests 1-3) or the CLI argument list — this task only adds a new self-test function and a call to it from `main()`, following the existing file's own pattern for where self-tests are registered and run.

- [ ] **Step 3: Run it**

```bash
(cd 05-App && uv run --package nidhinetra-pipeline python contracts/validate.py --self-test)
```
Expected: every existing self-test still `PASS`, the new one also `PASS`, `All self-tests passed.` at the end.

- [ ] **Step 4: Lint**

```bash
(cd 05-App && uvx ruff format --check contracts/validate.py && uvx ruff check contracts/validate.py)
```
Expected: `1 file already formatted` then `All checks passed!`

- [ ] **Step 5: The whole suite**

```bash
(cd 05-App && uv run pytest pipeline/tests -q && uv run pytest api/tests -q && make validate)
```
Expected: pipeline `524 passed` (523 before this plan, plus the one Task 4 detail test if it landed as a single new test — adjust the expectation to match Task 4's actual Step 6 count if `test_works.py` already had other tests added since this plan was written), API `165 passed`, and `make validate`'s final line `All self-tests passed. The validator has real teeth.`

- [ ] **Step 6: A real sync against the committed artifact, in a scratch copy**

`data/outcomes/outcomes.db` is off limits for a write from this plan. This proves the sync function against the real, committed `duplicate_candidates.json` without touching it.

```bash
(cd 05-App && SCRATCH=$(mktemp -d) && uv run --package nidhinetra-pipeline python - "$SCRATCH" <<'PY'
import sys
from pathlib import Path

from nidhinetra_api.routers import duplicates
from nidhinetra_pipeline.outcomes import duplicate_store

scratch = Path(sys.argv[1])
duplicate_store.DEFAULT_DB_PATH = scratch / "outcomes.db"

count = duplicates.sync_duplicate_candidates_from_snapshot(Path("data/snapshot"))
print("synced", count)

rows, total = duplicate_store.list_candidates(status=None, page_size=5)
print("total in store:", total)
print("threshold_crossing among first 5:", [r["threshold_crossing_batch"] for r in rows])
PY
)
```
Expected: `synced 1180` (1,176 identical batches plus 4 district ones), `total in store: 1180`, and a mix of `True`/`False` in the threshold line. This import needs `nidhinetra_api` on the path -- run it with `uv run --package nidhinetra-pipeline`, which resolves the whole workspace, not `--package nidhinetra-api` alone.

- [ ] **Step 7: Confirm nothing real was touched**

```bash
git status --porcelain -- 05-App/data
```
Expected: no output.

- [ ] **Step 8: Commit**

```bash
git add 05-App/contracts/validate.py
git commit -m "test(contracts): self-test the two new duplicate-review contracts (Phase 1 Stage C, 5/5)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

## Done when

- `uv run pytest pipeline/tests -q` and `uv run pytest api/tests -q` both pass, with 21 new tests across the two suites (11 in Task 2, 9 in Task 3, 2 in Task 4 minus 1 double-counted... count exactly from each task's own `Expected:` line, not this summary).
- `make validate` prints `All self-tests passed. The validator has real teeth.`
- `uvx ruff format --check` and `uvx ruff check` pass on every file this plan creates or edits.
- A sync against the real, committed `data/snapshot/duplicate_candidates.json` (Task 5 Step 6) produces exactly 1,180 candidates, and `git status -- 05-App/data` is empty throughout.
- Five commits, each green on its own tests before the next task starts.

## Not in this plan (Stage C, Part 2)

- The `duplicates` UI: a review-queue component (mirrors `AliasReviewQueue.tsx`), its CSS module, its `web/lib` client functions (mirrors `entity-aliases.ts`), and its tests.
- Mounting the queue inline on the Inspection List page with a pending count, matching the spec's placement.
- The detail panel's "Works with the same or similar description" section, reading the new `duplicate_context` field this plan adds to the API.
- The `strings.json` block (`duplicate_review`, modelled on `entity_alias_review`, reusing "These are the same" / "These are different").
- `web/lib/types.ts`'s mirror of the new API shapes, and `test_web_mirror_drift.py` coverage for them.
- Syncing near-copy pairs once Stage D has narrowed them by judge answer (Decision 1).
- `nav` changes: none are needed (`Global Constraints`: nav stays at four tabs), so nothing here should ever touch `web/components/shared/Nav*`.
