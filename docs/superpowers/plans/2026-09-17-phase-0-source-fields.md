# Phase 0: Source Fields Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Carry three values the MPLADS portal already publishes — the work's description, its activity type and its recommendation date — from the raw tiles through to the officer's screen, without changing any work's score, rank or flags.

**Architecture:** One contract change adds three required-but-nullable fields. The adapter fills them from the Sanctioned tile using helpers that already exist; `normalize.py` passes them through; `build_snapshot.py` needs no change because its Parquet columns come from the schema. The API lists columns explicitly, so it gains them there and in its header search. The detail panel shows the description under the existing title and the other two in the existing "Record as published" list.

**Tech Stack:** Python 3.13, `uv`, pytest, pandas/pyarrow, DuckDB, FastAPI, Next.js 16, React 19, vitest, jsdom 30, ruff, jsonschema.

**Spec:** `docs/superpowers/specs/2026-09-17-foundation-and-duplicate-works-design.md`

## Global Constraints

- **Never push.** Commit locally on `codex/finish-nidhinetra`. The user pushes after review; the live site must keep showing today's work.
- **No score change.** No work's `risk_score`, `inspection_rank`, `flags`, `why_flagged` or `peer_group` may move. Task 2 proves it.
- **Never rebuild `data/snapshot/`.** That is task T07 and is gated on the user's written go-ahead.
- All user-visible text lives in `05-App/contracts/strings.json`, with an `_meta.amendment_log` entry. Banned words (`lint.banned_literal`, `lint.banned_derived`) and the em dash are forbidden in UI copy. Never reformat that file with a JSON tool: it stores banned dashes as `\u` escapes on purpose.
- New contract fields are **required keys with nullable values**, following `vendor_name`. A missing key means the adapter broke; a null means the portal had no value.
- ruff: `line-length = 100`, rules `E,F,I,UP,B`. Run `uv run ruff format` before committing Python.
- Gates that must pass before each commit: `python3 contracts/validate.py`, `python3 contracts/validate.py --self-test`, `uv run pytest pipeline/tests api/tests -q`, and for web tasks `npx vitest run`, `npx tsc --noEmit`, `npx eslint <files>`.
- All paths below are relative to `05-App/` unless they start with `docs/`.

---

### Task 1: Three fields through the contract, adapter and normalizer

**Files:**
- Modify: `contracts/normalized_record.schema.json`
- Modify: `pipeline/src/nidhinetra_pipeline/ingest/mplads_adapter.py` (the `records.append({...})` block in `adapt()`)
- Modify: `pipeline/src/nidhinetra_pipeline/normalize/normalize.py` (`_REQUIRED_FIELDS`, `_map_one`)
- Modify: `contracts/fixtures/works.fixture.json` (20 rows)
- Test: `pipeline/tests/ingest/test_mplads_adapter.py`, `pipeline/tests/normalize/test_normalize.py`

**Interfaces:**
- Consumes: `_clean(value)`, `activity_of(activity_name)`, `_parse_ddmmmyyyy(value)` — all already in `mplads_adapter.py`.
- Produces: every normalized record gains `work_description: str | None`, `activity_name: str | None`, `recommendation_date: str | None` (ISO `YYYY-MM-DD`). Tasks 2 to 5 rely on those three names exactly.

- [ ] **Step 1: Write the failing adapter tests**

Append to `pipeline/tests/ingest/test_mplads_adapter.py`:

```python
def test_adapt_carries_description_activity_and_recommendation_date() -> None:
    sanctioned = [
        {
            "WORK_RECOMMENDATION_DTL_ID": 501,
            "STATE_NAME": "Bihar",
            "CONSTITUENCY": "ARARIA",
            "MP_NAME": "Test MP",
            "IDA_NAME": "ARARIA(DISTRICT PLANNING OFFICER ARARIA_IDA)",
            "ACTIVITY_NAME": "WS/\t MP418/2024-2025/133409-Construction of roads",
            "WORK_DESCRIPTION": "  PCC Road from\tRam house to Shyam house  ",
            "SANCTION_AMOUNT": "500000",
            "SANCTION_DATE": "09-Jul-2024",
            "RECOMMENDATION_DATE": "08-Jul-2024",
            "WORK_STAGE": "Work in Progress",
        }
    ]

    record = adapt(sanctioned, [], [], as_of=date(2026, 9, 4))[0]

    assert record["work_description"] == "PCC Road from Ram house to Shyam house"
    assert record["activity_name"] == "Construction of roads"
    assert record["recommendation_date"] == "2024-07-08"


def test_adapt_leaves_the_three_new_fields_null_when_the_portal_has_nothing() -> None:
    sanctioned = [
        {
            "WORK_RECOMMENDATION_DTL_ID": 502,
            "STATE_NAME": "Bihar",
            "CONSTITUENCY": "ARARIA",
            "MP_NAME": "Test MP",
            "IDA_NAME": "ARARIA(DISTRICT PLANNING OFFICER ARARIA_IDA)",
            "ACTIVITY_NAME": "",
            "WORK_DESCRIPTION": "   ",
            "SANCTION_AMOUNT": "500000",
            "SANCTION_DATE": "09-Jul-2024",
            "RECOMMENDATION_DATE": "",
            "WORK_STAGE": "Work in Progress",
        }
    ]

    record = adapt(sanctioned, [], [], as_of=date(2026, 9, 4))[0]

    assert record["work_description"] is None
    assert record["activity_name"] is None
    assert record["recommendation_date"] is None
```

If `adapt` and `date` are not already imported at the top of that file, add them:
`from datetime import date` and `from nidhinetra_pipeline.ingest.mplads_adapter import adapt`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd 05-App && uv run pytest pipeline/tests/ingest/test_mplads_adapter.py -q -k "three_new_fields or description_activity"`
Expected: FAIL with `KeyError: 'work_description'`.

- [ ] **Step 3: Add the three properties to the contract**

In `contracts/normalized_record.schema.json`, inside `properties`, directly after the `work_category` property, add:

```json
    "work_description": {
      "type": ["string", "null"],
      "description": "The recommendation's own free text from the Sanctioned tile (WORK_DESCRIPTION), spacing tidied and nothing else. Degradable: only the duplicate finder, the detail panel and the header search read it."
    },
    "activity_name": {
      "type": ["string", "null"],
      "description": "The portal's own activity string with its work-reference prefix stripped, one of 112 live values. Degradable: work_category stays the field every detector groups by."
    },
    "recommendation_date": {
      "type": ["string", "null"],
      "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$",
      "description": "YYYY-MM-DD or null. The date the MP recommended the work, from RECOMMENDATION_DATE. Degradable: nothing scores on it yet."
    },
```

Then add `"work_description"`, `"activity_name"` and `"recommendation_date"` to the `required` array, after `"work_category"`.

- [ ] **Step 4: Fill the three fields in the adapter**

In `mplads_adapter.py`, inside `adapt()`'s `records.append({...})`, directly after the
`"work_category": category_for(row.get("ACTIVITY_NAME")),` line, add:

```python
                # The portal's own words, carried without interpretation:
                # _clean() only tidies transport whitespace, activity_of()
                # only removes the "WS/ MP620/2024-2025/133166-" reference
                # prefix, and the date parser only reshapes dd-Mon-yyyy.
                # activity_of() returns "" for a missing activity, so _clean()
                # wraps it to produce a null rather than an empty string.
                "work_description": _clean(row.get("WORK_DESCRIPTION")),
                "activity_name": _clean(activity_of(row.get("ACTIVITY_NAME"))),
                "recommendation_date": _parse_ddmmmyyyy(row.get("RECOMMENDATION_DATE")),
```

- [ ] **Step 5: Pass them through the normalizer**

In `normalize.py`, add `"work_description"`, `"activity_name"` and `"recommendation_date"` to
`_REQUIRED_FIELDS` after `"work_category"`. In `_map_one`'s returned dict, after the
`"work_category": raw.get("work_category"),` line, add:

```python
        "work_description": raw.get("work_description"),
        "activity_name": raw.get("activity_name"),
        "recommendation_date": raw.get("recommendation_date"),
```

In the same function's docstring, change "the exact 14-key normalized shape" to
"the exact normalized shape" so the count cannot go stale again.

- [ ] **Step 6: Run the adapter tests to verify they pass**

Run: `cd 05-App && uv run pytest pipeline/tests/ingest -q`
Expected: PASS.

- [ ] **Step 7: Write the failing normalizer test**

Append to `pipeline/tests/normalize/test_normalize.py`:

```python
def test_normalize_carries_the_three_source_fields_and_allows_them_to_be_null() -> None:
    raw = {
        "work_id": "W1",
        "state": "Bihar",
        "constituency": "ARARIA",
        "mp_name": "Test MP",
        "tenure": "2024-2029",
        "implementing_district_authority": "ARARIA(DPO)",
        "implementing_agency": "KRIDL",
        "vendor_id": "V1",
        "vendor_name": "Test Vendor",
        "work_category": "Road",
        "work_description": "PCC Road from Ram house to Shyam house",
        "activity_name": "Construction of roads",
        "recommendation_date": "2024-07-08",
        "sanctioned_amount_inr": 500000.0,
        "expenditure_amount_inr": 0.0,
        "sanction_date": "2024-07-09",
        "completion_status": "In Progress",
        "last_updated": "2026-09-04",
    }

    kept = normalize_records([raw], source_rung=1)[0]
    assert kept["work_description"] == "PCC Road from Ram house to Shyam house"
    assert kept["activity_name"] == "Construction of roads"
    assert kept["recommendation_date"] == "2024-07-08"

    blanked = normalize_records(
        [{**raw, "work_description": None, "activity_name": None, "recommendation_date": None}],
        source_rung=1,
    )[0]
    assert blanked["work_description"] is None
    assert blanked["recommendation_date"] is None
```

- [ ] **Step 8: Run it, then the whole pipeline suite**

Run: `cd 05-App && uv run pytest pipeline/tests -q`
Expected: PASS. If `test_normalized_columns_match_the_frozen_schema` fails, the schema's
`properties` order and `_NORMALIZED_COLUMNS` disagree: fix the schema order, never the test.

- [ ] **Step 9: Give the demo fixture the new keys**

The fixture is rung 5, an openly labelled demo dataset, so four rows get plausible synthetic
descriptions (one deliberately tab-padded, to exercise cleaning) and the rest stay null. Run
exactly this from `05-App/`:

```python
uv run python - <<'PY'
import json, pathlib
p = pathlib.Path("contracts/fixtures/works.fixture.json")
rows = json.loads(p.read_text(encoding="utf-8"))
seed = {
    0: ("Construction of bore well near Zilla Parishad school, Ward 4", "Drinking water facilities", "2024-06-28"),
    1: ("  PCC road from\tKisan Bhawan to the bus stop  ", "Construction of roads", "2024-07-02"),
    2: ("Installation of 5 solar street lights at the village chowk", "Street lighting", "2024-07-11"),
    3: ("Construction of community hall at Ward 9", "Construction of buildings for community activities", None),
}
for i, row in enumerate(rows):
    desc, activity, rec = seed.get(i, (None, None, None))
    row["work_description"] = desc.replace("\t", " ").strip().replace("  ", " ") if desc else None
    row["activity_name"] = activity
    row["recommendation_date"] = rec
p.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("seeded", sum(1 for r in rows if r["work_description"]), "of", len(rows))
PY
```

- [ ] **Step 10: Validate the contracts and commit**

```bash
cd 05-App
python3 contracts/validate.py && python3 contracts/validate.py --self-test
uv run ruff format pipeline/src/nidhinetra_pipeline/ingest/mplads_adapter.py \
  pipeline/src/nidhinetra_pipeline/normalize/normalize.py \
  pipeline/tests/ingest/test_mplads_adapter.py pipeline/tests/normalize/test_normalize.py
uv run ruff check pipeline/src pipeline/tests
uv run pytest pipeline/tests api/tests -q
cd .. && git add 05-App/contracts/normalized_record.schema.json \
  05-App/contracts/fixtures/works.fixture.json \
  05-App/pipeline/src/nidhinetra_pipeline/ingest/mplads_adapter.py \
  05-App/pipeline/src/nidhinetra_pipeline/normalize/normalize.py \
  05-App/pipeline/tests/ingest/test_mplads_adapter.py \
  05-App/pipeline/tests/normalize/test_normalize.py
git commit -m "feat(pipeline): carry the portal's description, activity and recommendation date (Phase 0, 1/4)"
```

---

### Task 2: Prove the three fields cannot move a score

**Files:**
- Test: `pipeline/tests/test_build_snapshot.py`

**Interfaces:**
- Consumes: Task 1's three fields; `bs.build_snapshot(snapshot_dir=..., now=...)`, `bs.WORKS_FIXTURE_PATH`.
- Produces: nothing other tasks import. This is the guarantee the spec promises.

- [ ] **Step 1: Write the failing test**

Append to `pipeline/tests/test_build_snapshot.py`:

```python
DECISION_COLUMNS = ["work_id", "risk_score", "inspection_rank", "flags", "why_flagged", "peer_group"]


def _decisions(snapshot_dir: Path) -> list[dict]:
    frame = pd.read_parquet(snapshot_dir / "scored.parquet")[DECISION_COLUMNS]
    return json.loads(frame.sort_values("work_id").to_json(orient="records", double_precision=15))


def test_the_three_source_fields_never_change_a_score_rank_flag_or_reason(tmp_path, monkeypatch):
    """Phase 0 carries information; it must not move a single decision. The
    same works are built twice with the same pinned reference time, once with
    the portal's own text and once with all three fields blanked and altered.
    Every scored column must come out identical.
    """
    rows = json.loads(REAL_FIXTURE.read_text(encoding="utf-8"))
    with_text = tmp_path / "with_text.json"
    without_text = tmp_path / "without_text.json"
    with_text.write_text(json.dumps(rows), encoding="utf-8")
    without_text.write_text(
        json.dumps(
            [
                {
                    **row,
                    "work_description": None if i % 2 else "completely different wording",
                    "activity_name": None,
                    "recommendation_date": None,
                }
                for i, row in enumerate(rows)
            ]
        ),
        encoding="utf-8",
    )

    pinned = datetime(2026, 9, 13, 6, 27, 54, tzinfo=UTC)
    first, second = tmp_path / "a", tmp_path / "b"
    monkeypatch.setattr(bs, "WORKS_FIXTURE_PATH", with_text)
    bs.build_snapshot(snapshot_dir=first, now=pinned)
    monkeypatch.setattr(bs, "WORKS_FIXTURE_PATH", without_text)
    bs.build_snapshot(snapshot_dir=second, now=pinned)

    assert _decisions(first) == _decisions(second)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd 05-App && uv run pytest pipeline/tests/test_build_snapshot.py -q -k never_change`
Expected: FAIL before Task 1 exists. After Task 1 it should already PASS, because nothing in
`risk/` reads the new fields. If it fails **after** Task 1, a detector is reading text it must not:
find it with `rg "work_description|activity_name|recommendation_date" pipeline/src/nidhinetra_pipeline/risk`
and stop. Do not weaken this test.

- [ ] **Step 3: Verify the same property on the real snapshot**

This is a check, not a test, and it writes only to a temp folder:

```bash
cd 05-App
uv run --package nidhinetra-pipeline python \
  ~/Desktop/study/project/SIHGit/kit/rebuild_snapshot_offline.py 2>&1 | tail -25
git status --short -- 05-App/data   # must print nothing
```

Compare `flagged_under_implementation` in the printed table against the previous dry run recorded
in `SIHGit/review-packets/T05/dry-run-output.txt` (16,190). It must match exactly: Phase 0 adds
fields, so the number cannot move. If it does, stop and report rather than proceeding.

- [ ] **Step 4: Commit**

```bash
cd .. && git add 05-App/pipeline/tests/test_build_snapshot.py
git commit -m "test(pipeline): lock that Phase 0's source fields cannot move any score (Phase 0, 2/4)"
```

---

### Task 3: Report source completeness and refuse a silent date-format change

**Files:**
- Modify: `pipeline/src/nidhinetra_pipeline/ingest/mplads_adapter.py` (`load_and_adapt`)
- Test: `pipeline/tests/ingest/test_mplads_adapter.py`

**Interfaces:**
- Consumes: Task 1's fields; `load_and_adapt(raw_dir, as_of=...) -> (records, counts)`.
- Produces: `counts` gains `description_present`, `activity_present`, `recommendation_date_present`,
  `recommendation_date_unparseable`, `sanction_date_unparseable`. `UnreadableDateFormatError` is
  raised when more than 1% of non-empty date values fail to parse.

- [ ] **Step 1: Write the failing tests**

```python
def test_counts_report_how_complete_the_three_source_fields_are(tmp_path) -> None:
    rows = [_sanctioned_row(501, description="Road work", recommendation="08-Jul-2024"),
            _sanctioned_row(502, description=None, recommendation=None)]
    _write_tiles(tmp_path, rows)

    _records, counts = load_and_adapt(tmp_path, as_of=date(2026, 9, 4))

    assert counts["description_present"] == 1
    assert counts["recommendation_date_present"] == 1
    assert counts["recommendation_date_unparseable"] == 0


def test_a_changed_date_format_fails_the_build_instead_of_blanking_every_date(tmp_path) -> None:
    rows = [_sanctioned_row(600 + i, description="Road work", recommendation="2024-07-08")
            for i in range(50)]
    _write_tiles(tmp_path, rows)

    with pytest.raises(UnreadableDateFormatError) as caught:
        load_and_adapt(tmp_path, as_of=date(2026, 9, 4))

    assert "recommendation_date" in str(caught.value)
```

Write `_sanctioned_row(work_id, *, description, recommendation)` and `_write_tiles(dir, rows)` as
module-level helpers in that test file if they do not already exist: `_sanctioned_row` returns the
same dict shape as Task 1's tests, and `_write_tiles` writes `rows` to
`<dir>/mplads-sanctioned.json` as a JSON list.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd 05-App && uv run pytest pipeline/tests/ingest -q -k "complete or date_format"`
Expected: FAIL with `ImportError` on `UnreadableDateFormatError`.

- [ ] **Step 3: Implement the counts and the guard**

Near the top of `mplads_adapter.py`, beside the other module constants:

```python
# A portal format change must not pass silently. _parse_ddmmmyyyy() returns
# None for anything it cannot read, including a plain "2024-07-08", so a
# switch to ISO dates would blank every date without a single error. One odd
# row must not block a refresh, which is why this is a rate and not a count.
UNREADABLE_DATE_LIMIT = 0.01


class UnreadableDateFormatError(Exception):
    """Raised when too many non-empty date values fail to parse."""
```

In `load_and_adapt`, after `records` are built and before returning, add:

```python
    def _unreadable(raw_key: str, parsed_key: str) -> tuple[int, int]:
        supplied = [row.get(raw_key) for row in sanctioned]
        non_empty = [value for value in supplied if _clean(value) is not None]
        failed = sum(1 for value in non_empty if _parse_ddmmmyyyy(value) is None)
        return len(non_empty), failed

    for raw_key, parsed_key in (("RECOMMENDATION_DATE", "recommendation_date"),
                                ("SANCTION_DATE", "sanction_date")):
        non_empty, failed = _unreadable(raw_key, parsed_key)
        counts[f"{parsed_key}_unparseable"] = failed
        if non_empty and failed / non_empty > UNREADABLE_DATE_LIMIT:
            raise UnreadableDateFormatError(
                f"{failed} of {non_empty} non-empty {raw_key} values could not be read as "
                f"dd-Mon-yyyy ({parsed_key}). The portal's date format has probably changed; "
                "nothing was written."
            )

    counts["description_present"] = sum(1 for r in records if r["work_description"])
    counts["activity_present"] = sum(1 for r in records if r["activity_name"])
    counts["recommendation_date_present"] = sum(1 for r in records if r["recommendation_date"])
```

Add `UnreadableDateFormatError` to the module's `__all__` if it has one.

- [ ] **Step 4: Run the tests, then the suite**

Run: `cd 05-App && uv run pytest pipeline/tests -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd 05-App && uv run ruff format pipeline/src/nidhinetra_pipeline/ingest/mplads_adapter.py \
  pipeline/tests/ingest/test_mplads_adapter.py && uv run ruff check pipeline/src pipeline/tests
cd .. && git add 05-App/pipeline/src/nidhinetra_pipeline/ingest/mplads_adapter.py \
  05-App/pipeline/tests/ingest/test_mplads_adapter.py
git commit -m "feat(pipeline): report source completeness and refuse an unreadable date format (Phase 0, 3/4)"
```

---

### Task 4: The API returns the fields and searches them

**Files:**
- Modify: `api/src/nidhinetra_api/routers/works.py` (`_MERGED_SELECT`, `_SEARCH_COLUMNS`)
- Test: `api/tests/test_works.py`

**Interfaces:**
- Consumes: Task 1's three columns in `works.parquet`.
- Produces: every `/api/works` row and `/api/works/{work_id}` response carries `work_description`,
  `activity_name` and `recommendation_date`. Task 5's TypeScript types mirror exactly these names.

- [ ] **Step 1: Write the failing tests**

Append to `api/tests/test_works.py`, following that file's existing client fixture:

```python
def test_a_work_carries_the_portal_description_activity_and_recommendation_date(client):
    body = client.get("/api/works/MPLADS-FX-0001").json()["data"]

    assert body["work_description"] == "Construction of bore well near Zilla Parishad school, Ward 4"
    assert body["activity_name"] == "Drinking water facilities"
    assert body["recommendation_date"] == "2024-06-28"


def test_the_header_search_matches_a_word_in_the_description(client):
    body = client.get("/api/works", params={"q": "bore well"}).json()["data"]

    assert [row["work_id"] for row in body] == ["MPLADS-FX-0001"]


def test_the_header_search_matches_a_word_in_the_portal_activity(client):
    body = client.get("/api/works", params={"q": "street lighting"}).json()["data"]

    assert "MPLADS-FX-0003" in [row["work_id"] for row in body]
```

If the fixture work ids differ from `MPLADS-FX-0001` and `MPLADS-FX-0003`, read the first and third
rows of `contracts/fixtures/works.fixture.json` and use their real ids and text.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd 05-App && uv run pytest api/tests/test_works.py -q -k "portal_description or header_search"`
Expected: FAIL with `KeyError: 'work_description'` and empty search results.

- [ ] **Step 3: Add the columns and the search fields**

In `works.py`, inside `_MERGED_SELECT`, extend the `works.` column list so it reads:

```sql
        works.work_category, works.work_description, works.activity_name,
        works.recommendation_date, works.sanctioned_amount_inr,
```

In `_SEARCH_COLUMNS`, after `"works.vendor_id",` add:

```python
    # What an officer types is usually what was built, not who built it.
    "works.work_description",
    "works.activity_name",
```

- [ ] **Step 4: Run the tests, then both suites**

Run: `cd 05-App && uv run pytest pipeline/tests api/tests -q`
Expected: PASS.

- [ ] **Step 5: Check the search stays fast on the real snapshot**

```bash
cd 05-App
uv run python -c "
import time, sys; sys.path.insert(0, 'api/src')
from nidhinetra_api import db
con = db.connect()
for term in ('bore well', 'high mast', 'ARARIA'):
    start = time.perf_counter()
    con.execute(\"SELECT count(*) FROM works WHERE strpos(lower(work_description), ?) > 0\", [term]).fetchone()
    print(term, f'{(time.perf_counter() - start) * 1000:.0f} ms')
"
```

Expected: well under 1000 ms per term on 79,068 rows. If any term exceeds that, stop and report;
do not add an index without a design decision.

- [ ] **Step 6: Commit**

```bash
cd 05-App && uv run ruff format api/src/nidhinetra_api/routers/works.py api/tests/test_works.py \
  && uv run ruff check api/src api/tests
cd .. && git add 05-App/api/src/nidhinetra_api/routers/works.py 05-App/api/tests/test_works.py
git commit -m "feat(api): return and search the portal description and activity (Phase 0, 4/4)"
```

---

### Task 5: The officer sees the portal's own words

**Files:**
- Modify: `contracts/strings.json` (`detail_panel.record_fields`, `missing_fields`, `_meta.amendment_log`)
- Modify: `web/lib/types.ts` (`NormalizedRecord`)
- Modify: `web/components/detail-panel/DetailPanel.tsx`
- Modify: `PRODUCT.md`
- Test: `web/components/detail-panel/DetailPanel.test.tsx`, `pipeline/tests/test_web_mirror_drift.py`

**Interfaces:**
- Consumes: Task 4's API fields.
- Produces: the panel renders the description beneath the title, and two more rows in the existing
  "Record as published" list.

- [ ] **Step 1: Add the copy**

In `contracts/strings.json`, inside `detail_panel.record_fields`, after the
`"constituency": "Constituency",` line, add:

```text
      "work_description": "Work description",
      "activity": "Portal activity",
      "recommendation_date": "Recommended on",
```

Inside `missing_fields`, after `"district_authority": "District Authority not recorded",` add:

```text
    "description": "The portal record has no description for this work.",
```

Add a comma to the end of the last `_meta.amendment_log` entry and insert after it:

```text
      "2026-09-17: Phase 0. Added detail_panel.record_fields.work_description, .activity and .recommendation_date, and missing_fields.description. The portal publishes a description, an activity string and a recommendation date on every work; the pipeline dropped all three. They are shown as published, with only transport spacing tidied, and nothing about them is derived or interpreted."
```

Check: `python3 -m json.tool contracts/strings.json > /dev/null && echo parses`.

- [ ] **Step 2: Mirror the fields in TypeScript**

In `web/lib/types.ts`, inside `interface NormalizedRecord`, directly after
`  work_category: WorkCategory;`, add:

```ts
  work_description: string | null;
  activity_name: string | null;
  recommendation_date: string | null;
```

- [ ] **Step 3: Write the failing panel tests**

Append to `web/components/detail-panel/DetailPanel.test.tsx` (its `row()` helper needs the three
new keys too: `work_description: "PCC Road from Ram house to Shyam house"`, `activity_name:
"Construction of roads"`, `recommendation_date: "2024-07-02"`):

```tsx
test("shows the portal's own description under the title", () => {
  render(<DetailPanel row={row()} onClose={() => {}} quotaN={10} />);

  expect(screen.getByText(fields.work_description)).toBeInTheDocument();
  expect(screen.getByText("PCC Road from Ram house to Shyam house")).toBeInTheDocument();
});

test("says so plainly when the portal has no description", () => {
  render(<DetailPanel row={row({ work_description: null })} onClose={() => {}} quotaN={10} />);

  expect(screen.getByText(STRINGS.missing_fields.description)).toBeInTheDocument();
});

test("lists the portal activity and the recommendation date as published", () => {
  render(<DetailPanel row={row()} onClose={() => {}} quotaN={10} />);

  expect(screen.getByText(fields.activity).nextElementSibling).toHaveTextContent(
    "Construction of roads",
  );
  expect(screen.getByText(fields.recommendation_date).nextElementSibling).toHaveTextContent(
    formatDate("2024-07-02"),
  );
});
```

Import `formatDate` from `@/lib/format` at the top of that file if it is not already imported.

- [ ] **Step 4: Run them to verify they fail**

Run: `cd 05-App/web && npx vitest run components/detail-panel/DetailPanel.test.tsx`
Expected: FAIL, the labels are not rendered.

- [ ] **Step 5: Render them**

In `DetailPanel.tsx`, add two entries to the `fields` array, directly after the `constituency` entry:

```tsx
    {
      key: "activity",
      value: row.activity_name ? displayName(row.activity_name) : missing.generic,
    },
    {
      key: "recommendation_date",
      value: row.recommendation_date ? formatDate(row.recommendation_date) : missing.date,
    },
```

Then, directly after the `<h2 id="detail-panel-title" ...>{workTitle(row)}</h2>` element, add:

```tsx
        <p className={styles.description}>
          <span className={styles.descriptionLabel}>{strings.record_fields.work_description}</span>
          {row.work_description ? displayName(row.work_description) : missing.description}
        </p>
```

Add to `web/components/detail-panel/DetailPanel.module.css`:

```css
.description {
  margin: var(--space-3) 0 0;
  font-size: var(--font-sm);
  line-height: var(--leading-normal);
  color: var(--ink);
}

.descriptionLabel {
  display: block;
  font-size: var(--font-note);
  color: var(--ink-faint);
}
```

Every token above is already used in this same stylesheet (`--space-3` and `--ink` in `.title`,
`--font-note` and `--ink-faint` in `.fieldName`), so the description reads as one more part of the
record rather than a new visual idea. Never invent a raw colour or size.

- [ ] **Step 6: Lock the TypeScript mirror against drift**

Append to `pipeline/tests/test_web_mirror_drift.py`:

```python
def test_normalized_record_typescript_mirror_lists_every_contract_field() -> None:
    """web/lib/types.ts is hand-written (make contracts codegen is not wired
    up), so this test is the only thing stopping the frontend's idea of a work
    from drifting away from the contract.
    """
    schema = json.loads(
        (APP_ROOT / "contracts" / "normalized_record.schema.json").read_text(encoding="utf-8")
    )
    source = (APP_ROOT / "web" / "lib" / "types.ts").read_text(encoding="utf-8")
    block = source.split("export interface NormalizedRecord {", 1)[1].split("}", 1)[0]
    declared = {line.split(":", 1)[0].strip() for line in block.splitlines() if ":" in line}

    assert declared == set(schema["properties"]), (
        f"types.ts and the contract disagree: only in the contract "
        f"{set(schema['properties']) - declared}, only in types.ts {declared - set(schema['properties'])}"
    )
```

If that file has no `APP_ROOT` constant, add `APP_ROOT = Path(__file__).parents[2]` beside its
other module constants, and import `json` and `Path` if they are missing.

- [ ] **Step 7: Correct the product doc**

In `PRODUCT.md`, replace the line
`- Work descriptions are not in the source data yet. Titles are composed from category and constituency and are never invented.`
with:

```markdown
- Work descriptions come from the portal's Sanctioned tile and are shown as published, with only transport spacing tidied. Titles stay composed from category and constituency, because the portal's own text is free-form, often in capitals, and up to 500 characters.
```

- [ ] **Step 8: Run every gate**

```bash
cd 05-App/web && npx vitest run && npx tsc --noEmit \
  && npx eslint lib/types.ts components/detail-panel/DetailPanel.tsx components/detail-panel/DetailPanel.test.tsx \
  && npm run build
cd .. && python3 contracts/validate.py && python3 contracts/validate.py --self-test \
  && uv run pytest pipeline/tests api/tests -q
```

Expected: all green.

- [ ] **Step 9: Commit**

```bash
cd .. && git add 05-App/contracts/strings.json 05-App/web/lib/types.ts \
  05-App/web/components/detail-panel/DetailPanel.tsx \
  05-App/web/components/detail-panel/DetailPanel.module.css \
  05-App/web/components/detail-panel/DetailPanel.test.tsx \
  05-App/pipeline/tests/test_web_mirror_drift.py PRODUCT.md
git commit -m "feat(web): show the portal's description, activity and recommendation date (Phase 0, 5/5)"
```

---

## Done when

- `uv run pytest pipeline/tests api/tests -q` and `npx vitest run` are green, with the new tests in them.
- `python3 contracts/validate.py --self-test` passes.
- The decision-equivalence test in Task 2 passes, and the offline dry run still reports 16,190 flagged works under implementation.
- `git status --short -- 05-App/data` prints nothing, and `git log origin/main --oneline -1` is still `8fa4065`.
- Five local commits exist and nothing has been pushed.

## Not in this plan

Phase 1 Stage A (candidate generation) gets its own plan, because its thresholds are set by Stage D's
measurements and it depends on these fields existing first. Stages B, C and D follow after it.
