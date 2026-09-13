---
tags: [sih2026, plan, prototype]
ps: SIH26102
solution_name: NidhiNetra
created: 2026-09-01
---

# Implementation Plan: NidhiNetra Application Build

**Status:** planning complete, not started
**Builder:** Sonnet, via subagent waves
**Governs:** [[04 Prototype/Execution Plan|Execution Plan]] contracts, [[04 Prototype/Checkpoints|Checkpoints]] CP0 to CP7
**Design source of truth:** `NIDHINETRA-DESIGN-BRIEF.md` (vault root)

> **Kid version:** this is the build order. It says where every file goes, what each of the six agents does, and in what order they are allowed to start so they never trip over each other. Read section 5 if you only read one thing.

---

## 0. Decisions locked this session

| Question | Answer | Consequence |
|---|---|---|
| Where does code live | Subfolder in the vault: `05-App/` | Obsidian must be told to ignore it, see §1.3. Non-negotiable, or the vault hangs. |
| Database | DuckDB + Parquet | Parquet is the artifact of record and is committed. DuckDB is built at boot and is gitignored. |
| Claude Design output | Port to React now | `NidhiNetra.dc.html` becomes a read-only reference. All further visual work happens in the real stack. |

**Two things the multi-model command could not do here.** `~/.claude/bin/codeagent-wrapper` is absent and no `codex` CLI is installed, so there is no `CODEX_SESSION` or `GEMINI_SESSION` to hand off and `/ccg:execute` is not available. This plan is executed by subagent waves instead, per §5.

---

## 1. Folder structure

### 1.1 Why this shape

Three constraints drove it:

1. **Six agents work in parallel against frozen contracts.** So `contracts/` sits at the top level where nobody can claim they did not see it, not buried inside a service.
2. **CP6 demands the demo run with wifi off.** So the snapshot is a committed build artifact, not something fetched at runtime.
3. **Two Python services share models.** So a `uv` workspace, not two unrelated virtualenvs that drift.

### 1.2 The tree

```
SIH/
└── 05-App/
    ├── README.md                    # how to run it, first thing a judge opens
    ├── Makefile                     # make demo  <- the whole product, one command
    ├── pyproject.toml               # uv workspace root
    ├── uv.lock
    ├── .gitignore
    │
    ├── contracts/                   # CP0 lives here. Frozen before any code.
    │   ├── normalized_record.schema.json      # Execution Plan 3.1
    │   ├── risk_scored_record.schema.json     # Execution Plan 3.2
    │   ├── fund_flow_graph.schema.json        # Execution Plan 3.3
    │   ├── openapi.yaml                       # Execution Plan 3.4
    │   ├── fixtures/
    │   │   ├── works.fixture.json             # 20 realistic rows
    │   │   ├── scored.fixture.json            # same 20, ranked
    │   │   └── graph.fixture.json
    │   └── validate.py              # the CP0 validator. A script, not eyeballing.
    │
    ├── pipeline/                    # A1, A2, A3
    │   ├── pyproject.toml
    │   ├── tests/
    │   └── src/nidhinetra_pipeline/
    │       ├── ingest/              # A1
    │       │   ├── mplads_api.py    # the discovered REST endpoints
    │       │   ├── rungs.py         # the five-rung fallback ladder
    │       │   └── cache.py         # write-once to data/raw, never refetch
    │       ├── normalize/           # A1  ->  3.1 parquet
    │       ├── risk/                # A2
    │       │   ├── peer_groups.py   # builds the peer group. Mandatory field.
    │       │   ├── detectors.py     # IsolationForest, LOF, z-scores
    │       │   ├── explain.py       # why_flagged sentences, plain language
    │       │   └── rank.py          # inspection_rank, 1..N, no gaps
    │       ├── graph/               # A3  ->  NetworkX MP/Agency/Vendor
    │       └── cli.py               # python -m nidhinetra_pipeline build
    │
    ├── api/                         # A4
    │   ├── pyproject.toml
    │   ├── tests/
    │   └── src/nidhinetra_api/
    │       ├── main.py
    │       ├── db.py                # DuckDB over data/snapshot/*.parquet
    │       ├── models.py            # pydantic, mirrors contracts/
    │       └── routers/
    │
    ├── web/                         # A5
    │   ├── package.json
    │   ├── app/
    │   ├── components/
    │   │   ├── surfaces/            # DotField, GlassPanel  <- section 2
    │   │   ├── inspection-list/     # the hero screen
    │   │   ├── quota-meter/         # the ten percent line
    │   │   ├── summary-strip/
    │   │   ├── detail-panel/
    │   │   └── fund-flow/
    │   ├── styles/
    │   │   ├── tokens.css           # derived scales, oklch palette
    │   │   └── surfaces.css         # dots and glass
    │   └── lib/
    │
    ├── data/
    │   ├── raw/                     # gitignored. Immutable API pulls.
    │   ├── interim/                 # gitignored. Rebuildable.
    │   └── snapshot/                # COMMITTED. This is the offline demo.
    │       ├── works.parquet
    │       ├── scored.parquet
    │       ├── graph.json
    │       └── MANIFEST.json        # row count, pull date, source_rung mix
    │
    └── scripts/
        ├── bootstrap.sh
        └── demo.sh                  # the wifi-off runner for CP6
```

### 1.3 The Obsidian problem, and the fix

`node_modules` is roughly forty thousand files. Obsidian will try to index every one and the vault will hang on open. Before any `npm install`, patch `.obsidian/app.json`:

```json
{
  "useMarkdownLinks": false,
  "newLinkFormat": "shortest",
  "attachmentFolderPath": "Attachments",
  "alwaysUpdateLinks": true,
  "userIgnoreFilters": [
    "05-App/node_modules",
    "05-App/.venv",
    "05-App/web/.next",
    "05-App/web/node_modules",
    "05-App/data",
    "05-App/.ruff_cache",
    "05-App/.pytest_cache"
  ]
}
```

This is a Wave 0 task and it blocks everything. If it is skipped the vault becomes unusable and the mistake is expensive to notice.

---

## 2. Frontend: dots and glass, as one change

### 2.1 The tension, and why it resolves

`NIDHINETRA-DESIGN-BRIEF.md` section 3 says, verbatim: *"No frosted glass anywhere. Translucency depends on contrast with what sits behind it, and white on white has none."*

That reasoning is correct and still holds. What changes it is the other half of the request. **A visible dot field is the backdrop contrast that was missing.** Glass over flat white is invisible CSS. Glass over a dot field refracts, and the dots visibly bend and blur through it, which is the entire perceptual effect that makes glass read as a physical pane.

So these are not two features. They are one, and shipping either alone is worse than shipping neither.

The brief needs a section 3 amendment recording this, and it is a **Wave 0** task, not Wave 3. A5 builds glass in Wave 1; scheduling the amendment that authorises glass for Wave 3 would have A5 building for two waves against a brief that forbids what it is building.

### 2.2 Layering model

| z | Layer | Treatment |
|---|---|---|
| 0 | Paper | `--paper`, off-white, opaque |
| 1 | Dot field, base | always visible, low alpha |
| 2 | Dot field, hot | higher alpha, masked to a radius around the pointer |
| 3 | Content | opaque paper beneath the table, dots masked out |
| 4 | Floating surfaces | frosted glass, refracting layers 1 and 2 |

**Where glass is allowed:** the sticky filter bar once it detaches, the detail panel, tooltips, any popover.
**Where glass is forbidden:** the page itself, the table, anything containing a numeral, and inside another glass surface. Apple's own rule, and the one most often broken: never stack glass on glass. Controls inside the detail panel are flat, not glass.

### 2.3 Tokens

Added to `styles/tokens.css`. Every value derives, nothing hardcoded.

```css
:root {
  /* dots */
  --dot-ink-base:  color-mix(in oklch, var(--ink)  9%, transparent);
  --dot-ink-hot:   color-mix(in oklch, var(--ink) 22%, transparent);
  --dot-radius:    1px;
  --dot-gap:       calc(var(--space-unit) * 6);
  --dot-reveal-r:  calc(var(--space-unit) * 44);

  /* glass */
  --glass-tint:      color-mix(in oklch, var(--surface) 72%, transparent);
  --glass-blur:      20px;
  --glass-saturate:  180%;
  --glass-hairline:  color-mix(in oklch, var(--ink) 8%, transparent);
  --glass-highlight: color-mix(in oklch, white 70%, transparent);
}
```

`--dot-ink-base` at nine percent is the answer to "too faint": present as paper texture, never competing with type. Twenty two percent at the pointer is a clear, felt response without becoming a spotlight gimmick.

### 2.4 The dot field

Two stacked fixed layers. The base is always on. The hot layer is identical but masked to a soft circle that follows the pointer.

```css
.dot-field {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-image: radial-gradient(
    circle at center,
    var(--dot-ink-base) var(--dot-radius),
    transparent var(--dot-radius)
  );
  background-size: var(--dot-gap) var(--dot-gap);
}

.dot-field__hot {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-image: radial-gradient(
    circle at center,
    var(--dot-ink-hot) var(--dot-radius),
    transparent var(--dot-radius)
  );
  background-size: var(--dot-gap) var(--dot-gap);
  mask-image: radial-gradient(
    circle var(--dot-reveal-r) at var(--px) var(--py),
    #000 0%,
    transparent 70%
  );
  -webkit-mask-image: radial-gradient(
    circle var(--dot-reveal-r) at var(--px) var(--py),
    #000 0%,
    transparent 70%
  );
}
```

Pointer tracking writes CSS custom properties directly and never touches React state. A `useState` here would re-render the entire tree on every mouse move and visibly drop frames on a large table.

```js
useEffect(() => {
  const el = hotRef.current;
  if (!el) return;
  let raf = 0, x = 0, y = 0;
  const onMove = (e) => {
    x = e.clientX; y = e.clientY;
    if (raf) return;
    raf = requestAnimationFrame(() => {
      el.style.setProperty('--px', `${x}px`);
      el.style.setProperty('--py', `${y}px`);
      raf = 0;
    });
  };
  window.addEventListener('pointermove', onMove, { passive: true });
  return () => {
    window.removeEventListener('pointermove', onMove);
    cancelAnimationFrame(raf);
  };
}, []);
```

**Masking rule.** The table and every numeral sit on opaque paper. Give the table wrapper `background: var(--paper); position: relative; z-index: 1;`. Dots never appear behind data. They live in the margins, behind the title block, and in the region beside the summary strip.

### 2.5 Glass

```css
.glass {
  background: var(--glass-tint);
  backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  border: 1px solid var(--glass-hairline);
  border-radius: var(--radius-lg);
  box-shadow:
    inset 0 1px 0 var(--glass-highlight),
    0 1px  2px color-mix(in oklch, var(--ink) 4%, transparent),
    0 8px 24px color-mix(in oklch, var(--ink) 6%, transparent);
}
```

The `inset 0 1px 0` top highlight is the detail that does the work. Without it a glass panel reads as a blurry div. With it, it reads as a pane of physical material catching light on its top edge. Do not drop it.

### 2.6 Accessibility, all three signals

```css
@media (prefers-reduced-transparency: reduce) {
  .glass { background: var(--surface); backdrop-filter: none; -webkit-backdrop-filter: none; }
}
@media (prefers-reduced-motion: reduce) {
  .dot-field__hot { display: none; }   /* static field remains */
}
@media (prefers-contrast: more) {
  .dot-field, .dot-field__hot { display: none; }
}
```

### 2.7 Hover, everywhere it is earned

- **Table row.** Faint wash across the row, plus a short vertical tick in that row's risk colour at the left edge. No shadow, no lift, no scale.
- **Summary figure.** Reveals the underlying computation as one muted line. Information on demand, not tooltip chrome.
- **Quota meter.** Highlights the segment under the pointer and surfaces the rank at that position.
- All hover feedback fires on pointer enter with no delay.

### 2.8 The structural fixes that actually cause the emptiness

Texture does not fix a broken grid. These land in the same pass:

1. **Summary strip breaks 3 + 1**, orphaning the fourth figure beside a void. Force four equal columns, or 2 by 2 below the breakpoint. Never 3 + 1.
2. **Quota meter is missing.** A full-width bar showing the ten percent obligation, the cutoff rank marked with a vertical rule, everything past it as hairline outline only. This is the product thesis rendered physically and it is the single highest-value addition on the page.
3. **Vertical rhythm is roughly a third too loose** between title, summary, and filter bar. Keep the space above the table, which earns it.

### 2.9 "More accurate"

The figures currently on screen are placeholders. Accuracy means the summary strip and the table are fed by real MPLADS records through the A1 to A4 chain. That is not a frontend task, it is why Wave 1 and Wave 2 exist. Until then the frontend runs on `contracts/fixtures/`, and every screenshot taken before CP4 is labelled as fixture data in the logbook.

---

## 3. Backend

### 3.1 Shape

**Superseded 2026-09-01.** This section previously described a build-time pipeline that ran once and stopped, chosen so the demo could run with the network off. That constraint was withdrawn: an oversight instrument that cannot see live data is not an oversight instrument. The pipeline now pulls on a schedule and on demand, and the offline story becomes a fallback rather than the design.

The pipeline runs on a timer and on a manual trigger. It never serves a request directly. The API reads whatever the last successful run committed, so a slow or failed pull degrades the data's age, never the page.

```
                    +--------------------------------------+
                    |  scheduler (every N hours)           |
                    |  + manual "refresh now" button       |
                    +------------------+-------------------+
                                       v
  mplads.mospi.gov.in ----------->  ingest  ---->  validate  ---->  data/raw/<ts>.json
              |                                       |
      (timeout / ZK error /                           |  all four fatal fields present?
       rate limit / partial)                    no ---+--- yes
              |                                  |           |
              v                                  v           v
      keep last good                         reject,     normalize  ->  works.parquet
              |                              log it,         |
              |                              keep last       v
              |                              good        risk scoring   (fixed seed)
              |                                              |
              |                                              v
              |                                       scored.parquet
              |                                              |
              +------------------>  ATOMIC SWAP  <-----------+
                                          |    write temp, validate, then rename
                                          v
                                    data/current/
                                          v
                                FastAPI + DuckDB   (3.4)
                                          v
                                      Next.js
                                          |
                                 "data as of <ts>"
```

Two timestamps reach the screen and they are not the same thing. **Data age** is when the last successful pull landed. **List generation** is when the inspection list was last cut. The data moves continuously; the list is a dated artifact an officer works from over weeks. Conflating them is the likeliest UI bug in this design.

### 3.2 Endpoints

Exactly Execution Plan section 3.4, no additions:

- `GET /api/works` with `state`, `year`, `category`, `flag`. Paginated, **sorted by `inspection_rank` by default**
- `GET /api/works/{work_id}`
- `GET /api/graph` with `agency`, `vendor`
- `GET /api/stats/summary`

Response envelope follows the house pattern: status indicator, nullable data, nullable error, meta for paginated responses.

### 3.3 Ingest discipline

The discovered endpoints are undocumented and the dashboard JS is deliberately obfuscated, so treat them as unstable:

- Rate limit hard. One request at a time, with a delay.
- Write to `data/raw/` on first success and **never refetch**. `cache.py` refuses a network call when the cache file exists unless explicitly forced.
- Record `source_rung` on every record so the report can state honestly where each row came from.
- Never call the network during a demo. `demo.sh` sets an env var that makes any outbound call raise.

---

## 4. Database

### 4.1 Why Parquet is the artifact and DuckDB is the engine

Parquet is committed. DuckDB is not. The database file is rebuilt at boot from the Parquet, in about a second.

This matters because the offline demo has to survive a laptop swap, a fresh clone, and a corrupted local file. A committed binary `.db` is opaque, merges badly, and if it breaks the demo is gone. Committed Parquet is columnar, compresses well, is readable by pandas or DuckDB or anything else, and is regenerable. The DuckDB file becomes disposable, which is exactly what you want a cache to be.

```python
# api/src/nidhinetra_api/db.py
import duckdb
from pathlib import Path

SNAPSHOT = Path(__file__).parents[3] / "data" / "snapshot"

def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    con.execute(f"CREATE VIEW works  AS SELECT * FROM '{SNAPSHOT}/works.parquet'")
    con.execute(f"CREATE VIEW scored AS SELECT * FROM '{SNAPSHOT}/scored.parquet'")
    return con
```

In-memory, views straight over Parquet, no file to corrupt and no migration story to maintain. For a read-only snapshot this is strictly simpler than the alternatives.

**Correction 2026-09-01.** An earlier draft justified DuckDB as faster than SQLite for the peer-group aggregations in `risk/`. That was wrong: `risk/` is pandas inside the pipeline and never touches the database. DuckDB is chosen for the read path only, where it serves filtered and sorted queries over Parquet without a load step. At the corpus sizes in play that is a convenience, not a performance necessity, and it should be revisited if the spike returns far more or far fewer rows than expected.

### 4.2 Schema

Columns are exactly Execution Plan 3.1 and 3.2. No extra columns, no renames. `contracts/validate.py` enforces this and CI fails on drift.

`MANIFEST.json` beside the Parquet records: row count, pull date, `source_rung` breakdown, and the pipeline git SHA that produced it. When a judge asks where the numbers came from, that file is the answer.

---

## 5. Subagent waves

Rule from Execution Plan section 5, unchanged: **at most three streams open at once.** One human reviews all of them, and a fourth parallel stream is how integration debt becomes invisible.

### Wave 0. Contracts. Blocking. Nobody else starts.

Single agent, or done directly. Gates on **CP0**.

- Patch `.obsidian/app.json` with `userIgnoreFilters` (§1.3). Do this first.
- Scaffold the tree in §1.2, `uv` workspace, `.gitignore`, `Makefile`
- Write the four schema files from Execution Plan section 3
- Write 20 realistic fixture rows for each of the three contracts
- Write `contracts/validate.py` and prove it fails on a deliberately broken fixture

**Done when:** `python contracts/validate.py` exits 0 on the fixtures and non-zero on a corrupted copy.

### Wave 1. Three parallel. Fixtures make this possible.

| Agent | Job | Skills | Reads |
|---|---|---|---|
| **A1 Data** | Ingest ladder, normalize to 3.1 Parquet, cache to disk | `python-patterns`, `superpowers:test-driven-development` | Execution Plan 2 and 3.1 |
| **A2 Risk** | Peer groups, detectors, `why_flagged`, `inspection_rank`, on fixtures | `python-patterns`, `python-testing` | Execution Plan 3.2 |
| **A5 Frontend** | React port, on fixtures, **in this order**: (1) tokens lifted from `NidhiNetra.dc.html` lines 15-490, (2) the ranked table, (3) **the quota meter**, (4) the summary strip 4-up fix, (5) the detail panel, (6) dots and glass **last** | `apple-design`, `frontend-design:frontend-design`, `impeccable` | `NIDHINETRA-DESIGN-BRIEF.md`, §2 above |

**Why A5's order is fixed and not a suggestion.** The quota meter is the product thesis rendered as an object. The dot field is texture. Left unordered, time pressure ships the texture and drops the thesis, because texture always looks like progress. If A5 runs out of time, it must run out of time on the dots.

A2 and A5 do not wait for A1. That is the entire reason CP0 comes first.

Gates on **CP1** (A1) and **CP2** (A2).

### Wave 2. Two parallel.

| Agent | Job | Skills | Depends on |
|---|---|---|---|
| **A3 Graph** | NetworkX MP/Agency/Vendor, find a genuine concentration cluster | `python-patterns` | A1 real output |
| **A4 API** | FastAPI, DuckDB reader, the four endpoints | `python-patterns`, `security-review` | contracts only |

Gates on **CP3** and **CP4**.

### Wave 3. Integration. Single stream.

**A6.** Swap fixtures for real outputs behind the unchanged contract. Wire the frontend to the live API. Amend design brief section 3 to record the glass reversal and its reasoning (§2.1). Copy audit: no "fraud detected", no green, no em-dashes.

Gates on **CP5**.

### Wave 4. Demo hardening. Single stream.

**A6.** `demo.sh`, wifi physically off, full reload, timed dry run, watched by someone who did not build it. Prepared answers for the two hard questions in CP7.

Gates on **CP6** and **CP7**.

### Standing rule for every agent

After any checkpoint, fix, or decision: update [[04 Prototype/Checkpoints|Checkpoints]] and append to [[04 Prototype/Logbook|Logbook]]. Never skip the logbook entry, even for small fixes. The logbook is append-only and is never edited.

---

## 6. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Obsidian hangs after `npm install` | High if §1.3 skipped | `userIgnoreFilters` is the first Wave 0 task, before any install |
| MPLADS endpoints change or rate-limit | Medium | Cache-once discipline; five-rung ladder; snapshot committed so a dead API cannot kill the demo |
| `backdrop-filter` performance on a large table | Medium | Glass only on floating surfaces, never on the scrolling region. Profile with the panel open over 200 rows. |
| Dots read as decoration and cheapen the Swiss discipline | Medium | Nine percent base, masked out from under all data, killed under `prefers-contrast` |
| Frontend built on fixtures diverges from real data shape | Low | `validate.py` runs against real output at CP1; fixtures and real data share one schema |
| No labelled ground truth for "fraud" | Certain, by nature | Never claim detection. "Risk flags for human review." Inspection outcomes are the future label source. |
| Six streams, one reviewer, invisible integration debt | Medium | Hard cap of three open streams; CP gates between waves |

---

## 7. Vault documents to update

| File | Change | Wave |
|---|---|---|
| `.obsidian/app.json` | add `userIgnoreFilters` | 0 |
| `NIDHINETRA-DESIGN-BRIEF.md` | amend section 3: glass reinstated, with the dot-field reasoning | 3 |
| [[04 Prototype/Execution Plan]] | section 2 rewritten around the confirmed REST endpoints; section 7 stack narrowed to DuckDB | 0 |
| [[04 Prototype/Checkpoints]] | ticked and unticked live | every |
| [[04 Prototype/Logbook]] | appended after every decision | every |
| [[00 Dashboard]] | link to `05-App/README.md` | 0 |

---

## 8. Still open

- **The internal round date is unknown.** Execution Plan section 6 cannot be filled until it is. This is the only thing blocking a real calendar.
- **The ₹1,729.61 cr and ₹5.93 cr figures** still need confirming against primary sources before they appear on a slide.

---

Back to [[04 Prototype/PRD|PRD]] · [[04 Prototype/Execution Plan|Execution Plan]] · [[04 Prototype/Checkpoints|Checkpoints]] · [[04 Prototype/Logbook|Logbook]] · [[00 Dashboard|Dashboard]]

---

# ENG REVIEW OUTPUTS (2026-09-01)

## What already exists

| Artifact | Reuse verdict |
|---|---|
| `05 Design Reference/NidhiNetra.dc.html` lines 15-490 | **Reuse.** Roughly 475 lines of token CSS with the derived scales already working. A5 lifts this rather than rewriting it. The plan previously implied a port from scratch. |
| `05 Design Reference/support.js` | **Discard.** Claude Design runtime shim, 1911 lines, not portable. |
| `contracts/` JSON Schemas | **Promote.** Currently one of four hand-maintained copies. Becomes the single source, generating pydantic and TypeScript. |
| MPLADS `getStateData` endpoint | **Reuse, narrowly.** Confirmed working. Good for the state dropdown, useless for work data. |
| `graphify-out/graph.json` | **Not app code.** Knowledge graph over the planning docs. |

Everything else is greenfield. Zero test files exist.

## NOT in scope

| Deferred | Rationale |
|---|---|
| Authentication and user accounts | Single-officer demo. No multi-user story before the internal round. |
| Deployment, CI, container registry | Local demo. Distribution question is "can a judge clone and run it," answered by extracting the repo. |
| Pinning inspected works across regenerations (option C from issue 1) | Real workflow modelling, real state tracking, no time before an unknown internal round date. |
| Cutting the FastAPI service in favour of Next.js route handlers | Raised by the outside voice after the serving layer was already decided. Thrash costs more than the wrong serving layer. Revisit only if the spike changes the data volume by an order of magnitude. |
| National-scale corpus | Gated on the spike. The 8-state sampling frame is the demo bar, not a claim of national coverage. |
| Fund-flow graph (M5) | Not cut, but conditional. Survives only if `implementing_agency` and `vendor_name` come back across 8-plus states. |

## Failure modes

| New codepath | Realistic production failure | Test? | Error handling? | Silent? |
|---|---|---|---|---|
| `ingest/mplads_api.py` | Returns ZK framework HTML instead of JSON. **Proven on 2026-09-01.** | No | No | Would be |
| `ingest/cache.py` | Partial refresh overwrites a complete snapshot | No | No | **Yes** |
| `ingest/` refresh | Hung connection, UI stuck in refresh-in-progress forever | No | No | Yes |
| `risk/peer_groups.py` | Group of n=3 yields a meaningless z-score rendered as a confident sentence | No | No | **Yes** |
| `risk/detectors.py` | IsolationForest without `random_state` reshuffles ranks every fit | No | No | Yes |
| `risk/explain.py` | Emits an accusatory word or an em-dash into user-visible copy | No | No | Yes |
| `rank.py` | Rank deltas computed against a baseline that does not exist on day one | No | No | **Yes** |

**Critical gaps (no test AND no error handling AND fails silently): 3.**
Peer group below minimum size, partial-refresh overwrite, and rank deltas without a baseline. All three produce plausible-looking wrong output rather than an error, which is the worst failure mode for a tool whose only claim is "here is exactly why."

## Worktree parallelization

| Step | Modules touched | Depends on |
|---|---|---|
| Spike | none (browser only) | nothing |
| A1 Data | `pipeline/ingest/`, `pipeline/normalize/` | spike |
| A2 Risk | `pipeline/risk/` | contracts |
| A5 Frontend | `web/` | contracts |
| A3 Graph | `pipeline/graph/` | A1 output |
| A4 API | `api/` | contracts |

```
Lane A:  spike -> A1 Data                    (pipeline/ingest, pipeline/normalize)
Lane B:  A2 Risk                             (pipeline/risk)
Lane C:  A5 Frontend                         (web/)
Lane D:  A3 Graph                            (pipeline/graph, waits on Lane A)
Lane E:  A4 API                              (api/)
```

**Execution order.** Spike alone first, blocking. Then launch B, C and E in parallel worktrees while A runs. Merge. Then D.

**Conflict flag.** Lanes A, B and D all live under `pipeline/`. Separate subdirectories, but they share `pipeline/pyproject.toml` and `pipeline/tests/`. Add dependencies in one place before splitting, and give each lane its own test subdirectory.

## Implementation Tasks

Synthesized from this review's findings. 23 tasks, full detail in `~/.gstack/projects/<slug>/tasks-eng-review-*.jsonl`.

**P1, blocks ship (14):** capture the MPLADS listing request; extract the repo; Obsidian ignore filters; generate types from JSON Schema; peer-group minimum n of 30; fixed `random_state` and stable tie-breaking; dated inspection-list snapshot with deltas; replace the stale data flow diagram; atomic snapshot swap; propagate the live-data reversal to seven stale wifi-off references; start pull two tonight for a delta baseline; gate LOF `n_neighbors` on minimum n; remove CP2's perverse three-flags gate; order A5 Wave 1 with the quota meter first.

**P2, same branch (9):** ZK HTML fixture test; data-as-of timestamp; refresh throttle; refresh timeout; strings.json copy freeze; DuckDB justification correction; OpenAPI authority; visible refresh effect; sequence backwards from 2026-09-20.

## Completion summary

- Step 0 Scope Challenge: **scope accepted as-is** after the live-data reversal justified keeping the API
- Architecture Review: **5 issues**
- Code Quality Review: **3 issues**
- Test Review: diagram produced, **31 gaps**, 0 of 31 paths currently covered
- Performance Review: **1 new issue**, 1 pre-existing and already mitigated
- Outside voice: **ran (Claude subagent)**, 9 findings, 8 accepted, 1 declined as settled scope
- NOT in scope: written
- What already exists: written
- Failure modes: **3 critical gaps**
- Parallelization: 5 lanes, 3 parallel, 2 sequential
- Lake Score: 5/6 recommendations chose the complete option

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | - | - |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | - | - |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | ISSUES_OPEN | 18 issues, 3 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | - | - |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | - | - |

**CROSS-MODEL:** Outside voice raised 9 findings this review missed. 8 accepted and folded into tasks, including three critical gaps. 1 declined: the proposal to cut FastAPI, which reverses a scope decision made earlier in the same session and would cost more in thrash than the serving layer is worth.

**VERDICT:** ENG REVIEW COMPLETE, issues open. 23 tasks generated, 14 of them P1. Not cleared to implement until the spike returns, because 12 of the 23 tasks assume data that is not yet proven retrievable.

**COPY FREEZE RESOLVED (post-report, research subagent):** freeze all user-visible copy in CP0, not only the flag sentences. Grounded in design brief section 11, which already requires that no label be baked into a component, and in an ownership defect the review missed: Execution Plan section 1 assigns the plain-language reasons to A2 while Checkpoints gates A5 on the copy audit. A complete `strings.json` (16 templates, 4 flag types, 6 data states plus an offline dataset label, Indian numbering rules) and a 78-token banned list in three tiers are drafted in `graphify-out/copy-research.md`. Two corrections came with it: the 46ch reason measure is a CSS wrap width, not a character cap, so the lint bounds at 92 worst case; and the peer-group sentence already exists in two drifted forms across the design brief and the PRD. Tasks T24 to T26.

NO UNRESOLVED DECISIONS

