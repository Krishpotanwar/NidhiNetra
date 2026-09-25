# NidhiNetra Finish-and-Win Plan (SIH26102)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (inline) or superpowers:subagent-driven-development. Per task: superpowers:test-driven-development (red, then green). Before any "done" claim: superpowers:verification-before-completion. On a surprise failure: superpowers:systematic-debugging. Steps use `- [ ]`.
> Repo copy of this file: `docs/superpowers/plans/2026-09-26-finish-and-win.md` (T0 saves and commits it).

**Goal:** Win SIH26102 at the December 2026 Grand Finale. Close the problem statement's named gaps (automated compliance monitoring, early warning, role dashboards) with the least new code, while keeping the live prototype secure and its data honest.
**Architecture:** Unchanged. FastAPI + DuckDB read a committed Parquet snapshot. The `nidhinetra_pipeline` package builds offline artifacts. Next.js reads only the API. All copy lives in `05-App/contracts/strings.json`. New features are SQL predicates in the API, one small offline model artifact, and UI sections built from existing components. **No new dependencies.**
**Tech stack:** Python ≥3.11 (uv workspace `pipeline` + `api`), FastAPI, DuckDB, pandas, scikit-learn; Next.js 16.3.x, React 19.2, TypeScript 5, CSS Modules, Vitest.
**Spec:** this file (§0 context, §4 decisions), plus the AI roadmap `docs/superpowers/specs/2026-09-17-foundation-and-duplicate-works-design.md`, whose Stage B to D rules still bind T12.

---

## 0. Context (verified 2026-09-26)

- **Problem statement (MoSPI, SIH26102)** asks for: anomalies, cost overruns, duplicate works, delayed projects, risk-based alerts, predictive insights, early warning, automated compliance monitoring, trend analysis, and dashboards for MPs, State Nodal Authorities, District Authorities and the Ministry.
- **Built and on branch `codex/finish-nidhinetra`:**
  - Ranked 10% inspection queue: 4 named flags plus an IsolationForest/LOF ensemble worth at most 20 points.
  - Fund-flow Sankey.
  - Vendor alias review queue.
  - Identical-description duplicate queue (Stage C).
  - Inspection recording, and a Reports page with Wilson intervals.
  - Provenance.
  - Offline pair judge (Stage B), never run.
  - Live at nidhinetra.vercel.app and nidhinetra-api.onrender.com. `origin/main` is about 13 commits behind this branch.
- **Gaps closed by this plan:**
  1. No compliance or pendency view.
  2. The early-warning model exists only as a script.
  3. No role views.
  4. Next.js 16.3.4 carries a critical advisory (GHSA-vcvr-r3jv-pc5j, fixed in 16.3.6 on 2026-09-22). Nine more fixes land in 16.3.7 on 2026-09-30.
  5. The near-copy duplicate judge has never run.
- **Judge hook:** MoSPI already reviews three pendency indicators every month (PIB release 2153066, 06 Aug 2025):
  - works yet to be sanctioned beyond 45 days;
  - works not completed even after one year of sanction;
  - works where no payments have been made three months post-sanction.

  The matching Guidelines 2023 paragraphs:
  - Para 3.2.4: sanction or rejection within 45 days of receipt.
  - Para 3.2.12: a completion limit that should "generally not exceed one year", with hilly terrain as an allowed exception.
  - Para 10.6.1: works finished within 18 months of the MP demitting office.

  NidhiNetra automates MoSPI's own review, per District Authority, every day.
- **SIH timeline:**
  - 2026-09-30: national idea submission deadline.
  - October: screening. Evaluators may open the live link, so P0 is to keep it secure, deployed and warm.
  - November: shortlist.
  - December: Grand Finale, offline, 36 hours, several jury rounds, one winner per problem statement.
- **Win thesis:** NidhiNetra turns MPLADS's existing legal duties into a daily, explainable worklist:
  - MoSPI's three pendency checks;
  - each District Authority's 10% inspection duty (clause 4.5.2);
  - third-party inspection coverage (clause 4.4.2);
  - an early warning for works likely to pass one year;
  - duplicate-description batches.

  Every item traces to a clause and a public record, and nothing is accusatory.

## 1. Global constraints (bind every task)

1. **Copy.** Every user-visible string goes in `05-App/contracts/strings.json`, with one dated `_meta.amendment_log` line per task. `contracts/validate.py` enforces `lint`, which bans words including fraud, detect/detected/detection, suspicious, anomaly, verified, confirmed, compliant, passed, finding(s), misuse, irregular(ity), probability, likelihood, confidence, accuracy, clean, safe, green, investigate and "the model says". It also bans the em dash (U+2014) and emoji. Prefer these words: flagged, overdue, beyond the 45-day limit, open past one year, no payment recorded, early warning, at risk of running late. Name the population and the as-of date beside every number.
2. **Honesty.**
   - Never fabricate, synthesize or seed data on any screen.
   - A model output is an ordering, never a per-work chance.
   - The 0 to 100 risk score, ranks and flags must stay byte-identical (`scored.parquet` untouched) except in T13's rebuild.
   - If two readings of a guideline exist, state the narrower claim.
3. **Numbers.** Use the existing helpers in `web/lib/format.ts` (Indian grouping, Rs lakh or crore). Keep Latin digits in Hindi too: Constitution Art. 343(1) uses the international form of Indian numerals.
4. **Colour.** Green encodes nothing. Risk colours come from the existing tokens.
5. **Dependencies.** Add no npm or PyPI dependency. Use the native option: SVG or CSS for charts, `window.print()` for PDF, the existing Radix components for pickers, a string overlay instead of an i18n library.
6. **Tests first.** API tests never mock DuckDB or Parquet; use `api/tests/conftest.py`. Web tests use Vitest and Testing Library, following existing `*.test.tsx`.
7. **Data safety.**
   - Never write the real `05-App/data/outcomes/outcomes.db`.
   - Never start the API against the shared `05-App/data/`.
   - Never delete anything under `05-App/data/raw/`.
8. **Git.**
   - Never push, force, rebase, amend or `git add -A`. Untracked personal files sit at the repo root.
   - Stage explicit paths only.
   - Conventional message with the task id, e.g. `feat(api): pendency endpoint (T4)`.
   - End with the trailer `Co-Authored-By: <your model name> <noreply@anthropic.com>`.
9. **Scope.** Build only what a task says. Anything else goes to "Parked additions" in your final report.
10. **Stop and report, never improvise, when:**
    - a gate fails outside the task's files;
    - a measured number on the committed snapshot differs from §7 by more than 1%;
    - a step needs a human (§3), a credential or a new dependency.

## 2. Environment (Linux VM; `/media/psf/project/SIH` is shared with the owner's Mac)

- `05-App/.venv` and `05-App/web/node_modules` belong to the Mac. **Never** run `uv sync` or `npm ci`/`npm install` inside the shared folder.
- Begin every shell that runs a gate with `. ~/.cache/nidhinetra-vm/env.sh`. This provides the VM-only uv wrappers and `OPENBLAS_CORETYPE=ARMV8`, without which numpy crashes with SIGILL.
- **Python gates** (cwd `05-App`):
  - `uv run --package nidhinetra-pipeline python -m pytest pipeline/tests -q -p no:cacheprovider`
  - `uv run --package nidhinetra-api python -m pytest api/tests -q -p no:cacheprovider`
  - `uv run --package nidhinetra-pipeline python contracts/validate.py && uv run --package nidhinetra-pipeline python contracts/validate.py --self-test`
  - `uvx ruff check <changed .py> && uvx ruff format --check <changed .py>`. Run it on changed files only, because the tree has pre-existing findings.
- **Web gates** run in a VM mirror; edit only in the shared folder. In order:
  1. `web-gates npm run build` (generates Next types)
  2. `web-gates npx tsc --noEmit`
  3. `web-gates npm run lint`
  4. `web-gates npx vitest run`

  If `web-gates` exits 3 (lockfile changed): `cd ~/.cache/nidhinetra-vm/mirror/05-App/web && PATH=$HOME/.cache/nidhinetra-vm/node/bin:$PATH npm ci && cp package-lock.json .linux-lock-installed`.
- **Commit identity:** prefix the commit with the env vars `GIT_AUTHOR_NAME="Krish Potanwar" GIT_AUTHOR_EMAIL=kpotanwar@gmail.com GIT_COMMITTER_NAME="Krish Potanwar" GIT_COMMITTER_EMAIL=kpotanwar@gmail.com`. Never run `git config`.
- **Git base:** `origin/main`. Local `main` is unrelated history. Measure with `git log origin/main..HEAD`.
- **Resume:** `git log --oneline origin/main..HEAD | grep -o '(T[0-9]*[a-z]*)' | sort -u` lists the finished tasks; skip them.
- **Running the app** (visual checks only). Use a scratch dir `$S` (your session scratchpad).
  1. Copy the snapshot: `cp 05-App/data/snapshot/* $S/snap/`.
  2. Write a Python launcher that, before importing `nidhinetra_api.main`, repoints `db.SNAPSHOT_DIR`, `snapshot.SNAPSHOT_DIR` (both to `$S/snap`) and `snapshot.RAW_DIR` (to `$S/none`). It must also set `DEFAULT_DB_PATH` of `nidhinetra_pipeline.outcomes.store`, `alias_store` and `duplicate_store` to `$S/outcomes.db`, the same way `api/tests/conftest.py` does. Then call `uvicorn.run(app, port=8000)`.
  3. Run it with `uv run --package nidhinetra-api python <launcher>`.
  4. Web: `web-gates npm run build`, then `web-gates npx next start -p 3000` in the background.
  5. Screenshots: `cd $S/pw && npm i playwright-core`, using VM node on PATH. Launch Chromium with `executablePath: ~/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux-arm64/chrome-headless-shell` and `args: ["--no-sandbox"]`.
  6. Take viewport shots at 1920x1080 and 390x844. Assert `document.documentElement.scrollWidth === document.documentElement.clientWidth`.
  7. Stop servers by the PID shown in `ss -ltnp`. Never use `pkill -f`: it kills your own shell.

## 3. HUMAN-only (never attempt; list the pending ones in every final report)

- **H1.** By 2026-09-30, confirm the SIH national idea submission is filed through the college SPOC. The paste-ready text is `SIH Idea Submission - NidhiNetra.txt`.
- **H2.** After each phase, from the Mac:
  - run `git push origin codex/finish-nidhinetra:main`. It is a fast-forward and redeploys Vercel and Render;
  - after T1, also run `cd 05-App/web && npm ci` on the Mac.
- **H3.** For T12: export `HF_TOKEN` on the machine running the judge, confirm Hugging Face credit, and send the line `GO STAGE-B RUN <date>`.
- **H4.** Presenters rehearse the T14 script twice against a timer. One run must be watched by someone who did not build it.
- **H5.** Paste the T14 slide text into the PPTX and check it in PowerPoint, not LibreOffice.

## 4. Decisions (do not re-litigate)

| ID | Decision |
|---|---|
| D1 | Pendency counts cover **works under implementation** only: `completion_status IN ('Sanctioned','In Progress')`, which is `policy.UNDER_IMPLEMENTATION`. |
| D2 | `as_of` = the date part of `manifest.json` `data_as_of`. It is never today and never `max(last_updated)`. |
| D3 | Late sanction is measured from the portal's recommendation date. The receipt date is not published, and copy says so. |
| D4 | Pendency and early warning never touch score, rank or flags. They are separate facts. |
| D5 | Never show a combined "any pendency" count. It covers 87% of works and means nothing. |
| D6 | A role lens = preset scope + one duty sentence. No new pages and no new nav tab: nav stays at 4 (PRODUCT.md). |
| D7 | A District Authority's quota = `quota_for(n)` of its own works under implementation. The duty for a scope = the **sum of per-authority quotas** (4,820 nationally), stated as "rounded up per authority". QuotaCard's list cutoff (4,481) stays as is and answers a different question. |
| D8 | Early warning is rank-based: the top 10% of works under implementation sanctioned ≤365 days ago. It ships only if test ROC-AUC ≥ 0.65 and lift@10% ≥ 1.8. The API ignores the artifact if its `data_as_of` ≠ the manifest's. |
| D9 | Hindi uses an overlay on `STRINGS`. Data values stay as published, missing keys fall back to English, and reasons are translated by template inversion. |
| D10 | Reuse patterns: KpiCards → PendencyCards; the `entity_aliases`/`duplicates` routers → the `pendency` router; `cli duplicates` → `cli early-warning`; `write_duplicate_candidates` → the early-warning writer; `StateSelect` → the DA and constituency pickers. |
| D11 | Figures are regenerated once, in T13, from `scripts/deck_figures.py` and `scripts/delay_model.py`. Never hand-edit a number. The deck's "ROC-AUC 0.729" is stale: the script gives 0.672 on the current snapshot. |

## 5. Task queue (priority order; P0 before 2026-09-30)

### Task 0 (T0): Baseline (no product code)
- [ ] Read this plan, `PRODUCT.md`, and the `lint` block of `05-App/contracts/strings.json`.
- [ ] `git status --short`; confirm the branch is `codex/finish-nidhinetra`; run the §2 resume command.
- [ ] Run every §2 gate. Record the pipeline, api and web test counts. If a gate fails on a clean tree, stop and report (§1.10).
- [ ] If `docs/superpowers/plans/2026-09-26-finish-and-win.md` is not committed yet, commit it: `docs(plan): finish-and-win plan (T0)`.

### Task 1 (T1): Next.js security patch (P0)
Files: `05-App/web/package.json`, `05-App/web/package-lock.json`.
- [ ] `export PATH=$HOME/.cache/nidhinetra-vm/node/bin:$PATH; npm view next versions --json | tr -d '[]" ' | tr ',' '\n' | grep -E '^16\.3\.[0-9]+$' | sort -V | tail -1`. Use that version `<v>`; it must be ≥16.3.6. Never use 16.4 canaries.
- [ ] `web-gates true`, then `cd ~/.cache/nidhinetra-vm/mirror/05-App/web && npm install --save-exact next@<v> eslint-config-next@<v>`.
- [ ] `cp package.json package-lock.json /media/psf/project/SIH/05-App/web/ && cp package-lock.json .linux-lock-installed`.
- [ ] Run all four web gates. `git diff --stat` must show exactly those 2 files. Commit: `chore(web): next <v> security release (T1)`.
- [ ] If `<v>` < 16.3.7, add "T1b: repeat T1 once 16.3.7 is published (due 2026-09-30)" to the report.

### Task 2 (T2): Copy honesty fixes (P0)
Files: `05-App/contracts/strings.json`, `README.md`.
- [ ] `duplicate_review.context_threshold` claims "This group is due third-party inspection (MPLADS Guidelines 2023, clause 4.4.2)." That is wrong, because 4.4.2 is a per-work rule. Replace the value with exactly: `Every work in this group is under Rs 15 lakh and together they total Rs 25 lakh or more. Clause 4.4.2 of the MPLADS Guidelines 2023 makes third-party inspection compulsory for a single work of Rs 25 lakh or more.`
- [ ] README.md's tech-stack table claims strings exist "in English and Hindi". Change that part to "in English, with Hindi identity marks in Devanagari tagged `lang="hi"`". T11 reverts this once Hindi ships.
- [ ] Add an amendment_log line: `2026-09-26 (T2): duplicate_review.context_threshold restated as the clause's per-work rule plus the group's facts.`
- [ ] `grep -rn "due third-party" 05-App --include=*.ts* --include=*.py`. Any literal assertion must read from STRINGS instead.
- [ ] Run validate.py and the web vitest. Commit: `fix(copy): state clause 4.4.2 per work, not per group (T2)`.

### Task 3 (T3): Deploy readiness (P0, no code)
- [ ] All gates are green on HEAD. In the report, print H2 and the output of `git log --oneline origin/main..HEAD`.
- [ ] After the human push (next session, read-only):
  - `curl -s https://nidhinetra-api.onrender.com/health` returns 200.
  - `curl -s "https://nidhinetra-api.onrender.com/api/duplicates?page=1" | head -c 200` shows `"success":true`. A 404 means the push is not live yet.
  - Startup peak RSS measured locally is 407 MB, against Render free's 512 MB. If Render restarts with an out-of-memory error, record it and open a parked item: "slim the duplicate sync". Do not guess a fix.

### Task 4 (T4): Pendency API (P1)
Files:
- Modify: `api/src/nidhinetra_api/policy.py`, `snapshot.py`, `models.py`, `main.py`, `routers/works.py`, `contracts/openapi.yaml`
- Create: `api/src/nidhinetra_api/routers/pendency.py`, `api/tests/test_pendency.py`

All paths are under `05-App/`.

Produces:
```python
# policy.py
SANCTION_DAYS_LIMIT = 45      # Guidelines 2023 para 3.2.4
COMPLETION_DAYS_LIMIT = 365   # Guidelines 2023 para 3.2.12, "generally not exceed one year"
NO_PAYMENT_DAYS = 90          # MoSPI monthly pendency review, PIB release 2153066 (06 Aug 2025)
PENDENCY_KINDS = ("late_sanction", "open_past_one_year", "no_payment_90_days")
def pendency_clause(kind: str, as_of: str) -> tuple[str, list[str]]:  # ValueError on unknown kind
# snapshot.py
def data_as_of_date(snapshot_dir: Path | None = None) -> str | None:  # "YYYY-MM-DD" from read_manifest()["data_as_of"][:10]
```
SQL is built over the table alias `works`, using the constants above in f-strings:
- `late_sanction`: `works.recommendation_date IS NOT NULL AND works.sanction_date IS NOT NULL AND date_diff('day', CAST(works.recommendation_date AS DATE), CAST(works.sanction_date AS DATE)) > 45`. Params: `[]`.
- `open_past_one_year`: `works.sanction_date IS NOT NULL AND date_diff('day', CAST(works.sanction_date AS DATE), CAST(? AS DATE)) > 365`. Params: `[as_of]`.
- `no_payment_90_days`: `works.sanction_date IS NOT NULL AND date_diff('day', CAST(works.sanction_date AS DATE), CAST(? AS DATE)) > 90 AND coalesce(works.expenditure_amount_inr, 0) = 0`. Params: `[as_of]`.

Steps:
- [ ] **Test first.** In `test_pendency.py`, `test_pendency_clause_boundaries` uses an in-memory `duckdb.connect()`. Create table `works(work_id, recommendation_date, sanction_date, expenditure_amount_inr)` from literal rows. With as_of `2026-09-04`, pin each boundary:
  - 45 days → not late; 46 days → late.
  - Sanctioned 365 days before as_of → not open past one year; 366 days → yes.
  - 90 days + zero spend → not counted; 91 days + zero → counted; 91 days + spend 1.0 → not counted; 91 days + null spend → counted.
  - A null date is never counted.
  - An unknown kind raises ValueError.
- [ ] `models.py`: extend `WorksQuery` and `works_query` with:
  - `pendency: Literal["late_sanction","open_past_one_year","no_payment_90_days"] | None`
  - `district_authority: str | None` (Query max_length 200)
  - `constituency: str | None` (Query max_length 120)

  Drop blank values, as the existing fields do.
- [ ] `works.py` `_where`:
  - `district_authority` → `works.implementing_district_authority = ?`
  - `constituency` → `works.constituency = ?`
  - `pendency` → `(<clause>)` with its params, where `as_of = snapshot.data_as_of_date()`. If that is None, return 503 via `HTTPException`.
- [ ] `works.py` `work_facets`: add `district_authorities` (GROUP BY `implementing_district_authority`, non-null only) and `constituencies` (GROUP BY `constituency`, `mp_name`, as rows `{value, count, mp_name}`). Both use the same population clause.
- [ ] `works.py`: add a helper `_decorate(rows)`, called on the rows of both `_fetch_merged_by_ids` and `get_work`. It sets:
  - `days_to_sanction`: int or None, from the two dates;
  - `days_since_sanction`: int or None, from sanction_date to `as_of`.

  Use Python `date.fromisoformat`, with no SQL change.
- [ ] `routers/pendency.py`: `GET /api/pendency` takes `state` (repeatable), `district_authority`, `constituency` and `group_by` (`state|district_authority|constituency`, optional). Reuse `works._where` by building a `WorksQuery(scope="under_implementation", ...)`. Response `data`:
  ```json
  {"as_of":"2026-09-04","population_n":44810,"population_inr":24967306023.15,
   "kinds":{"late_sanction":{"count":0,"sanctioned_inr":0.0,"median_days_to_sanction":90},
            "open_past_one_year":{"count":0,"sanctioned_inr":0.0},
            "no_payment_90_days":{"count":0,"sanctioned_inr":0.0}},
   "district_authority_n":729,"quota_sum":4820,
   "third_party":{"at_or_above_25_lakh":986,"between_15_and_25_lakh":1739,"required_n":1856},
   "groups":null}
  ```
  Field rules:
  - `quota_sum` = `sum(policy.quota_by_group(<per-DA counts in scope>).values())`.
  - `required_n` = `a + ceil(b/2)`.
  - `groups` is null unless `group_by` is set; then it is a list of `{group, population_n, late_sanction, open_past_one_year, no_payment_90_days, quota_n}` sorted by population_n desc, then group asc.
  - Amounts are rounded to 2 decimals. Close every connection with `contextlib.closing`, as the other routers do.
- [ ] `main.py`: `app.include_router(pendency.router)`. `openapi.yaml`: document the new params and endpoint.
- [ ] Endpoint tests run on the conftest fixture snapshot:
  - For each kind, the list endpoint `pendency=<kind>&scope=under_implementation&page_size=200` returns `meta.total` equal to the summary count.
  - `groups` sum to the totals.
  - `district_authority=X` gives `meta.total` equal to the fixture count for X, and `meta.quota_n == quota_for(total)`.
  - A bad `pendency` or `group_by` returns 422.
  - Facets include both new lists.
  - The detail and list rows carry `days_to_sanction` and `days_since_sanction`, equal to an independent computation from `works_fixture`.
- [ ] Self-check against the real snapshot. Use a read-only DuckDB query on `05-App/data/snapshot/works.parquet` with the same clauses; the numbers must match §7. Then run the gates and ruff on the changed files. Commit: `feat(api): pendency checks, district and constituency scope (T4)`.

### Task 5 (T5): Pendency on screen (P1)
Files:
- Modify: `web/lib/{types.ts,data.ts,filters.ts}`, `web/lib/filters.test.ts`, `web/components/dashboard/DashboardClient.tsx`, `web/components/filters/FilterPanel.tsx`, `web/components/detail-panel/{DetailPanel.tsx,DetailPanel.test.tsx}`, `contracts/strings.json`
- Create: `web/components/dashboard/{PendencyCards.tsx,PendencyCards.module.css,PendencyCards.test.tsx}`

Consumes T4.

- [ ] `filters.ts`: `FilterState` gains `pendency: string` (ALL or one of the kinds), `districtAuthority: string` (ALL or a value) and `constituency: string` (ALL or a value). Update `EMPTY_FILTERS`, `isFilterActive`, `filtersToQuery` (URL params `pendency`, `district_authority`, `constituency`) and `readListParams` (reject an unknown pendency → ALL). `tsc` lists every literal FilterState to fix.
- [ ] Tests first in `filters.test.ts`: round-trip the 3 new params, and check that an unknown pendency becomes ALL.
- [ ] `types.ts`:
  - Add `PendencySummary`, matching T4's JSON.
  - `InspectionRow` gains `days_to_sanction: number | null` and `days_since_sanction: number | null`.
  - `FacetOption` gains an optional `mp_name?: string`.
  - `Facets` gains `district_authorities` and `constituencies`.
- [ ] `data.ts`: `fetchPendency(filters: FilterState, signal?: AbortSignal): Promise<PendencySummary>` calls `GET /api/pendency` with scope params only: `state` (repeatable), `district_authority`, `constituency`. Never send year, category, flag or pendency: the cards describe a scope (ruling R3).
- [ ] Add a `strings.json` block `pendency`. Use exactly these values; the `_note` must cite PIB 2153066 and Guidelines 2023 paras 3.2.4 and 3.2.12:
  - `title`: "Timelines against the guidelines"
  - `lede`: "The three pendency checks the Ministry reviews every month, for every work under implementation as of {date}."
  - `late_sanction_label`: "Sanctioned after 45 days"
  - `late_sanction_context`: "Sanctioned more than 45 days after the MP's recommendation (para 3.2.4 counts from receipt). Median {days} days."
  - `open_past_one_year_label`: "Open past one year"
  - `open_past_one_year_context`: "Still under implementation more than a year after sanction. Para 3.2.12 sets a general limit of one year."
  - `no_payment_label`: "No payment after 90 days"
  - `no_payment_context`: "Sanctioned more than 90 days ago with no payment in the captured expenditure record."
  - `value_line`: "{count} works, {amount} sanctioned"
  - `view_list`: "View these works"
  - `filter_label`: "Timeline"
  - `filter_all`: "All timelines"
  - `detail_title`: "Timelines against the guidelines"
  - `detail_days_to_sanction`: "Sanctioned {days} days after recommendation. Limit 45 days, para 3.2.4."
  - `detail_open`: "Open {days} days after sanction. General limit 365 days, para 3.2.12."
  - `detail_no_payment`: "No payment recorded {days} days after sanction."
  - `detail_payment_seen`: "Payments recorded."
  - `detail_dates_missing`: "Recommendation or sanction date not published for this work."
  - `caveat`: "The expenditure record was captured on {date} and may be incomplete. A missing payment is a prompt to check."
- [ ] `PendencyCards({summary, status, onRetry, filters})`: tests first (three formatted counts, links carry `pendency=<kind>`, loading skeleton, error with retry). Three tiles styled like KpiCards (copy the CSS module and trim it). Each shows:
  - the label;
  - `formatIndianInt(count)`;
  - the value line with `formatCurrencyCrore(sanctioned_inr)`;
  - the context sentence (median days goes in via `renderTemplate`);
  - a link via `inspectionListHref({...EMPTY_FILTERS, states: filters.states, districtAuthority: filters.districtAuthority, constituency: filters.constituency, pendency: kind})`. It carries scope + pendency only, so the card count equals the list total (ruling R3; T6 adds `view` to this spread).

  The caveat goes under the row, with the date from `formatDate(summary.as_of)`.
- [ ] `DashboardClient`: `useApiResource(fetchPendency(filters))`, rendering `<PendencyCards>` directly below `<KpiCards>`.
- [ ] `FilterPanel`: a `SelectControl` "Timeline" with ALL plus the 3 kinds, placed after the flag select.
- [ ] `DetailPanel`: a section `detail_title` after the peer group and before "Record as published". It shows:
  - `detail_days_to_sanction` if `days_to_sanction` is not null;
  - `detail_open` if the work is under implementation and `days_since_sanction` > 365;
  - `detail_payment_seen` if `expenditure_amount_inr` > 0; `detail_no_payment` if `expenditure_amount_inr` == 0 and `days_since_sanction` > 90; otherwise no payment line (ruling R4: never claim payments for a zero-spend work);
  - `detail_dates_missing` when the dates are null.

  Add tests for each branch.
- [ ] Gates, plus a visual check (§2) at 1920 and 390 with no sideways scroll. Commit: `feat(web): pendency cards, timeline filter and panel section (T5)`.

### Task 6 (T6): Role lenses (P1)
Files: `web/components/filters/{FilterPanel.tsx,StateSelect.tsx}`, `web/lib/filters.ts` (+test), create `web/components/dashboard/{DutyLine.tsx,DutyLine.test.tsx}`, `web/components/{dashboard/DashboardClient.tsx,inspection-list/InspectionListClient.tsx}`, `contracts/strings.json`.
- [ ] `StateSelect`: add optional props `single?: boolean` (a choice closes the popover and replaces the value), `allLabel?: string` and `optionLabel?: (o: FacetOption) => string`. The defaults keep today's behaviour exactly, and the existing tests must pass unchanged. Do not rename the component.
- [ ] `FilterState.view`: `"ministry" | "state" | "district" | "mp"`, default `"ministry"`, URL param `view` (unknown → ministry). Switching the lens clears `states`, `districtAuthority` and `constituency`.
- [ ] `FilterPanel`: a `Segmented` "View as" control (Ministry / State Nodal Authority / District Authority / Member of Parliament) comes first. Show only the matching scope picker:
  - state: the current multi `StateSelect`;
  - district: `StateSelect single` over `facets.district_authorities`;
  - mp: `StateSelect single` over `facets.constituencies`, with the label `"{constituency}, {mp_name}"` through `displayName()`.
- [ ] `DutyLine({view, pendency}: {view: FilterState["view"]; pendency: PendencySummary | null})`: one sentence, rendered under QuotaCard on the Dashboard and under SummaryLine on the list. Every number comes from `pendency`, which is scope-only (ruling R5). The district sentence uses `{quota}` = `pendency.quota_sum` and `{n}` = `pendency.population_n`, and the MP sentence uses `pendency.population_n`. Works-page meta is never used, because it moves with the flag and category filters. The list page also fetches `fetchPendency(filters)`. Render nothing while `pendency` is null. Add a `strings.json` block `lens` containing:
  - `view_label` "View as"
  - `ministry` "Ministry"
  - `state` "State Nodal Authority"
  - `district` "District Authority"
  - `mp` "Member of Parliament"
  - `all_district_authorities` "All District Authorities"
  - `choose_constituency` "Choose a constituency"
  - `duty_ministry` "Each District Authority owes its own 10 percent, rounded up. Across the {da_n} authorities in view that is {quota_sum} inspections this year (clause 4.5.2)."
  - `duty_state` "Third-party inspection, clause 4.4.2: all {n25} works of Rs 25 lakh or more and half of the {n15} works between Rs 15 and 25 lakh, {required} in all. State officials also inspect at least 1 percent of works by value in each district (clause 4.4.1)."
  - `duty_district` "Clause 4.5.2: this District Authority inspects at least {quota} of its {n} works under implementation this year. The list below is ordered for that."
  - `duty_mp` "{late} of this constituency's {n} works under implementation were sanctioned more than 45 days after recommendation, and {open} are open more than a year after sanction."
- [ ] Tests: a DutyLine sentence per lens with numbers; a lens switch clears the other scopes and shows the right picker; the URL round-trips `view`, `district_authority` and `constituency`.
- [ ] Gates, plus a visual check of each lens. Commit: `feat(web): role lenses for Ministry, State, District Authority and MP (T6)`.

### Task 7 (T7): Printable inspection plan (P1)
Files: `web/components/inspection-list/InspectionListClient.tsx` (+test), `web/app/globals.css`, `contracts/strings.json`.
- [ ] Tests first:
  - A "Print this list" button calls `window.print` (`vi.spyOn(window,"print").mockImplementation(()=>{})`).
  - With `districtAuthority` set, the works request uses `pageSize` 100, so one page holds any authority's whole quota (max 82 today). Otherwise it stays at 50.
- [ ] Button (`data-print="hide"`) plus a print-only header (`className="print-only"`). The header shows: the DutyLine sentence, "Data as of {date}", and `STRINGS.framing.standing_note`. Add strings `print.button` "Print this list" and `print.as_of` "Data as of {date}".
- [ ] `globals.css`:
  - `.print-only{display:none}`
  - `@media print{ header,footer,nav,[data-print="hide"]{display:none!important} .print-only{display:block} body{background:#fff} table{width:100%;font-size:10pt} tr{break-inside:avoid} a{color:inherit;text-decoration:none} }`

  Hide the filter panel and the detail panel with `data-print="hide"` on their roots.
- [ ] Visual check: Playwright `page.pdf({format:"A4"})` of `/inspections?view=district&district_authority=<a real DA>`. The PDF must have no nav and show the rank, work, reason and amount columns. Commit: `feat(web): print an inspection plan (T7)`.

### Task 8 (T8): Early warning (P1)
Dispatched in two parts (ruling R7). **Part A** is the pipeline: module, tests, CLI and the real-snapshot artifact. **Part B** is the API and web. Each part gets its own review.
Files:
- Create: `pipeline/src/nidhinetra_pipeline/early_warning.py`, `pipeline/tests/test_early_warning.py`
- Modify: `pipeline/src/nidhinetra_pipeline/cli.py`, `api/src/nidhinetra_api/{snapshot.py,models.py,policy.py,routers/works.py,routers/pendency.py}`, create `api/src/nidhinetra_api/routers/early_warning.py` (+ `main.py` include), `api/tests/test_early_warning_api.py`, `web/...` (FilterPanel option, DetailPanel line, `components/reports/ReportsClient.tsx` method note), `contracts/strings.json`
- Artifact: `data/snapshot/early_warning.json` (committed)

Produces:
```python
MODEL_VERSION = "early_warning_v1"
NUMERIC = ["log_sanctioned", "agency_prior", "sanction_month"]   # exposure_months is excluded on purpose: it only says a work is young
CATEGORICAL = ["work_category", "state"]
AGENCY_PRIOR_SMOOTHING = 20; WATCH_SHARE = 0.10; MIN_TEST_AUC = 0.65; MIN_TEST_LIFT = 1.8
def build(works: pd.DataFrame, as_of: date) -> dict: ...        # deterministic
def write(artifact: dict, snapshot_dir: Path | None = None) -> Path:  # mirror build_snapshot.write_duplicate_candidates, using _stage_json + _commit_staged
```
Algorithm, ported from `scripts/delay_model.py`:
1. `sd = to_datetime(sanction_date)`; drop NaT; `y = completion_status != "Completed"`.
2. Windows: `start = as_of - DateOffset(months=26)`, `cutoff = as_of - 20 months`, `end = as_of - 17 months`. For 2026-09-04 these are 2024-07-04, 2025-01-04 and 2025-04-04. The cohort is `start ≤ sd ≤ end`; train is `sd < cutoff`; test is `sd ≥ cutoff`.
3. `agency_prior`: the smoothed mean of y by `implementing_agency` over works with `sd < cutoff`. A null or unseen agency gets that history's global rate. Other features: `log_sanctioned = log1p(sanctioned_amount_inr)`, `sanction_month = sd.month`.
4. `Pipeline(ColumnTransformer([("n", StandardScaler(), NUMERIC), ("c", OneHotEncoder(handle_unknown="ignore", min_frequency=30, sparse_output=False), CATEGORICAL)]), LogisticRegression(max_iter=2000))`.
5. Test metrics: `roc_auc`, `average_precision`, `base_rate`, and `lift_at_10` = (mean y over the top 10% by score) / base_rate. Round to 3 decimals.
6. If `roc_auc < 0.65 or lift_at_10 < 1.8`: `status="not_shipped"` and `watch=[]`. Otherwise refit on the whole cohort, with the prior computed from works where `sd ≤ end`. Score the "young" works: `completion_status in STALLABLE_STATUSES` (import from `risk.detectors`) and `0 ≤ (as_of - sd).days ≤ 365`. Sort by score desc, then work_id asc. `watch` = the first `ceil(0.10 × n)` work_ids.
7. Artifact: `{model_version, data_as_of, status, cohort:{start,train_cutoff,end,train_n,test_n}, features, metrics, scored_n, watch_n, watch}`.
- [ ] Tests first, on synthetic frames only:
  - For as_of 2026-09-04, the windows equal the three dates above.
  - Determinism: building twice gives an identical dict.
  - Pure-noise labels (`np.random.default_rng(0)`) → `not_shipped`.
  - Labels driven by agency → `shipped`, `roc_auc > 0.8`, `watch_n == ceil(0.1*young_n)`, `watch ⊆ young`, and no completed work in watch.
  - Changing `expenditure_amount_inr` does not change the output (leakage guard).
  - `json.dumps(artifact, allow_nan=False)` succeeds.
- [ ] CLI: `python -m nidhinetra_pipeline.cli early-warning [--write]` reads `works.parquet`, takes as_of from `manifest.json`, prints the metrics JSON, and writes only with `--write`. Mirror `duplicates()` in `cli.py`, with a test in `pipeline/tests/test_cli.py` style.
- [ ] Run it on the real snapshot with `--write`. Expect roc_auc 0.64 to 0.72, lift 2.0 to 2.6, scored_n ≈ 33,954, watch_n ≈ 3,396. If it comes back `not_shipped`, keep the artifact, skip every UI step below and record the metrics.
- [ ] API:
  - `snapshot.read_early_warning()` returns the artifact, cached by file mtime, or None when the file is missing, its `data_as_of` ≠ the manifest's, or its status ≠ `shipped`.
  - `_decorate` sets `row["early_warning"] = work_id in watch_set`.
  - `pendency=early_warning` in the Literal. `works._where` special-cases it before calling `policy.pendency_clause`, which stays guideline-only (ruling R6). The clause is `list_contains(?::VARCHAR[], works.work_id)` bound to the watch list, or `FALSE` when the artifact is None.
  - `GET /api/early-warning` returns the artifact without `watch`, or `data: null`.
  - The pendency summary adds `early_warning_n` (null when unavailable).
  - Tests: a fixture artifact written into the conftest snapshot dir; a stale `data_as_of` → None.
- [ ] Web:
  - `types.ts`: `InspectionRow` gains `early_warning?: boolean`. Add `EarlyWarningMeta` (the artifact minus `watch`).
  - `data.ts`: `fetchEarlyWarning(signal?): Promise<EarlyWarningMeta | null>`.
  - `filters.ts`: add `early_warning` to the pendency whitelist that `readListParams` accepts (ruling R6).
  - The FilterPanel adds the option "At risk of running late" only when `/api/early-warning` returns data.
  - The DetailPanel timeline section adds the `early_warning.detail` line when `row.early_warning`.
  - Reports gets a "How the early warning works" paragraph.
  - Add a strings block `early_warning`:
    - `filter`: "At risk of running late"
    - `detail`: "Early warning: among the tenth of recent works that a model trained on earlier sanctions ranks most at risk of staying open past one year."
    - `method_title`: "How the early warning works"
    - `method`: "Logistic regression on sanctioned amount, the implementing agency's record, category, state and sanction month. Trained on works sanctioned {start} to {cutoff} and checked on {cutoff} to {end}: its top tenth held {lift} times the average share of works still open (ROC-AUC {auc}). It orders works. It says nothing certain about any one of them."
- [ ] Gates, then commit in two parts: `feat(pipeline): early-warning artifact (T8)`, then `feat(api,web): early warning in list, panel and reports (T8)`.

### Task 9 (T9): Keep old portal captures on every pull (P2)
Files: `pipeline/src/nidhinetra_pipeline/cli.py` (`_write_tiles_atomically`, `pull_live` docstring), `pipeline/tests/test_cli.py`.
- [ ] Test first: after a second write, the old file's bytes sit at `raw/archive/<old mtime as UTC %Y%m%dT%H%M%SZ>/<name>`. Nothing is ever deleted, and an existing archive name gets suffix `.1`, `.2`.
- [ ] Before each `os.rename(tmp, final)`, if `final` exists, `os.replace(final, archive_dir / final.name)`.
- [ ] Docstring fact: on 2026-09-26 the portal answered from this VM (the owner's home network). The "datacenter tarpit" note stays true for CI. Commit: `fix(pipeline): archive the previous capture before a live pull replaces it (T9)`.

### Task 10 (T10): Carry three more portal fields (P2; follow `docs/superpowers/plans/2026-09-17-phase-0-source-fields.md` exactly)
Fields are required keys with nullable values:
- `work_stage` = `_clean(WORK_STAGE)` from the Sanctioned tile. Six values today: Sanction, Time Estimation, Vendor Identification, Physical Inspection, Work partially Completed, Work Completed.
- `completion_date` = `_parse_ddmmmyyyy(ACTUAL_END_DATE)` from the Completed-tile row with the same `WORK_RECOMMENDATION_DTL_ID`, else null.
- `has_public_document` = `True` if the Sanctioned row's `FILE_STATUS` is truthy, `False` if the key is present and falsy, null if the key is absent.

Touch: `contracts/normalized_record.schema.json`, `ingest/mplads_adapter.py`, `normalize/normalize.py`, `api db.py` (legacy projection `CAST(NULL AS …)`), `routers/works.py` `_MERGED_SELECT`, `web/lib/types.ts` + drift tests, `contracts/fixtures/works.fixture.json` (and regenerate the dependent fixtures the way Phase 0 did), and the DetailPanel "Record as published" rows plus `strings.json` labels ("Stage on the portal", "Completed on", "Documents on the public dashboard").
- [ ] Ranking equivalence: `scored.parquet` stays byte-identical on a pinned as_of rebuild, done in scratch, never on the real snapshot. The committed snapshot shows these fields as "Not published in this snapshot" until T13. Commit: `feat: carry work stage, completion date and document presence (T10)`.

### Task 11 (T11): Hindi and English (GIGW 3.0 requires Hindi and English on central government sites) (P2)
Dispatched in two parts (ruling R8). **Part A** is the infrastructure: overlay, LocaleRoot, toggle, `Str`, `"use client"` switches, and validate.py Hindi lint plus its self-test, with a seed `strings.hi.json` covering `nav` and `brand`. **Part B** is the full translation, `translateReason`, the README and the visual check.
Files:
- Create: `contracts/strings.hi.json`, `web/components/shell/{LanguageToggle.tsx,LocaleRoot.tsx,Str.tsx}` (+tests)
- Modify: `web/lib/strings.ts`, `web/app/layout.tsx`, `web/components/shell/{AppHeader.tsx,AppFooter.tsx}`, `web/components/dashboard/DashboardHero.tsx`, `web/app/**/page.tsx` (visible strings only), `contracts/validate.py`, `README.md`

Steps:
- [ ] **Overlay:** `strings.ts` keeps `STRINGS` as the live object and exports `setLocale(l: "en"|"hi")`. It walks the English tree, deep-copied once at load, and overwrites each string leaf in place from `strings.hi.json`, falling back to English. It skips `_`-prefixed keys, arrays, `lint`, `number_format` and `_measure`.
- [ ] **Root:** `LocaleRoot` is a client component. It starts in `"en"` so hydration matches, reads `localStorage["nn.locale"]` or `?lang=hi` in an effect, calls `setLocale`, sets `document.documentElement.lang`, and renders `<Fragment key={locale}>{children}</Fragment>` so everything re-reads STRINGS. Wrap AppHeader, main and AppFooter in it inside `layout.tsx`.
- [ ] **Server rendering:** these server components render STRINGS on the server: AppHeader, AppFooter and DashboardHero (add `"use client"`), plus visible text in `app/*/page.tsx` and `not-found.tsx` (replace it with `<Str k="a.b.c" />`, a client component that renders a STRINGS path). `metadata` titles stay English.
- [ ] **Reasons:** `translateReason(sentence)` goes in `strings.ts`. For each English `why_flagged` template, build an anchored regex with `{param}` → `(.+?)`. On a match, render the Hindi template with the captured params; with no match, return the English sentence. Test: every template round-trips.
- [ ] **Toggle:** `LanguageToggle` in AppHeader is a button showing "हिन्दी" / "English", with `aria-label="Language / भाषा"`.
- [ ] **Glossary** (use exactly):
  - MPLADS: एमपीलैड्स
  - Member of Parliament: संसद सदस्य
  - District Authority: जिला प्राधिकारी
  - Implementing Agency: कार्यान्वयन एजेंसी
  - State Nodal Authority: राज्य नोडल प्राधिकारी
  - Ministry of Statistics and Programme Implementation: सांख्यिकी और कार्यक्रम कार्यान्वयन मंत्रालय
  - work: कार्य
  - sanctioned: स्वीकृत
  - recommendation: अनुशंसा
  - under implementation: कार्यान्वयनाधीन
  - inspection: निरीक्षण
  - inspection list: निरीक्षण सूची
  - risk score: जोखिम अंक
  - flagged: चिह्नित
  - peer group: तुलना समूह
  - fund flow: निधि प्रवाह
  - vendor: विक्रेता
  - constituency: निर्वाचन क्षेत्र
  - expenditure: व्यय
  - lakh: लाख
  - crore: करोड़
  - third-party inspection: तृतीय पक्ष निरीक्षण
  - early warning: पूर्व चेतावनी
  - Guidelines: दिशानिर्देश
  - para: पैरा
  - clause: खंड
- [ ] **Lint:** add `lint.banned_hi` = धोखाधड़ी, धोखा, भ्रष्टाचार, भ्रष्ट, संदिग्ध, घोटाला, फर्जी, दुरुपयोग, अनियमितता, अनियमित, गबन, दोषी, सत्यापित, पुष्टि, संभावना, प्रायिकता, सटीकता, स्वच्छ, सुरक्षित, जांच, पता लगाया. `validate.py` lints `strings.hi.json` with the same character rules plus `banned_hi`. It checks that every hi key path exists in en and that the `{placeholder}` sets are identical. Add a self-test case.
- [ ] Tests: the toggle switches the nav to Hindi; `html[lang="hi"]`; fallback to English for a missing key.
- [ ] Visual check of every page in Hindi at 390px (Devanagari is wider), with no sideways scroll. README: the bilingual claim becomes true. Commit: `feat(web): Hindi and English interface (T11)`.

### Task 12 (T12): Near-copy duplicate judge (P2; gated on H3; else skip and list H3)
- [ ] Hugging Face docs were re-checked 2026-09-26. Provider-scoped routes (`https://router.huggingface.co/<provider>/v1`) and `json_schema` with `strict: true` are still documented, so `judge/runner.py` needs no change. Never use `:fastest` or `:cheapest`.
- [ ] Run Task 7 of `docs/superpowers/plans/2026-09-22-phase-1-stage-b-pair-judge.md` exactly: a 2-request trial with `--max-usd 0.05`. Then `cli judge --run --max-usd 3` (resumable; the spec estimates $1 to $2).
- [ ] Before any code, use superpowers:writing-plans to write `docs/superpowers/plans/<date>-stage-d-lite.md` from the spec's sections "From a text answer to a work-level candidate" and "What reaches the officer". Scope:
  - `work_candidate_derivation_v1` exactly as frozen in the spec;
  - `duplicate_store` sync widened to judged `same_asset_same_place` pairs whose both-side quotes are verified;
  - a queue label "Near-identical descriptions, read by a model, quotes checked by code".

  No two-model reference panel. Report only the abstention and quote-rejection rates, and never an agreement or "accuracy" figure. Record in that plan that this widens Stage C Decision 1 on the spec's own rule. Then execute it.

### Task 13 (T13): Finale data refresh (P1; run once 7 to 10 days before the finale; needs T9)
- [ ] `cli pull-live` from this VM. On failure, stop and keep the old data.
- [ ] Then, in order: `cli build`, `cli duplicates --write`, `cli early-warning --write`, `make validate`, all gates.
- [ ] `uv run --package nidhinetra-pipeline python scripts/deck_figures.py > $S/figures.txt` and `scripts/delay_model.py`.
- [ ] Update every figure in `README.md` and the T14 script from those outputs, never by hand. Commit data and docs: `chore(data): snapshot as of <date> (T13)`.
- [ ] Optional Rajya Sabha probe (the dashboard's Rajya button sends combo `"0,0,0,1"`): fetch only the Sanctioned tile to `$S`, count the rows, and check whether `WORK_RECOMMENDATION_DTL_ID` intersects the Lok Sabha ids. Report only; merging houses changes every population figure, so it becomes a new task.

### Task 14 (T14): Demo kit (P1; after T5 to T8)
- [ ] `04 Prototype/Finale Demo Script.md` (≤150 lines) contains:
  - a 10-minute click path with lines to say, per role lens;
  - a 3-minute cut;
  - an offline fallback: on the laptop, `make demo`, then turn Wi-Fi off and re-check;
  - Q&A additions:
    - "74% sanctioned after 45 days?" The median is 90 days, a systemic delay, so it is shown per authority rather than as a work flag;
    - "4,481 vs 4,820?" One is the list's 10% line; the other is each authority's own 10%, rounded up;
    - "Why logistic regression?" About 5,000 labelled works and 5 features; it beat gradient boosting; its coefficients explain;
    - "Is 0.68 good?" It orders. Its top tenth holds 2.3 times the average share of late works.
- [ ] A silent walkthrough video. Playwright `recordVideo` at 1920x1080 follows the script's path and writes `docs/demo/walkthrough.webm`. Keep it under 25 MB, or store it outside git and note the path. ffmpeg ships at `~/.cache/ms-playwright/ffmpeg-1011`.
- [ ] Refresh `docs/screenshots/*.png` and add `pendency.png`, `district-lens.png` and `hindi.png` (if T11). Write slide text for H5: 3 bullets per new feature.

### Task 15 (T15): 36-hour finale build menu (write only, into the T14 file)
Six increments, each ≤2 hours and visible in the demo, to build live between jury rounds:
1. A state league table from `GET /api/pendency?group_by=state` on Reports.
2. A District Authority league table (top 20 by open past one year).
3. The top 3 logistic-regression coefficients behind a work's early warning.
4. A Hindi print view (if T11).
5. One jury-requested filter.
6. The T13 live pull on stage, if the venue network allows.

## 6. Parked (do not build; each has a trigger)

| Item | Why | Trigger |
|---|---|---|
| India map or choropleth | Official-boundary risk before a government jury | MoSPI supplies boundary files |
| Chatbot, NL query, model prose to officers | Spec principle: no model prose reaches an officer | Never for this finale |
| Document or photo reuse detection (public `POST /rest/PreLoginDashboardData/getAttachIdsbyFlag {"json":{"FLAG":"3","WORK_ID":<id>}}` → `POST /rest/PreLoginCitizenWorkRcmdRest/getAttachmentById%20 {"id":…}` returns base64) | The one probed file was a 19-page scanned contract; about 25k works × MBs is heavy on a government server | Finale buffer: a 300-work sample at 1.5 s per request, pHash of page images, labelled as a sample |
| Citizen ratings (`AVERAGE_RATING`) | 4 of 34,258 completed works are rated | Rating coverage reaches 10% |
| R-05 control registry, R-10 PWA, R-12 routes, R-13 signed dockets, auth | Each needs a design or a policy | A written design is approved |
| TypeScript 7, React 19.3, other majors; Actions v7 bumps | CI was green 2026-09-22 under forced Node 24 | A CI failure that names Node 20 |
| Phase 0 leftovers (fixture contradictions, `_clean()` line breaks, dead `_REQUIRED_FIELDS`, `EXPENDITURE_DATE` guard); Stage A Decision 10 | Not visible to the jury | After the finale |
| Slimming the duplicate artifact at startup | 407 MB peak vs 512 MB | Render OOM (T3) |

## 7. Verified numbers (committed snapshot, `data_as_of` 2026-09-04; used by the self-checks)

- **Works:**
  - 79,068 works; 44,810 under implementation (Rs 2,496.73 cr); 36 states and UTs; 535 constituencies, one MP each.
  - 729 District Authorities hold works under implementation. The largest holds 813 works (quota 82); the median holds 39 (quota 4). Only 2 have a quota over 50.
  - National quota: 4,481. Sum of per-authority quotas: 4,820.
- **Pendency (under implementation):**
  - late_sanction: 33,204 works (Rs 1,810.69 cr); median 90 days to sanction.
  - open_past_one_year: 10,856 (Rs 596.24 cr).
  - no_payment_90_days: 17,441 (Rs 906.87 cr).
  - Any of the three: 39,007 (not shown, per D5).
- **Third party:** 986 works at or above Rs 25 lakh; 1,739 between Rs 15 and 25 lakh; 1,856 required.
- **Early-warning feasibility** (script cohort, no exposure feature):
  - train 5,108, test 8,538, base rate 0.231, ROC-AUC 0.677, PR-AUC 0.429, lift@10% 2.32.
  - Young works under implementation (≤365 days): 33,954.
- **Raw tiles:**
  - All rows are 18th Lok Sabha (house 2).
  - Sanctioned rows carry WORK_STAGE (six values) and FILE_STATUS/ATTACH_ID (24,955).
  - The Completed tile carries ACTUAL_END_DATE (34,258).
  - The expenditure tile is salvaged and incomplete.
- **Reachability:** the MPLADS portal answers from this VM (2026-09-26); the `mplads.gov.in` guidelines host does not.
- **API:** peak RSS 407 MB at startup (VM, Python 3.13).

## 8. Final report format (every session, ≤25 lines)

- Tasks done, with commit SHAs.
- Gate counts: pipeline, api, web, validate.
- Measured versus §7.
- HUMAN items pending (H1 to H5).
- Parked additions.
- Next task id.
