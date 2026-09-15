# NidhiNetra Audit Remediation: AI Handoff Logbook

Last updated: 2026-09-15 (Asia/Kolkata)

Repository: `git@github.com:Krishpotanwar/NidhiNetra.git`

Working branch: `codex/finish-nidhinetra`

Code handoff boundary: `d545e770253251768247b70da05c357a827cde0a`

Upstream base: `origin/main` at `0fe4840b771b17e74cbd13d710bb9618f27ba6e4`

Status: remediation is implemented and committed through approved Next Step 4. Next Step 5 has not been edited or tested. The code boundary is two local commits ahead of `origin/main`; this logbook is the following documentation-only commit, making the final branch three commits ahead. Nothing has been pushed.

## 1. Start here

Before doing anything else, including Git inspection, read `docs/designs/nemotron-audit-remediation.md` in full. It is the approved and maintained specification, and its latest Next Steps and DONE notes control if an older paragraph conflicts with them.

After reading that document, run these commands from the repository root:

```bash
git status -sb
git log --oneline --decorate -12
git rev-list --left-right --count origin/main...HEAD
```

Then read, in this order:

1. This handoff logbook.
2. `nemotronreview.md`, especially the finding being implemented. It is an audit input, not the implementation spec.
3. The applicable JSON Schemas and `contracts/strings.json`. `contracts/` is the source of truth for response/data shapes and user-facing copy.

Before any web edit, also read `05-App/web/AGENTS.md`. This Next.js 16 project requires the relevant local guide under `05-App/web/node_modules/next/dist/docs/` to be read before coding because current APIs and conventions may differ from model training data.

Do not reset, rebase, merge, pull, push, rebuild real data, or stage files merely to make the workspace look clean. Preserve the user's existing files.

Critical Git warning: the local branch named `main` is not this branch's usable base. It points at `7eb78c4`, has no merge-base with the `origin/main` lineage used here, and diverges by 56/15 commits in the inspected histories. Use `origin/main` only for comparison. Do not switch to, merge, rebase onto, or reset against local `main`.

## 2. Authority and scope

The original instruction was to execute the approved remediation in order:

1. F-03/F-04 per-District-Authority quota correctness.
2. F-02 evidence-backed fund-flow paths.
3. Replace the hand-rolled graph SVG with Sigma.js, staying 2D.
4. Build R-06's entity alias-review queue.
5. Implement the real F-01 `IA_NAME` versus `IDA_NAME` separation.
6. Implement F-09 with a server-assigned control-group flag. F-08 needs no live-app code change.
7. Address the remaining audit backlog only if time remains.

Steps 1 through 4 are complete. Continue with Step 5, then Step 6, then the exact Step 7 backlog. Do not reopen completed work unless a new failing regression proves it necessary.

## 3. Non-negotiable safety rules

- Never read, edit, stage, delete, or otherwise touch `krish.txt`, `krish.txt.pub`, `.obsidian/graph.json`, or any deck/PPT file.
- Do not run a live pull from the MPLADS portal in tests or development.
- Tests must not write to `05-App/data/snapshot/`, `05-App/data/raw/`, or the real `05-App/data/outcomes/outcomes.db`.
- Reuse the existing temporary-directory and monkeypatch isolation patterns in `api/tests/conftest.py` and the pipeline test fixtures.
- Do not add dependencies unless the approved plan requires one and the standard library or an existing dependency cannot solve the problem. The plan already rejected `apportionment` and `networkx` for these fixes.
- Ask the user before pushing to `main` or performing any destructive Git operation.
- One logical remediation per conventional commit. Use the existing `fix:`, `feat:`, or `docs:` style.
- Use TDD for every implementation: add the failing regression first, run it, confirm the failure is for the intended missing behavior, then implement.
- If a change needs a new UI that the approved document does not specify, do not invent it. Record the need for a design pass in the remediation document.

## 4. Git and workspace state at handoff

`git status -sb` at the code handoff boundary, immediately before this logbook commit:

```text
## codex/finish-nidhinetra...origin/main [ahead 2]
 M 05-App/web/.impeccable/hook.cache.json
```

There are also many unrelated untracked files and directories, including `.chart-data-*`, `.codex-finalizer/`, `.codex-ppt-build/`, research notes, images, PDFs, and deck assets. They predate this handoff and are not part of the remediation.

Rules for the dirty tree:

- `05-App/web/.impeccable/hook.cache.json` is a pre-existing tracked modification. Do not stage or revert it.
- Do not stage any unrelated untracked file. In particular, `nemotronreview.md` is currently untracked even though it is an audit input.
- A fresh remote clone will not contain `nemotronreview.md` unless the user supplies it separately. Do not assume its absence means the approved remediation document can be ignored.
- Stage explicit paths only. Never use `git add -A` or `git add .`.
- After this logbook is committed, expect the branch to report three commits ahead. Two are implementation commits and the third is documentation only.
- There is no unfinished Step 5 diff. The clean semantic restart point is code commit `d545e77` followed by this documentation-only handoff commit.
- Local `main` is a divergent, unrelated-history hazard. It is not a restart target. The branch's actual upstream and merge base are both `origin/main` at `0fe4840`.
- No Step 5 explorer produced usable implementation work, and no development server/process needs to be resumed. Two read-only explorer attempts ended on account usage limits.

## 5. Commit ledger

| Commit | Scope | State |
| --- | --- | --- |
| `71a9197` | Added the approved Nemotron audit remediation plan | Already on `origin/main` |
| `4b31e45` | Removed the blue DotCanvas hover glow | Already on `origin/main`; not a numbered remediation step |
| `27d1bc5` | F-03/F-04 per-District-Authority inspection quota and comparable frozen ranks | Step 1 DONE; already on `origin/main` |
| `4e1136e` | F-02 real shared-work evidence on graph paths | Step 2 DONE; already on `origin/main` |
| `0f3991a` | Render cold-start tolerance | Already on `origin/main`; deployment hardening outside the numbered audit sequence |
| `0fe4840` | CORS support for this project's Vercel preview URLs | Current `origin/main`; outside the numbered audit sequence |
| `519c365` | Replaced the fund-flow SVG with Sigma.js | Step 3 DONE; local, not pushed |
| `d545e77` | Added the R-06 entity alias-review queue | Step 4 DONE; local, not pushed; handoff code HEAD |
| This document's `docs:` commit | Captures the AI-to-AI remediation handoff | Documentation only; run `git log -1 --oneline` for its non-self-referential hash |

The code boundary relationship is `origin/main...d545e77 = 0 behind, 2 ahead`. After the logbook commit, the branch relationship is `origin/main...HEAD = 0 behind, 3 ahead`.

## 6. Completed remediation record

### Step 1: F-03/F-04 district quota correctness

Commit: `27d1bc5 fix: enforce per-District Authority inspection quota (F-03/F-04)`

What landed:

- `policy.quota_by_group()` applies the existing `quota_for()` ceiling independently per District Authority.
- `_district_population_and_rank()` freezes population, rank, and cutoff from the same authority-scoped under-implementation population.
- The implementation deliberately used the then-mislabeled `works.implementing_agency` field because that column currently contains `IDA_NAME` values.
- The regression independently recomputes the population and rank from the works endpoint instead of trusting the endpoint's own arithmetic.

Verification recorded in the approved document: API 66/66 passed.

Deliberate deferral: the global quota card was not replaced with a per-district tracker because that UI was not designed. The existing card's copy is scoped honestly, but it remains a national/filter aggregate.

Critical Step 5 follow-up: every quota or frozen district-rank reference that currently uses `implementing_agency` must move to `implementing_district_authority` when the fields are separated.

### Step 2: F-02 real work evidence for fund-flow paths

Commit: `4e1136e fix: require shared work evidence for fund-flow graph paths (F-02)`

What landed:

- Every graph edge now carries its real supporting `work_ids`.
- `fund_flow_graph.schema.json` requires a non-empty `work_ids` array.
- `contracts/validate.py` verifies that every referenced work ID exists.
- Both `allVendorConcentrations()` and `subgraphFor()` require an intersection between the two legs' work IDs. Merely sharing an agency no longer creates an MP-to-vendor path.
- The graph fixture is generated by the real graph builder.

Verification recorded at that step: API 66 passed, pipeline 244 passed excluding six known baseline failures, web 20 passed, contract validation and validator self-test passed.

Deliberate deferrals:

- F-17's client-side `allVendorConcentrations()` performance work was not moved server-side.
- The proposed on-screen before/after audit demo was not built because its UI is not designed.

The Verification Pass earlier in the design document suggested folding F-17 into F-02, but the later Step 2 DONE note explicitly defers it. Treat the later DONE note as current. Step 5 must measure the true-IA graph after the roughly eightfold agency-node increase; do not silently expand scope unless the measurement makes correctness or usability unacceptable.

The Engineering Review's T1-T6 checkboxes were not updated as work landed. Trust the dated Next Steps DONE entries and commits instead. T4 (`_modal_string`) and T7 (the F-09 regression) are genuinely still open.

### Step 3: Sigma.js fund-flow rendering

Commit: `519c365 fix: render fund-flow graph with Sigma.js`

Change size: 10 files, 756 insertions, 153 deletions.

What landed:

- `GraphView.tsx` now dynamically loads Sigma.js 3.0.3 after mount and renders through WebGL.
- Graphology 0.26.0 is the graph model. No React wrapper or force-layout dependency was added.
- `sigma-graph.ts` is a pure adapter with fixed MP, Agency, and Vendor tiers normalized into a bounded 0..1 coordinate space.
- The prior visual language remains: risk-sized nodes, capped/logarithmic edge widths, contract-backed labels, CSS token colors, focused-vendor dimming, hover details, deep links, empty state, and the three-column legend.
- The component owns and kills the renderer on prop changes and unmount, keeps Next static rendering safe, and contains initialization failures with `data-render-state="failed"`.
- A review found and fixed a subtle F-02 cross-branch highlight bug: endpoint membership alone can no longer highlight an unrelated edge.

Tests added:

- `05-App/web/components/fund-flow/GraphView.test.tsx`
- `05-App/web/components/fund-flow/sigma-graph.test.ts`
- A cross-branch regression in `05-App/web/lib/vendor-concentration.test.ts`

Verification:

- Web: 31/31 passed.
- `npx tsc --noEmit`: passed.
- ESLint on every touched TypeScript file: passed.
- Optimized Next build: passed.
- Real-browser deep-link check at 796x432: 7 Sigma canvases, 0 SVG elements, renderer ready, no console warnings or errors.

Deliberate deferrals: 3D, force layout, minimap, reset/zoom toolbar, node actions, animation, rich node details, keyboard graph navigation/alternate table, a visible renderer-specific error UI, F-17 server aggregation, and the before/after demo. These need either no change or a separate design pass as described in the approved document.

### Step 4: R-06 entity alias-review queue

Commit: `d545e77 feat: add entity alias review queue`

Change size: 41 files, 3,071 insertions, 225 deletions.

Pipeline and contracts:

- The expenditure adapter carries `VENDOR_ID` only from real events associated with the chosen modal vendor name, preventing an independently selected false ID/name pair.
- `vendor_id` is required as a key but nullable as a value in the normalized record contract.
- Vendor graph identity is a reversible, collision-free percent encoding of the source ID. The modal name is display copy only.
- `alias_candidates.py` deterministically builds ambiguous ID/name candidates with the union of supporting work IDs.
- `build_snapshot.py` stages and validates `alias_candidates.json` as the fifth snapshot artifact.
- Added `entity_alias_candidate.schema.json`, `entity_alias_review.schema.json`, an alias fixture, and cross-file evidence checks.

Persistent review store:

- `outcomes/alias_store.py` is a sibling of the inspection store and uses the same physical SQLite file without merging the two modules.
- Candidate upserts use `(entity_type, proposed_canonical_id, alias_label)` and preserve candidate IDs and prior decisions while refreshing reasons/evidence.
- Review history is append-only. The server owns UTC timestamps and `supersedes`.
- Corrections run under `BEGIN IMMEDIATE` and automatically supersede the currently effective review.

API:

- `GET /api/entity-aliases?status=pending` is paginated and resolves all evidence for a page with one batched DuckDB query.
- `POST /api/entity-aliases/{id}/review` owns timestamps/supersession and rejects extra client-owned fields.
- Startup and successful refreshes sync the rebuildable candidate artifact into persistent review state.
- An old snapshot without `alias_candidates.json` boots with an empty queue and a warning.
- The compatibility view projects `vendor_id = NULL` for pre-R-06 Parquet.

Web:

- The Fund Flow page has the specified in-page `{N} pending` anchor, not a fifth navigation tab.
- The review table uses contract-backed plain copy and the exact actions `These are the same` and `These are different`.
- Competing vendor names and source IDs are visible beside linked evidence works.
- Reviewer initials reuse the existing device preference and therefore inherit F-10's self-reported-identity weakness.
- It includes row-treatment controls, DotCanvas states, pagination, accessible success/failure announcements, and last-row page backup.

Review fixes included before commit:

1. Legacy Parquet no longer fails binding when `vendor_id` is absent.
2. Save failures no longer show the wrong copy.
3. Competing source IDs are visible.
4. Resolving the final row on page 2 does not leave a false empty page.
5. Screen readers receive error announcements.
6. The TypeScript POST helper matches the actual response shape.

Verification:

- API: 85 passed, with one known Starlette deprecation warning.
- Pipeline: 274 passed, 6 failed. The six failures are the pre-existing CLI baseline described below.
- Web: 40 passed.
- TypeScript, touched ESLint, optimized Next build, touched Ruff checks, and Ruff format check: passed.
- `python3 contracts/validate.py` and `python3 contracts/validate.py --self-test`: passed.
- Real-browser temporary-fixture flow: evidence visible, initials entered, review POST succeeded, pending count reached zero, graph remained intact.
- Independent code review: approved with no critical, high, medium, or low findings.

Deliberate deferrals:

- A confirmed alias decision does not rewrite graph identity. The current candidate contract lacks a second entity ID/canonical rewrite target.
- Missing candidates from a later artifact are not retired. The schema has no active/generation/retirement field, and deletion could orphan review history.
- The checked-in real snapshot remains pre-`vendor_id` and has no alias artifact. Its queue is empty until a separately authorized rebuild.
- Reviewed-history/correction UI is not designed. Storage and API correction semantics exist, but the minimum UI lists pending work only.
- `reviewed_by` remains self-reported and must be included when F-10 authentication/attribution is addressed.

## 7. Verification baseline and commands

Run commands from `05-App` unless a different directory is shown.

API full suite:

```bash
uv run --package nidhinetra-api pytest api/tests/
```

Pipeline full suite:

```bash
uv run --package nidhinetra-pipeline pytest pipeline/tests/
```

Web full gates:

```bash
cd web
npx vitest run
npx tsc --noEmit
npm run build
```

Lint only files touched by the current logical fix:

```bash
# From 05-App; replace paths with the actual touched Python files.
uv run ruff check <touched-python-files>
uv run ruff format --check <touched-python-files>

# From 05-App/web; replace paths with the actual touched TS/TSX files.
npx eslint <touched-ts-or-tsx-files>
```

After any contract or fixture change:

```bash
. .venv/bin/activate && python3 contracts/validate.py
. .venv/bin/activate && python3 contracts/validate.py --self-test
```

Before a commit:

```bash
git diff --check
git status --short
git diff --cached --name-only
```

Do not start implementation by running every suite. First add one focused failing test and prove its failure reason. After the change, run targeted tests, then every relevant full suite above.

### Known pipeline baseline

The last full pipeline run at `d545e77` produced `274 passed, 6 failed`. All six failures are in `pipeline/tests/test_cli.py` and call `cli.build(..., snapshot_dir=...)` even though `build()` does not accept that keyword. This mismatch predates Steps 3 and 4 and is documented in the Step 2 DONE note.

Do not:

- claim the pipeline suite is green;
- hide the six failures by running a narrower suite in the final report;
- attribute them to F-01 without first proving the baseline changed;
- fix them inside F-01 unless the audit ordering or a direct dependency makes that work in scope.

## 8. Next Step 5: real F-01 field separation

Finding: `F-01 — Blocker: Implementing District Authority is mislabeled as Implementing Agency`.

### Source truth and target model

| Concept | Raw source | Raw tile | Target normalized field | Primary consumers |
| --- | --- | --- | --- | --- |
| Implementing District Authority | `IDA_NAME` | Sanctioned | `implementing_district_authority` | Statutory per-authority quota and frozen district rank |
| Implementing Agency | `IA_NAME` | Expenditure/payment events | `implementing_agency` | Agency concentration detector, fund-flow graph, work display/search |

Current defect: `mplads_adapter.py` writes `IDA_NAME` directly into `implementing_agency`. The actual `IA_NAME` is not rolled up at all.

Expected data change:

- About 733 distinct IDA values become the District Authority dimension.
- About 5,868 distinct IA values become the true agency dimension, roughly eight times the current graph's middle-node cardinality.
- About 31,953 works with no expenditure event will correctly have `implementing_agency = null`. Do not substitute the District Authority to fill the blank.

### Required implementation sequence

1. In `pipeline/tests/ingest/test_mplads_adapter.py`, add the focused failing tests first:
   - one work with different `IDA_NAME` and `IA_NAME` returns both under the correct field names;
   - multiple expenditure events select IA by event-count mode with an alphabetical tie-break;
   - a zero-expenditure work retains its IDA and has a null IA;
   - vendor ID/name pairing behavior from R-06 remains unchanged.
2. Extract the modal-count selection in `_ExpenditureRollup.vendor()` into the approved shared `_modal_string(counts)` helper. Add an `IA_NAME` counter and agency accessor that use the same helper. Do not independently combine values from unrelated payment events.
   - A stale sentence in the Engineering Review says this helper is “now shared.” The current source proves it is not: `_ExpenditureRollup.vendor()` still contains the selection inline. The Step 5 Next Step is authoritative.
3. Add `implementing_district_authority` as a required-nullable contract key and keep `implementing_agency` required-nullable. Update normalization, fixtures, snapshot round-trip tests, and contract validation.
4. Audit semantic consumers, not just names:
   - `api/policy.py` documentation and every quota grouping use District Authority;
   - `api/routers/inspections.py::_district_population_and_rank()` groups by District Authority;
   - `pipeline/risk/detectors.py` agency concentration uses true IA;
   - `pipeline/graph/build_graph.py` MP-to-Agency-to-Vendor nodes use true IA;
   - `api/routers/works.py` selects and, where appropriate, searches both fields;
   - `api/routers/entity_aliases.py` returns the intended context field explicitly;
   - web record/outcome types, inspection table, detail panel, deep links, and alias evidence use correct semantics and labels.
5. Extend `api/db.py` compatibility deliberately. The committed old Parquet has only an `implementing_agency` column, but its values are IDA data. In legacy mode, expose that old column as `implementing_district_authority` and expose true `implementing_agency` as null. Never keep presenting legacy IDA values under the new IA meaning. This behavior is an inference from the current deploy-before-rebuild constraint, not a spelled-out implementation choice in the approved document; record and test the chosen compatibility policy in the Step 5 DONE note.
6. Decide and test inspection-outcome migration semantics before editing `outcomes/store.py` or `inspection_outcome.schema.json`. The existing SQLite column named `implementing_agency` contains the old IDA meaning. A safe end-to-end fix likely needs a District Authority context column plus a nullable true-agency column, but old rows must not be silently reinterpreted. Use only temporary DBs in tests. Because inspection outcomes and R-06 alias candidates/reviews share the same physical database, seed both subsystems in the migration regression and prove the migration preserves candidate identity plus append-only alias review history.
7. Handle the committed legacy `graph.json` honestly. It is IDA-based. `api/routers/graph.py` currently returns the file without a semantic/version guard. Do not serve it as a true-IA graph after relabeling the rest of the product. Choose a backward-compatible guard, honest legacy label, or versioned artifact policy and cover it with tests; do not rebuild the real snapshot during development. This is also an inferred compatibility requirement and remains an unresolved implementation decision, not prior approval for one particular guard.
8. Update the existing frontend surfaces so a sampled work shows District Authority and Agency separately. Keep copy in `contracts/strings.json`. If satisfying the acceptance criterion requires a new layout or interaction beyond adding correctly labeled data to an existing surface, stop and record the need for a design pass instead of inventing one.
9. Re-run graph correctness tests and measure the representative true-IA graph path/rendering cost. F-02 path evidence must remain correct. Record node/edge counts and timing. F-17 remains deferred unless this measured result makes the Step 5 result unusable.
10. Run all relevant gates, obtain an independent review, add a Step 5 DONE note in the exact style of Steps 1 through 4, and create one conventional commit.

### Likely files for Step 5

This is an audit map, not permission to edit every file blindly:

- `05-App/contracts/normalized_record.schema.json`
- `05-App/contracts/inspection_outcome.schema.json`
- `05-App/contracts/fixtures/works.fixture.json`
- `05-App/contracts/strings.json`
- `05-App/contracts/validate.py`
- `05-App/pipeline/src/nidhinetra_pipeline/ingest/mplads_adapter.py`
- `05-App/pipeline/src/nidhinetra_pipeline/normalize/normalize.py`
- `05-App/pipeline/src/nidhinetra_pipeline/risk/detectors.py`
- `05-App/pipeline/src/nidhinetra_pipeline/graph/build_graph.py`
- `05-App/pipeline/src/nidhinetra_pipeline/build_snapshot.py`
- `05-App/pipeline/src/nidhinetra_pipeline/outcomes/store.py`
- Pipeline tests and conftest record factories that currently set only `implementing_agency`
- `05-App/api/src/nidhinetra_api/db.py`
- `05-App/api/src/nidhinetra_api/policy.py`
- `05-App/api/src/nidhinetra_api/routers/works.py`
- `05-App/api/src/nidhinetra_api/routers/inspections.py`
- `05-App/api/src/nidhinetra_api/routers/entity_aliases.py`
- API tests and temporary Parquet/SQLite fixtures
- `05-App/web/lib/types.ts`
- `05-App/web/lib/entity-aliases.ts`
- `05-App/web/components/inspection-list/InspectionTable.tsx`
- `05-App/web/components/detail-panel/DetailPanel.tsx`
- `05-App/web/components/fund-flow/AliasReviewQueue.tsx`
- Associated web tests
- `docs/designs/nemotron-audit-remediation.md`

### Step 5 acceptance criteria

- A synthetic raw record with different `IDA_NAME` and `IA_NAME` preserves both exactly under separate fields.
- A sampled source record can be traced to separately labeled District Authority and Agency values in the UI.
- Zero-expenditure works show a missing agency, not a copied authority.
- District quota/rank behavior remains grouped by IDA.
- Concentration and fund-flow behavior uses IA.
- Legacy snapshots boot without semantic mislabeling.
- Existing outcome rows cannot acquire a new meaning merely because a column was renamed.
- F-02 false-path tests remain green.
- Graph size/timing after the remap is measured and documented.

## 9. Next Step 6: F-09 control assignment

Finding: `F-09 — High: Control-group status is chosen by the client after the fact`.

Current behavior:

- `InspectionOutcomeRequest` accepts `in_control_sample` from the request body.
- `InspectionCapture.tsx` exposes a checkbox and sends that value.
- `record_inspection()` persists and echoes the client value.
- `test_in_control_sample_round_trips_true` explicitly protects the current unsafe behavior.

Minimum regression already specified by the engineering review:

- Add the failing API test first.
- A client-supplied `in_control_sample: true` must not be persisted as true.
- The server owns the stored and returned group.

The current UI checkbox and its contract copy explicitly tell an officer to choose the group. That control and claim must be removed or replaced by a truthful server-owned state as part of Step 6. Preserve the stored outcome flag and Reports grouping so server-created control assignments can still be analyzed. Tests that need control rows should seed or monkeypatch the server assignment boundary; they must not regain client ownership by posting `true`.

Important specification gap: the audit's full best fix is broader than merely ignoring the request field. It calls for assignment before inspection, a stored assignment run and inclusion probability, immutable group membership, and score blinding where practical. The approved remediation Next Step only says “server-assigned, not client-settable,” and its explicit regression covers ignoring the client value. Do not invent a randomization algorithm, assignment registry, or new UI in the Step 6 commit without first documenting and approving that design. R-05 remains a later backlog feature and describes the fuller assignment registry.

At minimum, audit these files when Step 6 begins:

- `05-App/api/src/nidhinetra_api/routers/inspections.py`
- `05-App/api/tests/test_inspections.py`
- `05-App/contracts/inspection_outcome.schema.json`
- `05-App/pipeline/src/nidhinetra_pipeline/outcomes/store.py`
- `05-App/pipeline/tests/outcomes/test_store.py`
- `05-App/web/components/detail-panel/InspectionCapture.tsx`
- `05-App/web/components/detail-panel/InspectionCapture.test.tsx`
- `05-App/web/lib/types.ts`
- `05-App/contracts/strings.json`

F-08: there is no unsupported precision/lift claim in the live app, so no code change is required. Any slide/deck audit is outside this handoff's authorization and the deck/PPT files remain forbidden.

## 10. Step 7 backlog, exact approved order

Only begin this after Steps 5 and 6 are complete. Follow the order in `nemotronreview.md` and create one logical commit per item or tightly coupled fix.

Findings:

1. F-05, Blocker: a single modal vendor is substituted for multi-vendor payment history.
2. F-07, High: the normalized schema drops fields needed for duplicate-work and audit-evidence problems.
3. F-10, High: outcome records are weakly validated and are not attributable.
4. F-11, High: snapshot refresh is not atomic as a release.
5. F-12, High: documented pipeline command and tests disagree.
6. F-13, Medium: peer-group gating suppresses absolute and network findings.
7. F-14, Medium: current anomaly features are too lossy for strong ML claims.
8. F-15, Medium: contamination does not calibrate the score as claimed.
9. F-16, Medium: global min-max scoring is snapshot-relative.
10. F-17, Medium: graph endpoint and frontend algorithm are unnecessarily expensive.
11. F-18, Medium: provenance is insufficient for audit use.
12. F-19, Medium: `make clean` can erase irreplaceable source evidence.
13. F-20, Medium: contracts claim generated types, but code generation is not operational.
14. F-21, Medium: no repository-owned continuous integration was found.
15. F-22, Low/conditional: CORS, headers, and read limits need deployment profiles.
16. F-23, Low/conditional: query input and connection hygiene can improve.

Features:

1. R-05: server-assigned stratified control and evaluation registry.
2. R-07: duplicate-work candidate explorer.
3. R-08: data-quality and detector-capability panel.
4. R-09: snapshot trends and change detection.
5. R-10: offline-first field inspection PWA.
6. R-11: evidence-backed compliance rules.
7. R-12: route planning and inspection workload board.
8. R-13: signed evidence docket export.

The approved plan does not put F-06 or R-01 through R-04 into Step 7. Do not silently broaden the list. R-06 is complete even though one stale sentence in the document says “see step 3”; its actual DONE entry is Step 4.

## 11. Definition of done for each remaining step

Before calling a step complete, all of the following must be true:

1. A focused regression was added first and observed failing for the intended missing behavior.
2. The smallest complete implementation is in place without unrelated cleanup.
3. All relevant full suites were run, including known baseline failures in the report.
4. Contract validation ran after every contract/fixture change.
5. Ruff or ESLint/TypeScript checks passed for touched files.
6. Browser behavior was checked when the change affects a user flow or rendering.
7. An independent code review found no unresolved critical, high, medium, or low issue.
8. `docs/designs/nemotron-audit-remediation.md` contains a dated DONE note matching the detail level and deferral format of Steps 1 through 4.
9. Only intentional paths are staged.
10. One conventional commit exists for the logical fix.
11. Nothing has been pushed without the user's explicit approval.

## 12. Copy-paste prompt for the next AI agent

```text
Continue the NidhiNetra Nemotron audit remediation in /Users/krish/Desktop/study/project/SIH on branch codex/finish-nidhinetra. First read docs/designs/nemotron-audit-remediation.md in full, then read docs/handoffs/nidhinetra-audit-remediation-handoff.md in full. Treat the remediation document as the approved spec and the handoff as the exact execution state. Steps 1-4 are complete; code commit d545e77 contains Step 4, followed only by the handoff documentation commit, and there is no Step 5 code in progress. Start with Next Step 5, the real F-01 IA_NAME versus IDA_NAME separation, using TDD and the file-by-file semantic map in the handoff. Preserve all unrelated dirty/untracked files; never touch forbidden key/Obsidian/deck files; never let tests or development runs write to the real snapshot, raw cache, or outcomes database; use the existing temporary-directory and monkeypatch isolation; never pull live MPLADS data; do not add dependencies without necessity; and do not push or perform destructive Git operations without asking. Run every prescribed full suite and validator, add the Step 5 DONE note, obtain an independent review, and make one conventional commit before moving to Step 6.
```

## 13. Handoff boundary

No F-01 implementation was started. No tests were modified for F-01. No real snapshot, raw cache, or outcomes database was written. The next agent can begin with the first failing ingestion test without reconciling a partial implementation.
