# Phase 1 Stage D-lite: Judged Near-Copy Candidates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put the pair judge's strongest, code-verified answers (judged `same_asset_same_place` pairs, both-side quotes verified, at least one discriminating fact) in front of officers in the existing duplicate review queue as work-level candidates, derived by the spec's frozen `work_candidate_derivation_v1` -- without ever calling anything a duplicate, without a two-model reference panel, and without moving any score, rank or flag.

**Architecture:** One new pure pipeline module (`duplicates/judged_candidates.py`) turns a judged pair plus Stage A's artifact into review-store-shaped candidate dicts: code finds, the model already read, code verifies (twice: `judge/verify.py` already ran; this module adds the discriminating-fact filter), the officer still decides. `duplicate_candidate.schema.json` and `outcomes/duplicate_store.py` (built in `docs/superpowers/plans/2026-09-22-phase-1-stage-c-review-store.md`) gain four new optional columns to hold a second text and its quote. `api/routers/duplicates.py` gains a second sync function, mirroring the existing `sync_duplicate_candidates_from_snapshot`, plus the two reportable rates in the queue's own response. The web layer (`web/components/inspection-list/DuplicateReviewQueue.tsx`, `web/components/detail-panel/DetailPanel.tsx`, `contracts/strings.json`) gains the required queue label, both quoted spans, and the rate note -- reusing every existing CSS class and component pattern.

**Tech Stack:** Python 3.13, `uv`, pytest, pandas (already a dependency, via `nidhinetra_pipeline.judge.store`), FastAPI, sqlite3 (stdlib), jsonschema. Next.js/React/Vitest on the web side. No new dependency anywhere.

**Spec:** `docs/superpowers/specs/2026-09-17-foundation-and-duplicate-works-design.md`, sections "From a text answer to a work-level candidate (code, not AI)", "What reaches the officer" and "Phase 1, Stage C: the review surface". Prior art: `docs/superpowers/plans/2026-09-22-phase-1-stage-c-review-store.md` (the store this plan extends; its Decision 1 is the one this plan widens) and `docs/superpowers/plans/2026-09-22-phase-1-stage-b-pair-judge.md` (the judge; its end now also carries the full-run record Task 1 below adds).

## Global Constraints

1. **Copy.** Every new or changed user-visible string goes in `05-App/contracts/strings.json` only, under `duplicate_review`, with one `_meta.amendment_log` line. `contracts/validate.py`'s `lint_strings()` bans (among others) `verified`, `confirmed`, `accuracy`, `confidence`, `probability`, `likelihood`, `finding`/`findings`, `established`, `the model says`, the em dash, and emoji. `05-App/contracts/strings.hi.json` needs no new keys: `check_hi_against_en` only checks hi's *existing* keys resolve in `strings.json` (D9: a missing hi key falls back to English), so a new English-only key is valid as-is.
2. **Honesty.** "Duplicate" never appears as a verdict. `work_relation` (`duplicate_candidate` / `split_or_phase_candidate`) is an internal classification name, never rendered to an officer as that literal string. Report only the abstention rate and the quote-rejection rate; never an accuracy, agreement or confidence figure -- there is no two-model reference panel in this pass. Name the population beside every number (the rates are of *every pair the judge was asked about*, not of judged pairs only, matching how the full run was already recorded).
3. **No score change.** Nothing here imports `risk/`, touches `build_snapshot.py`, or changes `scored.parquet`, ranks or flags.
4. **No new dependency.**
5. **Data safety.** Every pipeline/API test uses `tmp_path` / the existing `isolated_outcomes_db` fixture; nothing here writes the real `05-App/data/outcomes/outcomes.db`. `05-App/data/raw/` is never touched. The one deliberate exception to "never write real data" is Task 1, which *commits* the already-produced, already-on-disk `05-App/data/judgments/text_pair_judgments.parquet` -- it does not run the judge again.
6. **Environment.** From `05-App`, after `. ~/.cache/nidhinetra-vm/env.sh`:
   - `uv run --package nidhinetra-pipeline python -m pytest pipeline/tests -q -p no:cacheprovider`
   - `uv run --package nidhinetra-api python -m pytest api/tests -q -p no:cacheprovider`
   - `uv run --package nidhinetra-pipeline python contracts/validate.py && uv run --package nidhinetra-pipeline python contracts/validate.py --self-test`
   - `uvx ruff check <changed .py> && uvx ruff format --check <changed .py>` (changed files only)
   - Web, in order: `web-gates npm run build`, `web-gates npx tsc --noEmit`, `web-gates npm run lint`, `web-gates npx vitest run`.
7. **Git.** Stage explicit paths only, never `git add -A`. Commit prefix: `GIT_AUTHOR_NAME="Krish Potanwar" GIT_AUTHOR_EMAIL=kpotanwar@gmail.com GIT_COMMITTER_NAME="Krish Potanwar" GIT_COMMITTER_EMAIL=kpotanwar@gmail.com`. Message form `<type>(<scope>): <what> (T12B.N)`, trailer `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`. Never push, rebase, amend or touch git config. Another writer may be active in this checkout on unrelated files (e.g. Task 10's Hindi work) -- stage and commit only the files each task below names.
8. **Scope.** Build only what a task below says. Do not add a CLI subcommand for this sync (the existing `identical_batch` sync has none either; both run from the API's startup hook only).

## Decisions

- **D1 -- this widens Stage C's Decision 1.** `docs/superpowers/plans/2026-09-22-phase-1-stage-c-review-store.md`'s Decision 1 restricted the review-store sync to identical batches only, deferring near-copy pairs "until Stage D has narrowed them by judge answer." That narrowing has now happened, via Stage B's completed judge run, specifically for the `same_asset_same_place` relation, quote-verified, and further narrowed here by the discriminating-fact filter. This plan adds a second, independent sync function alongside the first; it does not touch `identical_batch`/`district_identical_batch` rows or their sync path.
- **D2 -- one review-store row per judged text pair, not per work pair.** The spec's frozen `work_candidate_derivation_v1` is defined over a work pair's own date and amount. Measured on the real, committed data (below), 1,156 of 1,265 discriminating survivors are between two single-work groups, where "the work pair" is unambiguous. The remaining 109 have more than one work on at least one side (up to 330 implied work pairs); Stage D-lite does not fan these out into per-work-pair rows or guess a representative work, because the review-store's identity (`scope, fingerprint_a, fingerprint_b, finder_version`) is one row per *text* pair (Stage C Decision 2), and a group's summary stats (`amount_total_inr`, a sum; `sanction_date_first`/`_last`, a range) cannot stand in for one work's own amount and date without misrepresenting them. These 109 are labelled `split_or_phase_candidate` -- the label that makes no duplicate-funding claim -- rather than invented as `duplicate_candidate`. Cost if wrong: a future Stage D task adds real per-work-pair enrichment for multi-work groups (it would need to join `works.parquet`, which this pass deliberately avoids); today's measured count affected is small (109 of 1,265, 8.6%). **A human could reasonably override this and ask for the per-work-pair join instead.**
- **D3 -- `discriminating_fact_stoplist_v1` is frozen to the brief's own nine words.** `village, gram, ward, road, school, shamshan, ghat, community, hall`. Measured effect on the real data: 12 of 1,277 judged `same_asset_same_place` pairs are excluded (place quotes: `village` x5, `Village` x3, `shamshan ghat`/`Shamshan ghat`/`Shamshan Ghat` x1 each, `school` x1) -- exactly the GURDASPUR failure mode the Stage B trial surfaced (a same-place claim resting only on a generic term), reproduced at small scale. **Stage D may widen this list from measured officer feedback; a human could reasonably add more generic words now instead of waiting.**
- **D4 -- `finder_version` for a judged candidate is `work_candidate_derivation_v1`, not the artifact's `candidate_generation_v0` or the judge's own prompt/schema version.** This is the review-store's own identity, computed directly (mirrors Stage C Decision 3), and changes only if this derivation rule itself changes. Only one model, provider and prompt have been run to date, so the sync does not filter judgments by stamp; if a second model/prompt version is ever judged into the same file, this sync reads whichever row is in `text_pair_judgments.parquet` for that pair without preferring one stamp over another. **A human doing Stage D's real bake-off will need to add that preference; it does not exist here.**
- **D5 -- `threshold_crossing_batch` is always `False` for a judged candidate.** MPLADS clause 4.4.2's per-batch amount test (`build_duplicate_candidates`'s `_batch()`) is defined for one text group's own works; Stage D-lite computes no analogous combined-group fact across two *different* text groups, so it states nothing about it (`False`, never an unearned `True`).
- **D6 -- `duplicate_review.body` and `.context_title` are edited, not only added to.** Once the queue and the detail panel's shared-description section also show near-copy pairs, "the exact same portal description" (body) and "Works with the same description" (context_title) become overclaims for those specific rows. Both are softened to "the same or a closely matching / similar" wording, still exactly true for identical batches.
- **D7 -- the two rates are read fresh from the judgments parquet on every `GET /api/duplicates` call, uncached.** The file is ~1.6 MB; a pandas read is milliseconds. No profiler result justifies a cache yet (ponytail: add one if it ever shows up as a bottleneck).

## Self-check, measured on the real committed data (2026-09-26)

Run read-only against `05-App/data/judgments/text_pair_judgments.parquet` (39,093 rows) and `05-App/data/snapshot/duplicate_candidates.json`:

| Step | Count |
|---|---|
| Judged `same_asset_same_place` pairs | 1,277 |
| Pass `discriminating_fact_stoplist_v1` | 1,265 (12 rejected) |
| Of those: both sides a single work (eligible for the date/amount test) | 1,156 |
| Of those: either side more than one work (D2, conservative) | 109 |
| `duplicate_candidate` (close date, comparable amount, no continuation marker) | 1,103 |
| `split_or_phase_candidate` (continuation marker: 12; failed date/amount test: 41; multi-work, D2: 109) | 162 |
| **Total synced work-level candidates** | **1,265** |
| Quote-rejection rate (of all 39,093 pairs asked) | 2,468 / 39,093 = 6.3% |
| Abstention rate (of all 39,093 pairs asked) | 2,278 / 39,093 = 5.8% |

Task 5's last step re-derives the 1,265 / 1,103 / 162 numbers from the real files as an executable check.

## Task 1: Commit the full judge run

**Files:**
- Stage (already on disk, untracked): `05-App/data/judgments/text_pair_judgments.parquet`
- Modify: `docs/superpowers/plans/2026-09-22-phase-1-stage-b-pair-judge.md` (append only, after its existing "Trial run, 2026-09-26" section)

**Interfaces:** none (data + docs only).

- [ ] **Step 1: Confirm the file on disk matches the recorded run**

```bash
cd 05-App && . ~/.cache/nidhinetra-vm/env.sh && uv run --package nidhinetra-pipeline python -c "
import pandas as pd
frame = pd.read_parquet('data/judgments/text_pair_judgments.parquet')
assert len(frame) == 39093, len(frame)
assert dict(frame['status'].value_counts()) == {'judged': 36625, 'rejected': 2468}
judged = frame[frame['status'] == 'judged']
assert dict(judged['relation'].value_counts()) == {
    'same_asset_different_place': 31887,
    'not_enough_detail': 2278,
    'same_asset_same_place': 1277,
    'unrelated': 790,
    'same_place_different_asset': 393,
}
print('matches the recorded full run: OK')
"
```
Expected: `matches the recorded full run: OK`. If any assertion fails, STOP and report -- do not proceed with a plan whose self-check numbers no longer match the committed file (Global Constraint 10 of the master plan's shared context).

- [ ] **Step 2: Append the run record to the Stage B plan doc**

Append this section to the end of `docs/superpowers/plans/2026-09-22-phase-1-stage-b-pair-judge.md` (after its "Trial run, 2026-09-26" section):

```markdown
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
```

- [ ] **Step 3: Stage and commit**

```bash
cd /media/psf/project/SIH
git add 05-App/data/judgments/text_pair_judgments.parquet docs/superpowers/plans/2026-09-22-phase-1-stage-b-pair-judge.md
GIT_AUTHOR_NAME="Krish Potanwar" GIT_AUTHOR_EMAIL=kpotanwar@gmail.com GIT_COMMITTER_NAME="Krish Potanwar" GIT_COMMITTER_EMAIL=kpotanwar@gmail.com \
git commit -m "feat(judge): commit the full judge run and record it (T12B.1)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
git status --short 05-App/data
```
Expected: clean status for `05-App/data` afterward (the file is now tracked, not modified).

## Task 2: Fix the CLI report crash (TDD)

**Files:**
- Modify: `05-App/pipeline/src/nidhinetra_pipeline/cli.py` (import line 57; `judge()`'s print, line 429)
- Modify: `05-App/pipeline/tests/test_cli.py`

**Interfaces:** none new; `cli.judge()`'s signature and return value are unchanged.

- [ ] **Step 1: Write the failing regression test**

In `05-App/pipeline/tests/test_cli.py`, add `from collections import Counter` to the imports (alphabetical position, before `from datetime import ...`), and add this test after `test_judge_run_stores_the_answers_and_prints_the_report`:

```python
def test_judge_report_prints_when_some_answers_were_rejected(
    monkeypatch, snapshot_dir, tmp_path, capsys
):
    """Regression, full run 2026-09-26: dataclasses.asdict() rebuilds a Counter field by calling
    Counter(generator_of_(key, value)_pairs), which Counter's own constructor reads as elements to
    tally, not a mapping to copy, so the printed report ended up with tuple keys and
    json.dumps crashed. The judge's answers were already saved (flush() runs before this print);
    only the report crashed."""
    _write_candidates(snapshot_dir)
    monkeypatch.setenv("HF_TOKEN", "hf_x")
    fake_report = cli.runner.Report(
        requests=2,
        pairs=30,
        judged=28,
        abstained=1,
        rejected=Counter({"place_quotes_differ": 2}),
        no_answer=0,
        prompt_tokens=100,
        completion_tokens=200,
        cost_usd=0.01,
    )
    monkeypatch.setattr(cli.runner, "run_judge", lambda items, **kwargs: fake_report)

    code = cli.judge(
        snapshot_dir=snapshot_dir,
        out_dir=tmp_path / "judgments",
        run=True,
        max_usd=1.0,
        transport=_provider,
    )

    assert code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["rejected"] == {"place_quotes_differ": 2}
    assert (report["requests"], report["pairs"], report["judged"]) == (2, 30, 28)
```

- [ ] **Step 2: Run it and watch it fail**

```bash
cd 05-App && . ~/.cache/nidhinetra-vm/env.sh && uv run --package nidhinetra-pipeline python -m pytest pipeline/tests/test_cli.py -q -k test_judge_report_prints_when_some_answers_were_rejected
```
Expected: the test errors with `TypeError: keys must be str, int, float, bool or None, not tuple` raised out of `cli.judge(...)` (not a clean `AssertionError` -- the bug is an uncaught exception, since `json.dumps(...)` sits outside the function's `try`/`except`).

- [ ] **Step 3: Fix it at the root -- stop reconstructing the Counter through asdict**

In `05-App/pipeline/src/nidhinetra_pipeline/cli.py`, remove the now-unused import at line 57:

```python
from dataclasses import asdict
```

and change `judge()`'s final print (line 429) from:

```python
    print(json.dumps({**asdict(report), "cost_usd": round(report.cost_usd, 4)}, indent=2))
```

to:

```python
    report_dict = {**vars(report), "rejected": dict(report.rejected), "cost_usd": round(report.cost_usd, 4)}
    print(json.dumps(report_dict, indent=2))
```

`vars(report)` returns the dataclass's real `__dict__` (the actual `Counter` instance, untouched --
unlike `asdict()`, it does not try to reconstruct it), and `dict(report.rejected)` copies it into a
plain, guaranteed-JSON-safe dict. Every other field on `Report` (`requests`, `pairs`, `judged`,
`abstained`, `no_answer`, `prompt_tokens`, `completion_tokens`, `cost_usd`, `stopped`) is already a
plain `int`/`float`/`str | None`, so this produces byte-identical JSON to before for every report
that has no rejections, and correct JSON for one that does.

- [ ] **Step 4: Run it and watch it pass**

```bash
cd 05-App && uv run --package nidhinetra-pipeline python -m pytest pipeline/tests/test_cli.py -q
```
Expected: all tests in the file pass (the existing judge tests plus the new one).

- [ ] **Step 5: Full pipeline suite and lint**

```bash
cd 05-App && uv run --package nidhinetra-pipeline python -m pytest pipeline/tests -q -p no:cacheprovider
uvx ruff check pipeline/src/nidhinetra_pipeline/cli.py pipeline/tests/test_cli.py
uvx ruff format --check pipeline/src/nidhinetra_pipeline/cli.py pipeline/tests/test_cli.py
```
Expected: full suite passes (one more test than the prior baseline); ruff clean on both files.

- [ ] **Step 6: Commit**

```bash
cd /media/psf/project/SIH
git add 05-App/pipeline/src/nidhinetra_pipeline/cli.py 05-App/pipeline/tests/test_cli.py
GIT_AUTHOR_NAME="Krish Potanwar" GIT_AUTHOR_EMAIL=kpotanwar@gmail.com GIT_COMMITTER_NAME="Krish Potanwar" GIT_COMMITTER_EMAIL=kpotanwar@gmail.com \
git commit -m "fix(judge): print the report without asdict breaking a Counter field (T12B.2)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

## Task 3: The pure derivation module

**Files:**
- Create: `05-App/pipeline/src/nidhinetra_pipeline/duplicates/judged_candidates.py`
- Create: `05-App/pipeline/tests/duplicates/test_judged_candidates.py`

**Interfaces:**
- Consumes: `canonical_description_v1` from `nidhinetra_pipeline.duplicates.candidates` (already used the same way by `judge/verify.py`); a `pandas.DataFrame` shaped like `judge.store.COLUMNS` (already-judged rows only need `scope`, `fingerprint_a`, `fingerprint_b`, `status`, `relation`, `place_a`, `place_b`); Stage A's artifact dict (only `artifact["groups"]` is read: each group is `{scope, text_fingerprint, text, work_ids, work_count, amount_total_inr, sanction_date_first, ...}`).
- Produces: `DERIVATION_VERSION = "work_candidate_derivation_v1"`; `STORE_FINDER = "judged_same_asset_same_place"`; `DISCRIMINATING_STOPLIST_V1`; `CONTINUATION_MARKERS_V1`; `is_discriminating(place_quote: str) -> bool`; `build_judged_candidates(artifact: dict, judgments: pd.DataFrame) -> list[dict]` (each dict has keys `finder, scope, fingerprint_a, fingerprint_b, finder_version, threshold_crossing_batch, text, text_b, quote_a, quote_b, work_relation, work_ids` -- exactly `duplicate_candidate.schema.json`'s shape after Task 4 extends it); `judge_rates(judgments: pd.DataFrame) -> dict` (`abstention_rate`, `quote_rejection_rate`, `pairs_total`).

- [ ] **Step 1: Write the failing tests**

Create `05-App/pipeline/tests/duplicates/test_judged_candidates.py`:

```python
"""Phase 1 Stage D-lite: judged same_asset_same_place pairs -> work-level review candidates."""

from __future__ import annotations

import pandas as pd
import pytest
from nidhinetra_pipeline.duplicates.judged_candidates import (
    CONTINUATION_MARKERS_V1,
    DERIVATION_VERSION,
    DISCRIMINATING_STOPLIST_V1,
    STORE_FINDER,
    build_judged_candidates,
    is_discriminating,
    judge_rates,
)


def _group(scope, fingerprint, text, work_ids, *, amount=500_000.0, sanction_date="2024-07-01"):
    return {
        "scope": scope,
        "text_fingerprint": fingerprint,
        "text": text,
        "work_ids": work_ids,
        "work_count": len(work_ids),
        "amount_total_inr": amount,
        "sanction_date_first": sanction_date,
    }


def _artifact(groups: dict) -> dict:
    return {"groups": groups}


def _judgment_row(scope, fp_a, fp_b, *, status="judged", relation="same_asset_same_place",
                   place_a="Kheda Chowk", place_b="Kheda Chowk"):
    return {
        "scope": scope,
        "fingerprint_a": fp_a,
        "fingerprint_b": fp_b,
        "status": status,
        "relation": relation,
        "place_a": place_a,
        "place_b": place_b,
    }


FP_A, FP_B = "a" * 16, "b" * 16


def test_duplicate_candidate_when_close_in_date_and_amount():
    groups = {
        "g1": _group("C1", FP_A, "Shed at Kheda Chowk", ["W1"], amount=500_000.0, sanction_date="2024-07-01"),
        "g2": _group("C1", FP_B, "Shed near Kheda Chowk", ["W2"], amount=520_000.0, sanction_date="2024-07-31"),
    }
    judgments = pd.DataFrame([_judgment_row("C1", FP_A, FP_B)])

    [candidate] = build_judged_candidates(_artifact(groups), judgments)

    assert candidate["finder"] == STORE_FINDER
    assert candidate["finder_version"] == DERIVATION_VERSION
    assert candidate["work_relation"] == "duplicate_candidate"
    assert candidate["threshold_crossing_batch"] is False
    assert candidate["text"] == "Shed at Kheda Chowk"
    assert candidate["text_b"] == "Shed near Kheda Chowk"
    assert candidate["quote_a"] == "Kheda Chowk"
    assert candidate["quote_b"] == "Kheda Chowk"
    assert candidate["work_ids"] == ["W1", "W2"]


def test_split_or_phase_when_date_gap_exceeds_one_year():
    groups = {
        "g1": _group("C1", FP_A, "Shed at Kheda Chowk", ["W1"], sanction_date="2022-01-01"),
        "g2": _group("C1", FP_B, "Shed near Kheda Chowk", ["W2"], sanction_date="2024-07-31"),
    }
    judgments = pd.DataFrame([_judgment_row("C1", FP_A, FP_B)])

    [candidate] = build_judged_candidates(_artifact(groups), judgments)

    assert candidate["work_relation"] == "split_or_phase_candidate"


def test_split_or_phase_when_amount_ratio_is_below_half():
    groups = {
        "g1": _group("C1", FP_A, "Shed at Kheda Chowk", ["W1"], amount=100_000.0),
        "g2": _group("C1", FP_B, "Shed near Kheda Chowk", ["W2"], amount=300_000.0),
    }
    judgments = pd.DataFrame([_judgment_row("C1", FP_A, FP_B)])

    [candidate] = build_judged_candidates(_artifact(groups), judgments)

    assert candidate["work_relation"] == "split_or_phase_candidate"


def test_split_or_phase_when_a_continuation_marker_is_present_even_if_date_and_amount_would_pass():
    groups = {
        "g1": _group("C1", FP_A, "Phase 2 shed at Kheda Chowk", ["W1"]),
        "g2": _group("C1", FP_B, "Shed near Kheda Chowk", ["W2"]),
    }
    judgments = pd.DataFrame([_judgment_row("C1", FP_A, FP_B)])

    [candidate] = build_judged_candidates(_artifact(groups), judgments)

    assert candidate["work_relation"] == "split_or_phase_candidate"


def test_split_or_phase_when_either_side_has_more_than_one_work():
    groups = {
        "g1": _group("C1", FP_A, "Shed at Kheda Chowk", ["W1", "W3"], amount=1_000_000.0),
        "g2": _group("C1", FP_B, "Shed near Kheda Chowk", ["W2"], amount=500_000.0),
    }
    judgments = pd.DataFrame([_judgment_row("C1", FP_A, FP_B)])

    [candidate] = build_judged_candidates(_artifact(groups), judgments)

    assert candidate["work_relation"] == "split_or_phase_candidate"
    assert candidate["work_ids"] == ["W1", "W2", "W3"]


def test_non_discriminating_place_quote_is_excluded():
    groups = {
        "g1": _group("C1", FP_A, "Shed at village", ["W1"]),
        "g2": _group("C1", FP_B, "Shed near village", ["W2"]),
    }
    judgments = pd.DataFrame(
        [_judgment_row("C1", FP_A, FP_B, place_a="village", place_b="village")]
    )

    assert build_judged_candidates(_artifact(groups), judgments) == []
    assert is_discriminating("village") is False
    assert is_discriminating("Village") is False
    assert is_discriminating("Shamshan Ghat") is False
    assert is_discriminating("Kheda Chowk") is True


@pytest.mark.parametrize(
    ("status", "relation"),
    [("rejected", None), ("judged", "same_asset_different_place")],
    ids=["rejected pair", "different relation"],
)
def test_only_judged_same_asset_same_place_rows_are_considered(status, relation):
    groups = {
        "g1": _group("C1", FP_A, "Shed at Kheda Chowk", ["W1"]),
        "g2": _group("C1", FP_B, "Shed near Kheda Chowk", ["W2"]),
    }
    judgments = pd.DataFrame([_judgment_row("C1", FP_A, FP_B, status=status, relation=relation)])

    assert build_judged_candidates(_artifact(groups), judgments) == []


def test_fingerprint_order_is_sorted_and_text_quotes_follow_their_own_side():
    zzzz, aaaa = "z" * 16, "a" * 16
    groups = {
        "g1": _group(zzzz[:0] or "C1", zzzz, "Shed at Kheda Chowk near Ram Mandir", ["W2"]),
        "g2": _group("C1", aaaa, "Shed at Kheda Chowk near Shiv Mandir", ["W1"]),
    }
    judgments = pd.DataFrame([_judgment_row("C1", zzzz, aaaa)])

    [candidate] = build_judged_candidates(_artifact(groups), judgments)

    assert candidate["fingerprint_a"] == aaaa
    assert candidate["fingerprint_b"] == zzzz
    assert candidate["text"] == "Shed at Kheda Chowk near Shiv Mandir"
    assert candidate["text_b"] == "Shed at Kheda Chowk near Ram Mandir"
    assert candidate["work_ids"] == ["W1", "W2"]


def test_judge_rates_uses_every_pair_asked_as_the_population():
    rows = (
        [("judged", "same_asset_same_place")]
        + [("judged", "not_enough_detail")] * 3
        + [("rejected", None)] * 2
        + [("judged", "unrelated")]
        + [("judged", "same_asset_different_place")] * 2
        + [("judged", "same_place_different_asset")]
    )
    judgments = pd.DataFrame(
        [_judgment_row("C1", FP_A, FP_B, status=s, relation=r) for s, r in rows]
    )

    assert judge_rates(judgments) == {
        "abstention_rate": 30.0,
        "quote_rejection_rate": 20.0,
        "pairs_total": 10,
    }


def test_judge_rates_is_zero_on_an_empty_frame():
    assert judge_rates(pd.DataFrame(columns=["status", "relation"])) == {
        "abstention_rate": 0.0,
        "quote_rejection_rate": 0.0,
        "pairs_total": 0,
    }


def test_frozen_constants_are_pinned():
    assert DERIVATION_VERSION == "work_candidate_derivation_v1"
    assert STORE_FINDER == "judged_same_asset_same_place"
    assert DISCRIMINATING_STOPLIST_V1 == frozenset(
        "village gram ward road school shamshan ghat community hall".split()
    )
    assert CONTINUATION_MARKERS_V1 == ("phase", "continuation", "continue", "remaining", "balance work")
```

- [ ] **Step 2: Run and watch it fail**

```bash
cd 05-App && . ~/.cache/nidhinetra-vm/env.sh && uv run --package nidhinetra-pipeline python -m pytest pipeline/tests/duplicates/test_judged_candidates.py -q
```
Expected: `ModuleNotFoundError: No module named 'nidhinetra_pipeline.duplicates.judged_candidates'`

- [ ] **Step 3: Write the module**

Create `05-App/pipeline/src/nidhinetra_pipeline/duplicates/judged_candidates.py`:

```python
"""Phase 1 Stage D-lite: judged same_asset_same_place pairs -> work-level review candidates.

Code, not AI (spec: "From a text answer to a work-level candidate (code, not AI)"). Every input
row here is already judged and already quote-verified: nidhinetra_pipeline.judge.verify rejected
any answer whose quotes are not literally present in their own text, and, for a same_asset_same_place
or same_place_different_asset answer, whose place quotes do not canonically match on both sides
(nidhinetra_pipeline.duplicates.candidates.canonical_description_v1). A rejected answer never
reaches status "judged", so a judged same_asset_same_place row here always has a non-null,
canonically-matching place_a/place_b -- this module trusts that and does not re-check it.

Two things this module adds on top of that:

1. The discriminating-fact filter (DISCRIMINATING_STOPLIST_V1): a place quote made only of generic
   words ("Shamshan Ghat", a cremation ground, with no village or ward attached) is not enough to
   send an officer anywhere -- see the Stage B trial's GURDASPUR case,
   docs/superpowers/plans/2026-09-22-phase-1-stage-b-pair-judge.md.
2. work_candidate_derivation_v1, exactly as frozen in
   docs/superpowers/specs/2026-09-17-foundation-and-duplicate-works-design.md ("From a text answer
   to a work-level candidate"). A text pair whose either side already groups more than one
   identically-worded work is labelled split_or_phase_candidate without inventing a per-work-pair
   date/amount comparison the frozen rule does not define for a group (see the Stage D-lite plan's
   Decision D2 on why, and the measured count this affects).
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

import pandas as pd

from .candidates import canonical_description_v1

DERIVATION_VERSION = "work_candidate_derivation_v1"
STORE_FINDER = "judged_same_asset_same_place"

# The Stage D-lite plan's own frozen list (Decision D3). Stage D may widen this from measured
# review-queue noise; any change is a new version name.
DISCRIMINATING_STOPLIST_V1 = frozenset(
    "village gram ward road school shamshan ghat community hall".split()
)

# Spec, verbatim ("From a text answer to a work-level candidate").
CONTINUATION_MARKERS_V1 = ("phase", "continuation", "continue", "remaining", "balance work")


def is_discriminating(place_quote: str) -> bool:
    """True when the quoted place/institution has at least one token that is not in the frozen,
    generic stoplist. place_a and place_b are already guaranteed to canonically match by
    nidhinetra_pipeline.judge.verify.check_answer, so checking either side's quote is equivalent;
    this checks the one it is given.
    """
    tokens = canonical_description_v1(place_quote).split()
    return any(token not in DISCRIMINATING_STOPLIST_V1 for token in tokens)


def _has_continuation_marker(text_a: str, text_b: str) -> bool:
    canonical_a = canonical_description_v1(text_a)
    canonical_b = canonical_description_v1(text_b)
    return any(marker in canonical_a or marker in canonical_b for marker in CONTINUATION_MARKERS_V1)


def _work_relation(
    group_a: dict[str, Any], group_b: dict[str, Any]
) -> Literal["duplicate_candidate", "split_or_phase_candidate"]:
    """work_candidate_derivation_v1, applied to a judged same_asset_same_place pair's two text
    groups (see the module docstring and the plan's Decision D2 for the multi-work case)."""
    if _has_continuation_marker(group_a["text"], group_b["text"]):
        return "split_or_phase_candidate"
    if group_a["work_count"] != 1 or group_b["work_count"] != 1:
        return "split_or_phase_candidate"
    date_a, date_b = group_a["sanction_date_first"], group_b["sanction_date_first"]
    amount_a, amount_b = group_a["amount_total_inr"], group_b["amount_total_inr"]
    if not date_a or not date_b or not amount_a or not amount_b:
        return "split_or_phase_candidate"
    gap_days = abs((date.fromisoformat(date_a) - date.fromisoformat(date_b)).days)
    ratio = min(amount_a, amount_b) / max(amount_a, amount_b)
    if gap_days <= 365 and ratio >= 0.5:
        return "duplicate_candidate"
    return "split_or_phase_candidate"


def build_judged_candidates(
    artifact: dict[str, Any], judgments: pd.DataFrame
) -> list[dict[str, Any]]:
    """One review-store candidate per judged same_asset_same_place pair whose place quote is
    discriminating. fingerprint_a/fingerprint_b are sorted here (matching
    outcomes.duplicate_store's own sort of every candidate it stores), with text/quote swapped
    along with them, so the store's later re-sort of an already-sorted pair is a no-op.
    """
    groups_by_scope_fp = {
        (group["scope"], group["text_fingerprint"]): group for group in artifact["groups"].values()
    }
    same_asset_same_place = judgments[
        (judgments["status"] == "judged") & (judgments["relation"] == "same_asset_same_place")
    ]
    candidates = []
    for row in same_asset_same_place.itertuples():
        if not is_discriminating(row.place_a):
            continue
        fingerprint_a, fingerprint_b = row.fingerprint_a, row.fingerprint_b
        quote_a, quote_b = row.place_a, row.place_b
        group_a = groups_by_scope_fp[(row.scope, fingerprint_a)]
        group_b = groups_by_scope_fp[(row.scope, fingerprint_b)]
        if fingerprint_a > fingerprint_b:
            fingerprint_a, fingerprint_b = fingerprint_b, fingerprint_a
            quote_a, quote_b = quote_b, quote_a
            group_a, group_b = group_b, group_a
        candidates.append(
            {
                "finder": STORE_FINDER,
                "scope": row.scope,
                "fingerprint_a": fingerprint_a,
                "fingerprint_b": fingerprint_b,
                "finder_version": DERIVATION_VERSION,
                "threshold_crossing_batch": False,
                "text": group_a["text"],
                "text_b": group_b["text"],
                "quote_a": quote_a,
                "quote_b": quote_b,
                "work_relation": _work_relation(group_a, group_b),
                "work_ids": sorted(set(group_a["work_ids"]) | set(group_b["work_ids"])),
            }
        )
    return candidates


def judge_rates(judgments: pd.DataFrame) -> dict[str, float]:
    """The two rates the spec allows reporting: abstention and quote-rejection, both of every
    pair asked -- never of judged pairs only, and never an agreement or accuracy figure (there is
    no two-model reference in Stage D-lite)."""
    total = len(judgments)
    if total == 0:
        return {"abstention_rate": 0.0, "quote_rejection_rate": 0.0, "pairs_total": 0}
    rejected = int((judgments["status"] == "rejected").sum())
    abstained = int(
        ((judgments["status"] == "judged") & (judgments["relation"] == "not_enough_detail")).sum()
    )
    return {
        "abstention_rate": round(100 * abstained / total, 1),
        "quote_rejection_rate": round(100 * rejected / total, 1),
        "pairs_total": total,
    }


__all__ = [
    "CONTINUATION_MARKERS_V1",
    "DERIVATION_VERSION",
    "DISCRIMINATING_STOPLIST_V1",
    "STORE_FINDER",
    "build_judged_candidates",
    "is_discriminating",
    "judge_rates",
]
```

Note on the test file's `test_fingerprint_order_is_sorted_and_text_quotes_follow_their_own_side`: the `zzzz[:0] or "C1"` expression is just `"C1"` (a leftover-safe way to keep the line from looking like a copy-paste mistake); write it as plain `"C1"` if preferred -- either is correct, since `zzzz[:0]` is always `""`, which is falsy.

- [ ] **Step 4: Run and watch it pass**

```bash
cd 05-App && uv run --package nidhinetra-pipeline python -m pytest pipeline/tests/duplicates/test_judged_candidates.py -v
```
Expected: all 11 tests pass.

- [ ] **Step 5: Full pipeline suite and lint**

```bash
cd 05-App && uv run --package nidhinetra-pipeline python -m pytest pipeline/tests -q -p no:cacheprovider
uvx ruff check pipeline/src/nidhinetra_pipeline/duplicates/judged_candidates.py pipeline/tests/duplicates/test_judged_candidates.py
uvx ruff format --check pipeline/src/nidhinetra_pipeline/duplicates/judged_candidates.py pipeline/tests/duplicates/test_judged_candidates.py
```
Expected: full suite passes (11 more than Task 2's count); ruff clean.

- [ ] **Step 6: Commit**

```bash
cd /media/psf/project/SIH
git add 05-App/pipeline/src/nidhinetra_pipeline/duplicates/judged_candidates.py 05-App/pipeline/tests/duplicates/test_judged_candidates.py
GIT_AUTHOR_NAME="Krish Potanwar" GIT_AUTHOR_EMAIL=kpotanwar@gmail.com GIT_COMMITTER_NAME="Krish Potanwar" GIT_COMMITTER_EMAIL=kpotanwar@gmail.com \
git commit -m "feat(pipeline): judged near-copy pairs into work-level candidates, code not AI (T12B.3)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

## Task 4: Extend the Stage C contracts and the review store

**Files:**
- Modify: `05-App/contracts/duplicate_candidate.schema.json`
- Modify: `05-App/pipeline/src/nidhinetra_pipeline/outcomes/duplicate_store.py`
- Modify: `05-App/pipeline/tests/outcomes/test_duplicate_store.py`
- Modify: `05-App/contracts/validate.py`

**Interfaces:**
- Consumes: Task 3's candidate dict shape.
- Produces: `duplicate_candidate.schema.json` accepts `finder: "judged_same_asset_same_place"` with optional `text_b`, `quote_a`, `quote_b`, `work_relation`; `duplicate_store.duplicate_context(work_id)` includes those four keys only on a candidate that has them (identical-batch rows are unchanged).

- [ ] **Step 1: Extend the schema**

In `05-App/contracts/duplicate_candidate.schema.json`, change the `finder` property and add four new optional properties (leave `required` unchanged -- these four stay optional):

```json
    "finder": {
      "type": "string",
      "enum": ["identical_batch", "district_identical_batch", "judged_same_asset_same_place"]
    },
```

Add after `"text"`'s definition and before `"work_ids"`:

```json
    "text_b": {
      "type": "string",
      "minLength": 1,
      "description": "The second side's description, as published, spacing tidied. Present only for a judged_same_asset_same_place candidate; identical_batch and district_identical_batch candidates have one shared text and omit this."
    },
    "quote_a": {
      "type": "string",
      "minLength": 1,
      "description": "The place or institution words the judge quoted from text (side A), exactly as quoted. Present only for a judged_same_asset_same_place candidate."
    },
    "quote_b": {
      "type": "string",
      "minLength": 1,
      "description": "The place or institution words the judge quoted from text_b (side B), exactly as quoted. Present only for a judged_same_asset_same_place candidate."
    },
    "work_relation": {
      "type": "string",
      "enum": ["duplicate_candidate", "split_or_phase_candidate"],
      "description": "work_candidate_derivation_v1's label for this pair. An internal classification, never shown to an officer as this literal string -- both values reach the same review queue and neither is a verdict. Present only for a judged_same_asset_same_place candidate."
    },
```

- [ ] **Step 2: Check the schema is still valid Draft-07**

```bash
cd 05-App && . ~/.cache/nidhinetra-vm/env.sh && uv run --package nidhinetra-pipeline python -c "
import json, jsonschema
schema = json.loads(open('contracts/duplicate_candidate.schema.json').read())
jsonschema.Draft7Validator.check_schema(schema)
print('ok')
"
```
Expected: `ok`

- [ ] **Step 3: Write the failing store test**

Add to `05-App/pipeline/tests/outcomes/test_duplicate_store.py` (after the existing
`test_duplicate_context_summarizes_without_the_work_itself`; do not modify that test):

```python
def test_duplicate_context_includes_the_near_copy_fields_only_when_present(db_path: Path) -> None:
    identical, judged = (
        _candidate("C1", "1111111111111111"),
        {
            "finder": "judged_same_asset_same_place",
            "scope": "C2",
            "fingerprint_a": "2222222222222222",
            "fingerprint_b": "3333333333333333",
            "finder_version": "work_candidate_derivation_v1",
            "threshold_crossing_batch": False,
            "text": "Shed at Kheda Chowk",
            "text_b": "Shed near Kheda Chowk",
            "quote_a": "Kheda Chowk",
            "quote_b": "Kheda Chowk",
            "work_relation": "duplicate_candidate",
            "work_ids": ["W3", "W4"],
        },
    )
    duplicate_store.upsert_candidates([identical, judged], db_path=db_path)

    identical_context = duplicate_store.duplicate_context("W1", db_path=db_path)[0]
    judged_context = duplicate_store.duplicate_context("W3", db_path=db_path)[0]

    assert "text_b" not in identical_context
    assert "work_relation" not in identical_context
    assert judged_context["text_b"] == "Shed near Kheda Chowk"
    assert judged_context["quote_a"] == "Kheda Chowk"
    assert judged_context["quote_b"] == "Kheda Chowk"
    assert judged_context["work_relation"] == "duplicate_candidate"
    assert judged_context["other_work_ids"] == ["W4"]
```

- [ ] **Step 4: Run and watch it fail**

```bash
cd 05-App && uv run --package nidhinetra-pipeline python -m pytest pipeline/tests/outcomes/test_duplicate_store.py -q -k near_copy_fields
```
Expected: fails, either on `upsert_candidates` (schema now accepts the shape but the table has no matching columns yet) or on the `duplicate_context` assertions -- `sqlite3.OperationalError: table duplicate_candidates has no column named text_b`.

- [ ] **Step 5: Migrate the table and thread the new columns through**

In `05-App/pipeline/src/nidhinetra_pipeline/outcomes/duplicate_store.py`:

Change the `CREATE TABLE IF NOT EXISTS duplicate_candidates` block inside `init_db()`'s `executescript` (add `text_b`, `quote_a`, `quote_b`, `work_relation` right after `text TEXT NOT NULL,` and before `work_ids TEXT NOT NULL,`):

```python
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
```

Change `init_db()`'s ending from:

```python
        )
        connection.commit()
```

to:

```python
        )
        _migrate_judged_columns(connection)
        connection.commit()
```

Add this new function right after `init_db()`:

```python
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
```

Change `upsert_candidates()`'s `executemany` call from:

```python
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
```

to:

```python
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
```

Change `_RESOLVED_CANDIDATES_CTE`'s inner `SELECT` (the `resolved_candidates AS (...)` block) from:

```python
        candidate.threshold_crossing_batch,
        candidate.text,
        candidate.work_ids,
```

to:

```python
        candidate.threshold_crossing_batch,
        candidate.text,
        candidate.text_b,
        candidate.quote_a,
        candidate.quote_b,
        candidate.work_relation,
        candidate.work_ids,
```

Change `_RESOLVED_COLUMNS` from:

```python
_RESOLVED_COLUMNS = """
candidate_id, finder, scope, fingerprint_a, fingerprint_b, finder_version,
threshold_crossing_batch, text, work_ids, current_status, review_id, review_status,
reviewed_by, reviewed_at, reviewer_note, supersedes
"""
```

to:

```python
_RESOLVED_COLUMNS = """
candidate_id, finder, scope, fingerprint_a, fingerprint_b, finder_version,
threshold_crossing_batch, text, text_b, quote_a, quote_b, work_relation, work_ids,
current_status, review_id, review_status, reviewed_by, reviewed_at, reviewer_note, supersedes
"""
```

Change `_resolved_candidate()` from:

```python
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
```

to:

```python
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
```

Change `duplicate_context()` from:

```python
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
```

to:

```python
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
```

- [ ] **Step 6: Run and watch it pass**

```bash
cd 05-App && uv run --package nidhinetra-pipeline python -m pytest pipeline/tests/outcomes/test_duplicate_store.py -v
```
Expected: all pass, including the unmodified `test_duplicate_context_summarizes_without_the_work_itself` (its exact `==` dict still has exactly 7 keys, because `text_b` is `None` for that identical-batch row).

- [ ] **Step 7: Add validate.py's Self-test 13**

In `05-App/contracts/validate.py`, insert this block right after Self-test 12's `print(f"  PASS: ...")` line (before `print("\nAll self-tests passed. The validator has real teeth.")`), reusing `candidate_schema` already loaded by Self-test 6 earlier in the same function:

```python
    print("\nSelf-test 13: duplicate_candidate.schema.json accepts a judged near-copy candidate ...")
    good_judged = {
        "finder": "judged_same_asset_same_place",
        "scope": "C1",
        "fingerprint_a": "1111111111111111",
        "fingerprint_b": "2222222222222222",
        "finder_version": "work_candidate_derivation_v1",
        "threshold_crossing_batch": False,
        "text": "Shed at Kheda Chowk",
        "text_b": "Shed near Kheda Chowk",
        "quote_a": "Kheda Chowk",
        "quote_b": "Kheda Chowk",
        "work_relation": "duplicate_candidate",
        "work_ids": ["W1", "W2"],
    }
    judged_errors = list(jsonschema.Draft7Validator(candidate_schema).iter_errors(good_judged))
    if judged_errors:
        print(f"  FAIL: a well-formed judged candidate was rejected: {judged_errors[0].message}")
        return 1
    broken_judged = {**good_judged, "work_relation": "maybe"}
    broken_judged_errors = list(
        jsonschema.Draft7Validator(candidate_schema).iter_errors(broken_judged)
    )
    if not broken_judged_errors:
        print("  FAIL: validator did not catch an unknown work_relation")
        return 1
    print(f"  PASS: caught {len(broken_judged_errors)} error(s) on an unknown work_relation")
```

- [ ] **Step 8: Run validate.py and the whole pipeline suite; lint**

```bash
cd 05-App && uv run --package nidhinetra-pipeline python contracts/validate.py && uv run --package nidhinetra-pipeline python contracts/validate.py --self-test
uv run --package nidhinetra-pipeline python -m pytest pipeline/tests -q -p no:cacheprovider
uvx ruff check contracts/validate.py pipeline/src/nidhinetra_pipeline/outcomes/duplicate_store.py pipeline/tests/outcomes/test_duplicate_store.py
uvx ruff format --check contracts/validate.py pipeline/src/nidhinetra_pipeline/outcomes/duplicate_store.py pipeline/tests/outcomes/test_duplicate_store.py
```
Expected: `All self-tests passed. The validator has real teeth.`; full pipeline suite passes (one more test than Task 3's count); ruff clean.

- [ ] **Step 9: Commit**

```bash
cd /media/psf/project/SIH
git add 05-App/contracts/duplicate_candidate.schema.json 05-App/contracts/validate.py 05-App/pipeline/src/nidhinetra_pipeline/outcomes/duplicate_store.py 05-App/pipeline/tests/outcomes/test_duplicate_store.py
GIT_AUTHOR_NAME="Krish Potanwar" GIT_AUTHOR_EMAIL=kpotanwar@gmail.com GIT_COMMITTER_NAME="Krish Potanwar" GIT_COMMITTER_EMAIL=kpotanwar@gmail.com \
git commit -m "feat(outcomes): store a judged near-copy candidate's second text and quotes (T12B.4)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

## Task 5: Wire the sync and the judge's rates into the API

**Files:**
- Modify: `05-App/api/src/nidhinetra_api/db.py`
- Modify: `05-App/api/src/nidhinetra_api/routers/duplicates.py`
- Modify: `05-App/api/src/nidhinetra_api/main.py`
- Modify: `05-App/api/tests/test_duplicates.py`

**Interfaces:**
- Consumes: `build_judged_candidates`, `judge_rates` (Task 3); `duplicate_store.upsert_candidates` (Task 4).
- Produces: `sync_judged_candidates_from_judgments(snapshot_dir=None, judgments_dir=None) -> int`; `GET /api/duplicates`'s `meta` gains `judge_abstention_rate`, `judge_quote_rejection_rate`, `judge_pairs_total` (each `None` until a judgments file exists).

- [ ] **Step 1: Add the judgments directory constant**

In `05-App/api/src/nidhinetra_api/db.py`, right after `SNAPSHOT_DIR = _APP_ROOT / "data" / "snapshot"`, add:

```python
JUDGMENTS_DIR = _APP_ROOT / "data" / "judgments"
```

- [ ] **Step 2: Write the failing API tests**

Add `import pandas as pd` to `05-App/api/tests/test_duplicates.py`'s imports (alphabetical position, before the `pytest` import), then add:

```python
def _judgments_frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_sync_judged_candidates_upserts_and_is_safe_when_either_file_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshot_dir = tmp_path / "snapshot"
    judgments_dir = tmp_path / "judgments"
    snapshot_dir.mkdir()
    judgments_dir.mkdir()
    monkeypatch.setattr(duplicates.db, "SNAPSHOT_DIR", snapshot_dir)
    monkeypatch.setattr(duplicates.db, "JUDGMENTS_DIR", judgments_dir)

    assert duplicates.sync_judged_candidates_from_judgments() == 0

    artifact = {
        "groups": {
            "g1": {
                "scope": "C1",
                "text_fingerprint": "1111111111111111",
                "text": "Shed at Kheda Chowk",
                "work_ids": ["MPLADS-FX-0001"],
                "work_count": 1,
                "amount_total_inr": 500000.0,
                "sanction_date_first": "2024-07-01",
            },
            "g2": {
                "scope": "C1",
                "text_fingerprint": "2222222222222222",
                "text": "Shed near Kheda Chowk",
                "work_ids": ["MPLADS-FX-0002"],
                "work_count": 1,
                "amount_total_inr": 520000.0,
                "sanction_date_first": "2024-07-20",
            },
        }
    }
    (snapshot_dir / "duplicate_candidates.json").write_text(json.dumps(artifact), encoding="utf-8")
    _judgments_frame(
        [
            {
                "scope": "C1",
                "fingerprint_a": "1111111111111111",
                "fingerprint_b": "2222222222222222",
                "status": "judged",
                "relation": "same_asset_same_place",
                "place_a": "Kheda Chowk",
                "place_b": "Kheda Chowk",
            }
        ]
    ).to_parquet(judgments_dir / "text_pair_judgments.parquet", index=False)

    assert duplicates.sync_judged_candidates_from_judgments() == 1
    rows, total = duplicate_store.list_candidates(status="pending")
    assert total == 1
    assert rows[0]["finder"] == "judged_same_asset_same_place"
    assert rows[0]["work_relation"] == "duplicate_candidate"


def test_list_duplicates_reports_the_judges_rates(
    duplicates_client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    judgments_dir = tmp_path / "judgments"
    judgments_dir.mkdir()
    monkeypatch.setattr(duplicates.db, "JUDGMENTS_DIR", judgments_dir)
    _judgments_frame(
        [{"status": "judged", "relation": "not_enough_detail"}] * 3
        + [{"status": "rejected", "relation": None}] * 2
        + [{"status": "judged", "relation": "unrelated"}] * 5
    ).to_parquet(judgments_dir / "text_pair_judgments.parquet", index=False)

    body = duplicates_client.get("/api/duplicates").json()

    assert body["meta"]["judge_abstention_rate"] == 30.0
    assert body["meta"]["judge_quote_rejection_rate"] == 20.0
    assert body["meta"]["judge_pairs_total"] == 10


def test_list_duplicates_rates_are_null_without_a_judgments_file(
    duplicates_client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(duplicates.db, "JUDGMENTS_DIR", tmp_path / "no-judgments-here")

    body = duplicates_client.get("/api/duplicates").json()

    assert body["meta"]["judge_abstention_rate"] is None
    assert body["meta"]["judge_quote_rejection_rate"] is None
    assert body["meta"]["judge_pairs_total"] is None
```

- [ ] **Step 3: Run and watch it fail**

```bash
cd 05-App && . ~/.cache/nidhinetra-vm/env.sh && uv run --package nidhinetra-api python -m pytest api/tests/test_duplicates.py -q
```
Expected: `AttributeError: module 'nidhinetra_api.routers.duplicates' has no attribute 'sync_judged_candidates_from_judgments'` (and, once that exists, a `KeyError`/`AssertionError` on the new `meta` keys until Step 4's endpoint change lands).

- [ ] **Step 4: Add the sync function and the rates to the endpoint**

In `05-App/api/src/nidhinetra_api/routers/duplicates.py`, add to the imports:

```python
from nidhinetra_pipeline.duplicates.judged_candidates import build_judged_candidates
from nidhinetra_pipeline.duplicates.judged_candidates import judge_rates as compute_judge_rates
from nidhinetra_pipeline.judge import store as judge_store
```

Add this function right after `sync_duplicate_candidates_from_snapshot`:

```python
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
```

Change `list_duplicates`'s `Envelope(...)` return from:

```python
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
```

to:

```python
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
```

Add `"sync_judged_candidates_from_judgments"` to the module's `__all__` list, alphabetically.

In `05-App/api/src/nidhinetra_api/main.py`, change:

```python
    entity_aliases.sync_alias_candidates_from_snapshot()
    duplicates.sync_duplicate_candidates_from_snapshot()
    yield
```

to:

```python
    entity_aliases.sync_alias_candidates_from_snapshot()
    duplicates.sync_duplicate_candidates_from_snapshot()
    duplicates.sync_judged_candidates_from_judgments()
    yield
```

- [ ] **Step 5: Run and watch it pass**

```bash
cd 05-App && uv run --package nidhinetra-api python -m pytest api/tests/test_duplicates.py -v
```
Expected: all pass, including the pre-existing tests (the session snapshot has no `duplicate_candidates.json`, so `sync_judged_candidates_from_judgments()` in `main.py`'s lifespan is a no-op for the whole suite, same as its sibling already is).

- [ ] **Step 6: Full API suite and lint**

```bash
cd 05-App && uv run --package nidhinetra-api python -m pytest api/tests -q -p no:cacheprovider
uvx ruff check api/src/nidhinetra_api/db.py api/src/nidhinetra_api/main.py api/src/nidhinetra_api/routers/duplicates.py api/tests/test_duplicates.py
uvx ruff format --check api/src/nidhinetra_api/db.py api/src/nidhinetra_api/main.py api/src/nidhinetra_api/routers/duplicates.py api/tests/test_duplicates.py
```
Expected: full API suite passes (three more tests than the pre-Task-5 baseline); ruff clean.

- [ ] **Step 7: Self-check against the real, committed data, in a scratch store**

```bash
cd 05-App && SCRATCH=$(mktemp -d) && uv run --package nidhinetra-pipeline python - "$SCRATCH" <<'PY'
import sys
from pathlib import Path

from nidhinetra_api.routers import duplicates
from nidhinetra_pipeline.outcomes import duplicate_store

scratch = Path(sys.argv[1])
duplicate_store.DEFAULT_DB_PATH = scratch / "outcomes.db"

count = duplicates.sync_judged_candidates_from_judgments(
    snapshot_dir=Path("data/snapshot"), judgments_dir=Path("data/judgments")
)
print("synced", count)

rows, total = duplicate_store.list_candidates(status=None, page_size=5000)
by_relation = {}
for row in rows:
    by_relation[row["work_relation"]] = by_relation.get(row["work_relation"], 0) + 1
print("total in store:", total)
print("by work_relation:", by_relation)
assert count == 1265, count
assert total == 1265, total
assert by_relation == {"duplicate_candidate": 1103, "split_or_phase_candidate": 162}, by_relation
print("matches the plan's self-check numbers: OK")
PY
)
git status --porcelain -- 05-App/data
```
Expected: `synced 1265`, `total in store: 1265`, `by work_relation: {'duplicate_candidate': 1103, 'split_or_phase_candidate': 162}`, `matches the plan's self-check numbers: OK`, and an empty `git status` for `05-App/data` (this touches only the scratch temp directory). If any number differs from the plan's Decisions/self-check table, STOP and report the discrepancy rather than editing the plan's stated numbers to match.

- [ ] **Step 8: Commit**

```bash
cd /media/psf/project/SIH
git add 05-App/api/src/nidhinetra_api/db.py 05-App/api/src/nidhinetra_api/main.py 05-App/api/src/nidhinetra_api/routers/duplicates.py 05-App/api/tests/test_duplicates.py
GIT_AUTHOR_NAME="Krish Potanwar" GIT_AUTHOR_EMAIL=kpotanwar@gmail.com GIT_COMMITTER_NAME="Krish Potanwar" GIT_COMMITTER_EMAIL=kpotanwar@gmail.com \
git commit -m "feat(api): sync judged near-copy candidates and report the judge's rates (T12B.5)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

## Task 6: Web -- the queue label, both quoted spans, and honest copy

**Files:**
- Modify: `05-App/contracts/strings.json`
- Modify: `05-App/web/lib/duplicates.ts`
- Modify: `05-App/web/components/inspection-list/DuplicateReviewQueue.tsx`
- Modify: `05-App/web/components/inspection-list/DuplicateReviewQueue.test.tsx`
- Modify: `05-App/web/components/detail-panel/DetailPanel.tsx`
- Modify: `05-App/web/components/detail-panel/DetailPanel.test.tsx`

**Interfaces:**
- Consumes: the API's `meta.judge_abstention_rate` / `judge_quote_rejection_rate` / `judge_pairs_total` (Task 5); a candidate/context row's `finder`, `text_b`, `quote_a`, `quote_b`, `work_relation` (Task 4).
- Produces: no new exported functions; `DuplicateCandidatePage` gains `judgeAbstentionRate`, `judgeQuoteRejectionRate`, `judgePairsTotal` (each `number | null`).

- [ ] **Step 1: strings.json -- soften two existing lines, add three new ones**

In `05-App/contracts/strings.json`'s `duplicate_review` block, change:

```json
  "body": "These works share the exact same portal description within one constituency. Check the works before recording a decision.",
```
to:
```json
  "body": "These works share the same or a closely matching portal description within one constituency. Check the works before recording a decision.",
```

and change:
```json
  "context_title": "Works with the same description",
```
to:
```json
  "context_title": "Works with the same or similar description",
```

Add these three keys at the end of the `duplicate_review` block (after `context_threshold`):

```json
  "judged_badge": "Near-identical descriptions, read by a model, quotes checked by code",
  "judged_quotes": "The words a model quoted from each description: “{quote_a}” and “{quote_b}”.",
  "judge_rates_note": "Of {total} near-identical description pairs a model read, {abstained_percent} were left unclear and {rejected_percent} had a quoted word rejected by code."
```

Add one `_meta.amendment_log` line (after the existing 2026-09-26 (T2) line):

```json
      "2026-09-26 (T12B): duplicate_review widened for Stage D-lite's judged near-copy candidates -- judged_badge, judged_quotes and judge_rates_note added; body and context_title softened from 'the same'/'exact same' to 'the same or similar' now that the queue and the detail panel's shared-description section also show near-copy pairs, not only identical batches.",
```

- [ ] **Step 2: Run validate.py's lint (still pipeline-side, quick to check before touching web code)**

```bash
cd 05-App && uv run --package nidhinetra-pipeline python contracts/validate.py
```
Expected: no lint failures reported (self-test-level lint checks run under `--self-test`; this plain run re-validates the fixtures/schemas -- run `--self-test` too as a fuller check before Step 8's full gates):

```bash
cd 05-App && uv run --package nidhinetra-pipeline python contracts/validate.py --self-test
```
Expected: `All self-tests passed. The validator has real teeth.` (Self-test 8 covers the real `strings.json` lint.)

- [ ] **Step 3: Extend the TypeScript types and the fetch function**

In `05-App/web/lib/duplicates.ts`, change:

```ts
export type DuplicateFinder = "identical_batch" | "district_identical_batch";
```
to:
```ts
export type DuplicateFinder =
  | "identical_batch"
  | "district_identical_batch"
  | "judged_same_asset_same_place";
```

Change `DuplicateCandidateRecord` from:

```ts
export interface DuplicateCandidateRecord {
  candidate_id: number;
  finder: DuplicateFinder;
  scope: string;
  threshold_crossing_batch: boolean;
  text: string;
  work_ids: string[];
  status: DuplicateReviewStatus;
  current_review: DuplicateCurrentReview | null;
}
```
to:
```ts
export interface DuplicateCandidateRecord {
  candidate_id: number;
  finder: DuplicateFinder;
  scope: string;
  threshold_crossing_batch: boolean;
  text: string;
  text_b?: string;
  quote_a?: string;
  quote_b?: string;
  work_relation?: "duplicate_candidate" | "split_or_phase_candidate";
  work_ids: string[];
  status: DuplicateReviewStatus;
  current_review: DuplicateCurrentReview | null;
}
```

Change `DuplicateContextEntry` from:

```ts
export interface DuplicateContextEntry {
  candidate_id: number;
  finder: DuplicateFinder;
  threshold_crossing_batch: boolean;
  text: string;
  work_count: number;
  other_work_ids: string[];
  status: DuplicateReviewStatus;
}
```
to:
```ts
export interface DuplicateContextEntry {
  candidate_id: number;
  finder: DuplicateFinder;
  threshold_crossing_batch: boolean;
  text: string;
  text_b?: string;
  quote_a?: string;
  quote_b?: string;
  work_relation?: "duplicate_candidate" | "split_or_phase_candidate";
  work_count: number;
  other_work_ids: string[];
  status: DuplicateReviewStatus;
}
```

Change `DuplicateCandidatePage` from:

```ts
export interface DuplicateCandidatePage {
  rows: DuplicateCandidate[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}
```
to:
```ts
export interface DuplicateCandidatePage {
  rows: DuplicateCandidate[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  judgeAbstentionRate: number | null;
  judgeQuoteRejectionRate: number | null;
  judgePairsTotal: number | null;
}
```

Add, right after the existing `metaNumber` function:

```ts
function metaNullableNumber(meta: Record<string, unknown> | null, key: string): number | null {
  const value = meta?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}
```

Change `fetchDuplicateCandidates`'s return statement from:

```ts
  return {
    rows: result.data,
    page: metaNumber(result.meta, "page", page),
    pageSize: metaNumber(result.meta, "page_size", pageSize),
    total: metaNumber(result.meta, "total", result.data.length),
    totalPages: metaNumber(result.meta, "total_pages", result.data.length > 0 ? 1 : 0),
  };
```
to:
```ts
  return {
    rows: result.data,
    page: metaNumber(result.meta, "page", page),
    pageSize: metaNumber(result.meta, "page_size", pageSize),
    total: metaNumber(result.meta, "total", result.data.length),
    totalPages: metaNumber(result.meta, "total_pages", result.data.length > 0 ? 1 : 0),
    judgeAbstentionRate: metaNullableNumber(result.meta, "judge_abstention_rate"),
    judgeQuoteRejectionRate: metaNullableNumber(result.meta, "judge_quote_rejection_rate"),
    judgePairsTotal: metaNullableNumber(result.meta, "judge_pairs_total"),
  };
```

- [ ] **Step 4: Queue row -- the badge and the second description; queue header -- the rate note**

In `05-App/web/components/inspection-list/DuplicateReviewQueue.tsx`, add `formatPercent` to the existing `format` import:

```tsx
import { displayName, formatIndianInt, formatPercent } from "@/lib/format";
```

In the component body, right after `const result = queue.data;`, add nothing new (the rate fields are already on `result` via Step 3's type). In the `<header>`, right after the existing `<p className={styles.body}>{s.body}</p>` line, add:

```tsx
            {result && result.judgePairsTotal !== null && (
              <p className={styles.body}>
                {renderTemplate(s.judge_rates_note, {
                  total: formatIndianInt(result.judgePairsTotal),
                  abstained_percent: formatPercent(result.judgeAbstentionRate ?? 0),
                  rejected_percent: formatPercent(result.judgeQuoteRejectionRate ?? 0),
                })}
              </p>
            )}
```

In `DuplicateRow`, change:

```tsx
      <td>
        <span className={styles.text}>{displayName(candidate.text)}</span>
        <span className={styles.scope}>{displayName(candidate.scope)}</span>
        {candidate.threshold_crossing_batch && (
          <p className={styles.thresholdNote}>{s.threshold_note}</p>
        )}
      </td>
```
to:
```tsx
      <td>
        <span className={styles.text}>{displayName(candidate.text)}</span>
        {candidate.text_b && <span className={styles.text}>{displayName(candidate.text_b)}</span>}
        <span className={styles.scope}>{displayName(candidate.scope)}</span>
        {candidate.threshold_crossing_batch && (
          <p className={styles.thresholdNote}>{s.threshold_note}</p>
        )}
        {candidate.finder === "judged_same_asset_same_place" && (
          <p className={styles.thresholdNote}>{s.judged_badge}</p>
        )}
      </td>
```

- [ ] **Step 5: Write the failing queue test**

Add to `05-App/web/components/inspection-list/DuplicateReviewQueue.test.tsx`, after the existing `candidate` fixture:

```tsx
const judgedCandidate = {
  candidate_id: 20,
  finder: "judged_same_asset_same_place" as const,
  scope: "GURDASPUR",
  threshold_crossing_batch: false,
  text: "Shed at Kheda Chowk",
  text_b: "Shed near Kheda Chowk village",
  quote_a: "Kheda Chowk",
  quote_b: "Kheda Chowk",
  work_relation: "duplicate_candidate" as const,
  work_ids: ["W10", "W11"],
  status: "pending" as const,
  current_review: null,
  evidence_works: [],
};
```

and this test at the end of the `describe` block:

```tsx
  test("shows the judged badge, both descriptions, and the judge's rates for a near-copy candidate", async () => {
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(
      response([judgedCandidate], {
        page: 1,
        page_size: 25,
        total: 1,
        total_pages: 1,
        judge_abstention_rate: 5.8,
        judge_quote_rejection_rate: 6.3,
        judge_pairs_total: 39093,
      }),
    );

    render(<DuplicateReviewQueue />);

    await screen.findByText("Shed at Kheda Chowk");
    expect(screen.getByText("Shed near Kheda Chowk village")).toBeInTheDocument();
    expect(
      screen.getByText("Near-identical descriptions, read by a model, quotes checked by code"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Of 39,093 near-identical description pairs a model read, 6% were left unclear and 6% had a quoted word rejected by code.",
      ),
    ).toBeInTheDocument();
  });
```

- [ ] **Step 6: Detail panel -- both descriptions and the quoted spans**

In `05-App/web/components/detail-panel/DetailPanel.tsx`, change the `entries.map(...)` block inside `DuplicateContextSection` from:

```tsx
      {entries.map((entry) => (
        <div key={entry.candidate_id} className={styles.contribution}>
          <p className={styles.contributionHead}>{displayName(entry.text)}</p>
          <p className={styles.reason}>
            {renderTemplate(duplicateStrings.context_count, { count: entry.work_count - 1 })}
          </p>
          {entry.threshold_crossing_batch && (
            <p className={styles.note}>{duplicateStrings.context_threshold}</p>
          )}
          <ul className={styles.evidenceList}>
```
to:
```tsx
      {entries.map((entry) => (
        <div key={entry.candidate_id} className={styles.contribution}>
          <p className={styles.contributionHead}>{displayName(entry.text)}</p>
          {entry.text_b && <p className={styles.contributionHead}>{displayName(entry.text_b)}</p>}
          <p className={styles.reason}>
            {renderTemplate(duplicateStrings.context_count, { count: entry.work_count - 1 })}
          </p>
          {entry.threshold_crossing_batch && (
            <p className={styles.note}>{duplicateStrings.context_threshold}</p>
          )}
          {entry.quote_a && entry.quote_b && (
            <p className={styles.note}>
              {renderTemplate(duplicateStrings.judged_quotes, {
                quote_a: entry.quote_a,
                quote_b: entry.quote_b,
              })}
            </p>
          )}
          <ul className={styles.evidenceList}>
```

(the closing tags below this block are unchanged -- this replaces only the lines shown above, up to and including the pre-existing `<ul className={styles.evidenceList}>` line.)

- [ ] **Step 7: Write the failing detail-panel test**

Add to `05-App/web/components/detail-panel/DetailPanel.test.tsx`:

```tsx
test("shows both descriptions and the quoted spans for a near-copy shared-description entry", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        success: true,
        error: null,
        meta: null,
        data: {
          duplicate_context: [
            {
              candidate_id: 20,
              finder: "judged_same_asset_same_place",
              threshold_crossing_batch: false,
              text: "Shed at Kheda Chowk",
              text_b: "Shed near Kheda Chowk village",
              quote_a: "Kheda Chowk",
              quote_b: "Kheda Chowk",
              work_relation: "duplicate_candidate",
              work_count: 2,
              other_work_ids: ["MPLADS-FX-0099"],
              status: "pending",
            },
          ],
        },
      }),
    })),
  );

  render(<DetailPanel row={row()} onClose={() => {}} quotaN={10} />);

  expect(await screen.findByText("Shed at Kheda Chowk")).toBeInTheDocument();
  expect(screen.getByText("Shed near Kheda Chowk village")).toBeInTheDocument();
  expect(
    screen.getByText('The words a model quoted from each description: “Kheda Chowk” and “Kheda Chowk”.'),
  ).toBeInTheDocument();
});
```

- [ ] **Step 8: Full web gates**

```bash
web-gates npm run build
web-gates npx tsc --noEmit
web-gates npm run lint
web-gates npx vitest run
```
Expected: build/tsc/lint clean; vitest passes with two more tests than the pre-Task-6 baseline (one in `DuplicateReviewQueue.test.tsx`, one in `DetailPanel.test.tsx`), every pre-existing test in both files unchanged and still passing (each new field is optional/conditionally rendered, so a candidate/context object without `text_b`/`quote_a`/`quote_b` renders exactly as before).

- [ ] **Step 9: Commit**

```bash
cd /media/psf/project/SIH
git add 05-App/contracts/strings.json 05-App/web/lib/duplicates.ts 05-App/web/components/inspection-list/DuplicateReviewQueue.tsx 05-App/web/components/inspection-list/DuplicateReviewQueue.test.tsx 05-App/web/components/detail-panel/DetailPanel.tsx 05-App/web/components/detail-panel/DetailPanel.test.tsx
GIT_AUTHOR_NAME="Krish Potanwar" GIT_AUTHOR_EMAIL=kpotanwar@gmail.com GIT_COMMITTER_NAME="Krish Potanwar" GIT_COMMITTER_EMAIL=kpotanwar@gmail.com \
git commit -m "feat(web): judged near-copy candidates in the review queue and detail panel (T12B.6)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

## Done when

- `uv run --package nidhinetra-pipeline python -m pytest pipeline/tests -q` passes, 12 more tests than the pre-T12B baseline (1 in Task 2, 11 in Task 3, 1 in Task 4).
- `uv run --package nidhinetra-api python -m pytest api/tests -q` passes, 3 more tests than the pre-T12B baseline (Task 5).
- `uv run --package nidhinetra-pipeline python contracts/validate.py --self-test` prints `All self-tests passed. The validator has real teeth.` (Self-test 13 included).
- Web gates (`build`, `tsc --noEmit`, `lint`, `vitest run`) are clean, 2 more tests than the pre-T12B baseline.
- The real-data self-check (Task 5, Step 7) reproduces exactly: 1,265 synced candidates, 1,103 `duplicate_candidate`, 162 `split_or_phase_candidate`.
- `git status --short 05-App/data` is empty after every task except Task 1 (which commits the one intended data file).
- Six commits, each green on its own gates before the next task starts, each tagged `(T12B.N)`.
- No score, rank or flag changed anywhere (`scored.parquet` untouched by every task's `git status`).

## Not in this plan (parked additions)

- Per-work-pair enrichment for the 109 multi-work-side candidates (Decision D2) -- needs a `works.parquet` join Stage D-lite deliberately avoids.
- A preference rule for when more than one model/prompt version has judged the same pair (Decision D4) -- Stage D's real bake-off.
- Widening `DISCRIMINATING_STOPLIST_V1` from measured officer feedback (Decision D3).
- `duplicate_review.empty_body`'s wording ("New candidates appear when a data snapshot contains works sharing an identical description.") still names only the identical-batch path; not fixed here since it is only shown when the queue is empty, which becomes rarer once this plan ships. A one-line honesty fix for later.
- Hindi translation of the three new `duplicate_review` keys -- D9 means English is a correct fallback today; Task 11B's own full-translation pass picks these up.
- A CLI subcommand for this sync, a Reports-page rendering of the two rates, or any caching of `judge_rates()` -- none are asked for and the existing per-request read is fast enough at this file size (Decision D7).
