# Phase 1 Stage B: The Pair Judge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ask a pinned model on Hugging Face Inference Providers what each near-copy pair of work descriptions has in common, check in code that every quote it gives is literally in the two texts, and store the answers, with what produced them, in `data/judgments/text_pair_judgments.parquet`. It never touches the build, a score, a rank, a flag or the app.

**Architecture:** One new package, `nidhinetra_pipeline/judge/`, five small modules with one job each: `inputs.py` (what the judge reads), `rubric.py` (the prompt, the answer schema and the request), `verify.py` (the evidence check), `store.py` (the parquet file) and `runner.py` (batches, retries, dollar cap, resume). The network sits behind one injected function, so all 120 new tests run offline. A `cli judge` command runs it by hand: a dry run by default, and `--run` only with `HF_TOKEN` in the environment and a dollar cap.

**Tech Stack:** Python 3.13, `uv`, pytest, `httpx`, `jsonschema`, pandas and pyarrow (all already in `pipeline/pyproject.toml`; add no dependency), ruff.

**Spec:** `docs/superpowers/specs/2026-09-17-foundation-and-duplicate-works-design.md` ("Phase 1, Stage B: the pair judge"). Read that section first; this plan cites it rather than repeating it. Its input is Stage A's artifact: `docs/superpowers/plans/2026-09-21-phase-1-stage-a-candidates.md`.

## Global Constraints

- **Never push.** Commit locally on `codex/finish-nidhinetra`; the user pushes after review.
- **No network in any test, no secret anywhere.** Tests use a stand-in provider (Task 5) or a throwaway server on `127.0.0.1`. `HF_TOKEN` is read from the environment in `cli.judge` only, goes out only as the `Authorization` header, and is never logged, stored or printed (Task 5 tests it).
- **`data/` is off limits until Task 7**, which is gated on the user's written go-ahead. Every test writes under `tmp_path`, and the one real-data check (Task 6) writes to a scratch folder.
- **Nothing moves a score.** Nothing here imports `risk/`, `build_snapshot.py` is not touched, and the judge is never part of `build`.
- **No user-visible text.** `contracts/strings.json` is not touched: Stage C owns what an officer reads. The model's answer has no prose field, only a relation from a list of five and four quotes.
- **No new dependency, and no new file outside `judge/` and `tests/judge/`.**
- **Pinned.** A model and its provider run together or not at all. Only a pair listed in `PRICES_USD_PER_MILLION` can run (Task 5), which refuses routing policies such as `:fastest` and `:cheapest`.
- **Frozen once answers exist.** `SYSTEM_PROMPT` and `ANSWER_SCHEMA` are versioned facts: editing either needs a new `PROMPT_VERSION` or `SCHEMA_VERSION` and a new pin in `test_rubric.py`, never an edit in place.
- ruff: `line-length = 100`, rules `E,F,I,UP,B`. Run `uvx ruff format` and `uvx ruff check` on the files a task changes, and only those: ruff is not in `uv.lock`, and the tree has known findings in files this plan never touches (`rungs.py`, `test_rungs.py`, `test_web_mirror_drift.py`).
- Gates before each commit: the task's own tests; in Task 6 also `uv run pytest pipeline/tests -q` and `uv run pytest api/tests -q`.
- Every command block starts from the repository root, and a block that needs `05-App` runs in a subshell, `(cd 05-App && ...)`, so the working directory never changes between steps. File paths in the prose are relative to `05-App/pipeline/` unless they start with `docs/`, `05-App/` or `data/`; `git add` paths carry the `05-App/` prefix.
- In the Linux VM `uv` and `uvx` exist only after `. ~/.cache/nidhinetra-vm/env.sh`, and the package-scoped forms are the ones that work: `uv run --package nidhinetra-pipeline python -m pytest ...` for `uv run pytest ...`. The VM has no git identity: commit with one-off `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_NAME` and `GIT_COMMITTER_EMAIL` variables matching the repository's history, and never write git config.

## What the real data says

Measured on 2026-09-22, read-only, on the artifact Stage A's code builds from the committed `data/snapshot/works.parquet` (sha256 starting `7340fc4dc2755730`, 23,643,683 bytes), with the code in this plan and an instant stand-in provider. Task 6 prints the first line of this table again.

| Quantity | Value |
|---|---|
| Near-copy pairs the judge reads | 39,123 (the district audit's 3 pairs are not judged) |
| Distinct texts in those pairs | 12,440 |
| Text length | mean 95 characters, median 85, 95th percentile 185, longest 498 |
| Texts with a character beyond Latin-1 (Devanagari) | 19 |
| Texts with a line break or a tab (shown to the judge as a space) | 96 |
| Texts with a backslash / with a double quote | 87 / 1 |
| Pairs whose two sides carry different portal activities | 829 (2.1%); no activity is null |
| Pair keys / input fingerprints | 39,123 unique / 39,123 unique |
| Requests at 15 pairs each | 2,609 |
| Prompt per request | mean 7,894 characters, longest 17,357 (the rubric is 1,639 of them) |
| Prompt tokens for all pairs | about 5.9 million (an estimate at 3.5 characters per token), about $0.24 at the spec's DeepInfra input price of $0.04 per million |
| Output tokens | unknowable offline: a reply's reasoning tokens are billed as output. The spec's "$1 to $2 for all pairs" holds while replies average between about 1,700 and 4,000 tokens per request |
| Validating the 23.6 MB artifact before a run | about 5 seconds |
| The runner's own time for all 2,609 requests against an instant stand-in | 26 seconds; the judgments file is 1.1 MB; a second run sends nothing |

The trial run in Task 7 sends 2 requests and costs well under a cent; multiply its tokens per request by 2,609 for the full run.

## Decisions where the spec is silent, or its facts cannot be checked offline

The user may overrule any of these. Each is small to reverse before Task 7 and cheap after it, except the prompt (11), which Stage D is meant to revise.

1. **The judge reads the artifact and nothing else.** Every text, its activity and its constituency are already in `duplicate_candidates.json`, so `judge/` never opens `works.parquet` and cannot see an amount, a date, an agency or a work count (Task 1 tests the shape of `Item`).
2. **Only near-copy pairs are judged: 39,123.** The district audit's three pairs stay unjudged (the spec calls that pass unfeatured), and an identical batch is not a pair: identical text gives the model nothing to add.
3. **The judge sees each text with every run of whitespace collapsed to one space, and quotes are checked against exactly that text.** 96 of the 12,440 texts hold a line break or a tab. Without this, a model that copies "road near school" from a text holding "road" and "near school" on two lines would be rejected for being honest. `input_fingerprint` is computed over the collapsed text.
4. **Two same-place quotes must name the same place under `canonical_description_v1`: case, punctuation and spacing are ignored, the words must match.** The spec says "quote the shared identifier from both texts" without saying how two quotes are compared. Byte equality would reject "GOVT. SCHOOL, RAMPUR" against "Govt School Rampur"; a substring test would accept "Madugula" as the same place as "Madugula Koduru", the spec's own example of two places that differ. It is one line in `verify.py`.
5. **A wrong quote is stored as an unjudged row; an unreadable reply is not stored at all.** A pair whose quote is not in its text gets a `rejected` row with no relation and no quote, so a rerun does not pay for it again and the rejection rate can be read from the file. A reply the code cannot read, or that skips a pair, stores nothing for those pairs: they are asked again on the next run. Cost if wrong: a systematic failure (say the provider ignores the schema) is paid for on every rerun until someone looks; `--max-usd` bounds it, the report shows `no_answer` at once, and Task 5 logs the start of every unreadable reply.
6. **The provider is pinned in the URL: `https://router.huggingface.co/<provider>/v1/chat/completions`.** That is the form Hugging Face's structured-output guide uses (`.../cerebras/v1`). Its docs describe only the policy suffixes `:fastest`, `:cheapest` and `:preferred` for the `model` field, and all three route automatically, so no suffix is used. `PRICES_USD_PER_MILLION` doubles as the allow-list: a model and provider without a price cannot run, which refuses `:cheapest`, `auto` and any unpriced provider in one place. **Not verifiable offline, and what Task 7's trial run checks:** that the DeepInfra route accepts `openai/gpt-oss-120b` with `strict: true`, and that its replies carry `usage`.
7. **Money.** Each reply's `usage` times the price table is its cost. The run stops between windows of requests once the amount spent reaches `--max-usd`, so it can overshoot by one window (`--workers` requests). A reply without `usage` stops the run, because its cost is unknown. `--run` refuses to start without a `--max-usd` above zero.
8. **Temperature 0, no seed, no `reasoning_effort`.** The router's chat-completion reference lists `seed` and `temperature`, but neither promises identical replies across providers; reproducibility comes from committing the answers, as the spec says. It also lists `reasoning_effort` ("none, minimal, low, medium, high, xhigh; support and defaults are provider and model-dependent"). Version 1 does not send it: a provider that does not support it may refuse the request, and the trial run shows how many tokens the default spends. Reasoning tokens are billed as output tokens, so if they dominate the bill, `"reasoning_effort": "low"` is one line in `ask()` (Task 7's table says when).
9. **`max_tokens` is 6,000 per request.** Fifteen answers need about 1,000; the rest is room for reasoning. A reply that is cut off is unreadable: `no_answer` shows it and the log line shows the tail of what came back.
10. **No new dependency.** `httpx` posts, `jsonschema` checks each reply against the same schema the request sent (a provider's `strict` mode is a request, not a guarantee), and pandas and pyarrow write the parquet.
11. **The prompt is a first version.** Stage D tests the rubric itself. Editing it means a new `PROMPT_VERSION` and a new pin; the old answers stay in the file under the old version and are simply not counted as answers to the new question.
12. **Independent of Stage A's Decision 10.** Judgments are keyed on the pair key (scope and both text fingerprints), the input fingerprint and the stamp. Nothing here reads a `candidate_id` or a group id, so leaving the finder version in Stage A's ids, or dropping it, changes nothing in this plan.
13. **The artifact is validated before any money is spent.** `cli judge` checks the 23.6 MB file against its schema on every run (about 5 seconds), so a truncated or hand-edited file cannot start a paid run.

## Vocabulary

- **Item**: one near-copy pair as the judge reads it (`judge/inputs.py`).
- **Pair key**: `(scope, fingerprint_a, fingerprint_b)`, the scope being the constituency and the fingerprints those of the two texts.
- **Input fingerprint**: a hash of everything the judge reads for an item: scope, both texts as shown, both activities. A pair whose input changed is asked again.
- **Stamp**: what produced an answer. Model, provider, prompt version and schema version say which question was asked; judge code version and run timestamp are the record.
- **Judged, rejected, no answer**: a judged pair has a relation and quotes that passed; a rejected one had a quote that failed a rule and keeps neither; a pair with no answer got no readable reply and is not stored.
- **Window**: the `--workers` batches sent together. The dollar cap is checked between windows.
- **Pinned**: a model and a provider named together, with a price.

## File Structure

Create (all under `05-App/pipeline/`):

- `src/nidhinetra_pipeline/judge/__init__.py`: the package's docstring.
- `src/nidhinetra_pipeline/judge/inputs.py`: `Item`, `items_from_artifact`.
- `src/nidhinetra_pipeline/judge/rubric.py`: the prompt, the answer schema, `response_format`, `render_messages`.
- `src/nidhinetra_pipeline/judge/verify.py`: `check_answer`.
- `src/nidhinetra_pipeline/judge/store.py`: the parquet file's columns, read, atomic write, `answered`.
- `src/nidhinetra_pipeline/judge/runner.py`: `run_judge`, `pending`, `Report`, the transport, the price table.
- `tests/judge/__init__.py` (empty), `test_inputs.py`, `test_rubric.py`, `test_verify.py`, `test_store.py`, `test_runner.py`.

Modify: `src/nidhinetra_pipeline/cli.py` (the `judge` command) and `tests/test_cli.py` (its tests).

Task 7, gated, is the only step that creates `05-App/data/judgments/text_pair_judgments.parquet`. Not touched: `build_snapshot.py`, `risk/`, `contracts/`, `api/`, `web/`.

## Spec coverage

| Spec requirement (Stage B) | Where |
|---|---|
| Sees the two descriptions as published, each side's activity and the constituency; not amounts, dates, agencies or work counts | Task 1 (`Item` and its test), Task 2 (`render_messages`) |
| Five answers; abstaining is first-class and its rate is reported | Task 2 (`RELATIONS`, the prompt), Task 5 (`Report.abstained`, `judged`) |
| Evidence quoted verbatim or null; a same-place answer quotes the shared identifier from both texts; code rejects a quote that is not literally present, counts it, and leaves the pair unjudged | Task 3, Task 5 (`rejected` rows and counts) |
| No model prose reaches an officer | Task 2 (the schema has no prose field and refuses extra keys); the fixed sentences are Stage C |
| One command, never the build; strict JSON schema; 10 to 20 pairs per request; temperature 0 | Task 6 (`cli judge`), Task 2 (`response_format`), Task 5 (batches of 15, temperature 0) |
| Answers in `data/judgments/text_pair_judgments.parquet`, stamped with model, provider, prompt version, schema version and date, committed; the folder is covered by no ignore rule | Task 4, Task 5, Task 1 (checks the ignore rule); the file itself is Task 7 |
| A dollar budget cap, resumable, prices in config | Task 5 (`--max-usd`, the store as the resume point, `PRICES_USD_PER_MILLION`) |
| A model and its provider pinned together; routing selectors forbidden for the production run | Task 5 (`_stamp`), Task 6 |
| Every answer stores model, provider, prompt version, schema version, judge code version, timestamp and the pair's fingerprint | Task 4 (`COLUMNS`), Task 5 |
| About $1 to $2 for all pairs | measured input above; the output side is Task 7's trial run |
| Strict JSON on `openai/gpt-oss-120b` via DeepInfra | Task 7 only: it cannot be verified offline |

## Task 1: What the judge reads

**Files:**
- Create: `05-App/pipeline/src/nidhinetra_pipeline/judge/__init__.py`
- Create: `05-App/pipeline/src/nidhinetra_pipeline/judge/inputs.py`
- Create: `05-App/pipeline/tests/judge/__init__.py`
- Create: `05-App/pipeline/tests/judge/test_inputs.py`

**Interfaces:**
- Consumes: `fingerprint(text) -> str` from `nidhinetra_pipeline.duplicates.candidates` (the first 16 hex characters of a sha256); a *validated* `duplicate_candidates.json` as a dict: `groups[id]` with `text`, `text_fingerprint` and `activity`, and `pairs[*]` with `finder`, `scope`, `a` and `b`.
- Produces: `Item` (frozen dataclass: `scope`, `fingerprint_a`, `fingerprint_b`, `text_a`, `text_b`, `activity_a`, `activity_b`, `input_fingerprint`) and `items_from_artifact(artifact) -> list[Item]`, one item per `near_copy` pair, sorted by `(scope, fingerprint_a, fingerprint_b)`.

- [ ] **Step 1: Write the failing tests**

```bash
mkdir -p 05-App/pipeline/tests/judge && touch 05-App/pipeline/tests/judge/__init__.py
```

Create `05-App/pipeline/tests/judge/test_inputs.py`:

```python
"""Tests for what the pair judge reads."""

from __future__ import annotations

import copy
from dataclasses import fields
from typing import Any

from nidhinetra_pipeline.duplicates.candidates import (
    build_duplicate_candidates,
    validate_duplicate_candidates,
)
from nidhinetra_pipeline.judge.inputs import Item, items_from_artifact


def _group(text: str, fingerprint: str, activity: str | None = "Roads") -> dict[str, Any]:
    return {"text": text, "text_fingerprint": fingerprint, "activity": activity}


def _artifact() -> dict[str, Any]:
    """The parts of a duplicate_candidates.json the judge reads, with amounts the judge must not."""
    return {
        "groups": {
            "g1": {**_group("Boundary wall\n at  Govt School Rampur", "f1"), "amount_total_inr": 5},
            "g2": _group("Boundary wall at Govt School Rampur Kalan", "f2", "Schools"),
            "g3": _group("Hall no 3", "f3", None),
        },
        "pairs": [
            {"finder": "near_copy", "scope": "RAMPUR", "a": "g1", "b": "g2"},
            {"finder": "district_near_copy", "scope": "MORADABAD", "a": "g1", "b": "g3"},
            {"finder": "near_copy", "scope": "AGRA", "a": "g3", "b": "g2"},
        ],
    }


class TestItemsFromArtifact:
    def test_there_is_one_item_per_near_copy_pair_and_none_for_the_district_audit(self) -> None:
        items = items_from_artifact(_artifact())

        assert [(i.scope, i.fingerprint_a, i.fingerprint_b) for i in items] == [
            ("AGRA", "f3", "f2"),
            ("RAMPUR", "f1", "f2"),
        ]

    def test_the_order_does_not_depend_on_the_order_of_the_pairs(self) -> None:
        artifact = _artifact()
        reversed_artifact = {**artifact, "pairs": artifact["pairs"][::-1]}

        assert items_from_artifact(artifact) == items_from_artifact(reversed_artifact)

    def test_texts_are_shown_with_every_run_of_whitespace_collapsed(self) -> None:
        rampur = items_from_artifact(_artifact())[1]

        assert rampur.text_a == "Boundary wall at Govt School Rampur"
        assert rampur.text_b == "Boundary wall at Govt School Rampur Kalan"

    def test_the_activities_pass_through_and_may_be_null(self) -> None:
        agra, rampur = items_from_artifact(_artifact())

        assert (agra.activity_a, agra.activity_b) == (None, "Schools")
        assert (rampur.activity_a, rampur.activity_b) == ("Roads", "Schools")

    def test_an_item_holds_no_amount_date_agency_or_work_count(self) -> None:
        assert {f.name for f in fields(Item)} == {
            "scope",
            "fingerprint_a",
            "fingerprint_b",
            "text_a",
            "text_b",
            "activity_a",
            "activity_b",
            "input_fingerprint",
        }


class TestInputFingerprint:
    @staticmethod
    def _rampur(artifact: dict[str, Any]) -> Item:
        return items_from_artifact(artifact)[1]

    def test_it_ignores_what_the_judge_does_not_read(self) -> None:
        changed = copy.deepcopy(_artifact())
        changed["groups"]["g1"]["amount_total_inr"] = 999
        changed["groups"]["g1"]["text_fingerprint"] = "another"  # the key of the answer, not input

        assert (
            self._rampur(changed).input_fingerprint == self._rampur(_artifact()).input_fingerprint
        )

    def test_it_moves_with_every_field_the_judge_reads(self) -> None:
        base = self._rampur(_artifact()).input_fingerprint
        edits = {
            "text a": lambda a: a["groups"]["g1"].update(text="Boundary wall at Govt School"),
            "text b": lambda a: a["groups"]["g2"].update(text="Boundary wall at Govt School"),
            "activity a": lambda a: a["groups"]["g1"].update(activity="Schools"),
            "activity b": lambda a: a["groups"]["g2"].update(activity="Roads"),
            "constituency": lambda a: a["pairs"][0].update(scope="AGRA"),
        }
        for label, edit in edits.items():
            changed = copy.deepcopy(_artifact())
            edit(changed)

            fingerprints = {i.input_fingerprint for i in items_from_artifact(changed)}

            assert base not in fingerprints, label

    def test_the_two_sides_are_not_interchangeable(self) -> None:
        swapped = copy.deepcopy(_artifact())
        swapped["pairs"][0].update(a="g2", b="g1")

        assert (
            self._rampur(swapped).input_fingerprint != self._rampur(_artifact()).input_fingerprint
        )


def test_it_reads_an_artifact_the_real_builder_made() -> None:
    records = [
        {
            "work_id": work_id,
            "constituency": "C1",
            "implementing_district_authority": "D1",
            "implementing_agency": "Agency 1",
            "work_description": description,
            "activity_name": "Lighting of public spaces",
            "sanctioned_amount_inr": 500_000.0,
            "sanction_date": "2024-07-09",
            "completion_status": "Sanctioned",
        }
        for work_id, description in (
            ("W1", "Installation of high mask light at Kheda"),
            ("W2", "Installation of high mast light at Kheda"),
        )
    ]
    artifact = build_duplicate_candidates(records)
    validate_duplicate_candidates(artifact)

    (item,) = items_from_artifact(artifact)

    assert item.scope == "C1"
    assert {item.text_a, item.text_b} == {
        "Installation of high mask light at Kheda",
        "Installation of high mast light at Kheda",
    }
    assert {item.fingerprint_a, item.fingerprint_b} == {
        group["text_fingerprint"] for group in artifact["groups"].values()
    }
    assert item.activity_a == item.activity_b == "Lighting of public spaces"
```

- [ ] **Step 2: Run it and watch it fail**

```bash
(cd 05-App && uv run pytest pipeline/tests/judge/test_inputs.py -q)
```

Expected: `No module named 'nidhinetra_pipeline.judge'`

- [ ] **Step 3: Write the package and the module**

Create `05-App/pipeline/src/nidhinetra_pipeline/judge/__init__.py`:

```python
"""Phase 1 Stage B: the pair judge.

Reads the near-copy pairs in duplicate_candidates.json, asks a pinned model on Hugging Face
Inference Providers what each pair of descriptions has in common, checks every quote against the
two texts, and stores the answers. It is never part of the build: `cli judge` runs it by hand.
"""
```

Create `05-App/pipeline/src/nidhinetra_pipeline/judge/inputs.py`:

```python
"""What the pair judge reads: one item per near-copy pair, built from duplicate_candidates.json.

The judge sees the two descriptions as published, each side's portal activity and the
constituency, and nothing else: no amounts, dates, agencies or work counts. Those are facts about
works, and keeping them out is what lets one answer serve every work behind a text.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from nidhinetra_pipeline.duplicates.candidates import fingerprint


@dataclass(frozen=True)
class Item:
    scope: str  # the constituency
    fingerprint_a: str  # each side's text_fingerprint, as in the artifact
    fingerprint_b: str
    text_a: str  # as published, every run of whitespace collapsed to one space
    text_b: str
    activity_a: str | None
    activity_b: str | None
    input_fingerprint: str  # over everything the judge reads, so a changed input is judged again


def items_from_artifact(artifact: dict[str, Any]) -> list[Item]:
    """One item per near-copy pair, in a fixed order. `artifact` must already be validated.

    The district audit's pairs are left out: that pass is stored and unfeatured.
    """
    groups = artifact["groups"]
    items = []
    for pair in artifact["pairs"]:
        if pair["finder"] != "near_copy":
            continue
        a, b = groups[pair["a"]], groups[pair["b"]]
        text_a, text_b = " ".join(a["text"].split()), " ".join(b["text"].split())
        read = json.dumps(
            [pair["scope"], text_a, a["activity"], text_b, b["activity"]], ensure_ascii=False
        )
        items.append(
            Item(
                pair["scope"],
                a["text_fingerprint"],
                b["text_fingerprint"],
                text_a,
                text_b,
                a["activity"],
                b["activity"],
                fingerprint(read),
            )
        )
    return sorted(items, key=lambda i: (i.scope, i.fingerprint_a, i.fingerprint_b))
```

- [ ] **Step 4: Run the tests**

```bash
(cd 05-App && uv run pytest pipeline/tests/judge/test_inputs.py -q)
```

Expected: `9 passed`

- [ ] **Step 5: Lint**

```bash
(cd 05-App && uvx ruff format --check pipeline/src/nidhinetra_pipeline/judge pipeline/tests/judge)
```

Expected: `4 files already formatted`

```bash
(cd 05-App && uvx ruff check pipeline/src/nidhinetra_pipeline/judge pipeline/tests/judge)
```

Expected: `All checks passed!`

- [ ] **Step 6: Check that the judgments folder is not git-ignored**

The spec wants `data/judgments/` committed, unlike `data/outcomes/`. This asks git whether it would ignore the file Task 7 creates; exit code 1 means it would not.

```bash
git check-ignore -v 05-App/data/judgments/text_pair_judgments.parquet; echo "exit $?"
```

Expected: `exit 1`

- [ ] **Step 7: Commit**

```bash
git add 05-App/pipeline/src/nidhinetra_pipeline/judge/__init__.py 05-App/pipeline/src/nidhinetra_pipeline/judge/inputs.py 05-App/pipeline/tests/judge/__init__.py 05-App/pipeline/tests/judge/test_inputs.py
git commit -m "feat(judge): read the near-copy pairs the way the pair judge sees them (Phase 1 Stage B, 1/6)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

## Task 2: The rubric, the answer schema and the request

**Files:**
- Create: `05-App/pipeline/src/nidhinetra_pipeline/judge/rubric.py`
- Create: `05-App/pipeline/tests/judge/test_rubric.py`

**Interfaces:**
- Consumes: `Item` from Task 1; `fingerprint` from Stage A (the tests use it to pin the prompt and the schema).
- Produces: `PROMPT_VERSION`, `SCHEMA_VERSION`, `RELATIONS` (the five answers), `SYSTEM_PROMPT`, `ANSWER_SCHEMA` (a JSON schema: an object with `answers`, each with `id`, `relation` and four nullable quotes, no other key), `response_format() -> dict` (a strict `json_schema` request field) and `render_messages(batch) -> list[dict]` (a system message and a user message; pairs numbered `"1"`, `"2"`, ... within the request).

- [ ] **Step 1: Write the failing tests**

Create `05-App/pipeline/tests/judge/test_rubric.py`:

```python
"""Tests for the pair judge's rubric, answer schema and request."""

from __future__ import annotations

import json
from typing import Any

import jsonschema
import pytest
from nidhinetra_pipeline.duplicates.candidates import fingerprint
from nidhinetra_pipeline.judge.inputs import Item
from nidhinetra_pipeline.judge.rubric import (
    ANSWER_SCHEMA,
    PROMPT_VERSION,
    RELATIONS,
    SCHEMA_VERSION,
    SYSTEM_PROMPT,
    render_messages,
    response_format,
)

# Editing the prompt or the schema changes what every stored answer means. Bump the version, add
# its pin here, and expect the whole judgments file to be asked again.
PROMPT_PINS = {"pair_judge_prompt_v1": "cd72fac3420753e7"}
SCHEMA_PINS = {"pair_judge_schema_v1": "95a5b6a647997601"}


def _answer(**overrides: Any) -> dict[str, Any]:
    answer = {
        "id": "1",
        "relation": "same_asset_same_place",
        "asset_a": "boundary wall",
        "place_a": "Govt School Rampur",
        "asset_b": "boundary wall",
        "place_b": "Govt School Rampur",
    }
    return {**answer, **overrides}


def _valid(answers: list[dict[str, Any]]) -> None:
    jsonschema.validate({"answers": answers}, ANSWER_SCHEMA)


def test_the_prompt_and_the_schema_are_pinned_to_their_versions() -> None:
    schema_text = json.dumps(ANSWER_SCHEMA, sort_keys=True)

    assert PROMPT_PINS[PROMPT_VERSION] == fingerprint(SYSTEM_PROMPT)
    assert SCHEMA_PINS[SCHEMA_VERSION] == fingerprint(schema_text)


def test_the_prompt_names_every_relation_the_schema_allows() -> None:
    assert all(relation in SYSTEM_PROMPT for relation in RELATIONS)


class TestAnswerSchema:
    def test_a_well_formed_answer_passes(self) -> None:
        _valid([_answer(), _answer(id="2", relation="unrelated")])

    def test_a_quote_may_be_null(self) -> None:
        _valid([_answer(relation="not_enough_detail", asset_a=None, place_a=None, place_b=None)])

    @pytest.mark.parametrize(
        "bad",
        [
            _answer(relation="duplicate"),
            _answer(relation=None),
            _answer(id=1),
            _answer(place_a=5),
            {**_answer(), "confidence": 0.9},
            {key: value for key, value in _answer().items() if key != "place_b"},
        ],
        ids=[
            "unknown relation",
            "null relation",
            "numeric id",
            "numeric quote",
            "extra key",
            "gap",
        ],
    )
    def test_a_malformed_answer_is_refused(self, bad: dict[str, Any]) -> None:
        with pytest.raises(jsonschema.ValidationError):
            _valid([bad])

    def test_the_reply_must_be_an_object_with_answers(self) -> None:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate([_answer()], ANSWER_SCHEMA)


def test_the_request_asks_for_a_strict_json_schema() -> None:
    fmt = response_format()

    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["strict"] is True
    assert fmt["json_schema"]["schema"] is ANSWER_SCHEMA


class TestRenderMessages:
    ITEMS = [
        Item("RAMPUR", "fa", "fb", "Boundary wall", "Boundary wall at स्कूल", "Roads", None, "i1"),
        Item("AGRA", "fc", "fd", "Hall no 3", "Hall no 4", None, "Schools", "i2"),
    ]

    def test_the_system_message_is_the_rubric(self) -> None:
        system, _ = render_messages(self.ITEMS)

        assert system == {"role": "system", "content": SYSTEM_PROMPT}

    def test_pairs_are_numbered_from_one_and_carry_only_what_the_judge_reads(self) -> None:
        _, user = render_messages(self.ITEMS)

        assert user["role"] == "user"
        assert json.loads(user["content"]) == {
            "pairs": [
                {
                    "id": "1",
                    "constituency": "RAMPUR",
                    "a": {"text": "Boundary wall", "activity": "Roads"},
                    "b": {"text": "Boundary wall at स्कूल", "activity": None},
                },
                {
                    "id": "2",
                    "constituency": "AGRA",
                    "a": {"text": "Hall no 3", "activity": None},
                    "b": {"text": "Hall no 4", "activity": "Schools"},
                },
            ]
        }

    def test_non_latin_text_is_sent_as_written_not_escaped(self) -> None:
        _, user = render_messages(self.ITEMS)

        assert "स्कूल" in user["content"]
```

- [ ] **Step 2: Run it and watch it fail**

```bash
(cd 05-App && uv run pytest pipeline/tests/judge/test_rubric.py -q)
```

Expected: `No module named 'nidhinetra_pipeline.judge.rubric'`

- [ ] **Step 3: Write the module**

Create `05-App/pipeline/src/nidhinetra_pipeline/judge/rubric.py`:

```python
"""The pair judge's rubric, its answer schema and the request built from them.

Editing SYSTEM_PROMPT or ANSWER_SCHEMA changes what every stored answer means, so it must come
with a new PROMPT_VERSION or SCHEMA_VERSION. test_rubric.py fails until it does.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from .inputs import Item

PROMPT_VERSION = "pair_judge_prompt_v1"
SCHEMA_VERSION = "pair_judge_schema_v1"

RELATIONS = (
    "same_asset_same_place",
    "same_place_different_asset",
    "same_asset_different_place",
    "not_enough_detail",
    "unrelated",
)

SYSTEM_PROMPT = """\
You compare pairs of short descriptions of public works funded by an Indian government scheme \
(MPLADS). Each pair comes from one constituency and looks alike. Say what the two descriptions \
have in common, using only their words and the activity label shown with each.

Choose exactly one relation for every pair:
- same_asset_same_place: the same kind of asset at the same named place or institution.
- same_place_different_asset: the same named place or institution, but a different asset or a \
different numbered unit (hall no 3 and hall no 4 are different assets).
- same_asset_different_place: the same kind of asset, at different named places or institutions.
- not_enough_detail: the words do not name a place or institution, or not the asset, so you \
cannot tell. "Construction of Mandap" against "Construction of Mandap" is this. It is a correct \
answer, and you should prefer it whenever a description names no place or institution.
- unrelated: a different asset at a different place.

Evidence: asset_a and asset_b are the words in each description that name the asset. place_a \
and place_b are the words that name the place or institution (a village, ward, road, school, \
hospital, temple or office). Copy them exactly, character for character, from that description. \
Use null where a description has no such words. For same_asset_same_place and \
same_place_different_asset, place_a and place_b must both be copied words and must name the same \
place or institution. Never write words that are not in the description.

Do not explain or comment. Reply with JSON only: one answer for every pair, using each pair's \
id exactly as given.
"""

_QUOTE = {"type": ["string", "null"]}

ANSWER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["answers"],
    "properties": {
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "relation", "asset_a", "place_a", "asset_b", "place_b"],
                "properties": {
                    "id": {"type": "string"},
                    "relation": {"type": "string", "enum": list(RELATIONS)},
                    "asset_a": _QUOTE,
                    "place_a": _QUOTE,
                    "asset_b": _QUOTE,
                    "place_b": _QUOTE,
                },
            },
        }
    },
}


def response_format() -> dict[str, Any]:
    """The `response_format` field of a chat completion request: strict JSON schema."""
    return {
        "type": "json_schema",
        "json_schema": {"name": "pair_judge_answers", "schema": ANSWER_SCHEMA, "strict": True},
    }


def render_messages(batch: Sequence[Item]) -> list[dict[str, str]]:
    """The chat messages for one request. Pairs are numbered 1, 2, ... within the request."""
    pairs = [
        {
            "id": str(n),
            "constituency": item.scope,
            "a": {"text": item.text_a, "activity": item.activity_a},
            "b": {"text": item.text_b, "activity": item.activity_b},
        }
        for n, item in enumerate(batch, 1)
    ]
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps({"pairs": pairs}, ensure_ascii=False)},
    ]
```

- [ ] **Step 4: Run the tests**

```bash
(cd 05-App && uv run pytest pipeline/tests/judge/test_rubric.py -q)
```

Expected: `15 passed`

The first test pins the prompt and the schema by hash. If it ever fails after an edit, that is the point: bump the version constant, add the new pin, and read Decision 11.

- [ ] **Step 5: Lint**

```bash
(cd 05-App && uvx ruff format --check pipeline/src/nidhinetra_pipeline/judge/rubric.py pipeline/tests/judge/test_rubric.py)
```

Expected: `2 files already formatted`

```bash
(cd 05-App && uvx ruff check pipeline/src/nidhinetra_pipeline/judge/rubric.py pipeline/tests/judge/test_rubric.py)
```

Expected: `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add 05-App/pipeline/src/nidhinetra_pipeline/judge/rubric.py 05-App/pipeline/tests/judge/test_rubric.py
git commit -m "feat(judge): the rubric, the strict answer schema and the request (Phase 1 Stage B, 2/6)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

## Task 3: Check every quote against the two texts

**Files:**
- Create: `05-App/pipeline/src/nidhinetra_pipeline/judge/verify.py`
- Create: `05-App/pipeline/tests/judge/test_verify.py`

**Interfaces:**
- Consumes: `Item` from Task 1; `canonical_description_v1` from Stage A.
- Produces: `SAME_PLACE` (the two relations that claim the same place) and `check_answer(item, answer) -> str | None`: `None` when the evidence holds, else the code of the first rule broken: `asset_a_not_in_text`, `place_a_not_in_text`, `asset_b_not_in_text`, `place_b_not_in_text`, `same_place_without_quotes`, `place_quote_without_words` or `place_quotes_differ`.

- [ ] **Step 1: Write the failing tests**

Create `05-App/pipeline/tests/judge/test_verify.py`:

```python
"""Tests for the evidence check on a judge answer."""

from __future__ import annotations

from typing import Any

import pytest
from nidhinetra_pipeline.judge.inputs import Item
from nidhinetra_pipeline.judge.verify import SAME_PLACE, check_answer

TEXT_A = "Boundary wall at Govt School Rampur"
TEXT_B = "BOUNDARY WALL AT GOVT. SCHOOL, RAMPUR (phase 2)"


def _item(text_a: str = TEXT_A, text_b: str = TEXT_B) -> Item:
    return Item("C1", "fa", "fb", text_a, text_b, "Schools", "Schools", "i1")


def _answer(**overrides: Any) -> dict[str, Any]:
    answer = {
        "relation": "same_asset_same_place",
        "asset_a": "Boundary wall",
        "place_a": "Govt School Rampur",
        "asset_b": "BOUNDARY WALL",
        "place_b": "GOVT. SCHOOL, RAMPUR",
    }
    return {**answer, **overrides}


class TestQuotes:
    def test_quotes_found_in_their_own_text_pass_even_when_the_case_and_punctuation_differ(
        self,
    ) -> None:
        assert check_answer(_item(), _answer()) is None

    @pytest.mark.parametrize("field", ["asset_a", "place_a", "asset_b", "place_b"])
    def test_a_quote_that_is_not_in_its_text_is_refused_on_every_side_and_field(
        self, field: str
    ) -> None:
        assert check_answer(_item(), _answer(**{field: "Zila Parishad"})) == f"{field}_not_in_text"

    def test_a_quote_taken_from_the_other_text_is_refused(self) -> None:
        # "(phase 2)" is only in text b, so quoting it for side a must fail.
        assert check_answer(_item(), _answer(asset_a="(phase 2)")) == "asset_a_not_in_text"

    def test_a_quote_must_match_character_for_character(self) -> None:
        assert check_answer(_item(), _answer(asset_a="boundary wall")) == "asset_a_not_in_text"

    @pytest.mark.parametrize("empty", ["", "   "])
    def test_a_quote_with_no_characters_is_refused(self, empty: str) -> None:
        assert check_answer(_item(), _answer(asset_b=empty)) == "asset_b_not_in_text"

    def test_the_first_broken_rule_is_the_one_reported(self) -> None:
        answer = _answer(place_a="nowhere", place_b=None)  # also breaks the same-place rule

        assert check_answer(_item(), answer) == "place_a_not_in_text"


class TestSamePlace:
    def test_the_two_relations_that_claim_the_same_place(self) -> None:
        assert SAME_PLACE == {"same_asset_same_place", "same_place_different_asset"}

    @pytest.mark.parametrize("relation", sorted(SAME_PLACE))
    @pytest.mark.parametrize("missing", ["place_a", "place_b"])
    def test_a_same_place_answer_needs_a_place_quoted_from_both_texts(
        self, relation: str, missing: str
    ) -> None:
        answer = _answer(relation=relation, **{missing: None})

        assert check_answer(_item(), answer) == "same_place_without_quotes"

    @pytest.mark.parametrize(
        "relation", ["same_asset_different_place", "not_enough_detail", "unrelated"]
    )
    def test_the_other_relations_need_no_place(self, relation: str) -> None:
        answer = _answer(relation=relation, place_a=None, place_b=None)

        assert check_answer(_item(), answer) is None

    def test_places_that_differ_are_refused_for_a_same_place_answer(self) -> None:
        item = _item("RO plant at Madugula", "RO plant at Madugula Koduru")
        answer = _answer(
            asset_a="RO plant", place_a="Madugula", asset_b="RO plant", place_b="Madugula Koduru"
        )

        assert check_answer(item, answer) == "place_quotes_differ"

    def test_places_that_differ_are_what_a_different_place_answer_says(self) -> None:
        item = _item("RO plant at Madugula", "RO plant at Madugula Koduru")
        answer = _answer(
            relation="same_asset_different_place",
            asset_a="RO plant",
            place_a="Madugula",
            asset_b="RO plant",
            place_b="Madugula Koduru",
        )

        assert check_answer(item, answer) is None

    def test_a_place_quote_of_punctuation_alone_names_nothing(self) -> None:
        item = _item("Road - Rampur", "Road - Agra")
        answer = _answer(asset_a="Road", place_a="-", asset_b="Road", place_b="-")

        assert check_answer(item, answer) == "place_quote_without_words"
```

- [ ] **Step 2: Run it and watch it fail**

```bash
(cd 05-App && uv run pytest pipeline/tests/judge/test_verify.py -q)
```

Expected: `No module named 'nidhinetra_pipeline.judge.verify'`

- [ ] **Step 3: Write the module**

Create `05-App/pipeline/src/nidhinetra_pipeline/judge/verify.py`:

```python
"""Checks a judge answer's evidence against the two texts it was given."""

from __future__ import annotations

from typing import Any

from nidhinetra_pipeline.duplicates.candidates import canonical_description_v1

from .inputs import Item

SAME_PLACE = frozenset({"same_asset_same_place", "same_place_different_asset"})


def check_answer(item: Item, answer: dict[str, Any]) -> str | None:
    """None when the answer's evidence holds, else the code of the first rule it breaks.

    A quote must be words that appear, exactly, in the description it is quoted from. A same-place
    answer must quote a place from both sides, and the two quotes must name the same place.
    """
    for side, text in (("a", item.text_a), ("b", item.text_b)):
        for field in ("asset", "place"):
            quote = answer[f"{field}_{side}"]
            if quote is not None and (not quote.strip() or quote not in text):
                return f"{field}_{side}_not_in_text"
    if answer["relation"] in SAME_PLACE:
        place_a, place_b = answer["place_a"], answer["place_b"]
        if place_a is None or place_b is None:
            return "same_place_without_quotes"
        canonical = canonical_description_v1(place_a)
        if not canonical:
            return "place_quote_without_words"
        if canonical != canonical_description_v1(place_b):
            return "place_quotes_differ"
    return None
```

- [ ] **Step 4: Run the tests**

```bash
(cd 05-App && uv run pytest pipeline/tests/judge/test_verify.py -q)
```

Expected: `21 passed`

- [ ] **Step 5: Lint**

```bash
(cd 05-App && uvx ruff format --check pipeline/src/nidhinetra_pipeline/judge/verify.py pipeline/tests/judge/test_verify.py)
```

Expected: `2 files already formatted`

```bash
(cd 05-App && uvx ruff check pipeline/src/nidhinetra_pipeline/judge/verify.py pipeline/tests/judge/test_verify.py)
```

Expected: `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add 05-App/pipeline/src/nidhinetra_pipeline/judge/verify.py 05-App/pipeline/tests/judge/test_verify.py
git commit -m "feat(judge): check every quote against the two texts (Phase 1 Stage B, 3/6)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

## Task 4: The judgments file

**Files:**
- Create: `05-App/pipeline/src/nidhinetra_pipeline/judge/store.py`
- Create: `05-App/pipeline/tests/judge/test_store.py`

**Interfaces:**
- Consumes: nothing from the earlier tasks.
- Produces: `FILENAME` (`text_pair_judgments.parquet`), `COLUMNS` (17 names, in file order), `read_judgments(path) -> DataFrame` (an empty frame with every column when the file is missing), `write_judgments(frame, path)` (atomic; creates the folder) and `answered(frame, stamp) -> set[tuple[str, str, str, str]]`, the `(scope, fingerprint_a, fingerprint_b, input_fingerprint)` of every row answered under the stamp's model, provider, prompt version and schema version.

- [ ] **Step 1: Write the failing tests**

Create `05-App/pipeline/tests/judge/test_store.py`:

```python
"""Tests for the judgments file."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from nidhinetra_pipeline.judge import store

STAMP = {
    "model_id": "m",
    "provider_id": "p",
    "prompt_version": "prompt1",
    "schema_version": "schema1",
}


def _row(scope: str = "C1", **overrides: Any) -> dict[str, Any]:
    row = {
        "scope": scope,
        "fingerprint_a": "fa",
        "fingerprint_b": "fb",
        "input_fingerprint": "i1",
        "status": "judged",
        "relation": "unrelated",
        "rejection": None,
        "asset_a": None,
        "place_a": "Rampur",
        "asset_b": None,
        "place_b": None,
        **STAMP,
        "judge_code_version": "code1",
        "run_timestamp": "2026-09-22T10:00:00+00:00",
    }
    return {**row, **overrides}


def _frame(*rows: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(list(rows), columns=store.COLUMNS)


class TestFile:
    def test_a_missing_file_reads_as_an_empty_frame_with_every_column(self, tmp_path: Path) -> None:
        frame = store.read_judgments(tmp_path / "none.parquet")

        assert frame.empty
        assert list(frame.columns) == store.COLUMNS

    def test_a_frame_round_trips_with_its_nulls(self, tmp_path: Path) -> None:
        path = tmp_path / "judgments" / store.FILENAME  # the folder does not exist yet
        written = _frame(
            _row(),
            _row("C2", status="rejected", relation=None, rejection="place_quotes_differ"),
        )

        store.write_judgments(written, path)
        read = store.read_judgments(path)

        assert list(read.columns) == store.COLUMNS
        assert read["scope"].tolist() == ["C1", "C2"]
        assert read["status"].tolist() == ["judged", "rejected"]
        assert read["relation"].isna().tolist() == [False, True]
        assert read["rejection"].isna().tolist() == [True, False]
        assert read["place_a"].tolist() == ["Rampur", "Rampur"]

    def test_a_failed_write_leaves_the_old_file_and_no_temp_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / store.FILENAME
        store.write_judgments(_frame(_row()), path)
        before = path.read_bytes()

        def boom(self: pd.DataFrame, *args: Any, **kwargs: Any) -> None:
            raise OSError("disk full")

        monkeypatch.setattr(pd.DataFrame, "to_parquet", boom)
        with pytest.raises(OSError, match="disk full"):
            store.write_judgments(_frame(_row(), _row("C2")), path)

        assert path.read_bytes() == before
        assert list(tmp_path.iterdir()) == [path]


class TestAnswered:
    def test_a_row_answers_only_the_same_model_provider_prompt_and_schema(self) -> None:
        frame = _frame(
            _row("kept"),
            _row("other model", model_id="m2"),
            _row("other provider", provider_id="p2"),
            _row("other prompt", prompt_version="prompt2"),
            _row("other schema", schema_version="schema2"),
        )

        assert store.answered(frame, STAMP) == {("kept", "fa", "fb", "i1")}

    def test_a_rejected_row_counts_as_answered_so_it_is_not_paid_for_twice(self) -> None:
        frame = _frame(_row(status="rejected", relation=None, rejection="place_quotes_differ"))

        assert store.answered(frame, STAMP) == {("C1", "fa", "fb", "i1")}

    def test_a_changed_input_is_not_answered(self) -> None:
        frame = _frame(_row(input_fingerprint="old"))

        assert ("C1", "fa", "fb", "new") not in store.answered(frame, STAMP)

    def test_an_empty_frame_answers_nothing(self) -> None:
        assert store.answered(_frame(), STAMP) == set()
```

- [ ] **Step 2: Run it and watch it fail**

```bash
(cd 05-App && uv run pytest pipeline/tests/judge/test_store.py -q)
```

Expected: `cannot import name 'store' from 'nidhinetra_pipeline.judge'`

- [ ] **Step 3: Write the module**

Create `05-App/pipeline/src/nidhinetra_pipeline/judge/store.py`:

```python
"""The judgments file, data/judgments/text_pair_judgments.parquet.

One row for every pair a run got an evidence-checked reply for: judged, or rejected because a quote
was not in the text. A rejected row keeps no relation and no quote, so the pair stays unjudged. The
file can hold answers from more than one model (a bake-off), so every row says what produced it.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pandas as pd

FILENAME = "text_pair_judgments.parquet"

COLUMNS = [
    "scope",
    "fingerprint_a",
    "fingerprint_b",
    "input_fingerprint",
    "status",  # "judged" or "rejected"
    "relation",
    "rejection",  # the rule a rejected answer broke
    "asset_a",
    "place_a",
    "asset_b",
    "place_b",
    "model_id",
    "provider_id",
    "prompt_version",
    "schema_version",
    "judge_code_version",
    "run_timestamp",
]

# What makes an earlier row an answer to the same question: the same model behind the same
# provider, asked with the same prompt and schema. judge_code_version is a stamp, not a key.
_ASKED = ("model_id", "provider_id", "prompt_version", "schema_version")


def read_judgments(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path) if path.exists() else pd.DataFrame(columns=COLUMNS)


def write_judgments(frame: pd.DataFrame, path: Path) -> None:
    """Atomic: a half-written file never replaces a good one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    os.close(handle)
    try:
        frame[COLUMNS].to_parquet(temp, index=False)
        os.replace(temp, path)
    except BaseException:
        os.unlink(temp)
        raise


def answered(frame: pd.DataFrame, stamp: dict[str, str]) -> set[tuple[str, str, str, str]]:
    """(scope, fingerprint_a, fingerprint_b, input_fingerprint) of every pair already answered
    under `stamp`'s model, provider, prompt and schema."""
    same = frame
    for column in _ASKED:
        same = same[same[column] == stamp[column]]
    return set(
        zip(
            same["scope"],
            same["fingerprint_a"],
            same["fingerprint_b"],
            same["input_fingerprint"],
            strict=True,
        )
    )
```

- [ ] **Step 4: Run the tests**

```bash
(cd 05-App && uv run pytest pipeline/tests/judge/test_store.py -q)
```

Expected: `7 passed`

- [ ] **Step 5: Lint**

```bash
(cd 05-App && uvx ruff format --check pipeline/src/nidhinetra_pipeline/judge/store.py pipeline/tests/judge/test_store.py)
```

Expected: `2 files already formatted`

```bash
(cd 05-App && uvx ruff check pipeline/src/nidhinetra_pipeline/judge/store.py pipeline/tests/judge/test_store.py)
```

Expected: `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add 05-App/pipeline/src/nidhinetra_pipeline/judge/store.py 05-App/pipeline/tests/judge/test_store.py
git commit -m "feat(judge): the judgments file, atomic and keyed by what produced each answer (Phase 1 Stage B, 4/6)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

## Task 5: Run the judge in batches under a dollar cap

**Files:**
- Create: `05-App/pipeline/src/nidhinetra_pipeline/judge/runner.py`
- Create: `05-App/pipeline/tests/judge/test_runner.py`

**Interfaces:**
- Consumes: `Item` (Task 1); `ANSWER_SCHEMA`, `PROMPT_VERSION`, `SCHEMA_VERSION`, `render_messages`, `response_format` (Task 2); `check_answer` (Task 3); the whole of `store` (Task 4).
- Produces: `JudgeError`, `Report` (`requests`, `pairs`, `judged`, `abstained`, `rejected` by rule, `no_answer`, `prompt_tokens`, `completion_tokens`, `cost_usd`, `stopped`), `Transport` (a callable taking a URL, headers and a payload and returning `(status, body)`), `http_transport` (the real one, on `httpx`), `DEFAULT_MODEL`, `DEFAULT_PROVIDER`, `PRICES_USD_PER_MILLION`, `BATCH_SIZE`, `pending(items, store_path, model_id, provider_id, limit=None) -> list[Item]` and `run_judge(items, *, store_path, model_id, provider_id, token, max_usd, limit=None, transport=http_transport, workers=1, batch_size=BATCH_SIZE, sleep=time.sleep, now=...) -> Report`.

- [ ] **Step 1: Write the failing tests**

Create `05-App/pipeline/tests/judge/test_runner.py`:

```python
"""Tests for running the pair judge. A stand-in provider replaces the network."""

from __future__ import annotations

import json
import logging
import socket
import threading
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import pytest
from nidhinetra_pipeline.judge import runner, store
from nidhinetra_pipeline.judge.inputs import Item

Reply = tuple[int, dict[str, Any]]


def _items(count: int) -> list[Item]:
    return [
        Item(
            "C1",
            f"a{n:03d}",
            f"b{n:03d}",
            f"Road {n} at Rampur",
            f"Road {n} at Rampur Kalan",
            "Roads",
            "Roads",
            f"i{n:03d}",
        )
        for n in range(count)
    ]


def _answer(pair_id: str, **overrides: Any) -> dict[str, Any]:
    answer = {
        "id": pair_id,
        "relation": "same_asset_different_place",
        "asset_a": "Road",
        "place_a": "Rampur",
        "asset_b": "Road",
        "place_b": "Rampur Kalan",
    }
    return {**answer, **overrides}


def _pair_ids(payload: dict[str, Any]) -> list[str]:
    return [pair["id"] for pair in json.loads(payload["messages"][1]["content"])["pairs"]]


def _body(content: str | None, usage: dict[str, int] | None = None) -> dict[str, Any]:
    return {
        "choices": [{"message": {"content": content}}],
        "usage": usage or {"prompt_tokens": 1000, "completion_tokens": 200},
    }


def _reply(
    payload: dict[str, Any],
    answers: list[dict[str, Any]] | None = None,
    usage: dict[str, int] | None = None,
) -> Reply:
    """A good reply: an answer for every pair in the request, and the tokens it cost."""
    if answers is None:
        answers = [_answer(pair_id) for pair_id in _pair_ids(payload)]
    return 200, _body(json.dumps({"answers": answers}), usage)


def _cents(payload: dict[str, Any]) -> Reply:
    """A good reply that costs exactly 4 cents at the default model's prices."""
    return _reply(payload, usage={"prompt_tokens": 1_000_000, "completion_tokens": 0})


class Provider:
    """Stands in for the router. `handler(n, payload)` answers request number n."""

    def __init__(self, handler: Callable[[int, dict[str, Any]], Reply] | None = None) -> None:
        self.handler = handler or (lambda n, payload: _reply(payload))
        self.requests: list[tuple[str, dict[str, str], dict[str, Any]]] = []

    def __call__(self, url: str, headers: dict[str, str], payload: dict[str, Any]) -> Reply:
        self.requests.append((url, headers, payload))
        return self.handler(len(self.requests), payload)


def _run(tmp_path: Path, items: list[Item], provider: Provider, **overrides: Any) -> runner.Report:
    settings: dict[str, Any] = {
        "store_path": tmp_path / "judgments.parquet",
        "model_id": runner.DEFAULT_MODEL,
        "provider_id": runner.DEFAULT_PROVIDER,
        "token": "hf_test",
        "max_usd": 100.0,
        "transport": provider,
        "sleep": lambda seconds: None,
        **overrides,
    }
    return runner.run_judge(items, **settings)


def _stored(tmp_path: Path) -> pd.DataFrame:
    return store.read_judgments(tmp_path / "judgments.parquet")


class TestRun:
    def test_every_pending_pair_is_asked_in_batches_and_stored(self, tmp_path: Path) -> None:
        provider = Provider()

        report = _run(tmp_path, _items(40), provider)

        assert [len(_pair_ids(payload)) for _, _, payload in provider.requests] == [15, 15, 10]
        assert (report.requests, report.pairs, report.judged, report.no_answer) == (3, 40, 40, 0)
        assert dict(report.rejected) == {}
        assert report.stopped is None
        frame = _stored(tmp_path)
        assert len(frame) == 40
        assert set(frame["status"]) == {"judged"}
        assert set(frame["relation"]) == {"same_asset_different_place"}

    def test_an_abstention_is_a_judged_answer_and_is_also_counted_on_its_own(
        self, tmp_path: Path
    ) -> None:
        def mostly_vague(n: int, payload: dict[str, Any]) -> Reply:
            answers = [
                _answer("1", relation="not_enough_detail", asset_a=None, place_a=None),
                _answer("2"),
                _answer("3", relation="not_enough_detail", asset_b=None, place_b=None),
            ]
            return _reply(payload, answers)

        report = _run(tmp_path, _items(3), Provider(mostly_vague))

        assert (report.judged, report.abstained) == (3, 2)
        assert _stored(tmp_path)["relation"].tolist().count("not_enough_detail") == 2

    def test_the_tokens_and_the_cost_are_added_up_from_the_replies(self, tmp_path: Path) -> None:
        usage = {"prompt_tokens": 2_000_000, "completion_tokens": 1_000_000}
        provider = Provider(lambda n, payload: _reply(payload, usage=usage))

        report = _run(tmp_path, _items(20), provider)

        assert (report.prompt_tokens, report.completion_tokens) == (4_000_000, 2_000_000)
        assert report.cost_usd == pytest.approx(2 * (2 * 0.04 + 1 * 0.17))

    def test_a_rerun_asks_for_nothing_it_already_has(self, tmp_path: Path) -> None:
        _run(tmp_path, _items(40), Provider())
        again = Provider()

        report = _run(tmp_path, _items(40), again)

        assert again.requests == []
        assert (report.requests, report.pairs) == (0, 0)
        assert len(_stored(tmp_path)) == 40

    def test_a_pair_whose_input_changed_is_asked_again(self, tmp_path: Path) -> None:
        _run(tmp_path, _items(3), Provider())
        changed = _items(3)
        changed[1] = replace(changed[1], input_fingerprint="moved")
        again = Provider()

        _run(tmp_path, changed, again)

        assert len(again.requests) == 1
        assert len(_pair_ids(again.requests[0][2])) == 1
        assert len(_stored(tmp_path)) == 4

    def test_answers_are_matched_to_their_pair_by_id_not_by_position(self, tmp_path: Path) -> None:
        def backwards(n: int, payload: dict[str, Any]) -> Reply:
            relations = {
                "1": "unrelated",
                "2": "not_enough_detail",
                "3": "same_asset_different_place",
            }
            answers = [_answer(i, relation=relations[i]) for i in ("3", "2", "1")]
            return _reply(payload, answers)

        _run(tmp_path, _items(3), Provider(backwards))

        assert _stored(tmp_path)["relation"].tolist() == [
            "unrelated",
            "not_enough_detail",
            "same_asset_different_place",
        ]

    def test_the_first_answer_for_an_id_is_the_one_kept(self, tmp_path: Path) -> None:
        def twice(n: int, payload: dict[str, Any]) -> Reply:
            answers = [
                _answer("1", relation="unrelated"),
                _answer("1", relation="not_enough_detail"),
            ]
            return _reply(payload, answers)

        _run(tmp_path, _items(1), Provider(twice))

        assert _stored(tmp_path)["relation"].tolist() == ["unrelated"]

    def test_an_answer_for_a_pair_that_was_not_asked_is_ignored(self, tmp_path: Path) -> None:
        def extra(n: int, payload: dict[str, Any]) -> Reply:
            answers = [_answer("1"), _answer("2"), _answer("99", relation="unrelated")]
            return _reply(payload, answers)

        report = _run(tmp_path, _items(2), Provider(extra))

        assert (report.judged, report.no_answer) == (2, 0)
        assert set(_stored(tmp_path)["relation"]) == {"same_asset_different_place"}

    def test_the_request_is_the_one_the_provider_documents(self, tmp_path: Path) -> None:
        provider = Provider()

        _run(tmp_path, _items(2), provider, token="hf_abc")

        ((url, headers, payload),) = provider.requests
        assert url == "https://router.huggingface.co/deepinfra/v1/chat/completions"
        assert headers == {"Authorization": "Bearer hf_abc"}
        assert payload["model"] == "openai/gpt-oss-120b"
        assert payload["temperature"] == 0
        assert payload["max_tokens"] == runner.MAX_OUTPUT_TOKENS
        assert payload["response_format"]["json_schema"]["strict"] is True
        assert [m["role"] for m in payload["messages"]] == ["system", "user"]

    def test_every_row_says_what_produced_it(self, tmp_path: Path) -> None:
        moment = datetime(2026, 9, 22, 10, 30, tzinfo=UTC)

        _run(tmp_path, _items(2), Provider(), now=lambda: moment)

        row = _stored(tmp_path).iloc[0]
        assert row["model_id"] == "openai/gpt-oss-120b"
        assert row["provider_id"] == "deepinfra"
        assert row["prompt_version"] == "pair_judge_prompt_v1"
        assert row["schema_version"] == "pair_judge_schema_v1"
        assert row["judge_code_version"] == runner.JUDGE_CODE_VERSION
        assert row["run_timestamp"] == "2026-09-22T10:30:00+00:00"
        assert (row["scope"], row["fingerprint_a"], row["input_fingerprint"]) == (
            "C1",
            "a000",
            "i000",
        )

    def test_the_token_is_never_stored_or_reported(self, tmp_path: Path) -> None:
        report = _run(tmp_path, _items(3), Provider(), token="hf_SECRET_TOKEN")

        assert len(_stored(tmp_path)) == 3
        assert b"hf_SECRET_TOKEN" not in (tmp_path / "judgments.parquet").read_bytes()
        assert "hf_SECRET_TOKEN" not in repr(report)

    def test_a_limit_runs_only_that_many_pairs(self, tmp_path: Path) -> None:
        provider = Provider()

        report = _run(tmp_path, _items(100), provider, limit=20)

        assert (report.requests, report.pairs) == (2, 20)

    def test_workers_send_a_window_of_requests_together_and_all_of_it_is_stored(
        self, tmp_path: Path
    ) -> None:
        provider = Provider()

        report = _run(tmp_path, _items(50), provider, workers=3)

        assert (report.requests, report.judged) == (4, 50)
        assert len(_stored(tmp_path)) == 50


class TestEvidence:
    def test_an_answer_whose_quote_is_not_in_the_text_is_stored_as_unjudged(
        self, tmp_path: Path
    ) -> None:
        def one_bad(n: int, payload: dict[str, Any]) -> Reply:
            answers = [_answer("1"), _answer("2", place_a="Nowhere"), _answer("3")]
            return _reply(payload, answers)

        report = _run(tmp_path, _items(3), Provider(one_bad))

        assert (report.judged, dict(report.rejected)) == (2, {"place_a_not_in_text": 1})
        frame = _stored(tmp_path)
        rejected = frame[frame["status"] == "rejected"].iloc[0]
        assert rejected["rejection"] == "place_a_not_in_text"
        assert rejected["fingerprint_a"] == "a001"
        assert pd.isna(rejected["relation"])
        assert all(pd.isna(rejected[name]) for name in ("asset_a", "place_a", "asset_b", "place_b"))

    def test_a_rejected_pair_is_not_paid_for_again(self, tmp_path: Path) -> None:
        bad = Provider(lambda n, payload: _reply(payload, [_answer("1", place_b="Nowhere")]))
        _run(tmp_path, _items(1), bad)
        again = Provider()

        _run(tmp_path, _items(1), again)

        assert again.requests == []

    def test_a_pair_the_reply_skips_is_not_stored_and_is_asked_again(self, tmp_path: Path) -> None:
        skipping = Provider(lambda n, payload: _reply(payload, [_answer("1"), _answer("3")]))

        report = _run(tmp_path, _items(3), skipping)

        assert (report.judged, report.no_answer) == (2, 1)
        assert set(_stored(tmp_path)["fingerprint_a"]) == {"a000", "a002"}
        again = Provider()
        _run(tmp_path, _items(3), again)
        assert len(_pair_ids(again.requests[0][2])) == 1

    @pytest.mark.parametrize(
        "body",
        [
            _body("this is not json"),
            _body('{"answers": "none"}'),
            _body("[]"),
            _body(None),
            {"choices": [], "usage": {"prompt_tokens": 1, "completion_tokens": 1}},
            {"usage": {"prompt_tokens": 1, "completion_tokens": 1}},
        ],
        ids=["prose", "wrong shape", "a list", "no content", "no choices", "no choices key"],
    )
    def test_an_unreadable_reply_stores_nothing_for_its_batch(
        self, tmp_path: Path, body: dict[str, Any]
    ) -> None:
        report = _run(tmp_path, _items(4), Provider(lambda n, payload: (200, body)))

        assert (report.judged, report.no_answer, report.requests) == (0, 4, 1)
        assert _stored(tmp_path).empty

    def test_an_unreadable_reply_is_logged_so_a_trial_run_can_be_diagnosed(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        body = _body("the model wrote prose instead of json")

        with caplog.at_level(logging.WARNING, logger="nidhinetra_pipeline.judge.runner"):
            _run(tmp_path, _items(2), Provider(lambda n, payload: (200, body)))

        assert "JSONDecodeError" in caplog.text
        assert "the model wrote prose instead of json" in caplog.text


class TestBudget:
    def test_the_run_stops_once_the_money_spent_reaches_the_cap(self, tmp_path: Path) -> None:
        provider = Provider(lambda n, payload: _cents(payload))

        report = _run(tmp_path, _items(45), provider, max_usd=0.04)

        assert (report.requests, report.stopped) == (1, "budget")
        assert report.cost_usd == pytest.approx(0.04)
        assert len(_stored(tmp_path)) == 15

    def test_the_run_goes_on_while_the_cap_is_not_reached(self, tmp_path: Path) -> None:
        provider = Provider(lambda n, payload: _cents(payload))

        report = _run(tmp_path, _items(45), provider, max_usd=0.05)

        assert (report.requests, report.stopped) == (2, "budget")

    def test_a_cap_that_is_never_reached_does_not_stop_the_run(self, tmp_path: Path) -> None:
        provider = Provider(lambda n, payload: _cents(payload))

        report = _run(tmp_path, _items(45), provider, max_usd=0.13)

        assert (report.requests, report.stopped) == (3, None)

    def test_with_workers_the_cap_is_checked_between_windows(self, tmp_path: Path) -> None:
        provider = Provider(lambda n, payload: _cents(payload))

        report = _run(tmp_path, _items(60), provider, max_usd=0.04, workers=2)

        assert (report.requests, report.stopped) == (2, "budget")


class TestFailures:
    def test_an_interrupted_run_keeps_what_it_got_and_a_rerun_carries_on(
        self, tmp_path: Path
    ) -> None:
        def refused(n: int, payload: dict[str, Any]) -> Reply:
            return (401, {"error": "bad token"}) if n == 2 else _reply(payload)

        with pytest.raises(runner.JudgeError, match="HTTP 401"):
            _run(tmp_path, _items(40), Provider(refused))
        assert len(_stored(tmp_path)) == 15

        rest = Provider()
        _run(tmp_path, _items(40), rest)

        assert [len(_pair_ids(payload)) for _, _, payload in rest.requests] == [15, 10]
        assert len(_stored(tmp_path)) == 40

    def test_a_reply_with_no_token_usage_stops_the_run_and_is_not_stored(
        self, tmp_path: Path
    ) -> None:
        def no_usage(n: int, payload: dict[str, Any]) -> Reply:
            if n == 2:
                return 200, {"choices": [{"message": {"content": '{"answers": []}'}}]}
            return _reply(payload)

        with pytest.raises(runner.JudgeError, match="no token usage"):
            _run(tmp_path, _items(20), Provider(no_usage))

        assert len(_stored(tmp_path)) == 15

    def test_rate_limits_and_server_errors_are_retried_after_a_growing_pause(
        self, tmp_path: Path
    ) -> None:
        pauses: list[float] = []

        def flaky(n: int, payload: dict[str, Any]) -> Reply:
            return {1: (429, {}), 2: (500, {})}.get(n) or _reply(payload)

        provider = Provider(flaky)

        report = _run(tmp_path, _items(2), provider, sleep=pauses.append)

        assert (len(provider.requests), report.judged) == (3, 2)
        assert pauses == [1, 2]

    def test_a_dropped_connection_is_retried(self, tmp_path: Path) -> None:
        def drops(n: int, payload: dict[str, Any]) -> Reply:
            if n == 1:
                raise httpx.ConnectError("connection reset")
            return _reply(payload)

        provider = Provider(drops)

        report = _run(tmp_path, _items(2), provider)

        assert (len(provider.requests), report.judged) == (2, 2)

    def test_it_gives_up_after_four_attempts(self, tmp_path: Path) -> None:
        pauses: list[float] = []
        provider = Provider(lambda n, payload: (503, {}))

        with pytest.raises(runner.JudgeError, match="gave up after 4 attempts"):
            _run(tmp_path, _items(2), provider, sleep=pauses.append)

        assert (len(provider.requests), pauses) == (4, [1, 2, 4])

    @pytest.mark.parametrize("status", [400, 401, 402, 403, 404, 422])
    def test_any_other_refusal_is_not_retried(self, tmp_path: Path, status: int) -> None:
        pauses: list[float] = []
        provider = Provider(lambda n, payload: (status, {"error": "no"}))

        with pytest.raises(runner.JudgeError, match=f"HTTP {status}"):
            _run(tmp_path, _items(2), provider, sleep=pauses.append)

        assert (len(provider.requests), pauses) == (1, [])


class TestPinning:
    @pytest.mark.parametrize(
        ("model", "provider"),
        [
            ("openai/gpt-oss-120b:cheapest", "deepinfra"),
            ("openai/gpt-oss-120b:fastest", "deepinfra"),
            ("openai/gpt-oss-120b", "auto"),
            ("openai/gpt-oss-120b", "novita"),
            ("openai/gpt-oss-20b", "deepinfra"),
        ],
    )
    def test_only_a_model_and_provider_pinned_together_with_a_price_can_run(
        self, tmp_path: Path, model: str, provider: str
    ) -> None:
        stand_in = Provider()

        with pytest.raises(runner.JudgeError, match="pinned model and provider"):
            _run(tmp_path, _items(2), stand_in, model_id=model, provider_id=provider)
        with pytest.raises(runner.JudgeError, match="pinned model and provider"):
            runner.pending(_items(2), tmp_path / "j.parquet", model, provider)

        assert stand_in.requests == []


class TestPending:
    MODEL, PROVIDER = runner.DEFAULT_MODEL, runner.DEFAULT_PROVIDER

    def _pending(self, tmp_path: Path, count: int, limit: int | None) -> list[str]:
        items = runner.pending(
            _items(count), tmp_path / "judgments.parquet", self.MODEL, self.PROVIDER, limit
        )
        return [item.fingerprint_a for item in items]

    def test_a_limit_takes_pairs_spread_evenly_through_the_pending_ones(
        self, tmp_path: Path
    ) -> None:
        assert self._pending(tmp_path, 100, 10) == [f"a{n:03d}" for n in range(0, 100, 10)]

    def test_a_limit_that_does_not_divide_the_pending_count_still_takes_no_more_than_that(
        self, tmp_path: Path
    ) -> None:
        assert self._pending(tmp_path, 95, 10) == [f"a{n:03d}" for n in range(0, 90, 9)]

    def test_a_limit_above_the_pending_count_takes_them_all(self, tmp_path: Path) -> None:
        assert len(self._pending(tmp_path, 5, 10)) == 5

    def test_a_limit_only_counts_pairs_without_an_answer(self, tmp_path: Path) -> None:
        _run(tmp_path, _items(50), Provider())

        taken = self._pending(tmp_path, 100, 10)

        assert len(taken) == 10
        assert min(taken) >= "a050"

    def test_no_limit_means_every_pair_without_an_answer(self, tmp_path: Path) -> None:
        assert len(self._pending(tmp_path, 100, None)) == 100


class _Echo(BaseHTTPRequestHandler):
    """A one-route server: echoes what it was sent, or breaks when asked to."""

    def do_POST(self) -> None:
        sent = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if sent.get("break"):
            status, kind, body = 502, "text/plain", b"upstream broke"
        elif sent.get("refuse"):
            status, kind, body = 402, "application/json", b'{"error": "no credit"}'
        else:
            echo = {
                "path": self.path,
                "auth": self.headers["Authorization"],
                "type": self.headers["Content-Type"],
                "sent": sent,
            }
            status, kind, body = 200, "application/json", json.dumps(echo).encode()
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: Any) -> None:
        pass


@pytest.fixture
def echo_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Echo)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


class TestHttpTransport:
    def test_it_posts_the_payload_as_json_with_the_headers_to_the_url(self, echo_server) -> None:
        payload = {"pairs": ["स्कूल"], "n": 1}

        status, body = runner.http_transport(
            f"{echo_server}/deepinfra/v1/chat/completions", {"Authorization": "Bearer t"}, payload
        )

        assert status == 200
        assert body == {
            "path": "/deepinfra/v1/chat/completions",
            "auth": "Bearer t",
            "type": "application/json",
            "sent": payload,
        }

    def test_a_refusal_comes_back_with_its_status_and_body(self, echo_server) -> None:
        status, body = runner.http_transport(echo_server, {}, {"refuse": True})

        assert (status, body) == (402, {"error": "no credit"})

    def test_a_reply_that_is_not_json_comes_back_as_an_error_text(self, echo_server) -> None:
        status, body = runner.http_transport(echo_server, {}, {"break": True})

        assert (status, body) == (502, {"error": "upstream broke"})

    def test_a_refused_connection_raises_the_error_the_runner_retries(self) -> None:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            closed_port = probe.getsockname()[1]

        with pytest.raises(httpx.TransportError):
            runner.http_transport(f"http://127.0.0.1:{closed_port}", {}, {})
```

- [ ] **Step 2: Run it and watch it fail**

```bash
(cd 05-App && uv run pytest pipeline/tests/judge/test_runner.py -q)
```

Expected: `cannot import name 'runner' from 'nidhinetra_pipeline.judge'`

- [ ] **Step 3: Write the module**

Create `05-App/pipeline/src/nidhinetra_pipeline/judge/runner.py`:

```python
"""Runs the pair judge over the pairs that have no answer yet.

A model and its provider are pinned together: only the pairs listed in PRICES_USD_PER_MILLION can
run, so a routing policy such as `:fastest` or `:cheapest` cannot reach a production run. The
network sits behind `transport`, so everything here is tested without one.
"""

from __future__ import annotations

import json
import logging
import time
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import jsonschema
import pandas as pd

from . import store
from .inputs import Item
from .rubric import ANSWER_SCHEMA, PROMPT_VERSION, SCHEMA_VERSION, render_messages, response_format
from .verify import check_answer

logger = logging.getLogger("nidhinetra_pipeline.judge.runner")

JUDGE_CODE_VERSION = "pair_judge_code_v1"
ROUTER_URL = "https://router.huggingface.co/{provider}/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"
DEFAULT_PROVIDER = "deepinfra"
# USD per million tokens, (input, output). A model and provider with no price here cannot run:
# the budget cap would have nothing to count with. Stage D adds the bake-off's pairs.
PRICES_USD_PER_MILLION = {(DEFAULT_MODEL, DEFAULT_PROVIDER): (0.04, 0.17)}
BATCH_SIZE = 15
MAX_OUTPUT_TOKENS = 6000
ATTEMPTS = 4
FLUSH_EVERY = 25  # windows of requests between writes of the judgments file

Transport = Callable[[str, dict[str, str], dict[str, Any]], tuple[int, dict[str, Any]]]


class JudgeError(Exception):
    """The run cannot go on: a pair that may not run, a refused request, or a reply with no cost."""


@dataclass
class Report:
    requests: int = 0
    pairs: int = 0  # pairs sent
    judged: int = 0
    abstained: int = 0  # of the judged, the pairs answered not_enough_detail
    rejected: Counter[str] = field(default_factory=Counter)  # by the rule the answer broke
    no_answer: int = 0  # the reply skipped or garbled them: not stored, asked again next run
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    stopped: str | None = None  # "budget" when the cap ended the run


def http_transport(
    url: str, headers: dict[str, str], payload: dict[str, Any]
) -> tuple[int, dict[str, Any]]:
    reply = httpx.post(url, headers=headers, json=payload, timeout=120)
    try:
        return reply.status_code, reply.json()
    except ValueError:
        return reply.status_code, {"error": reply.text[:200]}


def _post(
    transport: Transport,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    sleep: Callable[[float], None],
) -> dict[str, Any]:
    """The reply body of one request. Rate limits, server errors and dropped connections are
    retried; any other refusal (a bad token, no credit, a parameter the provider rejects) is not."""
    last = "no attempt"
    for attempt in range(ATTEMPTS):
        if attempt:
            sleep(2 ** (attempt - 1))
        try:
            status, body = transport(url, headers, payload)
        except httpx.TransportError as exc:
            last = type(exc).__name__
            continue
        if status == 200:
            return body
        if status != 429 and status < 500:
            raise JudgeError(f"HTTP {status}: {str(body)[:200]}")
        last = f"HTTP {status}"
    raise JudgeError(f"gave up after {ATTEMPTS} attempts ({last})")


def _answers(batch: list[Item], body: dict[str, Any]) -> list[dict[str, Any] | None]:
    """The reply's answer for each item of the batch, None where it gave none."""
    try:
        reply = json.loads(body["choices"][0]["message"]["content"])
        jsonschema.validate(reply, ANSWER_SCHEMA)
    except (KeyError, IndexError, TypeError, ValueError, jsonschema.ValidationError) as exc:
        logger.warning("unreadable reply (%s): %.300s", type(exc).__name__, body)
        return [None] * len(batch)
    by_id: dict[str, dict[str, Any]] = {}
    for answer in reply["answers"]:
        by_id.setdefault(answer["id"], answer)
    return [by_id.get(str(n)) for n in range(1, len(batch) + 1)]


def _row(item: Item, answer: dict[str, Any], stamp: dict[str, str]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "scope": item.scope,
        "fingerprint_a": item.fingerprint_a,
        "fingerprint_b": item.fingerprint_b,
        "input_fingerprint": item.input_fingerprint,
        **stamp,
    }
    reason = check_answer(item, answer)
    if reason:
        empty = dict.fromkeys(("relation", "asset_a", "place_a", "asset_b", "place_b"))
        return {**row, **empty, "status": "rejected", "rejection": reason}
    quotes = {name: answer[name] for name in ("asset_a", "place_a", "asset_b", "place_b")}
    return {**row, **quotes, "status": "judged", "relation": answer["relation"], "rejection": None}


def _stamp(model_id: str, provider_id: str) -> dict[str, str]:
    if (model_id, provider_id) not in PRICES_USD_PER_MILLION:
        raise JudgeError(
            f"{model_id} on {provider_id} is not a pinned model and provider with a price; "
            "add the pair to PRICES_USD_PER_MILLION (never route by :fastest or :cheapest)"
        )
    return {
        "model_id": model_id,
        "provider_id": provider_id,
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "judge_code_version": JUDGE_CODE_VERSION,
    }


def pending(
    items: list[Item],
    store_path: Path,
    model_id: str,
    provider_id: str,
    limit: int | None = None,
) -> list[Item]:
    """The items with no answer yet from this model and provider. With a limit, that many spread
    evenly through them, so a small trial run is not one constituency's pairs."""
    done = store.answered(store.read_judgments(store_path), _stamp(model_id, provider_id))
    todo = [
        i
        for i in items
        if (i.scope, i.fingerprint_a, i.fingerprint_b, i.input_fingerprint) not in done
    ]
    if limit is not None:
        todo = todo[:: max(1, len(todo) // limit)][:limit]
    return todo


def run_judge(
    items: list[Item],
    *,
    store_path: Path,
    model_id: str,
    provider_id: str,
    token: str,
    max_usd: float,
    limit: int | None = None,
    transport: Transport = http_transport,
    workers: int = 1,
    batch_size: int = BATCH_SIZE,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> Report:
    """Ask the model about every pending item and store what comes back.

    Stops once the money spent reaches `max_usd`, so the last window of requests can overshoot it
    by their own cost. Whatever was answered is stored even when a request fails, so a rerun
    carries on from there.
    """
    stamp = _stamp(model_id, provider_id)
    price_in, price_out = PRICES_USD_PER_MILLION[(model_id, provider_id)]
    todo = pending(items, store_path, model_id, provider_id, limit)
    batches = [todo[n : n + batch_size] for n in range(0, len(todo), batch_size)]
    url = ROUTER_URL.format(provider=provider_id)
    headers = {"Authorization": f"Bearer {token}"}
    stamp["run_timestamp"] = now().isoformat(timespec="seconds")
    frame = store.read_judgments(store_path)
    rows: list[dict[str, Any]] = []
    report = Report()

    def ask(batch: list[Item]) -> tuple[list[dict[str, Any] | None], int, int]:
        payload = {
            "model": model_id,
            "messages": render_messages(batch),
            "temperature": 0,
            "max_tokens": MAX_OUTPUT_TOKENS,
            "response_format": response_format(),
        }
        body = _post(transport, url, headers, payload, sleep)
        try:
            usage = body["usage"]
            return (
                _answers(batch, body),
                int(usage["prompt_tokens"]),
                int(usage["completion_tokens"]),
            )
        except (KeyError, TypeError, ValueError):
            raise JudgeError("a reply carried no token usage, so its cost is unknown") from None

    def flush() -> None:
        nonlocal frame
        if rows:
            new = pd.DataFrame(rows, columns=store.COLUMNS)
            frame = new if frame.empty else pd.concat([frame, new], ignore_index=True)
            store.write_judgments(frame, store_path)
            rows.clear()

    try:
        with ThreadPoolExecutor(workers) as pool:
            for windows, start in enumerate(range(0, len(batches), workers), 1):
                if report.cost_usd >= max_usd:
                    report.stopped = "budget"
                    break
                window = batches[start : start + workers]
                for batch, (answers, sent, received) in zip(
                    window, pool.map(ask, window), strict=True
                ):
                    report.requests += 1
                    report.pairs += len(batch)
                    report.prompt_tokens += sent
                    report.completion_tokens += received
                    report.cost_usd += (sent * price_in + received * price_out) / 1_000_000
                    for item, answer in zip(batch, answers, strict=True):
                        if answer is None:
                            report.no_answer += 1
                            continue
                        row = _row(item, answer, stamp)
                        rows.append(row)
                        if row["status"] == "rejected":
                            report.rejected[row["rejection"]] += 1
                            continue
                        report.judged += 1
                        if row["relation"] == "not_enough_detail":
                            report.abstained += 1
                if windows % FLUSH_EVERY == 0:
                    flush()
                    logger.info("%d pairs asked, $%.4f spent", report.pairs, report.cost_usd)
    finally:
        flush()
    return report
```

- [ ] **Step 4: Run the tests**

```bash
(cd 05-App && uv run pytest pipeline/tests/judge/test_runner.py -q)
```

Expected: `52 passed`

```bash
(cd 05-App && uv run pytest pipeline/tests/judge -q)
```

Expected: `104 passed`

- [ ] **Step 5: Lint**

```bash
(cd 05-App && uvx ruff format --check pipeline/src/nidhinetra_pipeline/judge/runner.py pipeline/tests/judge/test_runner.py)
```

Expected: `2 files already formatted`

```bash
(cd 05-App && uvx ruff check pipeline/src/nidhinetra_pipeline/judge/runner.py pipeline/tests/judge/test_runner.py)
```

Expected: `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add 05-App/pipeline/src/nidhinetra_pipeline/judge/runner.py 05-App/pipeline/tests/judge/test_runner.py
git commit -m "feat(judge): run the judge in batches under a dollar cap, resumable (Phase 1 Stage B, 5/6)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

## Task 6: `cli judge`, a dry run unless told to spend

**Files:**
- Modify: `05-App/pipeline/src/nidhinetra_pipeline/cli.py`
- Modify: `05-App/pipeline/tests/test_cli.py`

**Interfaces:**
- Consumes: `runner` (Task 5), `store` (Task 4), `items_from_artifact` (Task 1), and Stage A's `validate_duplicate_candidates` and `DuplicateCandidateValidationError`.
- Produces: `cli.judge(*, snapshot_dir=None, out_dir=None, model=DEFAULT_MODEL, provider=DEFAULT_PROVIDER, limit=None, max_usd=None, run=False, workers=1, transport=http_transport) -> int` and the subcommand `judge [--run] [--max-usd N] [--limit N] [--model M] [--provider P] [--workers N]`. Exit code 0 on success, 1 on any refusal or failure. A dry run prints two lines and writes nothing; `--run` prints the report as JSON.

- [ ] **Step 1: Write the failing tests**

**Edit `05-App/pipeline/tests/test_cli.py`, the imports**: replace this text, which occurs exactly once,

```text
from nidhinetra_pipeline import cli
from nidhinetra_pipeline.ingest import cache
```

with:

```python
from nidhinetra_pipeline import cli
from nidhinetra_pipeline.duplicates.candidates import build_duplicate_candidates
from nidhinetra_pipeline.ingest import cache
```


Then append two blank lines and this block to the end of `05-App/pipeline/tests/test_cli.py`:

```python
def _write_candidates(snapshot_dir: Path) -> None:
    """A duplicate_candidates.json with two near-copy pairs, one in each of two constituencies:
    a description reworded by one letter."""
    base = {
        "implementing_district_authority": "D1",
        "implementing_agency": "Agency 1",
        "activity_name": "Lighting of public spaces",
        "sanctioned_amount_inr": 500000.0,
        "sanction_date": "2024-07-09",
        "completion_status": "Sanctioned",
    }
    records = [
        {**base, "work_id": f"W{n}{side}", "constituency": f"C{n}", "work_description": text}
        for n in (1, 2)
        for side, text in (
            ("a", "Installation of high mask light at Kheda"),
            ("b", "Installation of high mast light at Kheda"),
        )
    ]
    artifact = build_duplicate_candidates(records)
    (snapshot_dir / "duplicate_candidates.json").write_text(json.dumps(artifact), encoding="utf-8")


def _provider(url, headers, payload):
    """Answers every pair in the request 'unrelated', with no quotes to check."""
    pairs = json.loads(payload["messages"][1]["content"])["pairs"]
    empty = {"asset_a": None, "place_a": None, "asset_b": None, "place_b": None}
    answers = [{"id": pair["id"], "relation": "unrelated", **empty} for pair in pairs]
    content = json.dumps({"answers": answers})
    usage = {"prompt_tokens": 100_000, "completion_tokens": 20_000}
    return 200, {"choices": [{"message": {"content": content}}], "usage": usage}


def _no_network(url, headers, payload):
    raise AssertionError("the judge sent a request")


def test_judge_dry_run_sends_nothing_and_writes_nothing(snapshot_dir, tmp_path, capsys):
    _write_candidates(snapshot_dir)
    out_dir = tmp_path / "judgments"

    assert cli.judge(snapshot_dir=snapshot_dir, out_dir=out_dir, transport=_no_network) == 0

    out = capsys.readouterr().out
    assert "2 near-copy pairs; 2 to judge with openai/gpt-oss-120b on deepinfra." in out
    assert "Dry run: nothing was sent." in out
    assert not out_dir.exists()


def test_judge_dry_run_counts_only_the_pairs_a_limit_leaves(snapshot_dir, tmp_path, capsys):
    _write_candidates(snapshot_dir)

    assert cli.judge(snapshot_dir=snapshot_dir, out_dir=tmp_path / "j", limit=1) == 0

    assert "2 near-copy pairs; 1 to judge" in capsys.readouterr().out


@pytest.mark.parametrize("limit", [0, -3])
def test_judge_refuses_a_limit_below_one(snapshot_dir, tmp_path, limit):
    _write_candidates(snapshot_dir)

    assert cli.judge(snapshot_dir=snapshot_dir, out_dir=tmp_path / "j", limit=limit) == 1


@pytest.mark.parametrize(
    ("token", "max_usd"),
    [(None, 1.0), ("hf_x", None), ("hf_x", 0.0), ("hf_x", -1.0)],
    ids=["no token", "no cap", "zero cap", "negative cap"],
)
def test_judge_run_needs_a_token_and_a_dollar_cap(
    monkeypatch, snapshot_dir, tmp_path, token, max_usd
):
    _write_candidates(snapshot_dir)
    monkeypatch.delenv("HF_TOKEN", raising=False)
    if token:
        monkeypatch.setenv("HF_TOKEN", token)
    out_dir = tmp_path / "judgments"

    code = cli.judge(
        snapshot_dir=snapshot_dir,
        out_dir=out_dir,
        run=True,
        max_usd=max_usd,
        transport=_no_network,
    )

    assert code == 1
    assert not out_dir.exists()


def test_judge_run_stores_the_answers_and_prints_the_report(
    monkeypatch, snapshot_dir, tmp_path, capsys
):
    _write_candidates(snapshot_dir)
    monkeypatch.setenv("HF_TOKEN", "hf_x")
    out_dir = tmp_path / "judgments"

    code = cli.judge(
        snapshot_dir=snapshot_dir, out_dir=out_dir, run=True, max_usd=1.0, transport=_provider
    )

    assert code == 0
    stored = pd.read_parquet(out_dir / "text_pair_judgments.parquet")
    assert stored["relation"].tolist() == ["unrelated", "unrelated"]
    report = json.loads(capsys.readouterr().out)
    assert (report["requests"], report["pairs"], report["judged"]) == (1, 2, 2)
    assert report["cost_usd"] == pytest.approx((100_000 * 0.04 + 20_000 * 0.17) / 1e6, abs=1e-4)


def test_judge_run_passes_its_settings_to_the_runner(monkeypatch, snapshot_dir, tmp_path):
    _write_candidates(snapshot_dir)
    monkeypatch.setenv("HF_TOKEN", "hf_x")
    calls = []

    def fake_run_judge(items, **kwargs):
        calls.append((len(items), kwargs))
        return cli.runner.Report()

    monkeypatch.setattr(cli.runner, "run_judge", fake_run_judge)

    code = cli.judge(
        snapshot_dir=snapshot_dir,
        out_dir=tmp_path / "judgments",
        model="openai/gpt-oss-120b",
        provider="deepinfra",
        limit=1,
        max_usd=2.5,
        run=True,
        workers=3,
        transport=_provider,
    )

    assert code == 0
    assert calls == [
        (
            2,
            {
                "store_path": tmp_path / "judgments" / "text_pair_judgments.parquet",
                "model_id": "openai/gpt-oss-120b",
                "provider_id": "deepinfra",
                "token": "hf_x",
                "max_usd": 2.5,
                "limit": 1,
                "transport": _provider,
                "workers": 3,
            },
        )
    ]


def test_judge_reports_a_refusal_and_stores_nothing(monkeypatch, snapshot_dir, tmp_path):
    _write_candidates(snapshot_dir)
    monkeypatch.setenv("HF_TOKEN", "hf_x")
    out_dir = tmp_path / "judgments"

    code = cli.judge(
        snapshot_dir=snapshot_dir,
        out_dir=out_dir,
        run=True,
        max_usd=1.0,
        transport=lambda url, headers, payload: (402, {"error": "no credit"}),
    )

    assert code == 1
    assert not out_dir.exists()


@pytest.mark.parametrize("text", [None, "not json", "{}"], ids=["missing", "not json", "empty"])
def test_judge_reports_a_missing_or_broken_candidates_file(snapshot_dir, tmp_path, text):
    if text is not None:
        (snapshot_dir / "duplicate_candidates.json").write_text(text, encoding="utf-8")

    assert cli.judge(snapshot_dir=snapshot_dir, out_dir=tmp_path / "judgments") == 1


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (
            ["judge"],
            {
                "model": "openai/gpt-oss-120b",
                "provider": "deepinfra",
                "limit": None,
                "max_usd": None,
                "run": False,
                "workers": 1,
            },
        ),
        (
            [
                "judge",
                "--run",
                "--max-usd",
                "2.5",
                "--limit",
                "20",
                "--workers",
                "4",
                "--model",
                "m",
                "--provider",
                "p",
            ],
            {"model": "m", "provider": "p", "limit": 20, "max_usd": 2.5, "run": True, "workers": 4},
        ),
    ],
)
def test_the_judge_command_passes_its_flags_through(monkeypatch, argv, expected):
    calls = []
    monkeypatch.setattr(cli, "judge", lambda **kwargs: calls.append(kwargs) or 0)

    assert cli.main(argv) == 0

    assert calls == [expected]
```

- [ ] **Step 2: Run the new tests and watch them fail**

```bash
(cd 05-App && uv run pytest pipeline/tests/test_cli.py -k judge -q)
```

Expected: `16 failed`

- [ ] **Step 3: Edit `cli.py`**

Nine changes, none of which touches another part of the file. Each `old` text occurs exactly once.

**Edit `05-App/pipeline/src/nidhinetra_pipeline/cli.py`, change 1 of 9 (usage line)**: replace this text, which occurs exactly once,

```text
    python -m nidhinetra_pipeline.cli duplicates [--write]
```

with:

```python
    python -m nidhinetra_pipeline.cli duplicates [--write]
    python -m nidhinetra_pipeline.cli judge [--run --max-usd DOLLARS] [--limit N]
```

**Edit `05-App/pipeline/src/nidhinetra_pipeline/cli.py`, change 2 of 9 (module docstring)**: replace this text, which occurs exactly once,

```text
rank or flag can move (a full `build` scores again as of the day it runs).
"""
```

with:

```python
rank or flag can move (a full `build` scores again as of the day it runs).

`judge` is Phase 1 Stage B (`judge/`). It asks the pinned model on Hugging Face Inference
Providers what each near-copy pair in data/snapshot/duplicate_candidates.json has in common, and
stores the evidence-checked answers in data/judgments/text_pair_judgments.parquet. It sends
nothing unless `--run` is given, and then only with HF_TOKEN in the environment and a dollar cap
in `--max-usd`. It is never part of `build`.
"""
```

**Edit `05-App/pipeline/src/nidhinetra_pipeline/cli.py`, change 3 of 9 (dataclasses import)**: replace this text, which occurs exactly once,

```text
import tempfile
from pathlib import Path
```

with:

```python
import tempfile
from dataclasses import asdict
from pathlib import Path
```

**Edit `05-App/pipeline/src/nidhinetra_pipeline/cli.py`, change 4 of 9 (SNAPSHOT_DIR import)**: replace this text, which occurs exactly once,

```text
from .build_snapshot import (
    SnapshotDowngradeError,
```

with:

```python
from .build_snapshot import (
    SNAPSHOT_DIR,
    SnapshotDowngradeError,
```

**Edit `05-App/pipeline/src/nidhinetra_pipeline/cli.py`, change 5 of 9 (validator import)**: replace this text, which occurs exactly once,

```text
from .duplicates.candidates import DuplicateCandidateValidationError
```

with:

```python
from .duplicates.candidates import (
    DuplicateCandidateValidationError,
    validate_duplicate_candidates,
)
```

**Edit `05-App/pipeline/src/nidhinetra_pipeline/cli.py`, change 6 of 9 (judge imports)**: replace this text, which occurs exactly once,

```text
from .ingest.rungs import AllRungsFailedError, run_ladder
```

with:

```python
from .ingest.rungs import AllRungsFailedError, run_ladder
from .judge import runner, store
from .judge.inputs import items_from_artifact
```

**Edit `05-App/pipeline/src/nidhinetra_pipeline/cli.py`, change 7 of 9 (the judge function)**: replace this text, which occurs exactly once,

```text
def main(argv: list[str] | None = None) -> int:
```

with:

```python
def judge(
    *,
    snapshot_dir: Path | None = None,
    out_dir: Path | None = None,
    model: str = runner.DEFAULT_MODEL,
    provider: str = runner.DEFAULT_PROVIDER,
    limit: int | None = None,
    max_usd: float | None = None,
    run: bool = False,
    workers: int = 1,
    transport: runner.Transport = runner.http_transport,
) -> int:
    """Phase 1 Stage B: ask the pinned model about the near-copy pairs that have no answer yet.

    Sends nothing unless `run` is set, and then only with HF_TOKEN in the environment and a
    dollar cap in `max_usd`.
    """
    if limit is not None and limit < 1:
        logger.error("--limit must be at least 1")
        return 1
    token = os.environ.get("HF_TOKEN", "")
    if run and not (token and max_usd and max_usd > 0):
        logger.error("--run needs HF_TOKEN in the environment and --max-usd above zero")
        return 1
    store_path = (out_dir or _APP_ROOT / "data" / "judgments") / store.FILENAME
    try:
        candidates = (snapshot_dir or SNAPSHOT_DIR) / "duplicate_candidates.json"
        artifact = json.loads(candidates.read_text(encoding="utf-8"))
        validate_duplicate_candidates(artifact)
        items = items_from_artifact(artifact)
        if not run:
            todo = runner.pending(items, store_path, model, provider, limit)
            print(f"{len(items)} near-copy pairs; {len(todo)} to judge with {model} on {provider}.")
            print("Dry run: nothing was sent. Add --run and --max-usd DOLLARS to send them.")
            return 0
        report = runner.run_judge(
            items,
            store_path=store_path,
            model_id=model,
            provider_id=provider,
            token=token,
            max_usd=max_usd,
            limit=limit,
            transport=transport,
            workers=workers,
        )
    except (OSError, ValueError, DuplicateCandidateValidationError, runner.JudgeError) as exc:
        logger.error("The judge did not finish: %s", exc)
        return 1
    print(json.dumps({**asdict(report), "cost_usd": round(report.cost_usd, 4)}, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
```

**Edit `05-App/pipeline/src/nidhinetra_pipeline/cli.py`, change 8 of 9 (the judge subcommand)**: replace this text, which occurs exactly once,

```text
        "--write", action="store_true", help="Write data/snapshot/duplicate_candidates.json."
    )
```

with:

```python
        "--write", action="store_true", help="Write data/snapshot/duplicate_candidates.json."
    )
    judge_parser = subparsers.add_parser(
        "judge",
        help="Ask the pinned model about the near-copy pairs in duplicate_candidates.json.",
    )
    judge_parser.add_argument(
        "--run",
        action="store_true",
        help="Send the requests. Needs HF_TOKEN in the environment and --max-usd.",
    )
    judge_parser.add_argument("--max-usd", type=float, help="Stop once this much has been spent.")
    judge_parser.add_argument(
        "--limit", type=int, help="Judge only this many pairs, spread evenly through the pending."
    )
    judge_parser.add_argument("--model", default=runner.DEFAULT_MODEL)
    judge_parser.add_argument("--provider", default=runner.DEFAULT_PROVIDER)
    judge_parser.add_argument("--workers", type=int, default=1, help="Requests sent at once.")
```

**Edit `05-App/pipeline/src/nidhinetra_pipeline/cli.py`, change 9 of 9 (the dispatch)**: replace this text, which occurs exactly once,

```text
    if args.command == "duplicates":
        return duplicates(write=args.write)
```

with:

```python
    if args.command == "duplicates":
        return duplicates(write=args.write)
    if args.command == "judge":
        return judge(
            model=args.model,
            provider=args.provider,
            limit=args.limit,
            max_usd=args.max_usd,
            run=args.run,
            workers=args.workers,
        )
```


- [ ] **Step 4: Run the new tests**

```bash
(cd 05-App && uv run pytest pipeline/tests/test_cli.py -k judge -q)
```

Expected: `16 passed`

- [ ] **Step 5: Run everything**

```bash
(cd 05-App && uv run pytest pipeline/tests -q)
```

Expected: `523 passed`

```bash
(cd 05-App && uv run pytest api/tests -q)
```

Expected: `163 passed`

- [ ] **Step 6: Lint**

```bash
(cd 05-App && uvx ruff format --check pipeline/src/nidhinetra_pipeline/cli.py pipeline/tests/test_cli.py pipeline/src/nidhinetra_pipeline/judge pipeline/tests/judge)
```

Expected: `14 files already formatted`

```bash
(cd 05-App && uvx ruff check pipeline/src/nidhinetra_pipeline/cli.py pipeline/tests/test_cli.py pipeline/src/nidhinetra_pipeline/judge pipeline/tests/judge)
```

Expected: `All checks passed!`

- [ ] **Step 7: A dry run on the real artifact, in a scratch folder**

The real artifact is not in `data/snapshot/` until Stage A's Task 7, so this builds it from the committed `works.parquet` into a scratch folder with Stage A's own functions (about 30 seconds), then runs the dry run against that. It writes nothing under `data/`.

```bash
(cd 05-App && SCRATCH=$(mktemp -d) && cp data/snapshot/works.parquet "$SCRATCH/" && uv run --package nidhinetra-pipeline python - "$SCRATCH" <<'PY'
import sys
from pathlib import Path

from nidhinetra_pipeline import cli
from nidhinetra_pipeline.build_snapshot import (
    duplicate_candidates_from_snapshot,
    write_duplicate_candidates,
)

scratch = Path(sys.argv[1])
write_duplicate_candidates(duplicate_candidates_from_snapshot(scratch), scratch)
print("exit", cli.judge(snapshot_dir=scratch, out_dir=scratch / "judgments", limit=20))
print("judgments folder created by a dry run:", (scratch / "judgments").exists())
PY
)
```

Expected: `39123 near-copy pairs; 20 to judge with openai/gpt-oss-120b on deepinfra.`

The two lines after it are `Dry run: nothing was sent. Add --run and --max-usd DOLLARS to send them.`, `exit 0` and `judgments folder created by a dry run: False`.

- [ ] **Step 8: Check that `data/` is untouched**

```bash
git status --porcelain -- 05-App/data
```

Expected: no output.

- [ ] **Step 9: Commit**

```bash
git add 05-App/pipeline/src/nidhinetra_pipeline/cli.py 05-App/pipeline/tests/test_cli.py
git commit -m "feat(pipeline): cli judge, a dry run unless told to spend (Phase 1 Stage B, 6/6)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

## Task 7 (GATED): The trial run on Hugging Face

**Do not run this task without the user's written `GO STAGE-B RUN <date>`.** It spends real money (under a cent), needs a Hugging Face token, and creates `05-App/data/judgments/`. Run it from the Mac: the Linux VM has no token, and no credential of any kind should be pasted into a chat.

**What it is for.** Everything before this task is proved offline. This is the one step that shows whether the real provider does what Decisions 6 to 9 assume. It does not run the whole set: the spec has Stage D pick the model and provider by a bake-off, so the full run waits for that.

**Preconditions, all of them:**
1. Stage A's Task 7 is done: `05-App/data/snapshot/duplicate_candidates.json` exists and is committed.
2. The user has confirmed the Hugging Face credit (balance, expiry, and that it counts toward Inference Providers), the spec's open item 1.
3. `HF_TOKEN` is set in the Mac's shell for this command only. Read it without echoing or saving it: `read -rs HF_TOKEN && export HF_TOKEN`.

- [ ] **Step 1: A dry run against the real snapshot**

```bash
(cd 05-App && uv run --package nidhinetra-pipeline python -m nidhinetra_pipeline.cli judge --limit 30)
```

Expected: `39123 near-copy pairs; 30 to judge with openai/gpt-oss-120b on deepinfra.`

- [ ] **Step 2: The trial run: 30 pairs, two requests, capped at 25 cents**

```bash
(cd 05-App && uv run --package nidhinetra-pipeline python -m nidhinetra_pipeline.cli judge --run --limit 30 --max-usd 0.25)
```

Expected: exit code 0 and a JSON report with `"requests": 2` and `"pairs": 30`.

- [ ] **Step 3: Read the report against this table**

| What you see | What it means | What to do |
|---|---|---|
| Exit 1, `HTTP 401` or `403` | The token is wrong or lacks the Inference Providers permission | Fix the token; nothing was spent |
| Exit 1, `HTTP 402` | No credit | The credit check in the preconditions |
| Exit 1, `HTTP 400` or `422` | The provider refuses a parameter: most likely `strict` in `response_format`, or `max_tokens` | Read the message in the log; change that one field in `ask()` in `runner.py`, bump `JUDGE_CODE_VERSION`, re-run Task 5's tests |
| `"no_answer": 30` | The replies were unreadable. The `unreadable reply` log lines show the start of each: prose instead of JSON, a reply cut off by `max_tokens`, or a schema the provider ignored | Raise `MAX_OUTPUT_TOKENS` if cut off; if the provider ignores the schema, the model or provider is wrong for this job |
| `"rejected"` with many entries | The model quotes words that are not in the text, or names two different places as one | Read the `rejection` codes; this is what Stage D measures, so note it and do not edit the prompt here |
| `"abstained"` near `"judged"`, or near 0 | A judge that abstains on everything, or never | The spec says the abstention rate is reported and read; note it for Stage D |
| `completion_tokens` divided by `requests`, times 2,609 | The output tokens of a full run | The cost of a full run is about $0.24 plus $0.17 per million of them; the spec expects $1 to $2. If the tokens per request are far above the roughly 1,000 that fifteen answers need, reasoning dominates the bill: add `"reasoning_effort": "low"` to the payload in `ask()`, bump `JUDGE_CODE_VERSION`, re-run Task 5's tests and repeat this trial |

- [ ] **Step 4: Look at the answers themselves**

```bash
(cd 05-App && uv run --package nidhinetra-pipeline python - <<'PY'
import pandas as pd

frame = pd.read_parquet("data/judgments/text_pair_judgments.parquet")
print(frame["status"].value_counts().to_string())
print(frame["relation"].value_counts(dropna=False).to_string())
print(frame[["scope", "relation", "asset_a", "place_a", "asset_b", "place_b"]].to_string())
PY
)
```

Read all 30 rows against the two texts (the artifact has them). Note any answer that sounds sure of a place the texts do not name.

- [ ] **Step 5: Check the provider that was actually billed**

On the Hugging Face billing page for Inference Providers, confirm the two requests were served by DeepInfra. The code pins the provider in the URL and cannot see which provider answered.

- [ ] **Step 6: Record it and stop**

Add the trial's report and what Steps 3 to 5 showed to the end of this plan under a heading `Trial run, <date>`. Commit `05-App/data/judgments/text_pair_judgments.parquet` and the plan together only after the user has read them: they are answers bought under prompt v1, and a later run with the same model, provider, prompt and schema skips them. Do not run the full set. Stage D's bake-off comes first.

## Done when

- `uv run pytest pipeline/tests -q` passes with 523 tests (403 from before plus 120 new) and `uv run pytest api/tests -q` with 163.
- `uvx ruff format --check` and `uvx ruff check` pass on the 14 files this plan creates or edits.
- `cli judge` on the real artifact, in the scratch folder, prints `39123 near-copy pairs; 20 to judge ...` and writes nothing.
- `git status -- 05-App/data` is empty and nothing has been pushed.
- Tasks 1 to 6 are committed as six commits. Task 7 is done only with the user's go-ahead.

## Not in this plan

- The work-level derivation (`work_candidate_derivation_v1`), the discriminating-fact filter and the review surface. That is Stage C, and the wording an officer reads lives in `strings.json`.
- The 300-pair test set, the two-model reference and the bake-off of four model and provider pairs. That is Stage D. It adds pairs to `PRICES_USD_PER_MILLION` and may revise the prompt and, once, the thresholds.
- The full 39,123-pair run.
- A way to ask again for pairs that were rejected, or to force a new answer under the same version. A new prompt or schema version does it.
- Judging the district audit's pairs, or identical batches.
- Training or fine-tuning anything. The roadmap's only training step is Phase 4.

## Trial run, 2026-09-26

Ran from the Linux VM (task T12A), not the Mac, per that task's brief.

**Bug found and fixed first.** The pinned `ROUTER_URL` put the provider in the path
(`router.huggingface.co/{provider}/v1/chat/completions`), which Hugging Face's router refuses for
chat completions (`400 Not allowed to POST /v1/chat/completions for provider deepinfra`). Hugging
Face's documented unified endpoint is `router.huggingface.co/v1/chat/completions` with the provider
pinned by a `model:provider` suffix instead (confirmed against the real endpoint: 200, with
`usage.estimated_cost` in the reply). Fixed in `runner.py` (RED/GREEN in `test_runner.py`,
`JUDGE_CODE_VERSION` bumped to `pair_judge_code_v2`); full evidence is in
`.superpowers/sdd/2026-09-26-finish-and-win/task-12a-report.md`.

**Step 1, dry run:**
```
39123 near-copy pairs; 30 to judge with openai/gpt-oss-120b on deepinfra.
Dry run: nothing was sent. Add --run and --max-usd DOLLARS to send them.
```

**Step 2, the trial (`--run --limit 30 --max-usd 0.25`):**
```json
{
  "requests": 2,
  "pairs": 30,
  "judged": 30,
  "abstained": 1,
  "rejected": {},
  "no_answer": 0,
  "prompt_tokens": 4458,
  "completion_tokens": 7169,
  "cost_usd": 0.0014,
  "stopped": null
}
```
Tokens per request: 2229 prompt, 3584.5 completion (average of the 2 requests).

**Step 3, the decision table:** none of the failure rows applied to this run itself (no
401/403/402, `no_answer` is 0, `rejected` is empty). The 400 that fired before the fix, how it was
diagnosed (not a payload parameter; the URL shape), and how it was resolved is recorded above and
in the task report.

**Step 4, the answers:** by status, 30 judged, 0 rejected. By relation: `same_asset_different_place`
26, `same_asset_same_place` 2, `same_place_different_asset` 1, `not_enough_detail` 1 (the
abstention: both sides of that pair are just `"SR NO. 13/18 OF ATTACHED PDF"`, correctly too vague
to name a place). All 3 "same place" answers were checked against their source texts:
- SAGAR and SHRAWASTI: both sides independently name the same place in full (`Gram Panchayat
  Sironja`; `near Shankar Ji temple`) - solid.
- GURDASPUR (`same_place_different_asset`): flagged. Side A is `"...Shed at Shamshan Ghat in
  Village Charak..."`, side B is `"Shed and Bathroom construction at Shamshan Ghat..."` with no
  village named. The model matched on the shared generic term "Shamshan Ghat" alone; side A's more
  specific "Village Charak" is never confirmed on side B. Not a fabrication (both quotes are real,
  verified substrings), but the "same place" call is more confident than side B's text alone
  establishes - worth a look in Stage D's reference set.

No answer invented a place absent from its text (the evidence check that runs on every reply,
`verify.check_answer`, would have rejected that, and 0 rows were rejected here).

**Full-run projection** (39,093 pairs still pending after this trial; `BATCH_SIZE = 15` ->
ceil(39093 / 15) = 2,607 requests):
- Cost: ~$1.82 at the trial's per-request token average and the pinned prices ($0.04 in / $0.17
  out per million) - inside the spec's own $1-2 estimate.
- Wall-clock: a directly measured, real 15-pair batch (production size) took 70.04s. Serial
  (`--workers 1`, the CLI default): 2,607 x 70.04s ~ 50.7 hours. At `--workers 8`: 326 windows x
  70.04s ~ 6.3 hours.
- Recommendation: `--workers 8` - a large, safe win over serial without guessing at an unknown
  per-account concurrency ceiling; `_post`'s retry/backoff (4 attempts) absorbs occasional 429s at
  this level without raising `JudgeError`. Go higher only after this level runs clean.

Recommended full-run command (controller's call; not run by this task):
```
HF_TOKEN="$(cat <token file>)" uv run --package nidhinetra-pipeline python -m nidhinetra_pipeline.cli judge --run --max-usd 3 --workers 8
```

**Step 5 (Hugging Face billing page):** human-only, not done here. Confirm the billed requests show
DeepInfra as the serving provider.

## Full run, 2026-09-26

Launched by the controller as a background job once the trial above confirmed the runner against
a real token. Ran as a retry loop (8 attempts, 180 seconds apart, `--workers 6`; the first launch,
at `--workers 8`, stopped after 401 requests on sustained HTTP 503s), each attempt capped at
`max(0.05, 3.0 - rows_already_answered / 15 * 0.0008)` so cumulative spend across attempts stays
under this plan's $3 cap.

Final state, `05-App/data/judgments/text_pair_judgments.parquet`, 39,093 rows. The last attempt's
own report (unchanged from the attempt before it):

```json
{
  "requests": 2,
  "pairs": 30,
  "judged": 0,
  "abstained": 0,
  "rejected": {},
  "no_answer": 30,
  "prompt_tokens": 6883,
  "completion_tokens": 12000,
  "cost_usd": 0.0023,
  "stopped": null
}
```

These 30 pairs' replies are cut off by `MAX_OUTPUT_TOKENS = 6000` every attempt -- a
`JSONDecodeError` the runner logs as `unreadable reply` and counts as `no_answer` rather than
guessing. Retrying does not fix a token-cap failure, so these 30 stay unanswered under this
prompt/schema version; the spec's own "Not in this plan" list for the judge already reserves "a
way to ask again... under the same version" as future work.

By status: judged 36,625; rejected 2,468 (6.3% of 39,093 -- quote verification: an answer quoted
words not literally in the text, or two "same place" quotes that do not canonically match).
By relation (judged only): same_asset_different_place 31,887; not_enough_detail 2,278 (5.8% of
39,093, abstained); same_asset_same_place 1,277; unrelated 790; same_place_different_asset 393.

Total spend across every attempt: about $1.50, under this plan's $3 cap.

A code bug surfaced late in this run: `cli judge`'s final `print(json.dumps(...))` crashed with
`TypeError: keys must be str, int, float, bool or None, not tuple` while printing attempt 4's
report. Root cause: `dataclasses.asdict()` rebuilds a `Counter` field by calling
`Counter(generator_of_(key, value)_pairs)`, which `Counter`'s own constructor reads as elements to
tally, not a mapping to copy -- so every `(rejection_code, count)` pair became a tuple *key* with
count 1. The answers themselves were already saved (`flush()` runs in a `finally` block before the
crashing print; only the report crashed). Fixed under T12B.2, with a regression test.

This run is what Stage D-lite (`docs/superpowers/plans/2026-09-26-stage-d-lite.md`) reads: only the
`same_asset_same_place` rows above -- quote-verified by construction, since a rejected row never
reaches `judged` -- pass through its discriminating-fact filter and `work_candidate_derivation_v1`.
