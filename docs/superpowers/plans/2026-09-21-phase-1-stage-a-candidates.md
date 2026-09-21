# Phase 1 Stage A: Candidates for Duplicate and Split Works Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Find, without any model, the works whose portal descriptions are identical or nearly identical, and write them to `data/snapshot/duplicate_candidates.json` for the pair judge (Stage B) and the review queue (Stage C), without moving any work's score, rank or flags.

**Architecture:** One new package, `nidhinetra_pipeline/duplicates/`, with one pure function, `build_duplicate_candidates(records)`, and three finders: identical batches (Finder 1), near-copy pairs (Finder 2) and a quiet district audit (Finder 3). A *text group* (the works that share one canonical description in one scope) is stored once and referenced by id, which keeps the artifact at 23.6 MB instead of 55 MB. `build_snapshot()` stages the artifact as a sixth file in its all-or-none batch, and a small `cli duplicates` command adds it to the committed snapshot without re-scoring anything.

**Tech Stack:** Python 3.13, `uv`, pytest, scikit-learn (TF-IDF), numpy and scipy (installed with scikit-learn; add no dependency), jsonschema, pandas/pyarrow, ruff.

**Spec:** `docs/superpowers/specs/2026-09-17-foundation-and-duplicate-works-design.md` (Phase 1, Stage A). Read its "Phase 1, Stage A" section first; this plan cites it rather than repeating it.

## Global Constraints

- **Never push.** Commit locally on `codex/finish-nidhinetra`. The user pushes after review.
- **No score change.** No work's `risk_score`, `inspection_rank`, `flags`, `why_flagged` or `peer_group` may move. Nothing here imports `risk/`. `build_duplicate_candidates` never modifies its input (Task 4 tests it) and `cli duplicates --write` writes exactly one file (Task 6 tests it).
- **`data/snapshot/` is off limits until Task 7**, which is gated on the user's written go-ahead. Every test writes under `tmp_path` and none reads the real snapshot.
- **No user-visible text.** Nothing here reaches an officer. `contracts/strings.json` is not touched; Stage C owns the wording, including the clause 4.4.2 sentence.
- **Frozen rules.** `canonical_description_v1`, the `candidate_generation_v0` thresholds and `COMMON_TOKENS_V0` are versioned facts. Changing any of them means a new version, never an edit in place. (The spec lets Stage D revise the thresholds once.)
- **No model, no network, no clock, no new dependency.**
- **Neutral words.** A candidate is "works sharing the same or a similar portal description". Code names are `identical_batch`, `near_copy` and `difference_group`. Nothing in the artifact says a work is a duplicate, or mentions fraud, intent or evasion.
- ruff: `line-length = 100`, rules `E,F,I,UP,B`. Run `uvx ruff format` and `uvx ruff check` on the files a task changes, and only those: ruff is not in `uv.lock`, and the tree has known findings in files this plan never touches (`rungs.py`, `test_rungs.py`, `test_web_mirror_drift.py`).
- Gates before each commit: `make validate` (both contract checks) and `uv run pytest pipeline/tests -q`; in Task 6 also `uv run pytest api/tests -q`.
- Every command block starts from the repository root, and a block that needs `05-App` runs in a subshell, `(cd 05-App && ...)`, so the working directory never changes between steps. File paths in the prose are relative to `05-App/` unless they start with `docs/`; `git add` paths carry the `05-App/` prefix.

## What the real data says

Measured on 2026-09-21, read-only, with the code in this plan run against the committed `data/snapshot/works.parquet` (79,068 works, 79,066 with a description). Task 7 prints the same counts.

| Quantity | Spec (2026-09-04 capture) | This plan's code |
|---|---|---|
| Works with a readable description | not stated | 79,038 (28 descriptions are punctuation only) |
| Identical `work_description` inside a constituency (`cleaned_source_text_group`; not emitted, punctuation-only texts included) | 1,152 groups / 8,193 works | **1,152 groups / 8,193 works** |
| Identical batches (`canonical_v1_text_group`, what Finder 1 groups by) | 1,176 groups / 8,576 works | **1,176 groups / 8,576 works** |
| `threshold_crossing_batch` | 271 groups / 5,424 works / Rs 204.5 crore | **271 / 5,424 / Rs 204.5 crore** |
| Comparison space inside constituencies | 9,065,219; largest block 1,371 texts | **9,065,219; 1,371** |
| Near-copy text pairs | 40,304 | 39,123 (2.9% fewer) |
| of which reworded / one-sided / conflicting | 453 / 3,083 / 35,427 (earlier tokenizer, 38,963 pairs) | 147 / 2,386 / 36,590 |
| District audit: identical groups | 4 | **4** |
| District audit: near-copy pairs | 11 | 3 |
| Distinct text groups the artifact references | not stated | 13,008 |
| Artifact size | not stated | 23.6 MB compact (37.4 MB indented, 2.4 MB compressed) |
| Build and validate | not stated | about 23 s |

Two runs of the command produced the same file byte for byte (sha256 starting `7340fc4dc2755730`), including after the code was refactored into the shape below.

## Decisions where the spec is silent, or its numbers do not survive the data

The user may overrule any of these. Each one is small to reverse before Task 7 and expensive after it.

1. **Text groups are stored once.** The spec says every candidate carries both sides' work ids and summaries. Written that way the file is 55 MB compact and 84 MB at the repository's usual `indent=2`; GitHub warns at 50 MB and refuses at 100 MB. 13,008 groups serve 39,126 pairs and 1,180 batches, so groups live once under `groups` and pairs and batches point at them by id. Every field the spec lists is still present. The file is written without indentation.
2. **Scope is the constituency.** The spec says "same constituency" without naming the field. `constituency` reproduces the spec's block sizes exactly, and every constituency name belongs to one state, so adding `state` changes nothing.
3. **A description with no letter or digit is ignored** (28 works, for example "-"). Counting them as one text gives 1,181 groups / 8,604 works; ignoring them gives the spec's 1,176 / 8,576.
4. **"Content tokens" are the canonical tokens minus 19 frozen common words.** The spec does not define them. Words found in at least 10% of all distinct descriptions (`of`, `construction`, `village`, `road`, ...) identify nothing, and dropping them lands the near-copy yield within 3% of the spec's. A short function-word list gives about 79,000 pairs and no list gives 82,000. The list is frozen as `COMMON_TOKENS_V0` instead of derived on every build, so a rebuild cannot move it. The reworded / one-sided / conflicting split differs from the spec's because its run used an unrecorded tokenizer that also ignored single digits; the spec already has Stage D re-measure under the final tokenizer.
5. **The two channels, made exact.** Character channel: TF-IDF over 3 to 5 character n-grams inside words (`char_wb`), fitted once over all distinct texts so every block shares one vocabulary, cosine at or above 0.80. Token channel: Jaccard over content tokens at or above 0.75 with at least three shared tokens ("on at least three tokens" is read as three shared). Both scores are rounded to four decimals before they meet a threshold, because 12 to 14 pairs flip on float noise otherwise.
6. **Finder 3 finds 3 near-copy pairs, not 11.** Its 4 identical groups match. The spec does not define the comparison exactly; this plan compares texts within one district authority at 0.90 when the two sides span at least two constituencies. The pass is stored and unfeatured either way.
7. **The clause 4.4.2 sentence is not attached by code.** The artifact carries the boolean `threshold_crossing_batch` and the two amounts (`meta.thresholds`). The sentence is user-visible copy, so it belongs in `strings.json` with an amendment-log entry, which Stage C writes when a screen exists.
8. **The real artifact comes from `cli duplicates --write`, not from a full rebuild.** `build_snapshot()` scores against the day it runs (the offline rebuild kit calls it without `now`), and `stalled_work` and the anomaly ensemble both read that date, so a second full rebuild on another day can move scores. The new command reads the committed `works.parquet` and writes one file. `build_snapshot()` also produces the artifact, so a future full rebuild stays consistent. The kit (`SIHGit/kit/rebuild_snapshot_offline.py`) names five artifacts and lives outside this repository: if it is ever run again, add `duplicate_candidates.json` to its `ARTIFACTS`.
9. **Deferred, with reasons.** No `contracts/validate.py` wiring and no fixture file: the builder validates its own output, and a hand-written fixture only earns its keep once Stage C has a screen. The parked demo-fixture cleanup stays parked for the same reason (the 20 fixture works share no description, so their artifact is empty). `_clean()` is not touched: the canonical form already turns a stray line break into a space. **For Stage C:** do not `json.load` this 23.6 MB file at API start-up on Render's free tier; filter to the pairs a judgment makes eligible, or read it with DuckDB.
10. **Candidate ids carry the finder version.** `_candidate_id` hashes `FINDER_VERSION` in, as the spec's identity line reads (scope, both text fingerprints, finder version). When Stage D revises the thresholds and `candidate_generation_v0` becomes `v1`, every candidate id and every group id will change, including those of pairs the revision does not touch. **Open, for the user before Task 7:** either leave it and have Stage C key durable officer decisions on `(scope, groups[a].text_fingerprint, groups[b].text_fingerprint)`, which the artifact already carries, or drop `FINDER_VERSION` from the id hash now (one token in `_candidate_id`; the artifact's sha256 then stops being `7340fc4dc2755730`, which this plan records only as a note in Task 7 Step 6). The final review recommends the first: it costs nothing and keeps that hash as a cross-machine check.

## Vocabulary

- **Canonical text**: `canonical_description_v1(work_description)`. Two works "share a description" when their canonical texts are equal.
- **Scope**: the constituency for Finders 1 and 2, the implementing district authority for Finder 3.
- **Text group**: the works in one scope that share one canonical text. It carries the work ids, amount range and total, sanction dates, agencies, statuses and the most common published wording.
- **Batch**: a text group with two or more works (identical batch), or one whose works span two or more constituencies of one district authority (district batch).
- **Pair**: two text groups in one scope that a channel found similar. `a` is the side whose canonical text sorts first.
- **Difference group**: `reworded_match` (no content word on only one side), `one_sided_detail` (words on one side only), `conflicting_detail` (different words on both). The name says what the code knows, not what it suspects.

The finders read exactly these fields of a normalized record: `work_id`, `constituency`, `implementing_district_authority`, `implementing_agency`, `work_description`, `activity_name`, `sanctioned_amount_inr`, `sanction_date`, `completion_status`.

## File Structure

Create:
- `contracts/duplicate_candidates.schema.json`: the artifact's contract.
- `pipeline/src/nidhinetra_pipeline/duplicates/__init__.py` and `candidates.py`: everything else, in one file. The three finders share one similarity routine and one set of helpers, so splitting them would scatter it.
- `pipeline/tests/duplicates/__init__.py` and `test_candidates.py`.

Modify:
- `pipeline/src/nidhinetra_pipeline/build_snapshot.py` and `cli.py`.
- `pipeline/tests/test_build_snapshot.py` and `test_cli.py`.

Nothing else changes: no `pyproject.toml`, no API, no web, no `strings.json`.

## Spec coverage

| Spec, Phase 1 Stage A | Where |
|---|---|
| `canonical_description_v1`, frozen; original text kept separately | Task 1 (text kept as `group.text`, Task 2) |
| Finder 1: work count, amount range, total, sanction dates, agency; `threshold_crossing_batch` | Task 2 |
| Finder 2: same-constituency blocking, both channels over the full pair space, digits as tokens, three difference groups | Task 3 |
| Finder 3: district audit, stored and unfeatured | Task 4 |
| Thresholds named `candidate_generation_v0` | Task 1 |
| Deterministic identity (scope, both text fingerprints, finder version), hits, both scores, shared and one-sided tokens, work ids, summaries | Tasks 2 to 4 |
| Staged and committed with the other snapshot files, all or none | Task 5 (staging), Task 7 (commit) |
| Nothing changes any work's score, rank or flags | Tasks 4, 5 and 6 (tests), Task 7 (file hashes) |

---

### Task 1: The artifact contract and the frozen text rules

**Files:**
- Create: `contracts/duplicate_candidates.schema.json`
- Create: `pipeline/src/nidhinetra_pipeline/duplicates/__init__.py`
- Create: `pipeline/src/nidhinetra_pipeline/duplicates/candidates.py`
- Create: `pipeline/tests/duplicates/__init__.py` (empty)
- Test: `pipeline/tests/duplicates/test_candidates.py`

**Interfaces:**
- Consumes: nothing.
- Produces, all in `nidhinetra_pipeline.duplicates.candidates`: `canonical_description_v1(text: str) -> str`; `content_tokens(canonical: str) -> list[str]`; `fingerprint(canonical: str) -> str` (16 hex characters); `validate_duplicate_candidates(artifact: dict) -> None`, which raises `DuplicateCandidateValidationError`; the constants `CANONICAL_VERSION`, `FINDER_VERSION`, `CHARACTER_SIMILARITY_MIN`, `TOKEN_JACCARD_MIN`, `TOKEN_SHARED_MIN`, `DISTRICT_CHARACTER_SIMILARITY_MIN`, `PER_WORK_LIMIT_INR`, `GROUP_TOTAL_FLOOR_INR`, `SCORE_DECIMALS`, `COMMON_TOKENS_V0`, `SCHEMA_PATH`; and the private `_candidate_id(*parts: str) -> str`. The artifact's shape is the schema below: `meta`, `groups`, `batches`, `pairs`. Tasks 2 to 4 rely on those names exactly.

- [ ] **Step 1: Confirm the baseline**

```bash
(cd 05-App && uv run pytest pipeline/tests -q)
```
Expected: `332 passed`. If anything fails before you have changed a file, stop and report.

- [ ] **Step 2: Write the failing tests**

Create an empty `pipeline/tests/duplicates/__init__.py`, then create `pipeline/tests/duplicates/test_candidates.py`:

```python
"""Phase 1 Stage A: canonical text, identical batches, near-copy pairs, the district audit."""

from __future__ import annotations

import unicodedata

import pytest
from nidhinetra_pipeline.duplicates.candidates import (
    DuplicateCandidateValidationError,
    canonical_description_v1,
    content_tokens,
    fingerprint,
    validate_duplicate_candidates,
)


class TestCanonicalDescription:
    def test_lowercases_and_collapses_punctuation_and_spacing(self) -> None:
        assert (
            canonical_description_v1("  PCC Road,  from Ram-house (Ward 3)\n")
            == "pcc road from ram house ward 3"
        )

    def test_keeps_digits_and_folds_compatibility_forms(self) -> None:
        assert canonical_description_v1("Ｎｏ ３５ ﬁtting") == "no 35 fitting"

    def test_keeps_devanagari_words_whole(self) -> None:
        text = "सड़क निर्माण"
        assert canonical_description_v1(text) == unicodedata.normalize("NFKC", text)
        assert len(canonical_description_v1(text).split()) == 2

    def test_punctuation_only_is_empty(self) -> None:
        assert canonical_description_v1("--- . ,") == ""

    def test_fingerprint_is_16_hex_and_depends_only_on_the_canonical_text(self) -> None:
        assert fingerprint("pcc road") == fingerprint("pcc road")
        assert fingerprint("pcc road") != fingerprint("pcc roads")
        assert len(fingerprint("pcc road")) == 16
        assert int(fingerprint("pcc road"), 16) >= 0

    def test_content_tokens_drop_common_words_and_keep_numbers(self) -> None:
        assert content_tokens("construction of community hall no 3 at ward 9") == [
            "community",
            "hall",
            "3",
            "ward",
            "9",
        ]


def _valid_artifact() -> dict:
    return {
        "meta": {
            "canonical_version": "canonical_description_v1",
            "finder_version": "candidate_generation_v0",
            "thresholds": {
                "character_similarity_min": 0.8,
                "token_jaccard_min": 0.75,
                "token_shared_min": 3,
                "district_character_similarity_min": 0.9,
                "per_work_limit_inr": 1500000,
                "group_total_floor_inr": 2500000,
            },
            "common_tokens": ["of", "road"],
            "counts": {
                key: 0
                for key in (
                    "works_considered",
                    "groups",
                    "identical_batches",
                    "threshold_crossing_batches",
                    "district_identical_batches",
                    "near_copy_pairs",
                    "reworded_match",
                    "one_sided_detail",
                    "conflicting_detail",
                    "district_near_copy_pairs",
                )
            },
        },
        "groups": {},
        "batches": [],
        "pairs": [],
    }


class TestSchema:
    def test_an_empty_artifact_is_valid(self) -> None:
        validate_duplicate_candidates(_valid_artifact())

    def test_an_artifact_without_its_counts_is_rejected(self) -> None:
        artifact = _valid_artifact()
        del artifact["meta"]["counts"]

        with pytest.raises(DuplicateCandidateValidationError, match="counts"):
            validate_duplicate_candidates(artifact)

    def test_a_batch_from_an_unknown_finder_is_rejected(self) -> None:
        artifact = _valid_artifact()
        artifact["batches"].append(
            {
                "candidate_id": "0123456789abcdef",
                "finder": "guess",
                "scope": "C1",
                "threshold_crossing_batch": False,
                "group": "0123456789abcdef",
            }
        )

        with pytest.raises(DuplicateCandidateValidationError, match="finder"):
            validate_duplicate_candidates(artifact)
```

- [ ] **Step 3: Run the tests to verify they fail**

```bash
(cd 05-App && uv run pytest pipeline/tests/duplicates -q)
```
Expected: FAIL at collection with `ModuleNotFoundError: No module named 'nidhinetra_pipeline.duplicates'` (the package does not exist yet at this step).

- [ ] **Step 4: Add the contract**

Create `contracts/duplicate_candidates.schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://nidhinetra.local/contracts/duplicate_candidates.schema.json",
  "title": "DuplicateCandidates",
  "description": "Phase 1 Stage A output: works whose portal descriptions are identical or nearly identical. Facts about text and money only; nothing here says a work is a duplicate. A text group is stored once and referenced by id from the batches and pairs that use it.",
  "type": "object",
  "additionalProperties": false,
  "required": ["meta", "groups", "batches", "pairs"],
  "properties": {
    "meta": { "$ref": "#/definitions/meta" },
    "groups": {
      "type": "object",
      "additionalProperties": false,
      "patternProperties": {
        "^[0-9a-f]{16}$": { "$ref": "#/definitions/text_group" }
      }
    },
    "batches": { "type": "array", "items": { "$ref": "#/definitions/batch" } },
    "pairs": { "type": "array", "items": { "$ref": "#/definitions/pair" } }
  },
  "definitions": {
    "id": { "type": "string", "pattern": "^[0-9a-f]{16}$" },
    "date": { "type": ["string", "null"], "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$" },
    "tokens": {
      "type": "array",
      "items": { "type": "string", "minLength": 1 },
      "uniqueItems": true
    },
    "meta": {
      "type": "object",
      "additionalProperties": false,
      "required": ["canonical_version", "finder_version", "thresholds", "common_tokens", "counts"],
      "properties": {
        "canonical_version": { "const": "canonical_description_v1" },
        "finder_version": { "const": "candidate_generation_v0" },
        "thresholds": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "character_similarity_min",
            "token_jaccard_min",
            "token_shared_min",
            "district_character_similarity_min",
            "per_work_limit_inr",
            "group_total_floor_inr"
          ],
          "properties": {
            "character_similarity_min": { "type": "number" },
            "token_jaccard_min": { "type": "number" },
            "token_shared_min": { "type": "integer" },
            "district_character_similarity_min": { "type": "number" },
            "per_work_limit_inr": { "type": "number" },
            "group_total_floor_inr": { "type": "number" }
          }
        },
        "common_tokens": { "$ref": "#/definitions/tokens" },
        "counts": {
          "type": "object",
          "additionalProperties": { "type": "integer", "minimum": 0 },
          "required": [
            "works_considered",
            "groups",
            "identical_batches",
            "threshold_crossing_batches",
            "district_identical_batches",
            "near_copy_pairs",
            "reworded_match",
            "one_sided_detail",
            "conflicting_detail",
            "district_near_copy_pairs"
          ]
        }
      }
    },
    "text_group": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "scope",
        "text_fingerprint",
        "text",
        "activity",
        "constituencies",
        "work_ids",
        "work_count",
        "amount_min_inr",
        "amount_max_inr",
        "amount_total_inr",
        "sanction_date_first",
        "sanction_date_last",
        "agencies",
        "statuses"
      ],
      "properties": {
        "scope": { "type": "string", "minLength": 1 },
        "text_fingerprint": { "$ref": "#/definitions/id" },
        "text": {
          "type": "string",
          "minLength": 1,
          "description": "The description as published, spacing tidied: the most common variant among the group's works."
        },
        "activity": {
          "type": ["string", "null"],
          "description": "The most common portal activity among the group's works."
        },
        "constituencies": {
          "type": "array",
          "items": { "type": "string", "minLength": 1 },
          "minItems": 1,
          "uniqueItems": true
        },
        "work_ids": {
          "type": "array",
          "items": { "type": "string", "minLength": 1 },
          "minItems": 1,
          "uniqueItems": true
        },
        "work_count": { "type": "integer", "minimum": 1 },
        "amount_min_inr": { "type": "number", "minimum": 0 },
        "amount_max_inr": { "type": "number", "minimum": 0 },
        "amount_total_inr": { "type": "number", "minimum": 0 },
        "sanction_date_first": { "$ref": "#/definitions/date" },
        "sanction_date_last": { "$ref": "#/definitions/date" },
        "agencies": {
          "type": "array",
          "items": { "type": "string", "minLength": 1 },
          "uniqueItems": true
        },
        "statuses": {
          "type": "object",
          "additionalProperties": { "type": "integer", "minimum": 1 }
        }
      }
    },
    "batch": {
      "type": "object",
      "additionalProperties": false,
      "required": ["candidate_id", "finder", "scope", "threshold_crossing_batch", "group"],
      "properties": {
        "candidate_id": { "$ref": "#/definitions/id" },
        "finder": { "enum": ["identical_batch", "district_identical_batch"] },
        "scope": { "type": "string", "minLength": 1 },
        "threshold_crossing_batch": {
          "type": "boolean",
          "description": "True when every work in the group is below Rs 15 lakh and the group total is Rs 25 lakh or more (MPLADS Guidelines 2023, clause 4.4.2). A fact about amounts; the wording shown to an officer lives in strings.json."
        },
        "group": { "$ref": "#/definitions/id" }
      }
    },
    "pair": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "candidate_id",
        "finder",
        "scope",
        "hits",
        "character_similarity",
        "token_overlap",
        "difference_group",
        "shared_tokens",
        "only_a_tokens",
        "only_b_tokens",
        "a",
        "b"
      ],
      "properties": {
        "candidate_id": { "$ref": "#/definitions/id" },
        "finder": { "enum": ["near_copy", "district_near_copy"] },
        "scope": { "type": "string", "minLength": 1 },
        "hits": {
          "type": "array",
          "items": { "enum": ["character", "token"] },
          "minItems": 1,
          "uniqueItems": true
        },
        "character_similarity": { "type": "number", "minimum": 0, "maximum": 1 },
        "token_overlap": { "type": "number", "minimum": 0, "maximum": 1 },
        "difference_group": {
          "enum": ["reworded_match", "one_sided_detail", "conflicting_detail"],
          "description": "Names what the code knows about the words, not what it suspects: reworded_match has no word on only one side, one_sided_detail has words on one side only, conflicting_detail has different words on both."
        },
        "shared_tokens": { "$ref": "#/definitions/tokens" },
        "only_a_tokens": { "$ref": "#/definitions/tokens" },
        "only_b_tokens": { "$ref": "#/definitions/tokens" },
        "a": { "$ref": "#/definitions/id" },
        "b": { "$ref": "#/definitions/id" }
      }
    }
  }
}
```

- [ ] **Step 5: Implement the frozen rules**

Create `pipeline/src/nidhinetra_pipeline/duplicates/__init__.py`:

```python
"""Phase 1 Stage A: deterministic candidates for duplicate and split works.

Public surface: `build_duplicate_candidates`. See candidates.py and
contracts/duplicate_candidates.schema.json for the output contract.
"""
```

Create `pipeline/src/nidhinetra_pipeline/duplicates/candidates.py`:

```python
"""Phase 1 Stage A: candidate generation for duplicate and split works.

Pure functions over normalized records: no model, no network, no clock. The same records give the
same candidates in the same order, so the artifact can be committed and reviewed like any other
snapshot file. Nothing here reads or changes a work's score, rank or flags.

Spec: docs/superpowers/specs/2026-09-17-foundation-and-duplicate-works-design.md
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from pathlib import Path
from typing import Any

import jsonschema

# duplicates/candidates.py -> parents[4] is "05-App/".
_APP_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_PATH = _APP_ROOT / "contracts" / "duplicate_candidates.schema.json"

CANONICAL_VERSION = "canonical_description_v1"
FINDER_VERSION = "candidate_generation_v0"

# candidate_generation_v0. Stage D may revise these once, after which the version becomes v1.
CHARACTER_SIMILARITY_MIN = 0.80
TOKEN_JACCARD_MIN = 0.75
TOKEN_SHARED_MIN = 3
DISTRICT_CHARACTER_SIMILARITY_MIN = 0.90
# MPLADS Guidelines 2023 clause 4.4.2: third-party inspection is compulsory from Rs 25 lakh and
# needs 50% coverage between Rs 15 and 25 lakh.
PER_WORK_LIMIT_INR = 1_500_000
GROUP_TOTAL_FLOOR_INR = 2_500_000
# A score is rounded before it meets a threshold, so a pair sitting on a threshold is decided the
# same way on every machine.
SCORE_DECIMALS = 4

# The 19 words that appear in at least 10% of the distinct canonical descriptions of the
# 2026-09-04 capture (a 20th, "work", sits at 9.99%). They say what kind of work it is, not which
# work, so token overlap ignores them. Frozen: a list derived from the data would move with every
# rebuild.
COMMON_TOKENS_V0 = frozenset(
    "and at block construction from gram high house in installation ke light near no of "
    "panchayat road to village".split()
)


class DuplicateCandidateValidationError(Exception):
    """Raised instead of returning an artifact that breaks duplicate_candidates.schema.json."""


def canonical_description_v1(text: str) -> str:
    """NFKC, casefold, then every run of characters that are not letters, digits or combining
    marks becomes one space. Digits are kept; nothing is stemmed, corrected or dropped. Any change
    to this rule is a new version, because the same data would group differently.
    """
    out: list[str] = []
    gap = True
    for char in unicodedata.normalize("NFKC", text).casefold():
        if unicodedata.category(char)[0] in "LNM":
            out.append(char)
            gap = False
        elif not gap:
            out.append(" ")
            gap = True
    return "".join(out).strip()


def content_tokens(canonical: str) -> list[str]:
    return [token for token in canonical.split() if token not in COMMON_TOKENS_V0]


def fingerprint(canonical: str) -> str:
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _candidate_id(*parts: str) -> str:
    return hashlib.sha256("|".join((FINDER_VERSION, *parts)).encode("utf-8")).hexdigest()[:16]


def validate_duplicate_candidates(artifact: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = [
        f"{'.'.join(str(part) for part in error.path) or '<root>'}: {error.message[:200]}"
        for error in jsonschema.Draft7Validator(schema).iter_errors(artifact)
    ]
    if errors:
        raise DuplicateCandidateValidationError(
            f"{len(errors)} violation(s) of duplicate_candidates.schema.json, first 10:\n"
            + "\n".join(errors[:10])
        )
```

- [ ] **Step 6: Run the tests and the gates**

```bash
(cd 05-App && uv run pytest pipeline/tests/duplicates -q)
(cd 05-App && uvx ruff format pipeline/src/nidhinetra_pipeline/duplicates/candidates.py pipeline/src/nidhinetra_pipeline/duplicates/__init__.py pipeline/tests/duplicates/test_candidates.py && uvx ruff check pipeline/src/nidhinetra_pipeline/duplicates/candidates.py pipeline/src/nidhinetra_pipeline/duplicates/__init__.py pipeline/tests/duplicates/test_candidates.py )
(cd 05-App && make validate)
```
Expected: `9 passed`, ruff clean, and both contract checks pass (this task adds a schema that `validate.py` does not read, so they are unchanged).

- [ ] **Step 7: Commit**

```bash
git add 05-App/contracts/duplicate_candidates.schema.json 05-App/pipeline/src/nidhinetra_pipeline/duplicates 05-App/pipeline/tests/duplicates
git commit -m "feat(duplicates): the candidates contract and the frozen text rules (Phase 1 Stage A, 1/6)"
```

### Task 2: Text groups and identical batches (Finder 1)

**Files:**
- Modify: `pipeline/src/nidhinetra_pipeline/duplicates/candidates.py`
- Test: `pipeline/tests/duplicates/test_candidates.py`

**Interfaces:**
- Consumes: Task 1's constants, `canonical_description_v1`, `fingerprint`, `_candidate_id` and `validate_duplicate_candidates`.
- Produces: `build_duplicate_candidates(records: list[dict]) -> dict`, which returns the validated artifact and never modifies `records`. After this task it finds identical batches only. Also `_index`, `_registrar`, `_identical_batches`, `_artifact`, `_text_group` and `_batch`, which Tasks 3 and 4 call. `_registrar(groups)` returns `register(scope, canonical, members) -> (canonical, group_id, fingerprint)`, which stores a text group once.

- [ ] **Step 1: Write the failing tests**

In `pipeline/tests/duplicates/test_candidates.py`, replace the import block at the top with:

```python
import unicodedata
from typing import Any

import pytest
from nidhinetra_pipeline.duplicates.candidates import (
    DuplicateCandidateValidationError,
    build_duplicate_candidates,
    canonical_description_v1,
    content_tokens,
    fingerprint,
    validate_duplicate_candidates,
)
```

then append:

```python
def _rec(work_id: str, description: str | None, **overrides: Any) -> dict[str, Any]:
    """The fields Stage A reads from a normalized record."""
    record = {
        "work_id": work_id,
        "constituency": "C1",
        "implementing_district_authority": "D1",
        "implementing_agency": "Agency 1",
        "work_description": description,
        "activity_name": "Construction of roads",
        "sanctioned_amount_inr": 500_000.0,
        "sanction_date": "2024-07-09",
        "completion_status": "Sanctioned",
    }
    record.update(overrides)
    return record


class TestIdenticalBatches:
    def test_identical_descriptions_in_one_constituency_form_one_batch(self) -> None:
        records = [
            _rec("W1", "PCC Road, near Ram House", sanctioned_amount_inr=300_000.0),
            _rec(
                "W2",
                "PCC Road, near Ram House",
                sanctioned_amount_inr=400_000.0,
                sanction_date="2024-09-01",
            ),
            _rec(
                "W3",
                "pcc road near ram house.",
                sanctioned_amount_inr=500_000.0,
                completion_status="In Progress",
            ),
        ]

        artifact = build_duplicate_candidates(records)

        assert len(artifact["batches"]) == 1
        batch = artifact["batches"][0]
        group = artifact["groups"][batch["group"]]
        assert (batch["finder"], batch["scope"]) == ("identical_batch", "C1")
        assert group["work_ids"] == ["W1", "W2", "W3"]
        assert group["work_count"] == 3
        assert group["text"] == "PCC Road, near Ram House"  # the most common published variant
        assert group["activity"] == "Construction of roads"
        assert (group["amount_min_inr"], group["amount_max_inr"]) == (300_000.0, 500_000.0)
        assert group["amount_total_inr"] == 1_200_000.0
        assert (group["sanction_date_first"], group["sanction_date_last"]) == (
            "2024-07-09",
            "2024-09-01",
        )
        assert group["agencies"] == ["Agency 1"]
        assert group["statuses"] == {"In Progress": 1, "Sanctioned": 2}
        assert artifact["meta"]["counts"]["identical_batches"] == 1

    @pytest.mark.parametrize(
        ("amounts", "crosses"),
        [
            ([900_000.0, 900_000.0, 900_000.0], True),  # Rs 27 lakh, each below Rs 15 lakh
            ([900_000.0, 900_000.0, 700_000.0], True),  # exactly Rs 25 lakh counts
            ([900_000.0, 900_000.0, 600_000.0], False),  # Rs 24 lakh is under the floor
            ([1_500_000.0, 700_000.0, 700_000.0], False),  # one work at Rs 15 lakh is not below it
        ],
    )
    def test_threshold_crossing_needs_every_work_below_15_lakh_and_a_total_of_25_lakh(
        self, amounts: list[float], crosses: bool
    ) -> None:
        records = [
            _rec(f"W{n}", "Solar street lights", sanctioned_amount_inr=amount)
            for n, amount in enumerate(amounts)
        ]

        batch = build_duplicate_candidates(records)["batches"][0]

        assert batch["threshold_crossing_batch"] is crosses

    def test_the_same_text_in_two_constituencies_is_not_one_batch(self) -> None:
        records = [
            _rec(
                "W1", "Solar street lights", constituency="C1", implementing_district_authority="D1"
            ),
            _rec(
                "W2", "Solar street lights", constituency="C2", implementing_district_authority="D2"
            ),
        ]

        assert build_duplicate_candidates(records)["batches"] == []

    def test_descriptions_without_letters_or_digits_are_ignored(self) -> None:
        records = [_rec("W1", "---"), _rec("W2", "---"), _rec("W3", None), _rec("W4", "")]

        artifact = build_duplicate_candidates(records)

        assert artifact["batches"] == []
        assert artifact["meta"]["counts"]["works_considered"] == 0

    def test_a_single_work_is_never_a_batch(self) -> None:
        assert build_duplicate_candidates([_rec("W1", "Solar street lights")])["batches"] == []

    def test_no_records_gives_an_empty_valid_artifact(self) -> None:
        artifact = build_duplicate_candidates([])

        assert (artifact["groups"], artifact["batches"], artifact["pairs"]) == ({}, [], [])
        validate_duplicate_candidates(artifact)
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
(cd 05-App && uv run pytest pipeline/tests/duplicates -q)
```
Expected: FAIL at collection with `ImportError: cannot import name 'build_duplicate_candidates'`.

- [ ] **Step 3: Implement text groups and Finder 1**

In `candidates.py`, replace the import block at the top with:

```python
import hashlib
import json
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

import jsonschema
```

then append:

```python
_Members = dict[tuple[str, str], list[dict[str, Any]]]  # (scope, canonical text) -> works
_Side = tuple[str, str, str]  # (canonical text, group id, text fingerprint)
_Register = Callable[[str, str, list[dict[str, Any]]], _Side]


def _mode(values: list[str]) -> str | None:
    """The most common value, the smallest on a tie, None for an empty list."""
    counts = Counter(values)
    return min(counts, key=lambda value: (-counts[value], value)) if counts else None


def _text_group(scope: str, canonical: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    amounts = [record["sanctioned_amount_inr"] for record in records]
    dates = sorted(record["sanction_date"] for record in records if record["sanction_date"])
    return {
        "scope": scope,
        "text_fingerprint": fingerprint(canonical),
        "text": _mode([record["work_description"] for record in records]),
        "activity": _mode([r["activity_name"] for r in records if r["activity_name"]]),
        "constituencies": sorted({record["constituency"] for record in records}),
        "work_ids": sorted(record["work_id"] for record in records),
        "work_count": len(records),
        "amount_min_inr": round(min(amounts), 2),
        "amount_max_inr": round(max(amounts), 2),
        "amount_total_inr": round(sum(amounts), 2),
        "sanction_date_first": dates[0] if dates else None,
        "sanction_date_last": dates[-1] if dates else None,
        "agencies": sorted({r["implementing_agency"] for r in records if r["implementing_agency"]}),
        "statuses": dict(sorted(Counter(r["completion_status"] for r in records).items())),
    }


def _batch(finder: str, scope: str, group_id: str, group: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": _candidate_id(finder, scope, group["text_fingerprint"]),
        "finder": finder,
        "scope": scope,
        "threshold_crossing_batch": (
            group["amount_max_inr"] < PER_WORK_LIMIT_INR
            and group["amount_total_inr"] >= GROUP_TOTAL_FLOOR_INR
        ),
        "group": group_id,
    }


def _index(records: list[dict[str, Any]]) -> tuple[_Members, _Members, int]:
    """Works by (constituency, canonical text) and by (district authority, canonical text), and the
    number of works with a description that has at least one letter or digit.
    """
    by_constituency: _Members = defaultdict(list)
    by_district: _Members = defaultdict(list)
    considered = 0
    for record in records:
        canonical = canonical_description_v1(record["work_description"] or "")
        if not canonical:
            continue
        considered += 1
        by_constituency[(record["constituency"], canonical)].append(record)
        if record["implementing_district_authority"]:
            by_district[(record["implementing_district_authority"], canonical)].append(record)
    return by_constituency, by_district, considered


def _registrar(groups: dict[str, dict[str, Any]]) -> _Register:
    """`register(scope, canonical, members)` stores a text group once and returns the side tuple
    (canonical text, group id, text fingerprint) that batches and pairs refer to.
    """

    def register(scope: str, canonical: str, members: list[dict[str, Any]]) -> _Side:
        text_fingerprint = fingerprint(canonical)
        group_id = _candidate_id("group", scope, text_fingerprint)
        if group_id not in groups:
            groups[group_id] = _text_group(scope, canonical, members)
        return canonical, group_id, text_fingerprint

    return register


def _identical_batches(
    by_constituency: _Members, register: _Register, groups: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Finder 1: two or more works in one constituency with the same canonical description."""
    batches = []
    for (scope, canonical), members in sorted(by_constituency.items()):
        if len(members) >= 2:
            _, group_id, _ = register(scope, canonical, members)
            batches.append(_batch("identical_batch", scope, group_id, groups[group_id]))
    return batches


def _artifact(
    considered: int,
    groups: dict[str, dict[str, Any]],
    batches: list[dict[str, Any]],
    pairs: list[dict[str, Any]],
) -> dict[str, Any]:
    by_finder = Counter(candidate["finder"] for candidate in batches + pairs)
    by_difference = Counter(
        pair["difference_group"] for pair in pairs if pair["finder"] == "near_copy"
    )
    artifact = {
        "meta": {
            "canonical_version": CANONICAL_VERSION,
            "finder_version": FINDER_VERSION,
            "thresholds": {
                "character_similarity_min": CHARACTER_SIMILARITY_MIN,
                "token_jaccard_min": TOKEN_JACCARD_MIN,
                "token_shared_min": TOKEN_SHARED_MIN,
                "district_character_similarity_min": DISTRICT_CHARACTER_SIMILARITY_MIN,
                "per_work_limit_inr": PER_WORK_LIMIT_INR,
                "group_total_floor_inr": GROUP_TOTAL_FLOOR_INR,
            },
            "common_tokens": sorted(COMMON_TOKENS_V0),
            "counts": {
                "works_considered": considered,
                "groups": len(groups),
                "identical_batches": by_finder["identical_batch"],
                "threshold_crossing_batches": sum(
                    batch["threshold_crossing_batch"]
                    for batch in batches
                    if batch["finder"] == "identical_batch"
                ),
                "district_identical_batches": by_finder["district_identical_batch"],
                "near_copy_pairs": by_finder["near_copy"],
                "reworded_match": by_difference["reworded_match"],
                "one_sided_detail": by_difference["one_sided_detail"],
                "conflicting_detail": by_difference["conflicting_detail"],
                "district_near_copy_pairs": by_finder["district_near_copy"],
            },
        },
        "groups": groups,
        "batches": batches,
        "pairs": pairs,
    }
    validate_duplicate_candidates(artifact)
    return artifact


def build_duplicate_candidates(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Finder 1: works in one constituency whose descriptions are identical once canonicalised.
    Validated against duplicate_candidates.schema.json before it is returned. Never modifies
    `records`.
    """
    by_constituency, _, considered = _index(records)
    groups: dict[str, dict[str, Any]] = {}
    register = _registrar(groups)
    batches = _identical_batches(by_constituency, register, groups)
    return _artifact(considered, groups, batches, [])
```

- [ ] **Step 4: Run the tests and lint**

```bash
(cd 05-App && uv run pytest pipeline/tests/duplicates -q)
(cd 05-App && uvx ruff format pipeline/src/nidhinetra_pipeline/duplicates/candidates.py pipeline/tests/duplicates/test_candidates.py && uvx ruff check pipeline/src/nidhinetra_pipeline/duplicates/candidates.py pipeline/tests/duplicates/test_candidates.py )
```
Expected: `18 passed`, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add 05-App/pipeline/src/nidhinetra_pipeline/duplicates/candidates.py 05-App/pipeline/tests/duplicates/test_candidates.py
git commit -m "feat(duplicates): identical batches and the threshold-crossing fact (Phase 1 Stage A, 2/6)"
```

### Task 3: Near-copy pairs (Finder 2)

**Files:**
- Modify: `pipeline/src/nidhinetra_pipeline/duplicates/candidates.py`
- Test: `pipeline/tests/duplicates/test_candidates.py`

**Interfaces:**
- Consumes: Task 2's `_index`, `_registrar`, `_identical_batches`, `_artifact`, `_Members`, `_Side` and `_Register`.
- Produces: `_similarity_index(canonicals: list[str]) -> _Index`, a row per distinct canonical text with its character TF-IDF and content-token matrices; `_similar_pairs(idx, tfidf, tokens, character_min, use_tokens)`, which yields `(i, j, cosine, hits)` for every pair in a block that clears a threshold; `_near_copy_pairs(by_constituency, register, index) -> list[dict]`; `_pair(...)`. `build_duplicate_candidates` now also returns `near_copy` pairs. Task 4 reuses `_similarity_index` and `_similar_pairs`.

- [ ] **Step 1: Write the failing tests**

In `test_candidates.py`, replace the import block at the top with:

```python
import unicodedata
from typing import Any

import pytest
from nidhinetra_pipeline.duplicates.candidates import (
    DuplicateCandidateValidationError,
    _similar_pairs,
    build_duplicate_candidates,
    canonical_description_v1,
    content_tokens,
    fingerprint,
    validate_duplicate_candidates,
)
from scipy.sparse import csr_matrix
```

then append:

```python
def _pairs(records: list[dict[str, Any]], finder: str = "near_copy") -> list[dict[str, Any]]:
    return [p for p in build_duplicate_candidates(records)["pairs"] if p["finder"] == finder]


class TestNearCopyPairs:
    def test_a_typo_is_paired_by_character_similarity(self) -> None:
        records = [
            _rec("W1", "Installation of high mask light at Kheda"),
            _rec("W2", "Installation of high mast light at Kheda"),
        ]

        (pair,) = _pairs(records)

        assert pair["hits"] == ["character"]
        assert pair["character_similarity"] >= 0.80
        assert pair["difference_group"] == "conflicting_detail"
        assert sorted((pair["only_a_tokens"], pair["only_b_tokens"])) == [["mask"], ["mast"]]

    def test_many_shared_words_pair_by_token_overlap_when_the_letters_differ_a_lot(self) -> None:
        records = [
            _rec("W1", "ram sai raj may day sun venkatanarasimharajuvaripeta"),
            _rec("W2", "ram sai raj may day sun chandrasekharapuramcolony"),
        ]

        (pair,) = _pairs(records)

        assert pair["hits"] == ["token"]
        assert pair["character_similarity"] < 0.80
        assert pair["token_overlap"] == 0.75
        assert pair["shared_tokens"] == ["day", "may", "raj", "ram", "sai", "sun"]

    def test_the_same_words_in_another_order_are_a_reworded_match(self) -> None:
        records = [
            _rec("W1", "Road to Ram Mandir at village Kheda"),
            _rec("W2", "Kheda village road near Ram Mandir"),
        ]

        (pair,) = _pairs(records)

        assert pair["difference_group"] == "reworded_match"
        assert (pair["only_a_tokens"], pair["only_b_tokens"]) == ([], [])
        assert pair["shared_tokens"] == ["kheda", "mandir", "ram"]

    def test_extra_detail_on_one_side_is_one_sided_detail(self) -> None:
        records = [
            _rec("W1", "ram sai raj may day sun mandir"),
            _rec("W2", "ram sai raj may day sun mandir sector"),
        ]

        (pair,) = _pairs(records)

        assert pair["difference_group"] == "one_sided_detail"
        assert sorted((pair["only_a_tokens"], pair["only_b_tokens"])) == [[], ["sector"]]

    def test_numbers_count_so_numbered_siblings_are_conflicting_detail(self) -> None:
        records = [
            _rec("W1", "Community hall no 3 ward 9"),
            _rec("W2", "Community hall no 4 ward 9"),
        ]

        (pair,) = _pairs(records)

        assert pair["difference_group"] == "conflicting_detail"
        assert sorted((pair["only_a_tokens"], pair["only_b_tokens"])) == [["3"], ["4"]]

    def test_two_shared_words_are_not_enough_for_token_overlap(self) -> None:
        records = [
            _rec("W1", "Construction of road to Ram Mandir in village"),
            _rec("W2", "Installation near house at Mandir Ram gram panchayat"),
        ]

        assert _pairs(records) == []

    def test_token_overlap_below_three_quarters_is_not_a_pair(self) -> None:
        records = [
            _rec("W1", "ram sai raj may day sun venkatanarasimharajuvaripeta"),
            _rec("W2", "ram sai raj may day chandrasekharapuramcolony"),
        ]

        assert _pairs(records) == []

    def test_a_cosine_just_under_the_character_threshold_is_not_a_pair(self) -> None:
        # Cosine 0.79. Stage D may move the line; until then this pair is below it.
        records = [
            _rec("W1", "cremation ground at village"),
            _rec("W2", "cremation ground at village chak dana"),
        ]

        assert _pairs(records) == []

    def test_side_a_is_the_text_that_sorts_first(self) -> None:
        records = [
            _rec("W1", "Installation of high mast light at Kheda"),
            _rec("W2", "Installation of high mask light at Kheda"),
        ]

        (pair,) = build_duplicate_candidates(records)["pairs"]

        assert (pair["only_a_tokens"], pair["only_b_tokens"]) == (["mask"], ["mast"])

    def test_a_score_is_rounded_before_it_meets_a_threshold(self) -> None:
        # Rows [1, 0] and [0.79996, 0.6] have a dot product of 0.79996, which rounds to 0.8.
        just_over = csr_matrix([[1.0, 0.0], [0.79996, 0.6]])
        just_under = csr_matrix([[1.0, 0.0], [0.79994, 0.6]])
        no_tokens = csr_matrix((2, 1))

        assert [p[:3] for p in _similar_pairs([0, 1], just_over, no_tokens, 0.80, False)] == [
            (0, 1, 0.8)
        ]
        assert list(_similar_pairs([0, 1], just_under, no_tokens, 0.80, False)) == []
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
(cd 05-App && uv run pytest pipeline/tests/duplicates -q)
```
Expected: FAIL at collection with `ImportError: cannot import name '_similar_pairs'`.

- [ ] **Step 3: Implement Finder 2**

In `candidates.py`: replace the import block at the top with the block below, then **delete the existing `build_duplicate_candidates` function** (it is the last function in the file), then append the new code, which ends with the replacement `build_duplicate_candidates`.

```python
import hashlib
import json
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import jsonschema
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
```

```python
_Index = tuple[dict[str, int], csr_matrix, csr_matrix]  # row of each text, TF-IDF, content tokens


def _difference_group(only_a: list[str], only_b: list[str]) -> str:
    if not only_a and not only_b:
        return "reworded_match"
    if not only_a or not only_b:
        return "one_sided_detail"
    return "conflicting_detail"


def _pair(
    finder: str,
    scope: str,
    side_a: _Side,
    side_b: _Side,
    cosine: float,
    hits: list[str],
) -> dict[str, Any]:
    """Each side is (canonical text, group id, text fingerprint). The finders walk a block in
    sorted order, so `a` is always the side whose canonical text sorts first.
    """
    (canonical_a, group_a, fp_a), (canonical_b, group_b, fp_b) = side_a, side_b
    tokens_a, tokens_b = set(content_tokens(canonical_a)), set(content_tokens(canonical_b))
    union = tokens_a | tokens_b
    only_a, only_b = sorted(tokens_a - tokens_b), sorted(tokens_b - tokens_a)
    return {
        "candidate_id": _candidate_id(finder, scope, fp_a, fp_b),
        "finder": finder,
        "scope": scope,
        "hits": hits,
        "character_similarity": cosine,
        "token_overlap": (
            round(len(tokens_a & tokens_b) / len(union), SCORE_DECIMALS) if union else 0.0
        ),
        "difference_group": _difference_group(only_a, only_b),
        "shared_tokens": sorted(tokens_a & tokens_b),
        "only_a_tokens": only_a,
        "only_b_tokens": only_b,
        "a": group_a,
        "b": group_b,
    }


def _token_matrix(canonicals: list[str]) -> csr_matrix:
    """Row per text, column per content token, 1 where the text has the token."""
    vocabulary: dict[str, int] = {}
    rows: list[int] = []
    cols: list[int] = []
    for row, canonical in enumerate(canonicals):
        for token in set(content_tokens(canonical)):
            rows.append(row)
            cols.append(vocabulary.setdefault(token, len(vocabulary)))
    return csr_matrix(
        (np.ones(len(rows), dtype=np.int32), (rows, cols)),
        shape=(len(canonicals), max(len(vocabulary), 1)),
    )


def _similar_pairs(
    idx: list[int],
    tfidf: csr_matrix,
    tokens: csr_matrix,
    character_min: float,
    use_tokens: bool,
) -> Iterator[tuple[int, int, float, list[str]]]:
    """(i, j, cosine, hits) for every pair of the texts at matrix rows `idx` that clears the
    character threshold or, when `use_tokens`, the token-overlap threshold. i < j are positions
    within `idx`. The whole block is compared, one dense matrix at a time (largest block: 1,371).
    """
    if len(idx) < 2:
        return
    cosine = np.round((tfidf[idx] @ tfidf[idx].T).toarray(), SCORE_DECIMALS)
    by_character = cosine >= character_min
    by_token = np.zeros_like(by_character)
    if use_tokens:
        shared = (tokens[idx] @ tokens[idx].T).toarray()
        size = np.asarray(tokens[idx].sum(axis=1)).ravel()
        union = size[:, None] + size[None, :] - shared
        jaccard = np.round(
            np.divide(shared, union, out=np.zeros(shared.shape), where=union > 0), SCORE_DECIMALS
        )
        by_token = (shared >= TOKEN_SHARED_MIN) & (jaccard >= TOKEN_JACCARD_MIN)
    for i, j in np.argwhere(np.triu(by_character | by_token, 1)):
        hit_by = (("character", by_character[i, j]), ("token", by_token[i, j]))
        yield int(i), int(j), float(cosine[i, j]), [name for name, hit in hit_by if hit]


def _similarity_index(canonicals: list[str]) -> _Index:
    """Row per distinct canonical text: character TF-IDF (fitted on all of them, so every block
    shares one vocabulary) and the content-token matrix.
    """
    row_of = {canonical: row for row, canonical in enumerate(canonicals)}
    tfidf = (
        TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), lowercase=False)
        .fit(canonicals)
        .transform(canonicals)
        .tocsr()
    )
    return row_of, tfidf, _token_matrix(canonicals)


def _near_copy_pairs(
    by_constituency: _Members, register: _Register, index: _Index
) -> list[dict[str, Any]]:
    """Finder 2: distinct texts in the same constituency. Blocking by constituency is a blocking
    rule, not a claim that works cannot repeat across constituencies (Finder 3 looks there).
    """
    row_of, tfidf, tokens = index
    block_texts: dict[str, list[str]] = defaultdict(list)
    for scope, canonical in sorted(by_constituency):
        block_texts[scope].append(canonical)
    pairs = []
    for scope, block in block_texts.items():
        idx = [row_of[canonical] for canonical in block]
        for i, j, cosine, hits in _similar_pairs(
            idx, tfidf, tokens, CHARACTER_SIMILARITY_MIN, use_tokens=True
        ):
            side_i = register(scope, block[i], by_constituency[(scope, block[i])])
            side_j = register(scope, block[j], by_constituency[(scope, block[j])])
            pairs.append(_pair("near_copy", scope, side_i, side_j, cosine, hits))
    return pairs


def build_duplicate_candidates(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Finder 1 (identical batches) and Finder 2 (near-copy pairs) over the works whose
    description has at least one letter or digit. Validated against
    duplicate_candidates.schema.json before it is returned. Never modifies `records`.
    """
    by_constituency, _, considered = _index(records)
    groups: dict[str, dict[str, Any]] = {}
    register = _registrar(groups)
    batches = _identical_batches(by_constituency, register, groups)
    pairs: list[dict[str, Any]] = []
    if by_constituency:
        index = _similarity_index(sorted({canonical for _, canonical in by_constituency}))
        pairs += _near_copy_pairs(by_constituency, register, index)
    return _artifact(considered, groups, batches, pairs)
```

- [ ] **Step 4: Run the tests and lint**

```bash
(cd 05-App && uv run pytest pipeline/tests/duplicates -q)
(cd 05-App && uvx ruff format pipeline/src/nidhinetra_pipeline/duplicates/candidates.py pipeline/tests/duplicates/test_candidates.py && uvx ruff check pipeline/src/nidhinetra_pipeline/duplicates/candidates.py pipeline/tests/duplicates/test_candidates.py )
```
Expected: `28 passed`, ruff clean. The token-channel test and the cosine-just-under-0.80 test are the ones that move if a threshold moves; they are there on purpose.

- [ ] **Step 5: Commit**

```bash
git add 05-App/pipeline/src/nidhinetra_pipeline/duplicates/candidates.py 05-App/pipeline/tests/duplicates/test_candidates.py
git commit -m "feat(duplicates): near-copy pairs by character and token overlap (Phase 1 Stage A, 3/6)"
```

### Task 4: The quiet district audit (Finder 3) and the artifact's guarantees

**Files:**
- Modify: `pipeline/src/nidhinetra_pipeline/duplicates/candidates.py`
- Test: `pipeline/tests/duplicates/test_candidates.py`

**Interfaces:**
- Consumes: Task 3's `_similarity_index` and `_similar_pairs`, and Task 2's `_registrar` and `_artifact`.
- Produces: `_district_audit(by_district, register, groups, index) -> (batches, pairs)`. The finished `build_duplicate_candidates` returns all three finders' output. Tasks 5 and 6 call only `build_duplicate_candidates(records)`.

- [ ] **Step 1: Write the failing tests**

In `test_candidates.py`, replace the import block at the top with:

```python
import copy
import json
import random
import unicodedata
from typing import Any

import pytest
from nidhinetra_pipeline.duplicates.candidates import (
    DuplicateCandidateValidationError,
    _similar_pairs,
    build_duplicate_candidates,
    canonical_description_v1,
    content_tokens,
    fingerprint,
    validate_duplicate_candidates,
)
from scipy.sparse import csr_matrix
```

then append:

```python
class TestDistrictAudit:
    def test_identical_text_in_two_constituencies_of_one_district_is_a_quiet_batch(self) -> None:
        records = [
            _rec("W1", "Construction of Community Center", constituency="C1"),
            _rec("W2", "Construction of Community Center", constituency="C2"),
        ]

        artifact = build_duplicate_candidates(records)

        (batch,) = artifact["batches"]
        assert (batch["finder"], batch["scope"]) == ("district_identical_batch", "D1")
        assert artifact["groups"][batch["group"]]["constituencies"] == ["C1", "C2"]

    def test_similar_text_across_constituencies_of_one_district_is_a_district_pair(self) -> None:
        records = [
            _rec("W1", "Providing and installation of Open Gym Equipment", constituency="C1"),
            _rec("W2", "Providing and installation of Open Gym Equipments", constituency="C2"),
        ]

        (pair,) = _pairs(records, "district_near_copy")

        assert (pair["scope"], pair["hits"]) == ("D1", ["character"])
        assert pair["character_similarity"] >= 0.90

    def test_two_texts_that_sit_in_one_constituency_are_left_to_finder_two(self) -> None:
        records = [
            _rec("W1", "Providing and installation of Open Gym Equipment", constituency="C1"),
            _rec("W2", "Providing and installation of Open Gym Equipments", constituency="C1"),
        ]

        artifact = build_duplicate_candidates(records)

        assert [p["finder"] for p in artifact["pairs"]] == ["near_copy"]

    def test_across_constituencies_only_the_stricter_district_threshold_applies(self) -> None:
        # Cosine 0.87: a Finder 2 pair inside one constituency, but not a district pair.
        records = [
            _rec("W1", "Installation of high mask light at Kheda", constituency="C1"),
            _rec("W2", "Installation of high mast light at Kheda", constituency="C2"),
        ]

        assert build_duplicate_candidates(records)["pairs"] == []

    def test_works_without_a_district_authority_are_not_audited(self) -> None:
        records = [
            _rec(
                "W1",
                "Construction of Community Center",
                constituency="C1",
                implementing_district_authority=None,
            ),
            _rec(
                "W2",
                "Construction of Community Center",
                constituency="C2",
                implementing_district_authority=None,
            ),
        ]

        assert build_duplicate_candidates(records)["batches"] == []


class TestArtifact:
    @staticmethod
    def _mixed_records() -> list[dict[str, Any]]:
        return [
            _rec("W1", "Solar street lights", sanctioned_amount_inr=900_000.0),
            _rec("W2", "Solar street lights", sanctioned_amount_inr=900_000.0),
            _rec("W3", "Solar street lights", sanctioned_amount_inr=900_000.0),
            _rec("W4", "Installation of high mask light at Kheda"),
            _rec("W5", "Installation of high mast light at Kheda"),
            _rec("W6", "Construction of Community Center", constituency="C2"),
            _rec("W7", "Construction of Community Center", constituency="C3"),
        ]

    def test_the_output_does_not_depend_on_the_input_order(self) -> None:
        records = self._mixed_records()
        shuffled = records[:]
        random.Random(7).shuffle(shuffled)

        assert json.dumps(build_duplicate_candidates(records)) == json.dumps(
            build_duplicate_candidates(shuffled)
        )

    def test_every_reference_resolves_and_no_group_is_orphaned(self) -> None:
        artifact = build_duplicate_candidates(self._mixed_records())

        referenced = {batch["group"] for batch in artifact["batches"]}
        referenced |= {pair[side] for pair in artifact["pairs"] for side in ("a", "b")}

        assert referenced == set(artifact["groups"])
        assert artifact["meta"]["counts"]["groups"] == len(artifact["groups"])

    def test_the_input_records_are_not_modified(self) -> None:
        records = self._mixed_records()
        before = copy.deepcopy(records)

        build_duplicate_candidates(records)

        assert records == before

    def test_candidate_ids_are_unique(self) -> None:
        artifact = build_duplicate_candidates(self._mixed_records())
        ids = [c["candidate_id"] for c in artifact["batches"] + artifact["pairs"]]

        assert len(ids) == len(set(ids)) > 0

    def test_the_counts_add_up(self) -> None:
        artifact = build_duplicate_candidates(self._mixed_records())
        counts = artifact["meta"]["counts"]

        assert counts["works_considered"] == 7
        assert counts["identical_batches"] == 1
        assert counts["threshold_crossing_batches"] == 1
        assert counts["district_identical_batches"] == 1
        assert counts["near_copy_pairs"] == (
            counts["reworded_match"] + counts["one_sided_detail"] + counts["conflicting_detail"]
        )
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
(cd 05-App && uv run pytest pipeline/tests/duplicates -q)
```
Expected: `3 failed, 35 passed`, with `ValueError: not enough values to unpack (expected 1, got 0)` (no district pair or batch exists yet). The tests that already pass are the ones that hold whichever finders exist.

- [ ] **Step 3: Implement Finder 3**

In `candidates.py`: **delete the existing `build_duplicate_candidates` function** (the last function in the file), then append:

```python
def _district_audit(
    by_district: _Members,
    register: _Register,
    groups: dict[str, dict[str, Any]],
    index: _Index,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Finder 3, the quiet audit: one district authority, works in different constituencies."""
    row_of, tfidf, tokens = index
    batches: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    block_texts: dict[str, list[str]] = defaultdict(list)
    for authority, canonical in sorted(by_district):
        block_texts[authority].append(canonical)
        members = by_district[(authority, canonical)]
        if len({member["constituency"] for member in members}) >= 2:
            _, group_id, _ = register(authority, canonical, members)
            batches.append(
                _batch("district_identical_batch", authority, group_id, groups[group_id])
            )
    for authority, block in block_texts.items():
        idx = [row_of[canonical] for canonical in block]
        for i, j, cosine, _hits in _similar_pairs(
            idx, tfidf, tokens, DISTRICT_CHARACTER_SIMILARITY_MIN, use_tokens=False
        ):
            members_i = by_district[(authority, block[i])]
            members_j = by_district[(authority, block[j])]
            if len({member["constituency"] for member in members_i + members_j}) < 2:
                continue  # one constituency only: Finder 2 already looked there
            side_i = register(authority, block[i], members_i)
            side_j = register(authority, block[j], members_j)
            pairs.append(
                _pair("district_near_copy", authority, side_i, side_j, cosine, ["character"])
            )
    return batches, pairs


def build_duplicate_candidates(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Finder 1 (identical batches), Finder 2 (near-copy pairs) and Finder 3 (the quiet district
    audit) over the works whose description has at least one letter or digit. Validated against
    duplicate_candidates.schema.json before it is returned. Never modifies `records`.
    """
    by_constituency, by_district, considered = _index(records)
    groups: dict[str, dict[str, Any]] = {}
    register = _registrar(groups)
    batches = _identical_batches(by_constituency, register, groups)
    pairs: list[dict[str, Any]] = []
    if by_constituency:
        index = _similarity_index(sorted({canonical for _, canonical in by_constituency}))
        pairs += _near_copy_pairs(by_constituency, register, index)
        district_batches, district_pairs = _district_audit(by_district, register, groups, index)
        batches += district_batches
        pairs += district_pairs
    return _artifact(considered, groups, batches, pairs)
```

- [ ] **Step 4: Run the tests and lint**

```bash
(cd 05-App && uv run pytest pipeline/tests/duplicates -q)
(cd 05-App && uvx ruff format pipeline/src/nidhinetra_pipeline/duplicates/candidates.py pipeline/tests/duplicates/test_candidates.py && uvx ruff check pipeline/src/nidhinetra_pipeline/duplicates/candidates.py pipeline/tests/duplicates/test_candidates.py )
(cd 05-App && uv run pytest pipeline/tests -q)
```
Expected: `38 passed` in the `duplicates` folder, ruff clean, and `370 passed` for the whole pipeline suite (the baseline plus the new tests).

- [ ] **Step 5: Commit**

```bash
git add 05-App/pipeline/src/nidhinetra_pipeline/duplicates/candidates.py 05-App/pipeline/tests/duplicates/test_candidates.py
git commit -m "feat(duplicates): the quiet district audit and the artifact's guarantees (Phase 1 Stage A, 4/6)"
```

### Task 5: Stage the artifact with the rest of the snapshot

**Files:**
- Modify: `pipeline/src/nidhinetra_pipeline/build_snapshot.py`
- Test: `pipeline/tests/test_build_snapshot.py`

**Interfaces:**
- Consumes: `build_duplicate_candidates(records)` from Task 4.
- Produces: `data/snapshot/duplicate_candidates.json` as the sixth artifact of `build_snapshot()`, staged and committed in the same all-or-none batch as the other five, written without indentation through `bs._stage_compact_json(obj, final_path) -> Path`. The manifest is unchanged.

- [ ] **Step 1: Write the failing tests**

**In `pipeline/tests/test_build_snapshot.py`** (imports): directly below these lines,

```python
import pytest
from nidhinetra_pipeline import build_snapshot as bs
```

add:

```python
from nidhinetra_pipeline.duplicates.candidates import (
    canonical_description_v1,
    validate_duplicate_candidates,
)
```

**In `pipeline/tests/test_build_snapshot.py`** (`test_alias_candidate_stage_failure_leaves_the_whole_snapshot_unchanged`; the failure it injects must now also prove the sixth file untouched): replace

```python
            "alias_candidates.json",
            "manifest.json",
        )
```

with:

```python
            "alias_candidates.json",
            "duplicate_candidates.json",
            "manifest.json",
        )
```

**In `pipeline/tests/test_build_snapshot.py`** (a new method of `TestBuildSnapshotAtomicity`): directly above

```python
    def test_a_failed_stage_never_leaves_a_partial_snapshot_in_place
```

add:

```python
    def test_duplicate_candidate_stage_failure_leaves_the_whole_snapshot_unchanged(
        self, tmp_path, monkeypatch
    ):
        bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=tmp_path / "raw")
        artifact_names = (
            "works.parquet",
            "scored.parquet",
            "graph.json",
            "alias_candidates.json",
            "duplicate_candidates.json",
            "manifest.json",
        )
        before = {name: (tmp_path / name).read_bytes() for name in artifact_names}

        def _fail(obj, final_path):
            raise RuntimeError("simulated duplicate candidate staging failure")

        monkeypatch.setattr(bs, "_stage_compact_json", _fail)

        with pytest.raises(RuntimeError, match="duplicate candidate"):
            bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=tmp_path / "raw")

        assert {name: (tmp_path / name).read_bytes() for name in artifact_names} == before
        assert list(tmp_path.glob(".*tmp")) == []
```

**At the end of `pipeline/tests/test_build_snapshot.py`**, append:

```python
class TestDuplicateCandidatesArtifact:
    def test_the_build_writes_a_valid_compact_duplicate_candidates_file(self, tmp_path):
        bs.build_snapshot(snapshot_dir=tmp_path, raw_dir=tmp_path / "raw")

        text = (tmp_path / "duplicate_candidates.json").read_text(encoding="utf-8")
        artifact = json.loads(text)

        validate_duplicate_candidates(artifact)
        assert "\n" not in text
        fixture = json.loads(bs.WORKS_FIXTURE_PATH.read_text(encoding="utf-8"))
        readable = [w for w in fixture if canonical_description_v1(w["work_description"] or "")]
        assert artifact["meta"]["counts"]["works_considered"] == len(readable)
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
(cd 05-App && uv run pytest pipeline/tests/test_build_snapshot.py -q)
```
Expected: `3 failed, 30 passed`, all with `FileNotFoundError: ... duplicate_candidates.json`.

- [ ] **Step 3: Wire the artifact into the snapshot**

**In `pipeline/src/nidhinetra_pipeline/build_snapshot.py`** (module docstring): replace

```python
alias_candidates.json, manifest.json) follows the same
```

with:

```python
alias_candidates.json, duplicate_candidates.json, manifest.json) follows the same
```

**In `pipeline/src/nidhinetra_pipeline/build_snapshot.py`** (imports): directly above this line,

```python
from .graph.alias_candidates import build_alias_candidates
```

add:

```python
from .duplicates.candidates import build_duplicate_candidates
```

**In `pipeline/src/nidhinetra_pipeline/build_snapshot.py`** (a new staging helper): directly above this line,

```python
def _stage_parquet(df: pd.DataFrame, final_path: Path) -> Path:
```

add:

```python
def _stage_compact_json(obj: Any, final_path: Path) -> Path:
    """`_stage_json` without indentation, for duplicate_candidates.json, which is large."""
    payload = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return _stage_bytes(payload, final_path)
```

**In `pipeline/src/nidhinetra_pipeline/build_snapshot.py`** (`build_snapshot()` docstring): replace

```python
    """Runs fixture-read -> normalize -> score -> graph + alias candidates,
    writes all five artifacts to `snapshot_dir` (default data/snapshot/),
    and returns the manifest dict.
```

with:

```python
    """Runs fixture-read -> normalize -> score -> graph + alias candidates +
    duplicate candidates, writes all six artifacts to `snapshot_dir` (default
    data/snapshot/), and returns the manifest dict.
```

**In `pipeline/src/nidhinetra_pipeline/build_snapshot.py`** (in `build_snapshot()`): directly below this line,

```python
    alias_candidates = build_alias_candidates(normalized)
```

add:

```python
    duplicate_candidates = build_duplicate_candidates(normalized)
```

**In `pipeline/src/nidhinetra_pipeline/build_snapshot.py`** (the `targets` list, before the manifest): directly below this line,

```python
        (alias_candidates, snapshot_dir / "alias_candidates.json", _stage_json),
```

add:

```python
        (duplicate_candidates, snapshot_dir / "duplicate_candidates.json", _stage_compact_json),
```

- [ ] **Step 4: Run the tests and lint**

```bash
(cd 05-App && uv run pytest pipeline/tests -q)
(cd 05-App && uvx ruff format pipeline/src/nidhinetra_pipeline/build_snapshot.py pipeline/tests/test_build_snapshot.py && uvx ruff check pipeline/src/nidhinetra_pipeline/build_snapshot.py pipeline/tests/test_build_snapshot.py )
```
Expected: `372 passed` for the whole suite, ruff clean. The two atomicity tests are the point of this task: a failure while staging `duplicate_candidates.json` must leave all six real files untouched.

- [ ] **Step 5: Commit**

```bash
git add 05-App/pipeline/src/nidhinetra_pipeline/build_snapshot.py 05-App/pipeline/tests/test_build_snapshot.py
git commit -m "feat(pipeline): stage duplicate_candidates.json with the snapshot (Phase 1 Stage A, 5/6)"
```

### Task 6: Add the artifact to an existing snapshot without re-scoring

**Files:**
- Modify: `pipeline/src/nidhinetra_pipeline/build_snapshot.py`
- Modify: `pipeline/src/nidhinetra_pipeline/cli.py`
- Test: `pipeline/tests/test_cli.py`

**Interfaces:**
- Consumes: `build_duplicate_candidates(records)` from Task 4, and `_stage_compact_json` and `_commit_staged` from Task 5's module.
- Produces: `bs.duplicate_candidates_from_snapshot(snapshot_dir=None) -> dict`, which reads `works.parquet` and builds the artifact; `bs.write_duplicate_candidates(artifact, snapshot_dir=None) -> Path`, which writes `duplicate_candidates.json` and nothing else; `cli.duplicates(*, snapshot_dir=None, write=False) -> int`, which prints the counts and writes only when `write` is set; and the command `python -m nidhinetra_pipeline.cli duplicates [--write]`. Task 7 runs that command.

- [ ] **Step 1: Write the failing tests**

**In `pipeline/tests/test_cli.py`** (imports): directly above these lines,

```python
import pytest
from nidhinetra_pipeline import cli
```

add:

```python
import pandas as pd
```

**At the end of `pipeline/tests/test_cli.py`**, append:

```python
def _write_works_parquet(snapshot_dir: Path) -> None:
    """A works.parquet with two identical descriptions in one constituency and one null."""
    base = {
        "constituency": "C1",
        "implementing_district_authority": "D1",
        "implementing_agency": None,
        "activity_name": "Street lights",
        "sanctioned_amount_inr": 900000.0,
        "sanction_date": "2024-07-09",
        "completion_status": "Sanctioned",
    }
    rows = [
        {**base, "work_id": "W1", "work_description": "Solar street lights"},
        {**base, "work_id": "W2", "work_description": "Solar street lights"},
        {**base, "work_id": "W3", "work_description": None},
    ]
    frame = pd.DataFrame(rows)
    for column in ("implementing_agency", "work_description"):
        frame[column] = frame[column].astype("string")
    frame.to_parquet(snapshot_dir / "works.parquet", index=False)


def test_duplicates_dry_run_prints_the_counts_and_writes_nothing(snapshot_dir, capsys):
    _write_works_parquet(snapshot_dir)

    assert cli.duplicates(snapshot_dir=snapshot_dir) == 0

    assert '"identical_batches": 1' in capsys.readouterr().out
    assert not (snapshot_dir / "duplicate_candidates.json").exists()


def test_duplicates_write_adds_only_the_candidates_file(snapshot_dir):
    _write_works_parquet(snapshot_dir)
    (snapshot_dir / "scored.parquet").write_bytes(b"scored")
    (snapshot_dir / "manifest.json").write_text('{"row_count": 3}')
    before = {p.name: p.read_bytes() for p in snapshot_dir.iterdir()}

    assert cli.duplicates(snapshot_dir=snapshot_dir, write=True) == 0

    after = {p.name: p.read_bytes() for p in snapshot_dir.iterdir()}
    written = json.loads(after.pop("duplicate_candidates.json"))
    assert after == before
    assert written["meta"]["counts"]["identical_batches"] == 1


def test_duplicates_reports_a_missing_snapshot_and_writes_nothing(snapshot_dir):
    assert cli.duplicates(snapshot_dir=snapshot_dir, write=True) == 1
    assert list(snapshot_dir.iterdir()) == []


@pytest.mark.parametrize(
    ("argv", "write"), [(["duplicates"], False), (["duplicates", "--write"], True)]
)
def test_the_duplicates_command_passes_its_flag_through(monkeypatch, argv, write):
    calls = []
    monkeypatch.setattr(cli, "duplicates", lambda **kwargs: calls.append(kwargs) or 0)

    assert cli.main(argv) == 0

    assert calls == [{"write": write}]
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
(cd 05-App && uv run pytest pipeline/tests/test_cli.py -q)
```
Expected: `5 failed, 12 passed`, with `AttributeError: module 'nidhinetra_pipeline.cli' has no attribute 'duplicates'`.

- [ ] **Step 3: Implement the writer and the command**

**In `pipeline/src/nidhinetra_pipeline/build_snapshot.py`** (two new functions): directly above this line,

```python
def main(argv: list[str] | None = None) -> int:  # noqa: ARG001 - CLI entry point
```

add:

```python
def duplicate_candidates_from_snapshot(snapshot_dir: Path | None = None) -> dict[str, Any]:
    """Stage A candidates for the works already in `snapshot_dir`, read back from works.parquet."""
    works = pd.read_parquet((snapshot_dir or SNAPSHOT_DIR) / "works.parquet")
    return build_duplicate_candidates(
        works.astype(object).where(works.notna(), None).to_dict("records")
    )


def write_duplicate_candidates(artifact: dict[str, Any], snapshot_dir: Path | None = None) -> Path:
    """Add or refresh duplicate_candidates.json in an existing snapshot and touch nothing else.
    A full rebuild would score again as of today; this cannot move a score, rank or flag.
    """
    final_path = (snapshot_dir or SNAPSHOT_DIR) / "duplicate_candidates.json"
    _commit_staged(_stage_compact_json(artifact, final_path), final_path)
    return final_path
```

**In `pipeline/src/nidhinetra_pipeline/build_snapshot.py`** (`__all__`): replace

```python
__all__ = [
    "SnapshotDowngradeError",
    "SnapshotWriteError",
    "SNAPSHOT_DIR",
    "StaleCacheError",
    "build_snapshot",
    "main",
]
```

with:

```python
__all__ = [
    "SnapshotDowngradeError",
    "SnapshotWriteError",
    "SNAPSHOT_DIR",
    "StaleCacheError",
    "build_snapshot",
    "duplicate_candidates_from_snapshot",
    "main",
    "write_duplicate_candidates",
]
```

**In `pipeline/src/nidhinetra_pipeline/cli.py`** (module docstring): directly below this line,

```python
    python -m nidhinetra_pipeline.cli build
```

add:

```python
    python -m nidhinetra_pipeline.cli duplicates [--write]
```

**In `pipeline/src/nidhinetra_pipeline/cli.py`** (imports): replace

```python
from .build_snapshot import SnapshotDowngradeError, SnapshotWriteError, build_snapshot
```

with:

```python
from .build_snapshot import (
    SnapshotDowngradeError,
    SnapshotWriteError,
    build_snapshot,
    duplicate_candidates_from_snapshot,
    write_duplicate_candidates,
)
from .duplicates.candidates import DuplicateCandidateValidationError
```

**In `pipeline/src/nidhinetra_pipeline/cli.py`** (a new function): directly above this line,

```python
def main(argv: list[str] | None = None) -> int:
```

add:

```python
def duplicates(*, snapshot_dir: Path | None = None, write: bool = False) -> int:
    """Phase 1 Stage A candidates for the works in the served snapshot. Prints the counts and
    writes nothing unless `write` is set; with it, only duplicate_candidates.json is written,
    so no score, rank or flag can move.
    """
    try:
        artifact = duplicate_candidates_from_snapshot(snapshot_dir)
        path = write_duplicate_candidates(artifact, snapshot_dir) if write else None
    except (OSError, SnapshotWriteError, DuplicateCandidateValidationError) as exc:
        logger.error("Duplicate candidates were not written: %s", exc)
        return 1
    print(json.dumps(artifact["meta"]["counts"], indent=2))
    if path is None:
        print("Dry run: nothing was written. Add --write to write duplicate_candidates.json.")
    else:
        print(f"Wrote {path} ({path.stat().st_size / 1e6:.1f} MB)")
    return 0
```

**In `pipeline/src/nidhinetra_pipeline/cli.py`** (in `main()`): directly above this line,

```python
    args = parser.parse_args(argv)
```

add:

```python
    duplicates_parser = subparsers.add_parser(
        "duplicates",
        help="Find identical and near-identical work descriptions in data/snapshot/works.parquet.",
    )
    duplicates_parser.add_argument(
        "--write", action="store_true", help="Write data/snapshot/duplicate_candidates.json."
    )
```

**In `pipeline/src/nidhinetra_pipeline/cli.py`** (in `main()`): directly below these lines,

```python
    if args.command == "pull-live":
        return pull_live()
```

add:

```python
    if args.command == "duplicates":
        return duplicates(write=args.write)
```

- [ ] **Step 4: Run the tests and the gates**

```bash
(cd 05-App && uv run pytest pipeline/tests -q)
(cd 05-App && uvx ruff format pipeline/src/nidhinetra_pipeline/build_snapshot.py pipeline/src/nidhinetra_pipeline/cli.py pipeline/tests/test_build_snapshot.py pipeline/tests/test_cli.py && uvx ruff check pipeline/src/nidhinetra_pipeline/build_snapshot.py pipeline/src/nidhinetra_pipeline/cli.py pipeline/tests/test_build_snapshot.py pipeline/tests/test_cli.py pipeline/src/nidhinetra_pipeline/duplicates/candidates.py pipeline/tests/duplicates/test_candidates.py)
(cd 05-App && make validate)
(cd 05-App && uv run pytest api/tests -q)
git status --short -- 05-App/data
```
Expected: `377 passed` for the pipeline suite, ruff clean, both contract checks pass, the API suite unchanged and green, and `git status --short -- 05-App/data` prints nothing.

- [ ] **Step 5: Commit**

```bash
git add 05-App/pipeline/src/nidhinetra_pipeline/build_snapshot.py 05-App/pipeline/src/nidhinetra_pipeline/cli.py 05-App/pipeline/tests/test_cli.py
git commit -m "feat(pipeline): cli duplicates adds the candidates to a snapshot without re-scoring (Phase 1 Stage A, 6/6)"
```

### Task 7 (GATED): Write the real artifact

**Gate.** Do not start without a written go-ahead from the user in this session, in the form `GO STAGE-A DATA <date>`. Without it, stop after Task 6, report, and leave `data/` untouched. The file is 23.6 MB, it changes what the committed snapshot contains, and a committed blob cannot be taken back out of history.

**Files:**
- Create: `data/snapshot/duplicate_candidates.json` (only through the command below).
- Modify: nothing else.

**Interfaces:**
- Consumes: `python -m nidhinetra_pipeline.cli duplicates [--write]` from Task 6, and the committed `data/snapshot/works.parquet`.
- Produces: the committed artifact that Stage B will read.

- [ ] **Step 1: Check the preconditions**

```bash
git status --short -- 05-App/data/snapshot
git log origin/main --oneline -1
ls 05-App/data/snapshot
```
Expected: the status prints nothing; note the `origin/main` commit for your report; the folder holds exactly `alias_candidates.json`, `graph.json`, `manifest.json`, `scored.parquet` and `works.parquet`. Anything else: stop.

- [ ] **Step 2: Record the hashes of the five existing files**

```bash
shasum -a 256 05-App/data/snapshot/*
```
Keep the output. Step 5 compares against it.

- [ ] **Step 3: Dry run against the real snapshot**

```bash
(cd 05-App/pipeline && uv run python -m nidhinetra_pipeline.cli duplicates)
```
Expected, after about 25 seconds:

```json
{
  "works_considered": 79038,
  "groups": 13008,
  "identical_batches": 1176,
  "threshold_crossing_batches": 271,
  "district_identical_batches": 4,
  "near_copy_pairs": 39123,
  "reworded_match": 147,
  "one_sided_detail": 2386,
  "conflicting_detail": 36590,
  "district_near_copy_pairs": 3
}
Dry run: nothing was written. Add --write to write duplicate_candidates.json.
```

Stop, write nothing and report the numbers if `works_considered`, `identical_batches`, `threshold_crossing_batches` or `district_identical_batches` differ: those four also match the spec, so a difference means the data or the code changed. If only the two pair counts differ by a handful, that is float noise on this machine; report it and do not write.

- [ ] **Step 4: Write the artifact**

```bash
(cd 05-App/pipeline && uv run python -m nidhinetra_pipeline.cli duplicates --write)
```
Expected: the same counts, then `Wrote .../05-App/data/snapshot/duplicate_candidates.json (23.6 MB)`.

- [ ] **Step 5: Prove nothing else moved**

```bash
shasum -a 256 05-App/data/snapshot/alias_candidates.json 05-App/data/snapshot/graph.json 05-App/data/snapshot/manifest.json 05-App/data/snapshot/scored.parquet 05-App/data/snapshot/works.parquet
git status --short -- 05-App/data/snapshot
git diff --quiet -- 05-App/data/snapshot && echo "no tracked snapshot file changed"
```
Expected: the five hashes equal step 2's, the status is exactly `?? 05-App/data/snapshot/duplicate_candidates.json`, and the last line prints. Anything else: do not commit; report.

- [ ] **Step 6: Check the file and its determinism**

```bash
shasum -a 256 05-App/data/snapshot/duplicate_candidates.json
(cd 05-App/pipeline && uv run python -m nidhinetra_pipeline.cli duplicates --write)
shasum -a 256 05-App/data/snapshot/duplicate_candidates.json
```
Expected: the two hashes are identical (the review VM's began `7340fc4dc2755730`; a different hash on another machine is worth a note, and a different count is a stop). The write itself validated the file against the schema.

- [ ] **Step 7: Commit, and do not push**

```bash
git add 05-App/data/snapshot/duplicate_candidates.json
git commit -m "chore(data): add the Stage A duplicate candidates (Phase 1 Stage A, 7/7)"
```
Report the counts, the file size and the hashes. The user pushes.

---

## Done when

- `uv run pytest pipeline/tests api/tests -q` is green: the pipeline suite went from 332 to 403 tests (the plan counted 377 before the review rounds added tests) and the API suite is unchanged (163 tests).
- `make validate` passes, and ruff is clean on every file this plan touches.
- The committed `build_snapshot()` tests prove a failure while staging the sixth file leaves all six real files untouched, and the CLI test proves `--write` changes exactly one file.
- (Only if Task 7 was authorised) `data/snapshot/duplicate_candidates.json` is committed, the five other snapshot files hash exactly as before, and nothing has been pushed.

## Not in this plan

- **Stage B, the pair judge**, and its Hugging Face Inference Providers run. It reads this artifact. It still needs the user's Hugging Face credit check (balance, expiry, whether it counts as compute credit), which is open since 2026-09-15 and which only the user can answer.
- **Stage C, the review surface**: the store, the router, the panel section, the `strings.json` block and the clause 4.4.2 sentence. See the note in decision 9 about loading the file.
- **Stage D, the 300-pair test set and the bake-off**, which set the final thresholds and re-measure the three difference groups.
- **Phases 2 to 4**, including the CrossEncoder fine-tune, which waits for panel-labelled and officer-reviewed pairs that do not exist yet.
