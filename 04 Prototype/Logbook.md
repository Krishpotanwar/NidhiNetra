---
tags: [sih2026, logbook, prototype]
ps: SIH26102
solution_name: NidhiNetra
---

# Logbook — NidhiNetra Prototype

**PRD:** [[PRD]] · **Execution plan:** [[Execution Plan]] · **Checkpoints:** [[Checkpoints]]

> **Kid version:** this file only ever grows. Nobody edits or deletes an old entry, ever — not even to fix a typo in what it says happened. If something turns out to have been wrong, you write a **new** entry saying so. That way the file is proof of what actually happened, in order, and nobody can quietly rewrite history when something breaks later.

## Rules (every agent — including you, AI — must follow these)
1. **Append only.** Never edit or delete a past entry. Correct a mistake with a new entry, not a fix to the old one.
2. **Write an entry after every**: fix, feature landed, decision made, blocker hit, or checkpoint ticked/unticked in [[Checkpoints]].
3. **Use the template below.** Newest entry at the bottom.
4. **Be specific.** "Fixed the bug" is useless a week later. "Fixed A2: risk_score was NaN when expenditure_amount_inr was 0 — added a zero-division guard" is useful.
5. If an entry references a checkpoint, name it (e.g. "CP1") so the two files stay traceable to each other.

## Template
```
### [YYYY-MM-DD HH:MM] [Agent tag: A1-A6] [Type: build | fix | decision | blocker]
**What:** one or two sentences, specific.
**Why:** the reason, if not obvious.
**Verification:** how you confirmed it (test run, checkpoint ticked, screenshot, etc.) — or "unverified" if you couldn't yet.
```

---

### [2026-08-31 11:14] [Agent tag: A6] [Type: decision]
**What:** Kicked off prototype planning. Created [[PRD]], [[Execution Plan]], [[Checkpoints]], and this logbook. Confirmed with the human: build window is multi-day take-home (no fixed onsite hackathon clock), team model is 6 parallel agents (A1 Data/ETL, A2 Anomaly Engine, A3 Fund-Flow Graph, A4 Backend/API, A5 Frontend, A6 Integration/PM/Demo) instead of 6 humans.
**Why:** The idea-submission PPT (NidhiNetra, SIH26102) was already delivered on 2026-08-26. This is the next phase — building the actual working prototype for the internal round — and a 6-way parallel build only works safely if the data contracts between agents are frozen before anyone writes code (see [[Execution Plan]] §2).
**Verification:** unverified — this is a planning entry, no code shipped yet. Next real entry should be CP0 (contracts frozen) from whichever agent ships the fixture files first.

### [2026-08-31 11:40] [Agent tag: A6] [Type: decision]
**What:** Ran `/office-hours` hard-diagnostic on the plan. Four decisions landed, and they change the product, not just the schedule:
1. **Primary user narrowed to one:** the MoSPI/Ministry officer. District Collector demoted to drill-down persona. Decisive reason: the fund-flow graph is structurally meaningless below national scale (a single district has too few agencies/vendors for concentration patterns to exist), so picking a district-level primary user would have forced us to discard the only real differentiator.
2. **Product thesis reframed** from *fraud detection* to **inspection targeting**. MPLADS guidelines require District Authorities to physically inspect ≥10% of works under implementation annually, with no risk-based method for choosing which 10%. NidhiNetra ranks that existing, already-mandated queue.
3. **Wedge chosen:** the ranked Inspection List is the hero screen. Fund-flow graph becomes its drill-down. Choropleth map and trend charts demoted from must-have to nice-to-have.
4. **Stalled/idle funds promoted to a first-class flag type** — ₹1,729.61 cr currently unspent with district authorities; Parliamentary panels actively raising it.

**Why:** The reframe (2) is the load-bearing one. It (a) removes all adoption friction by slotting into a legal duty that already exists rather than proposing a new process, (b) answers the hardest judge question — "how is this different from what CAG already does?" — since CAG is a retrospective ~decadal sample while this is a continuous prospective ranking, and (c) neutralises the project's worst documented risk: under this framing a false positive costs one inspection visit rather than an accusation, and the inspection result then returns as a **label**, generating the supervised ground truth that does not currently exist for this problem.

**Research that produced it (all public sources):** MPLADS 2023 guidelines (≥10% annual district inspection duty, state-level third-party physical audit); CAG performance audits on MPLADS (2001, 2011) and their recommendations on data validation and reconciliation; CAG finding of ₹5.93 cr of one MP's funds paid to a cooperative society of co-party members — a fund-flow-graph-shaped pattern usable as the demo's hero example; 2023-24 MPLADS figures of ₹6,382.8 cr recommended vs ₹4,805.48 cr spent, ₹1,729.61 cr unspent.

**Also flagged, not yet resolved:** the plan has no fallback if scraping fails (cached snapshot presumes at least one successful scrape); the plan has no calendar dates; and the six-parallel-agent model may make the single human reviewer the integration bottleneck. Premises P6, P7, P8 in the session — accepted by default, not explicitly confirmed.

**Verification:** unverified as a build claim — no code written. The ≥10% inspection duty and the ₹1,729.61 cr figure are from public sources and should be re-confirmed against the primary MPLADS guidelines PDF before either appears on a slide.

### [2026-08-31 11:45] [Agent tag: A6] [Type: build]
**What:** Wrote [[Frontend Design Brief]] — a self-contained, paste-ready brief for a design tool. Specifies Liquid Glass as the visual language with one hard rule: **glass is chrome, never content** (nav / filter bars / floating panels / modals get glass; the inspection table and every rupee figure stay solid and high-contrast). Also specifies IBM Plex Sans with mandatory tabular figures, Indian numbering convention, a no-green risk ramp, and a table of banned UI copy.
**Why:** Two non-obvious constraints drove it. First, the hero screen is a dense data table, and frosted glass behind small numbers destroys legibility — Apple's own model puts Liquid Glass on the *controls* layer floating over solid content, so applying it correctly means restricting it, not diluting it. Second, **green is banned from the risk scale**: green reads as "verified clean," and we have no evidence any work is clean, only the absence of a flag. Showing green is an overclaim a domain-aware judge will catch.
**Verification:** unverified — no design produced yet. Brief is written to be handed to a design tool next.

### [2026-08-31 12:05] [Agent tag: A6] [Type: build]
**What:** Wrote [[Claude Design Prompt]] via `/design-taste-frontend`. Two parts: a paste-ready prompt for a design tool, and a resource pack (CSS tokens, honest Liquid Glass approximation, font and icon choices, underlying stack, reference links). Also revised the typography in [[Frontend Design Brief]] from IBM Plex Sans to **Geist + Geist Mono**.
**Why:** Three findings from running the skill properly, each of which changes what gets built:
1. **The skill declares dashboards and data tables out of its own scope.** Its landing-page layout playbook does not apply to NidhiNetra. Only its anti-slop rules, AI-tell bans, icon policy, and Liquid Glass appendix were used. Applying the rest would have produced a marketing page wearing a dashboard's clothes.
2. **There is no official Apple Liquid Glass for the web.** Apple documents it for Apple platforms only and ships no web package. Every web version is a `backdrop-filter` approximation, and the prompt labels it as one. Claiming otherwise to a technical judge is a credibility loss for zero gain. Same reasoning applies to icons: **SF Symbols is licensed to Apple platforms and cannot ship on the web**, so Phosphor Icons is the honest substitute (six weights, consistent grid, closest analog).
3. **Font switched to Geist + Geist Mono.** The skill bans Inter as a default, and the direction moved to Apple-premium. Geist has SF-adjacent geometry and real tabular figures; Geist Mono carries the rupee columns, which the skill mandates at this data density. IBM Plex Sans stays documented as the fallback if institutional-formal is later preferred over Apple-crisp.

**Dials set deliberately off-preset:** `DESIGN_VARIANCE: 4 / MOTION_INTENSITY: 5 / VISUAL_DENSITY: 8`. Both the trust-first preset (density 4-5) and the Apple-premium preset (density 3-4) are wrong here, because a ranked table of 400+ works is a genuine cockpit. Variance stays low because asymmetric layout fights tabular data.

**Also enforced:** zero em-dash characters in the prompt file, verified mechanically with `grep -c` returning 0. The em-dash is the most recognisable AI-writing signature and any that reach UI copy make the interface read as generated.
**Verification:** em-dash count verified 0. No design generated yet, so the visual direction itself is unverified. Next step is running the prompt through a design tool and recording the chosen variant here.

### [2026-08-31 12:20] [Agent tag: A6] [Type: fix]
**What:** Rewrote [[Claude Design Prompt]] after the human pointed out that a project-scoped **`apple-design` skill** exists at `.claude/skills/apple-design` and I had not loaded it. The first version was written from inference about Apple's design language. The rewrite is grounded in the skill's actual WWDC-derived content (*Designing Fluid Interfaces* 2018, *The Details of UI Typography* 2020, *Principles of Great Design* 2026).
**Why:** Four real gaps the skill closed, each of which would have shipped as vague direction a designer could not act on:
1. **Motion had no numbers.** I had written "spring curve, not linear easing," which is an adjective. Apple parameterises springs as **damping** (overshoot, 1.0 = critically damped) and **response** (seconds to target), never as duration plus easing, and ships specific values: move/reposition 1.0/0.4, rotation 0.8/0.4, drawer 0.8/0.3. Bounce is added **only when the gesture itself carried momentum**. Our drill-down therefore uses damping 1.0 rather than Apple's sheet value of 0.8, because it opens from a click with no momentum behind it. That deviation is now documented in the prompt rather than left as an accident.
2. **Typography had no tracking or leading spec.** Tracking is size-specific: large text needs *negative* tracking, small text *positive*, and a single `letter-spacing` value is wrong at some size. Added a seven-row scale with per-size tracking and leading, plus `font-optical-sizing: auto`.
3. **Materials were underspecified.** The skill adds rules I did not have: never stack a translucent surface on another (legibility collapses), bigger surfaces must read as thicker (stronger blur AND deeper shadow, so glass is now two tiers), text on glass needs vibrancy treatment rather than flat grey, **scroll edge effects replace the 1px divider** under the sticky table header, and "materialize, do not fade" (animate blur and scale together on enter). Also settled a real decision: the drill-down is a **parallel** surface with no dimming scrim, not a modal, because the officer needs the list behind it for comparison.
4. **Accessibility was one signal, not three.** Added `prefers-reduced-transparency` and `prefers-contrast: more` alongside `prefers-reduced-motion`, each with its own CSS block.

Also added from the skill: feedback fires on **pointer-down, not release**; every animation must be interruptible and animate from the current on-screen value rather than the target; enter and exit follow the same path; boundaries rubber-band rather than hard-stop.

**Note on the font override:** the skill says to prefer the platform system font, which ships its own optical sizing and tracking tables. We override to Geist for two stated reasons - the demo must render identically on an unknown judge's machine and projector regardless of OS, and we need guaranteed tabular figures. The skill permits overrides made with a reason, so the reason is now written into the prompt.

**Verification:** em-dash count verified 0 via `grep -o`. File is 550 lines, section numbering clean and sequential (an earlier patch-on-patch pass had left B5b/B5c stubs, fixed by full rewrite). Design itself still unverified - nothing has been generated yet.

### [2026-08-31 12:40] [Agent tag: A6] [Type: build]
**What:** Rewrote the whole plan to match the office-hours reframe, and consolidated the design docs. [[PRD]], [[Execution Plan]], and [[Checkpoints]] all rewritten. Created `NIDHINETRA-DESIGN-BRIEF.md` at the vault root as the single canonical, portable design document; the two copies in this folder are now pointer stubs.
**Why:** Three of the plan's real holes are now closed, and one redundancy removed:
1. **The scraper single point of failure (premise P6) is fixed.** The old plan named a cached snapshot as the safety net, which silently assumed the scrape succeeds at least once. It might not. [[Execution Plan]] §2 is now a five-rung ladder: XHR endpoint discovery, then Playwright scrape, then Empowered Indian's existing dataset, then data.gov.in plus Lok Sabha Q&A answers, then a hand-curated seed set that must be labelled in the UI as a demo dataset. `source_rung` is now a field on every record so the provenance is never lost.
2. **The plan had no dates (P7).** §6 is now a calendar with explicit blanks. The internal round date is still unknown and is the one thing that unblocks scheduling everything else.
3. **Six agents with one reviewer (P8).** The six-agent model is kept as instructed, but §5 adds integration controls: a hard cap of 3 open streams at once, review only at checkpoint boundaries, auto-reject on contract violation, and the rule that any code that cannot be defended to a judge is a liability rather than an asset.
4. **Two design docs had begun to contradict each other on typography.** Collapsed to one file at the root.

**Scope changes carried into the docs:** must-have list cut from seven items to six, with the choropleth map and trend charts demoted to nice-to-have. CP5 now gates on the Inspection List alone rather than "the dashboard," because that screen is the product. `peer_group` promoted from optional metadata to a mandatory contract field and a visible UI element, since it is what answers the strongest objection to the whole approach. A copy audit (no "fraud detected", no green, no em-dashes) is now an explicit checkpoint item rather than an aspiration.
**Verification:** files written and line counts confirmed. Nothing built yet, so every checkpoint remains unticked. CP0 is the next real action: A6 ships fixtures and the schema validator.

### [2026-08-31 13:20] [Agent tag: A1/A6] [Type: discovery]
**What:** **The MPLADS dashboard has a public, unauthenticated REST API.** Found by loading `mplads.mospi.gov.in/digigov/dashboard.html` in a browser and reading its own network traffic. This overturns the assumption, carried since the first research session, that no bulk API exists. That assumption was the basis of the project's only HIGH risk.

Verified endpoints on `https://mplads.mospi.gov.in`:
- `POST /rest/PreLoginDashboardData/getStateData` returned clean JSON, 36 states with numeric `STATE_ID`
- `POST /rest/PreLoginDashboardData/getTenureData` returned 200
- `POST /rest/PreLoginDashboardData/getTilesData` called on page load
- `POST /rest/PreLoginCitizenWorkRcmdRest/getAttachmentById` decoded out of the obfuscated client JS
- `getMpNameByStates`, `getReviewDetailsByWork`, `getAttachmentDataForTileReports` referenced in the dashboard's own code

All calls are POST, `application/json`, JSON body, **no auth**. The presence of `PreLoginCitizenWorkRcmdRest` and `getReviewDetailsByWork` means work-level records and their uploaded attachments are publicly reachable, not merely state aggregates. That is exactly what the product needs.

**Why this matters:** rung 1 of the [[Execution Plan]] §2 ladder is confirmed working, so the plan's single HIGH risk drops to LOW. The days budgeted for scraping can move to the risk engine and the frontend.

**Two cautions, both mandatory.** The dashboard's JS is deliberately obfuscated (unicode-escaped strings, some stored reversed), which signals the operators would rather people did not script against it. The data is public, unauthenticated and published for public consumption, so reading it is legitimate, but the team must rate-limit hard, cache the first successful pull to disk immediately, and never re-fetch during a demo. Getting the team IP-blocked by a government server mid-hackathon would be unrecoverable. Second, these are undocumented internal endpoints that can change without notice, so the cached snapshot is not an optimisation, it is what the demo actually runs on.

**Also verified this session:** data.gov.in carries several MoSPI MPLADS datasets each offering a Data API, though aggregate and historical (2014-15 to 2019-20 ranges) rather than current work-level. dataful.in lists work-level MPLADS datasets but is a commercial platform. Geist and Geist Mono are SIL OFL 1.1 (commercial use and self-hosting permitted, ship the licence file); Phosphor Icons is MIT. Both are safe to ship.

**The 10 percent rule is confirmed** and is not an obscure reading: it appears in the scheme guidelines, in a dedicated MoSPI circular on mandatory inspection, and has been examined in UPSC civil-service papers. **New detail worth using in the pitch:** projects implemented through societies and trusts get *full* inspection, not the 10 percent sample. The scheme already treats a higher-risk category differently, which is direct precedent for risk-based targeting and a strong answer to any judge who calls the idea a novel imposition.
**Verification:** endpoints verified live by reading actual network responses, not inferred. Licences verified against the projects' own LICENSE files. The 10 percent rule cross-checked across three independent source types. The rupee figures still need re-confirming against primary sources before they appear on a slide.

### [2026-08-31 13:25] [Agent tag: A6] [Type: build]
**What:** Rewrote `NIDHINETRA-DESIGN-BRIEF.md` from scratch after the human rejected the previous version. Theme changed from dark to light.
**Why:** The old file was bad for a specific reason worth recording: it was written once and then patched twice more (once for `design-taste-frontend`, once for `apple-design`), so it accreted instead of cohering. It also hardcoded scattered hex and pixel values and never specified an actual layout.

Direction chosen with the human: **Swiss editorial for content, Apple light for chrome.** Page and table get off-white paper, hairlines, no cards, no shadows, with typography and alignment carrying hierarchy. Only floating layers (detail panel, modals, tooltips, the sticky filter bar) get true-white surfaces and soft tinted elevation.

Consequences worth noting:
- **Frosted glass is gone entirely.** Translucency needs contrast with what sits behind it and white on white has none. Depth now comes from elevation and hairlines, which actually work in light.
- **Elevation inverts in light mode:** an elevated surface is *brighter* than the page, so paper is off-white and floating surfaces are pure white. Getting this backwards is the most common light-mode mistake.
- **Two-line table rows.** The plain-language reason gets its own line under the work name rather than a cramped column. This is the most consequential layout decision in the document, because that sentence is the product's voice.
- **No hardcoding, both meanings.** Type and space scales each derive from a single anchor by a ratio, so changing the ratio reshapes the whole page. And no figure or label is baked into a component, which made loading, empty, missing-field and overflow states part of the deliverable rather than an afterthought.
- Risk ramp moved to `oklch` so the steps stay perceptually even, and darkened for contrast against white. Still no green at any step.
**Verification:** em-dash count verified 0 by grep after two fix passes (four had slipped into my own section headers). Licences verified. No design generated yet, so the visual direction itself remains unverified until a tool renders it.

### [2026-09-01 19:45] [Agent tag: A1] [Type: spike]
**What:** Ran the data spike against the live MPLADS dashboard. Partial success. Rung 1 is alive and richer than this morning's probe suggested, but work-level records are still not retrieved.

**Confirmed working, verified by live response, not inference:**
- `POST /rest/PreLoginDashboardData/getTilesData` returns real national aggregates: **105,640 works recommended (Rs 5,671.31 Cr), 78,547 sanctioned (Rs 4,137.10 Cr), 34,067 completed (Rs 1,658.10 Cr)**, allocated limit Rs 8,318.06 Cr, expenditure Rs 2,748.49 Cr, current tenure 18th Lok Sabha (ID 7). **Works under implementation = 78,547 - 34,067 = 44,480.** This is the summary strip, live, today.
- `POST /rest/PreLoginDashboardData/getStateData` returns 36 states with IDs. This is the filter dropdown.
- `POST /rest/PreLoginDashboardData/getTilesReportData` responds 200 with structured JSON. The tile drill-down exists.

**Why this morning's probe was wrong.** The earlier curl sent an empty body and got a ZK error page, which led to the conclusion that the endpoint was dead. It is not. It needs a correct body and a Referer. The lesson is that a failed probe with the wrong request shape is not evidence the endpoint is dead, and I recorded it as if it were.

**Obfuscation decoded.** The dashboard JS hides endpoint paths as reversed strings plus unicode-escaped property names. `"tser/"` reversed is `rest/`. Four endpoints recovered this way:
- `/rest/PreLoginDashboardData/getTilesReportData`
- `/rest/PreLoginDashboardData/getTenureData`
- `/rest/PreLoginDashboardData/getRedirectUrl`
- `/rest/PreLoginCitizenWorkRcmdRest/getAttachmentById`

**Call signature recovered** from `poptable.js`:
```
POST /rest/PreLoginDashboardData/getTilesReportData
Content-Type: application/json; charset=utf-8
body: {"combo": <int>, "key": "<string>"}
```

**Still blocked.** Every `combo`/`key` pair tried returns `{"<Tile Name>": "[{\"Total_Amt\":0.0}]"}`. Tried combo 0, 6 and 7 against keys "Works Sanctioned" and "Works Completed". The `key` is not the tile caption. The call site that constructs the real parameters was not found in `poptable.js`, `graph.js`, `preLoginDashboard.js`, `loksaba.js`, `rajyasaba.js` or `dashboard.html`, so it is built by a handler loaded elsewhere or dynamically.

**Also worth noting:** the shape `Total_Amt` suggests this endpoint may return per-tile aggregates rather than work rows even when correctly parameterised. That would mean work-level data needs a different endpoint entirely, and rung 2 stays load-bearing.

**Verification:** all four confirmed endpoints called live and their responses read directly. Zero work-level records with amount, agency, vendor or category have been retrieved. `source_rung` for anything built on today's findings is rung 1 for aggregates only.

**Next action, needs a human:** open the dashboard in a real browser, click a tile to trigger the drill-down, and read the actual request body from the network tab. That single captured body unblocks the parameterisation. Everything else about rung 1 is now known.

### [2026-09-01 20:10] [Agent tag: A6] [Type: build]
**What:** Landed the Wave 0 tasks that do not depend on the spike. Three commits. The vault is now its own git repository.

**Repo extracted.** `SIH/` is a git repo at last, 42 files, clean tree. The design doc had prescribed `git rm -r --cached SIH` in the parent first; that turned out to be unnecessary because the parent tracked **zero** SIH files. It was simply never committed, showing as `?? SIH/`. One graphify cache blob slipped into the first commit and was untracked in a follow-up. Worth remembering why the first `git check-ignore` reported "no rule": gitignore patterns never apply to files already in the index, so the rule was correct all along and only `--no-index` revealed it.

**Obsidian filters set before anything installs.** `.obsidian/app.json` now carries `userIgnoreFilters` for `05-App/node_modules`, `.venv`, `.next`, `data`, the caches, and the Claude Design export folder. Backup at `app.json.bak`, which is gitignored. Doing this after an `npm install` would have meant opening a vault trying to index roughly forty thousand files.

**The live-data reversal propagated.** Seven references across PRD and Checkpoints still demanded a wifi-off demo after the constraint was withdrawn. All reconciled:
- PRD M6 is now "live data with a resilient fallback", and the definition of done runs the demo twice, once on the network and once with it disabled.
- CP6 was renamed and rewritten. It now tests the **live pull** as well as the fallback, plus debounce, timeout, and the ZK-HTML fixture leaving the previous snapshot untouched.
- CP1 gained the atomic swap requirement and a second pull separated by real time, because rank deltas have no baseline otherwise and backfilling one is fabrication.

**Two checkpoint gates were actively harmful and are gone.**
- CP2 demanded "3 or more flag types actually fire". In a product whose only claim is that its reasons are true, a gate demanding N flags pays you to loosen thresholds until N flags appear. Replaced with an honest count recorded in this logbook, no minimum.
- CP5's copy audit sat on A5, who renders sentences A2 writes. Gating an agent on text it cannot change means the gate gets skipped. Moved to whoever owns `contracts/strings.json`.

**Peer group hardened.** CP2 now requires `n` of at least 30, and explicitly forbids widening the group to a broader category to reach it, because the group's specificity is the entire defence against "a hill road genuinely costs more".

**Corrections to my own earlier work.**
- Plan section 3.1 still described the build-time pipeline that the live decision had replaced. Diagram redrawn with the scheduler, the validation gate, the atomic swap and the two distinct timestamps.
- Plan section 4.1 justified DuckDB as "faster than SQLite for the peer-group aggregations in `risk/`". Wrong: `risk/` is pandas in the pipeline and never touches the database. DuckDB is a read-path convenience at these corpus sizes, not a performance necessity.
- A5's Wave 1 listed the quota meter and the dot field as one unordered bundle. Order is now fixed, dots last, because texture always looks like progress and under time pressure the decoration ships while the thesis does not.
- The design brief amendment authorising glass was scheduled for Wave 3 while A5 builds glass in Wave 1. Moved to Wave 0.
- The peer-group sentence existed in two drifted forms. Frozen to the explicit one, "Compared against 1,72,961 road works in Bihar, 2023-24", because a judge reading a screenshot cannot infer which state and year "this state, this year" meant.

**The calendar is no longer blank, and I was wrong that it could not be filled.** The portal submission date `2026-09-20` had been sitting in Execution Plan section 6 the whole time while I repeated that the deadline was unknown. That is **19 days from today**. Milestones are now sequenced backwards from it with two days of buffer. The internal round date remains genuinely unknown and, when it lands, eats that buffer first.

**Verification:** all three commits made, working tree clean, em-dash count 0 in the design brief and the plan. Every checkpoint edit re-read after writing. Nothing here depended on the spike, which is why it could proceed while work-level data is still unresolved.

### [2026-09-01 21:05] [Agent tag: A6] [Type: build]
**What:** CP0 done. Repo scaffolded at `05-App/`, three JSON Schemas written from Execution Plan section 3, 20-row fixtures generated for all three contracts, `contracts/strings.json` promoted from the copy research draft, and a validator with a real self-test.

**Why the validator has a self-test, not just a happy-path run.** "A script, not eyeballing" (Checkpoints CP0) is easy to satisfy with a script that always prints OK. `validate.py --self-test` deliberately corrupts three copies of the fixtures (bad enum value, a duplicated inspection_rank, a peer_group.n of 3) and asserts the validator actually rejects each one, then confirms the real fixtures still pass. All four checks passed. The validator has teeth, not just a green light.

**Contract choices worth recording:**
- `source_rung` in the fixtures is set to 5 (the labelled seed set), honestly, since these are synthetic rows, not a real pull.
- `peer_group.n` is enforced at a schema level, minimum 30, matching the eng review rule. A scored record with flags and no peer_group, or peer_group.n below 30, fails validation, not just review.
- `strings.json` came from the research subagent's draft (`04 Prototype/Copy Research - strings.json.md`) rather than being re-derived. It parses clean, 21KB, and its own banned-word lint was already run against its own templates during research, catching negated false positives ("not findings"). No reason to redo that work.
- `openapi.yaml` states its own authority explicitly: hand-written until CP4, then FastAPI's generated spec takes over, per eng review task T21.

**Verification:** `python3 contracts/validate.py` and `python3 contracts/validate.py --self-test` both run clean, output captured above. `strings.json` re-parsed with `json.load` after copying, no errors.

**Next:** Wave 1 dispatched as three parallel subagents per the reviewed plan (max 3 concurrent streams): A1 Data, A2 Risk Engine, A5 Frontend. Each works against the fixtures just frozen. A1's live ingestion for real work-level records stays blocked on the `getTilesReportData` request body, which needs a human capture from the browser network tab -- see the 19:45 entry above.

### [2026-09-01 21:40] [Agent tag: A6] [Type: build]
**What:** Wave 1 landed. Three parallel subagents (A1 Data, A2 Risk Engine, A5 Frontend), each independently verified before being committed, none touching Checkpoints or this Logbook themselves to avoid three agents racing on one file. Consolidated here.

**A1 (ingest, normalize):** 55 tests, re-run independently, passed. MpladsClient wraps the three confirmed live endpoints with the correct headers and a 1.5s rate limit. The five-rung ladder is real: rung 1 raises rather than guesses, rungs 2-5 are honest stubs. cache.py's atomic swap was tested against a simulated torn write. Rung 1 is still genuinely blocked on the `getTilesReportData` request body.

**A2 (risk engine):** 57 tests, re-run independently, passed. The one test that had to pass: a peer group of 3, and separately 29, is never flagged even at 50x median cost; a group of exactly 30 at the same extremity does fire. Verified this is a floor, not a blanket suppression. Real finding, not fixed: `strings.json`'s own lint rule says every reason must contain a number, but `cost_outlier.no_multiple` legitimately has none, for the case where a multiple can't be honestly computed. Confirmed against the file directly.

**A5 (frontend), and the thing worth reading closely:** the killed-agent story. A5 was stopped mid-task, not completed. First look, in whatever the browser's default dark mode was, appeared to be a completely different, wrong design, dark background with an orange accent. That reading was wrong. Pulled the exact `oklch` values from both files: A5's tokens are byte-identical to the reference for every color that matters. The dark background was A5 correctly rendering its own dark-mode branch, which the reference (05 Design Reference/NidhiNetra.dc.html) never had (`grep -c prefers-color-scheme` returns 0 in the reference, added on an "if offered" permission in the design brief's section 13).

Fixed after this was understood, with the user directing the dots/glass work explicitly through the `impeccable` skill:
- Dark mode stripped. Verified by forcing the OS preference to dark and confirming the app still renders light.
- The dot field (deferred as step 6, correctly, by A5) built and wired in: `DotField.tsx` writes pointer position via a ref and `requestAnimationFrame`, never React state, per the plan's own reasoning about frame drops under a real table.
- A real bug found while wiring the dots in: the page's own wrapper painted an opaque background across the entire viewport above the dot field's z-index, so dots could never appear anywhere, including the true page margins. Fixed by making the wrapper transparent and giving `SummaryStrip` its own opaque backing (it had none; `InspectionTable` and `QuotaMeter` already did). Confirmed visually: dots now show in the margins and behind the title block, masked out under every number.
- Alpha raised from 9%/22% to 16%/32% on direct request for visibility.
- `DetailPanel` converted to actual glass (was flat elevation). A spring `damping: 1` against `stiffness: 170` was roughly 18x underdamped, guaranteed to bounce hard on every open; corrected to 24, just under critical, since a programmatic panel open carries no gesture momentum to spend a bounce on.

**A stray sync worth recording, not acted on:** a folder named `Precision and research first` (no suffix) reappeared at the vault root during this session, untracked, with a `NidhiNetra.dc.html` that differs from the one in `05 Design Reference`. Checked: its internal file timestamp (08:11) predates the one currently used as reference (08:32). It is an older resync, not a newer design update. Left alone, not deleted, not treated as authoritative.

**Verification:** all three lanes independently re-tested by A6 before committing, not taken on the subagents' self-reports alone. `tsc --noEmit` clean, `npm run build` succeeds, hover-reveal confirmed live via direct `--px`/`--py` inspection after a real pointer move.

**Status:** Wave 1 is code-complete against the CP0 fixtures. CP1, CP2, CP4, CP5 checkpoint gates stay unticked in [[Checkpoints]] until real MPLADS data replaces the fixtures -- that gate is still the `getTilesReportData` request body, unchanged since the 19:45 and 20:10 entries above.

### [2026-09-02 01:05] [Agent tag: A6] [Type: build]
**What:** Wave 2 landed. A3 (Graph) and A4 (API) ran as two truly parallel subagents -- A4 did not wait for A3 to exist, it imported A3's module defensively and fell back to a fixture graph if the import failed. A3 finished first; A4 confirmed at runtime it took the real path, not the fallback.

**A3:** `build_fund_flow_graph(normalized_records, scored_records) -> dict`, exact signature A4 depended on sight unseen. 18 tests, independently re-run. Independently re-verified the headline claim rather than trusting the report: ran the builder and `find_concentration_clusters` directly against the real CP0 fixture outside any test harness. 21 nodes, 31 edges, zero clusters even at the most permissive threshold (`min_work_count=1`), schema-valid. Matches CP3's own requirement to say so honestly when nothing clears the bar at this data scale, rather than lowering the threshold to manufacture a finding.

**A4, and the thing actually worth remembering from this wave:** nothing before this joined A1's `normalize_records()` and A2's `score_all()` into a single servable snapshot. A4 built `pipeline/build_snapshot.py` to do exactly that, reusing A1's atomic write-validate-rename discipline rather than inventing a different one. Found a real bug doing it: `why_flagged`/`flags`/`peer_group` can't survive a parquet round-trip as native struct/list columns without pyarrow corrupting them (padding phantom keys into `why_flagged`, or silently typing an all-empty `flags` column as `INTEGER`). Fixed by JSON-encoding those three columns to text before the write and decoding on read. Confirmed live, not just by test: cold-booted the server myself from a cleared `data/snapshot/` and curled every endpoint by hand.

**The one result worth explaining so it doesn't read as a regression later:** `/api/stats/summary` returned `flagged_count: 0` on this cold boot. That is correct. `contracts/fixtures/scored.fixture.json` (9 of 20 flagged) was a hand-authored CP0 validator example, built by a one-off script with fabricated peer-group sizes to satisfy the schema, never a claim about what the real risk engine would compute. Run the real `score_all()` on the real 20-row `works.fixture.json` and no category+state+year group reaches the minimum of 30, so the min-n gate correctly refuses to flag anything. Zero flags on this fixture is the engine being honest, not broken. This will look very different the moment real CP1 data lands with enough rows per peer group.

**Housekeeping found and fixed along the way, unrelated to either agent's actual work:** the `data/raw/*` + `!data/raw/.gitkeep` gitignore negation from CP0 was silently not working -- `git check-ignore` kept attributing the match to the broad glob line, never to the negation two lines below it. Root cause not chased down. Replaced with a nested `.gitignore` inside each of `data/raw/` and `data/interim/` (ignore everything except itself and `.gitkeep`), which is the more robust form of this pattern anyway. Verified this time: a planted test file in `data/raw/` is correctly ignored, `.gitkeep` is correctly tracked.

**Verification discipline held across both lanes:** all 155 tests (130 pipeline + 25 api) re-run independently from each package's own directory, not trusted from either subagent's self-report. The API was cold-booted and curled by hand against every one of its 5 endpoints, including the 404 and the 429 rate-limit path, before anything was committed.

**Status:** CP3 and CP4's code-level requirements are met against fixtures; both checkpoints stay unticked in [[Checkpoints]] because their official gates require real CP1 data, which is still blocked on the same thing named in every entry above it: the `getTilesReportData` request body.

**Not yet done, worth naming so it isn't assumed finished:** A5's frontend still reads `contracts/fixtures/*.json` directly on the client rather than calling A4's new API. Wiring that is Wave 3 (Integration) territory, not something either A3 or A4 was asked to do.

### [2026-09-02 01:50] [Agent tag: A6] [Type: build]
**What:** Wave 3 (integration) landed. Done directly, single stream, no subagent -- the plan calls this wave single-stream for a reason, and wiring two already-built pieces together benefits from one continuous train of thought rather than delegation.

**The change:** `lib/data.ts` no longer imports `contracts/fixtures/*.json`. It calls A4's live `/api/works` and `/api/stats/summary`. A5's own comment from Wave 1 predicted this exactly -- "When A4's API lands, only this file's data-loading changes" -- and it held. Every downstream component is untouched.

**Two contract-mandated pieces were missing and are not optional polish, so they landed in this wave rather than being deferred again:**
- The rung-5 demo-dataset banner ("Demo dataset. Not live MPLADS data.") Execution Plan section 2 calls this mandatory, not decorative. Caught my own mistake before shipping it: my first draft assumed the label's `detail` field was a `{record_count}` template like its parent `showing_cached_data` state. Checked `contracts/strings.json` directly before wiring it -- the demo variant's text is frozen and unparameterised. Would have rendered a literal `{record_count}` on screen if shipped as first written.
- A real `error` data state on the table (`api_unreachable` from strings.json), wired to an actual working retry button, not a placeholder.

**A real lint error, not a style nit:** React's compiler flagged a synchronous `setState` call inside the mount effect as a cascading-render risk. Restructured so only the click-triggered retry path resets state synchronously; the mount effect's fetch does all its `setState` calls inside `.then`/`.catch`, never at call time.

**Verification, and this is the part worth trusting over the summary:** not satisfied with tsc and a build passing. Actually killed the API mid-session and reloaded -- got the exact `api_unreachable` copy, no status code, no stack trace, table header stayed visible, summary strip and quota meter correctly disappeared rather than showing stale numbers. Restarted the API and clicked the real Retry button, not a page reload -- everything came back. Confirmed via `read_network_requests` that the page is genuinely calling `localhost:8000`, not serving a cached bundle.

**Honest gaps, recorded in [[Checkpoints]] rather than smoothed over:** CP5's "graph reachable from a flagged row" is still open -- the detail panel has no link to A3's `/api/graph`, which is live and tested but nothing in the frontend calls it. And "does not break on 0 results" was only exercised via the network-failure path this session, not a genuine zero-row API response, which is a different code branch even though it shares the same UI treatment.

**Status:** CP5 is now honestly partial, not fully ticked. What remains before it can close: the graph drill-down link, and an actual zero-row test. Both are small. Neither was rushed through to inflate the checkbox count.

### [2026-09-02 02:20] [Agent tag: A6] [Type: build]
**What:** Closed the one item Wave 3 left honestly open: CP5's "graph reachable from a flagged row." `strings.json` had frozen `detail_panel.fund_flow_entry: "View fund flow"` since Wave 1's copy research, and nothing ever wired it to a destination. Built `/fund-flow`, a new route filtered by `?agency=`/`?vendor=` against A4's live `/api/graph`, rendering a tiered MP -> Agency -> Vendor layout. Chose a fixed tiered layout over a force-directed simulation deliberately: the schema already specifies the geometry (edges only ever run MP to Agency to Vendor), so three columns and straight lines say what a physics simulation would only approximate, with no new dependency.

**Two things caught before shipping, both worth recording so the pattern is visible:**
- Wrote a back-navigation button that reused `detail_panel.close` ("Close") because no dedicated string existed for it. Caught it as a real semantic misuse before committing -- a page-navigation control is not a panel-dismiss control -- and added one new entry, `actions.back_to_inspection_list`, rather than shipping the wrong word. Same discipline A2 set in Wave 2 for a genuine template gap.
- The browser console showed a real, pre-existing React warning in `DetailPanel.tsx`'s `PanelBody`: "Each child in a list should have a unique key prop." Not something this change introduced -- A5's original `recordFields.map()` returned a shorthand `<>...</>` fragment with keys on its two children but none on the fragment itself, and shorthand fragments cannot carry a key at all. Fixed with the explicit `Fragment` form. First console check after the fix still showed the warning; before concluding the fix failed, cleared the console and did a full reload rather than trusting a possibly-stale read -- the second check came back clean. The first read was accumulated history from an earlier API restart during testing, not a real recurrence.

**Verification:** clicked a real row's "View fund flow" link end to end, landed on `/fund-flow?agency=PWD%20Division%207`, confirmed the correct 1-hop subgraph (2 MPs, 1 agency, 2 vendors, real labels and edges) via both extracted page text and a screenshot, not just a 200 status. tsc clean, eslint 0 errors, production build succeeds with `/fund-flow` as its own route.

**Status:** CP5 is now fully ticked. What's left before CP6/CP7 matter at all is unchanged from every entry above this one: the `getTilesReportData` request body, still the one thing separating this whole build from running on real MPLADS data instead of the CP0 fixtures.

### [2026-09-02 02:40] [Agent tag: A6] [Type: build]
**What:** Closed CP5's remaining partial item for real, then built CP6's refresh control, then landed two direct product requests (full-amount currency, tab navigation) that arrived mid-pass.

**CP5's "does not break on 0 results" was actually tested, not inferred, and it found a real crash.** Swapped the real fixture for `[]`, cold-booted the API cleanly (no shortcuts), and hit `KeyError('flags')` in `build_snapshot.py`: `pd.DataFrame([])` with no `columns=` has zero columns. This was a genuine, reproducible crash that would have hit the moment a filter combination ever returned zero rows. Fixed by deriving column lists from the frozen schemas and passing them explicitly.

**The same investigation surfaced three more real bugs**, none of them hypothetical:
- `QuotaMeter` divided by `totalN` with no zero guard -- `Infinity`/`NaN` styling on an empty result.
- `getQuotaFigures`' quota floor produced "1 of 0 works, the 10 percent minimum," nonsensical when there is nothing to have a quota over.
- Separately, writing the regression test for the first bug surfaced a distinct one: `implementing_agency`, `vendor_name` and `sanction_date` can round-trip through parquet as the float `NaN` instead of Python `None` on a plain pandas read. The live API was not actually affected (`db.py` reads through DuckDB, which maps NULL correctly) -- which is exactly why this stayed invisible until a test read the parquet file back with plain pandas, the most obvious tool for a parquet file and something a future consumer of this artifact could reasonably do without ever going through DuckDB. Fixed by casting the three nullable-string columns to pandas' `pd.NA`-based `"string"` dtype before the write.

**A fifth, structural issue found while fixing the first one:** the four snapshot artifacts were each individually atomic but not atomic as a group -- a failure on `graph.json` could leave `works.parquet` and `scored.parquet` already swapped to a new build while `graph.json` and `manifest.json` stayed on the old one. Restructured to stage all four first and commit (rename) only after every stage succeeds. The remaining gap, four separate renames rather than one, is real and named directly in both the module docstring and a test, not hidden.

**`pipeline/tests/test_build_snapshot.py` is new** -- this module had zero test coverage before today, which is exactly how the first bug shipped silently in Wave 2. 13 tests now cover empty input, schema validation against the real fixture (including the null round-trip, checked against a fixture row that genuinely has a null vendor), determinism, and both atomicity failure modes.

**CP6's refresh control, built from nothing** -- there was no frontend trigger for `/api/refresh` at all before this. New `RefreshControl` (idle / refreshing / failed states, matching `strings.json`'s explicit "never blank the table, never a spinner, never disable the filters"), a new `formatTimeIst()` for the failed state's `{time}` placeholder, and a debounce guard. **Caught a real bug live, not in review**: the first version of the guard blocked on any non-idle state, which included "failed" -- meaning once a refresh failed once, "Try again" could never fire a second request, ever. Found by actually clicking "Try again" and watching nothing happen, not by reading the code. Verified against the real 30-second server-side rate limit twice: once inside the window (correct 429, correct failed-state copy, table stayed fully visible), once after it cleared (correct success).

**Two direct requests, both real gaps, both closed:**
- Currency figures were abbreviating to lakh/crore, which the request named as making two amounts harder to compare without doing the conversion mentally. New `formatCurrencyFull()` replaces the threshold-based formatter at all four call sites. The old formatter stays in the file, unused -- it still implements the frozen contract's `number_format.currency` spec for anywhere a compact form is deliberately wanted later.
- No way existed to move between the Inspection List and Fund Flow views except a single row's agency-filtered link. New `NavTabs`, wired into both pages, active tab read from the real route. Explicitly did not invent a third "Specimen Sheet" tab the Claude Design reference showed -- nothing in this codebase specifies that view, and building one now would have been scope creep past what was actually asked.

**A tooling mistake, caught and fixed before it mattered:** the first commit for this batch used unescaped backticks inside a `-m` flag, and bash's command substitution silently ate one code-snippet line from the message (`refreshState !== "idle"` vanished, `"Real bug caught live, not in review: the debounce guard originally read , which also..."`). Caught by reading the actual committed message back rather than assuming `git commit` had done what was asked. Fixed with `git commit --amend -F <file>`, which sidesteps shell quoting entirely -- the correct approach for any future commit message containing backticks or nested quotes.

**Verification held to the same standard throughout:** every fix confirmed against the real running API and a real browser session, not just a passing test. Full pipeline suite (143 tests) and the new file's 13 both re-run independently. tsc clean, eslint 0 new errors, production build succeeds with both routes.

**Status:** CP5 fully closed. CP6 gained a real refresh mechanism where none existed; still open on CP6: an actual live pull from MPLADS (blocked, unchanged), and the network-disabled fallback test, which is next.

---

### 2026-09-02, 09:50 -- CP6 closed to the one remaining blocker: hung-pull timeout, network-disabled fallback, and malformed-pull integration test

Picked up where the last entry left off. Three of CP6's four items are now genuinely done, each verified against real running processes, not inferred from the code.

**The timeout half of "debounced and times out" did not exist.** The debounce guard was verified last pass; nobody had checked what actually happens to a *hung* pull, because `fetchEnvelope` (`web/lib/api-client.ts`) had no `AbortController` at all -- a backend that accepted a connection and never responded would have left "Refreshing the inspection list" on screen forever. Added a 20-second default timeout via `AbortController`, wired through both `fetchInspectionData` and `triggerRefresh` (they share the one `fetchEnvelope` implementation, so this is one fix, not two).

**Verified against a real hang, not a closed port** -- those are different failure modes and only one of them proves a timeout works. Wrote a 15-line raw Python socket server that accepts a TCP connection and then does nothing: no response, no close. Pointed `NEXT_PUBLIC_API_BASE_URL` at it via a temporary `.env.local`, temporarily shortened the timeout to 3s for a fast test, restarted the dev server, and watched both the initial page load and a Refresh click against it land in the correct failure state within the timeout window: "Cannot reach the data service" on load, "The previous results are still on screen. Try again" on refresh. Neither spun forever, neither leaked the raw `AbortError`.

**A false alarm caught and correctly dismissed, not just noted:** the first check (a reused browser tab) showed an extra `Uncaught ReferenceError: NavTabs is not defined`. Rather than assume the timeout work broke navigation, opened a genuinely fresh tab -- the error was gone, confirmed as leftover Fast Refresh state from restarting the dev server out from under a tab that was already open, the same class of stale-console-history problem this project has hit before. Not a real bug; would have been dishonest to log it as one just because it appeared once.

**Then reverted the shortened timeout back to 20s**, deleted the black-hole server and the temporary `.env.local`, and restarted the dev server clean against the real API -- confirmed a fresh tab loads with zero console errors before moving on.

**Network-disabled fallback, tested the more common way too:** loaded the real 14-row dataset, killed the API process outright (`curl` confirmed `ERR_CONNECTION_REFUSED`, a closed port rather than a hang), clicked Refresh. All 14 rows, the summary strip, and the quota meter stayed exactly as they were -- nothing blanked, nothing reset. The control correctly read "Refresh failed. Showing results from 09:36." with a real IST time pulled from the last good load, plus Try again. Console showed only the browser's own network-layer log and one sanitized `console.warn`; nothing uncaught, nothing raw reached the page.

**The malformed-pull item needed a real integration test, not another isolated one.** `pipeline/tests/ingest/test_mplads_api.py` already proved the ZK error HTML page raises a typed exception rather than parsing into garbage rows -- that existed before today. What didn't exist was any test of `cli.py`'s `build()`, the actual function that chains `run_ladder() -> normalize_records() -> cache.write_snapshot()`, which is the real place CP6's "leaves the previous snapshot untouched" wording lives. New `pipeline/tests/test_cli.py`, 4 tests: a rung handing back the shape a naively-parsed ZK error page would produce (no required fields) is rejected by `normalize_records()`'s schema validation, `build()` returns 1, and -- checked directly, not assumed -- `cache.write_snapshot()` is never called: a planted "previous good" snapshot file is asserted byte-for-byte identical afterward, both when a bad rung's data fails validation and when every rung fails and the fixture fallback is also missing. `build()` gained an optional `raw_dir` parameter (default `None`, behavior-preserving) so this could point at a temp directory instead of monkeypatching `cache` module globals.

**Verification:** full pipeline suite re-run independently (147 passed, up from 130), full API suite re-run (25 passed), `tsc --noEmit` clean, `eslint` clean on the changed file. Every claim above about browser behavior was watched happen live, not inferred from reading the code -- including the one false alarm, which was checked rather than either ignored or logged as a bug on first sight.

**Status:** CP6 is now 3 of 4 items done. The one remaining item -- "a real pull from MPLADS succeeds on demand" -- stays genuinely blocked on the same thing it has been blocked on since 2026-09-01: a human capturing the real `getTilesReportData` request body from the live dashboard's browser network tab. Nothing in this pass substitutes for that; it is the one task on the entire plan that only the user can do.

One CP7 item turned out to already be done: re-read `04 Prototype/NidhiNetra Viva Brief.html` section 07 in full rather than trusting the filename, and it already has prepared answers for both judge questions CP7 names plus 8 more, with traps flagged and a words-to-use/never-use cheat sheet in section 08. Ticked. The other three CP7 items (an actual unbroken timed run, watched by a second person) need a human in the loop and have not been started.

---

### 2026-09-02, 10:05 -- A real contradiction between the idea-submission PPT and the Viva Brief, caught by the user

The user pointed at one line: `03 Build Plan/NidhiNetra - SIH26102 Idea Submission.pptx` slide 4 (Feasibility) says "CAG audits and RTI cases already give labeled fraud patterns to validate against, ahead of any live dataset." The Viva Brief's own accuracy trap answer says "No labelled fraud data exists for this scheme," and the PRD calls the absence of ground truth the project's defining honest constraint ("that last row is the strongest thing in the whole project"). Direct contradiction, correctly caught -- a judge who read both would have caught it too.

Checking further surfaced a bigger version of the same problem: the PPT's "Technologies to be used" slide names DBSCAN, SHAP, Sentence-BERT, OpenCV/image hashing, geotag cross-checks, Airflow, and PostGIS. Grepped the real codebase for every one of those terms across pipeline/, api/, and web/ -- zero occurrences of all seven. Only Isolation Forest is actually in the engine, and as a minor supporting signal (20% weight cap), not the headline method the slide implies. The built prototype is narrower and more defensible than the idea-stage pitch: four rule-based detectors, peer-group z-scores, Isolation Forest/LOF as one ensemble input.

One fact that mattered for how to respond: the PPT is not yet submitted. `00 Dashboard.md` and `Execution Plan.md` both record the official SIH-portal idea submission as due 2026-09-20; this deck is an earlier internal draft (2026-08-26). Offered the user three options -- full reconciliation of the PPT, a surgical fix to just the flagged line, or leaving the PPT untouched and preparing a bridging answer instead. **User chose: leave the PPT alone.**

Added one new trap Q&A to the Viva Brief, section 07, right after the existing accuracy trap: names the exact contradiction, states plainly that the prototype's position is the correct one and the PPT line should not survive to the real 9/20 submission, explains *why* the gap exists (CAG/RTI material is prose case documentation, not a work-ID-joined labeled dataset -- that distinction only became clear once the team started building), and extends the same honest correction to the DBSCAN/SHAP/CV claims on the same slide. The "Do not" line is explicit: don't defend the PPT, don't claim CAG/RTI gives something it doesn't, say the correction out loud as evidence real work happened between idea stage and prototype.

**Open, by the user's own choice:** the PPT itself still contains both contradictions today. If it goes to the portal unedited before 9/20, the bridging answer in the Viva Brief is the only mitigation in place.

---

### 2026-09-02, 10:15 -- Correction: the portal submission already happened, ~9/20 was wrong

The user corrected a fact this vault had wrong: **the PPT was already submitted to the SIH portal, roughly 2026-08-31** -- not 2026-09-20, which every planning doc in this vault (`00 Dashboard.md`, `03 Build Plan/Build Plan.md`, `04 Prototype/Execution Plan.md`) had recorded as the deadline and scheduled backwards from, including `Execution Plan.md`'s calendar section, which had explicitly (and wrongly) reassured itself that date was solid ("that date has been in this table all along"). It was not solid; it was wrong, and nobody had reason to doubt it until the user said so directly.

Corrected all three docs: `00 Dashboard.md`'s header line and the PPT-delivery line, `Build Plan.md`'s timeline row, and `Execution Plan.md`'s calendar section, including marking every CP0-CP7 date in that table as "not re-anchored to a real deadline" rather than silently leaving them looking authoritative when the deadline they were sequenced against never existed as stated. Did not invent new dates for CP0-CP7 -- the only other real known constraint (the internal round date) is still unknown, so rebuilding the calendar against something real is not possible yet.

**This changes what the prior entry's "Open" item meant.** The PPT is not "still open to be fixed before 9/20" -- it is locked, submitted, done, and will be presented as-is. Rewrote the Viva Brief's new trap Q&A (07) from prospective tense ("should not survive to the real submission") to present-tense fact: the PPT already contains the error, it will not be edited, and the "Do not" guidance now explicitly says not to pretend the gap isn't there rather than warning against a future mistake that already happened. The underlying honest position (idea-stage hypothesis vs. what the prototype actually found) did not need to change, only its tense.

**Status:** the labeled-data / tech-stack contradiction between the submitted PPT and the prototype is now a permanent, unfixable fact of this project, not an open item. The only mitigation is the prepared answer in the Viva Brief, and it needs to be said plainly and immediately if it comes up, not danced around.

---

### 2026-09-02, 10:25 -- A second explanation doc, written to match the PPT's own framing instead of contradicting it

The user asked for a new document, not an edit: keep `Understanding NidhiNetra.html` exactly as it is, and produce a second version that explains the project using the submitted PPT's own feasibility framing rather than the more cautious "no labelled data exists at all" framing the original uses. Since the PPT cannot change (confirmed submitted, previous entry), this is the other lever available: make the companion explanation doc stop contradicting the document that is actually locked in front of judges.

New file: `04 Prototype/Understanding NidhiNetra - PPT Edition.html`, a copy of the original with three targeted rewrites, not a full rewrite:

- **Part 4** ("Why we say odd and never wrong"): reframed from "no labelled data exists, we have none" to the PPT's actual claim, read in its most defensible form -- CAG audit reports and RTI-obtained case files are real, confirmed, on-the-record instances of MPLADS-type misuse, and they were used to decide *what to build detectors for*, ahead of any live dataset. Kept two things unchanged on purpose: the teaching content on supervised vs. unsupervised learning (still accurate), and the "do not invent an accuracy number" rule -- that rule doesn't depend on which framing is used, and softening it would have been the one edit that crossed from reframing into actually overclaiming. The reason for no accuracy number changed (not "no data exists" but "not yet joined to live records at a scale anything could be scored against"), the rule itself did not.
- **Part 6**: added a new subsection naming DBSCAN and the NLP/CV cross-checks the PPT's tech slide lists, stating plainly that neither is running in this prototype and why (needs a live, work-level dataset at scale that does not exist yet) -- framed as staged next steps the working core proves out first, not as something built.
- **Words to use/avoid cheat sheet**: swapped the "no answer key exists" line for one matching the new framing.
- Added one paragraph to the intro box explaining the two documents now coexist on purpose and answer different questions, so nobody opening both is confused by the difference.

**What did not change and was not tempted to:** no fabricated accuracy percentage, no claim that DBSCAN/SHAP/CV are actually running, no claim that CAG/RTI cases are joined to live MPLADS work IDs. The whole point of this exercise was narrative alignment with a real, defensible reading of the PPT's claim -- not inventing capabilities the code does not have. Verified `<div>` open/close counts match the original (46/46) before treating the HTML as sound; read the rendered page in a browser tab, spot-checked Part 4's rendering for leaked markup.

Published as a new artifact (separate URL, old one untouched, per the user's explicit "keep the old one").


### 2026-09-03, 11:40 -- Frontend pass against the Claude Design reference: the filter bar that never existed, and a risk breakdown that was quietly wrong

The user asked for two things: move the app to Next.js, and match the frontend to `Precision and research first/NidhiNetra.dc.html`. The first was already true and was said so plainly rather than performed as work: `05-App/web/package.json` has pinned `next` since Wave 1 (16.3.4, React 19.2.8 underneath it). There was no React-only build to migrate off.

**The filter bar, element three of the design brief's page order, had never been built.** `contracts/strings.json` has carried a full `filters` block (state / year / category / flag / flag_names / clear) since CP0, and `data_states.empty_after_filter` describes what the table shows when a filter returns nothing. Neither had a UI. The empty state was literally unreachable: nothing in the app could narrow the list to zero. New `web/lib/filters.ts` and `web/components/filters/FilterBar.tsx` close that, plus `web/styles/filters.css`.

Details worth recording because they were decisions, not defaults:
- Every option list is derived from the rows the API actually returned, per brief section 11. Bihar is in the raw 20-row fixture but not in the State dropdown, correctly: its one work is not under implementation, so offering it would be offering a filter that can only return nothing. The Flag type list is the one exception and only partly, it is the four flag types the engine can emit rather than the ones present in this batch, because deriving it from the data would make the product look like it has fewer detectors than it does on any batch where one did not fire.
- Filtering renumbers `displayRank` over the survivors and leaves the scorer's global `inspection_rank` untouched. The quota meter reads `displayRank`, so a filtered list that kept its original ranks would draw the cut-off at a row that is no longer there. Verified live: filtering to Jharkhand took the meter from "2 of 14 works" to "1 of 4 works" and moved the cut-off marker with it.
- The summary strip deliberately does **not** respond to filters. It is the standing picture of the whole workload; four figures that moved on every filter change would stop being the fixed reference points they exist to be.
- The bar is flat in flow and only lifts once stuck, per brief section 4. Driven by a one pixel sentinel and an IntersectionObserver rather than a scroll handler.

**The detail panel's risk breakdown was misstating the engine, and that was the more serious find.** `riskFactors()` divided `risk_score` evenly across however many flags had fired, so a record flagged for cost and for agency concentration showed two identical weights. The engine does nothing of the kind: `risk/rank.py` weights the four flags 30 / 25 / 25 / 20, caps their sum at 80, and adds a separate ensemble component worth up to 20. An even split is not a simplification of that, it is a different claim, and it turned the one element the brief requires to be legible ("so the score is never a black box") into a black box wearing a breakdown's clothes.

New `web/lib/risk-weights.ts` mirrors the real weights (hand-mirrored, and the file says so, with the drift risk named and `test_rank.py` pointed at as where the assertion belongs once `make contracts` codegen exists). The panel now itemises each fired flag at its true weight, scales all of them by the same factor the engine applied when the 80 point cap bites, and shows the remainder as a separate ensemble line in muted ink rather than the risk ramp. Bar length is each contribution's share of that score, not the raw point value read as a percentage, which is what the old code did.

Verified by computation rather than by eye, across five flag combinations: every itemised list sums to the score exactly, including the four-flag case where the cap scales 30/25/25/20 down to 24/20/20/16 and the ensemble takes the remaining 15 of 95.

**One behaviour deliberately preserved:** an unflagged record still shows `framing.unflagged_caveat`, not an ensemble-only breakdown. Every one of the 14 current rows is unflagged, so this is the visible path today, and itemising "14 points of statistical pattern" would dress up "nothing was flagged" as a finding with a number attached.

**Contract amended, not patched in a component.** Three new keys under `detail_panel` (`breakdown_ensemble`, `breakdown_ensemble_note`, `breakdown_capped`), landed in `contracts/strings.json` with an `_meta.amendment_log` entry, per that file's own amendment rule. No existing string changed. Checked against the `lint.banned_derived` list before writing: the ensemble line says "Statistical pattern across all works" and never "model", "algorithm", "confidence" or "accuracy".

**Row treatment reconciled with the reference.** The reference bleeds the hover wash past the content edge, rounds it, tints the selected row with the interactive accent rather than the neutral wash, and draws a real focus ring. The build plan's section 2.7 specified a risk-coloured tick at the left edge. These do not conflict, so both are kept, and the reason they can coexist is worth stating: the tick is the only part carrying the warm risk ramp, and the wash underneath stays neutral or cool. A hovered row washed in the risk colour would have merged the two scales brief section 6 wants kept apart. Also added: ranks inside the annual quota now carry full ink and a heavier weight, so the cut-off is visible in the rank column and not only in the meter.

**The thing that stops the app looking like the reference, and it is not CSS.** The reference shows 16 works, all flagged, scores 52 to 96, every row carrying a reason line. The app shows 14 works, none flagged, scores 9 to 14. Traced to a single cause: `MIN_PEER_GROUP_N` is 30 and the largest real peer group in the 20-row fixture is 4, so every row's `peer_group` is null, `cost_outlier` and `expenditure_mismatch` can never fire, and scores come only from the ensemble component (capped at 20, which is exactly where the observed 9 to 14 sit). The knock-on effects are the two elements the brief cares most about: the reason line, "the most important element on the entire page", never renders because `why_flagged` is empty on every row; and the peer-group sentence, the thing that "answers the strongest objection anyone can raise against the whole product", never renders because there is no peer group to name.

Put to the user with three options. **User chose: frontend only for now.** The dataset work is deferred to a later phase, together with training against CAG and RTI material and feeding that into MPLADS risk scoring. Explicitly **not** done: no fixture rows were invented to make flags appear, and `MIN_PEER_GROUP_N` was not lowered. Lowering it was offered only to be argued against, since it weakens a real statistical guarantee to make a demo look better.

**Also declined, and worth recording as a boundary:** the reference's risk breakdown lists six factors. Three map to real detectors. "Time overrun since sanction date" is honestly computable from `sanction_date` but is not built, and the user chose to keep the real four rather than reopen CP2 for it. The remaining two, "No asset photograph at payment stage" and "Implementing agency is a society or trust", have no field or rule behind them anywhere in the schema. Copying those labels would have meant inventing a capability the system does not have, which is the same mistake the 2026-09-02 PPT entries exist to record. Not done.

**Verification:** `tsc --noEmit` clean, `eslint` 0 errors (5 warnings, all pre-existing on HEAD and confirmed so with `git show`), `contracts/validate.py` passing, pipeline suite 147 passed, API suite 25 passed. Filter behaviour, the stuck treatment, the selected-row accent and the detail panel were each checked live in the browser rather than inferred from the code.

**Note for the next phase, flagged and not acted on:** the user described the coming work as "train our model using CAG and RTI dataset". The 2026-09-02 10:05 entry above concluded the opposite about that material, that CAG audit reports and RTI case files are prose case documentation and not a work-ID-joined labelled dataset, which is exactly why the accuracy trap answer in the Viva Brief says no labelled fraud data exists for this scheme. Those two positions need reconciling before that phase starts, or the prototype will drift back into the contradiction the PPT is already locked into.

---

### 2026-09-03, 12:20 -- Reference-fidelity pass, part two: verified a concurrent session's work, then closed the rest of the gap list

The user pointed at a second Claude Code session working the same repo concurrently and asked for it to be checked before continuing. It had built the filter bar and fixed a real bug in the detail panel's risk breakdown (`risk_score` was being divided evenly across fired flags instead of using the engine's real 30/25/25/20 weights). Verified independently rather than trusted: cross-read `web/lib/risk-weights.ts` against `pipeline/src/nidhinetra_pipeline/risk/rank.py` and `web/lib/filters.ts`'s `financialYearOf` against `risk/peer_groups.py`'s `financial_year_of`, both line-for-line matches. Re-ran the full verification independently rather than trusting the reported numbers: pipeline suite 147 passed, API suite 25 passed, `contracts/validate.py` OK, `tsc --noEmit` clean, eslint 0 errors/5 warnings with one warning spot-checked against `git show HEAD` and confirmed pre-existing. Live in a fresh tab: filter bar renders, sticky, zero console errors. My own in-progress `strings.json` edits and their `detail_panel` additions had landed in the same file with zero key conflicts. Full findings relayed back to the user, including a flag they raised themselves: their Logbook entry named a "next phase" the user described to them ("train our model using CAG and RTI dataset"), which is in direct tension with this session's 10:05 entry today concluding no labelled dataset exists. Surfaced to the user, not acted on by either session.

**Then closed the rest of the gap list this session's own reconnaissance had found**, none of it touched by the other session:

- **Days stale column.** New `daysStale()` in `lib/format.ts`, computed against the snapshot's own `data_as_of` rather than the browser's real-world today (two officers on the same cached snapshot must see the same age). `columns.tsx`'s static `columns` export became `buildColumns(asOf)`, memoized in `InspectionTable` on `asOf` -- the accessor needs it to return a sortable number, not a raw date string. Verified against real data, not assumed: the fixture's `last_updated` is `2026-08-15` for the shown rows, `data_as_of` was `2026-09-03T06:36:30Z`, and the column correctly showed 19 for all of them -- confirmed by hand-computing the day count, not just eyeballing that a number appeared.
- **Quota meter replaced with the reference's plain sentence.** The existing `QuotaMeter` was a real, deliberately-built interactive bar (per-row risk-band colouring, hover-to-see-rank) -- not a placeholder, and arguably better UX than what the reference shows. Replaced anyway: the reference has no bar on the Inspection List at all, only one sentence, and the instruction was to match completely, not to keep what this build judged an improvement. New `table.filtered_summary` in `strings.json`, quoting the reference's sentence exactly, filled with real computed totals.
- **Top bar with the ministry name.** The reference puts "Ministry of Statistics and Programme Implementation" and the two nav tabs on one line above the title, on every page; the app had neither the ministry line nor tabs in that position (NavTabs lived below the premise paragraph on each page, duplicated in both `page.tsx` and `fund-flow/page.tsx`). New `nav.org_label` in `strings.json`, new `TopBar.tsx` in the shared `layout.tsx` (a Server Component; NavTabs stays a Client Component, Next.js allows the nesting without forcing the layout to become one too), which also removed the duplication rather than just relocating it twice.
- Also fixed in passing: `nav._note` pointed at a stale path (`05 Design Reference/...`) for the reference file, which actually lives at `Precision and research first/...` -- corrected, and its Specimen Sheet explanation updated to say plainly what part 8 of the design brief actually says it is (a type/spacing/colour specimen page, not a product view), rather than only saying what it is not.

**One warning caught by re-running the full check after the changes, not left for later:** removing the bar left `QuotaMeter`'s `quotaN` prop unused -- eslint caught it, fixed by dropping the prop from the component and its one caller rather than leaving dead surface area. Net eslint warnings after this pass: 4, down from 5 at the start of today (the `useMemo` import the other session had added ahead of need is now actually used).

**Verification:** `tsc --noEmit` clean, eslint 4 warnings (down one, zero new), `next build` succeeds for both routes, live checks in fresh tabs on both `/` and `/fund-flow` with zero console errors. One stale-console false alarm during this pass (an old Fast-Refresh error from an intermediate save, not the current state) -- checked in a fresh tab before concluding anything, per the standing rule this project keeps re-learning is worth keeping.

**Still open:** the Fund Flow view rebuild (the reference's threshold filter sidebar and cluster-in-focus panel) is the one item from the original gap list not yet started.

---

### 2026-09-03, 13:05 -- Fund Flow rebuilt against the reference: a threshold filter and a cluster-in-focus panel, both real

Closed the last item on the reference-fidelity gap list. The reference's Fund Flow view has a live "minimum Members per vendor" filter and a "cluster in focus" panel for whichever vendor is highlighted; the app had a static SVG subgraph and nothing else.

**New `lib/vendor-concentration.ts`** does the actual computation, kept apart from any component so it could be reasoned about on its own: `allVendorConcentrations` walks the graph's two edge hops (MP -> Agency, Agency -> Vendor -- there is no direct MP -> Vendor edge) to get each vendor's distinct Member count, work count and amount paid; `matchingVendors` filters and ranks by that count; `medianMemberCount` and `subgraphFor` (the "everything else is held back" behaviour) round it out.

**One figure deliberately not built: Districts.** The reference's cluster panel shows Members and Districts as two different numbers. Checked against `build_graph.py` before assuming they could both be computed: its own docstring says "the graph carries no separate district node -- an MP's constituency stands in for district here," and MP nodes are keyed by `mp_name`, one node per distinct MP, not per distinct constituency. There is no field to honestly produce a Districts count from in this schema. Named in `strings.json`'s amendment_log rather than either faked or silently dropped without explanation -- the same discipline the PPT entries from 09-02 exist to enforce, applied here before it became a mistake instead of after.

**Verified the new computation against the raw data directly, not just read the code.** Nothing in `vendor-concentration.ts` has a Python equivalent to cross-read the way the other session's risk-weights and financial-year code did, so independently recomputed it from `/api/graph`'s actual JSON in a standalone Python script: member counts, work counts, paid amounts, which vendors matched at threshold 3, and the median among them. Every number matched the rendered UI exactly, including the alphabetical tie-break between the two vendors both connected to 8 Members (Ganesh Infra Pvt Ltd sorts before Shree Balaji Construction, and the UI correctly focused Ganesh by default).

**Interaction, not just a static render.** `GraphView.tsx` gained an optional `highlightVendorId` (renders that vendor's path -- itself, its agencies, their MPs -- in the accent colour, everything else faded, matching the reference's single red-highlighted cluster) and `onVendorClick` (vendor nodes become real, keyboard-accessible buttons). Tested live: the stepper's +/- change the threshold and correctly re-rank and re-focus; "Show the vendors that do not match" toggles the full graph back in without touching the threshold or the focused vendor; pushing the threshold to 9 (above every vendor's count) correctly shows the existing `empty`/`empty_body` state with no crash and no console error, and the cluster panel correctly disappears rather than rendering with an undefined vendor.

**Scope boundary, deliberate:** the existing `?agency=`/`?vendor=` deep link from a flagged row's "View fund flow" link keeps its original simple view, unchanged. That is a different, already-real use case (a server-filtered subgraph for one specific entity) from the reference's unfiltered landing view this pass matches; extending it to also carry the new filter UI was not attempted and was not asked for.

**One test-tooling lesson, not a code bug:** a batched `repeat: 10` click on the decrement stepper appeared to do nothing. Turned out to be the batching resolving the click coordinate once and repeating it at a now-stale position after the first click shifted the layout, not a broken handler -- confirmed by single fresh clicks, which worked every time. Worth remembering before reporting a false negative as a real bug next time repeat clicking is used on a layout that reflows.

**Verification:** `tsc --noEmit` clean, eslint 4 warnings (all pre-existing, zero new), `next build` succeeds for both routes, `contracts/validate.py` OK, pipeline suite 147 passed, API suite 25 passed. Live: fresh-tab console clean on both routes; every number in the filter and cluster panel independently recomputed from the raw `/api/graph` response and matched exactly.

**Status:** the reference-fidelity pass that started this session's "start the frontend" / "shift to Next.js" (already true) / "completely matched with the reference" request is now complete against every gap the side-by-side comparison found: filter bar, risk breakdown weights, days stale column, quota sentence, top bar, and the Fund Flow threshold filter and cluster panel. Known, named, deliberate gaps remain (Specimen Sheet, the Districts figure, the fabricated flag types) -- all documented at the point each was found, not discovered later.

---

### 2026-09-03, 19:30 -- Full-codebase review, two fixes, one correction I owed the user, and phases 6-7 finally on the plan

Reviewed all ~5,700 lines rather than a diff (tree was clean). Security came back genuinely clean, and not by assertion: no hardcoded credentials anywhere, `npm audit` 0 vulnerabilities with both lockfiles present, no XSS vectors (no `dangerouslySetInnerHTML`, `innerHTML`, `eval`, `new Function`), and SQL injection and path traversal both **probed live** rather than reasoned about (`state=' OR 1=1--` returned 0 rows and no error; `works/../../etc/passwd` returned 404). No files over 800 lines, no TODO/FIXME, no emoji, no `console.log`. Accessibility is genuinely strong: every `role="button"` is keyboard-reachable, the table has arrow-key navigation, and aria attributes are present in all eight interactive components.

**Two real defects found and fixed, both committed.** The CORS one is the one that mattered: `allow_origins` was exactly `["http://localhost:3000"]`, and `next dev` silently moves to `:3001` when `:3000` is taken. On stage that shows "Cannot reach the data service" -- the honest fallback working perfectly, with nothing actually wrong. Verified the fix against seven origins including two hostile lookalikes, which stay blocked. The other was "1 points" in the detail panel: reachable only through the ensemble remainder, so invisible on the current fixture (no flagged rows), which is why I compiled `risk-weights.ts` and ran the real module rather than looking for it in the browser and concluding it wasn't there.

**A finding whose severity dissolved on inspection, worth recording as a method note.** The naive "functions over 50 lines" check flagged nine Python functions. Measuring code lines against comment lines changed the picture completely: `build_snapshot()` is 87 lines but **39 code**, `score_all()` 83 but **39 code**. Only three functions genuinely exceed the guideline in code terms (56, 61, 61). Reporting the raw spans as HIGH findings would have been technically defensible and substantively wrong.

**The correction I owed.** On 2026-09-02 I told the user the PPT's CAG/RTI line "directly contradicts" the prototype, and wrote a Viva Brief answer instructing the presenter to disown it. The user pushed back, saying the unsupervised-now-then-learn-from-inspections approach is already in the deck and the explanation doc. They were right and I was wrong. Slide 4 says, three lines under the line I objected to: *"Lean on unsupervised detection first; save supervised classifiers for once confirmed cases pile up."* The same slide lists *"confirmed fraud is rare, so the data is heavily imbalanced"* as a known risk, and slide 2 commits to *"reviewers train the model, not the reverse."* I had weighted one loosely-worded feasibility bullet and missed the strategy bullet that already stated the honest position. Rewrote the Viva Brief answer: it now points at the deck's own strategy line as the answer, concedes only the narrow true thing (the word "labeled" is doing more work than it should; CAG/RTI give pattern knowledge, not a joined corpus), keeps the genuine DBSCAN/SHAP/CV gap, and explicitly warns against the over-concession my earlier version told them to make. Apologising on stage for a defensible strategy would have cost more than the loose word ever did.

**Phases 6 and 7 now exist on the plan.** They were promised in three places and planned in none. Added as CP8 (feedback loop) and CP9 (learning) in [[Checkpoints]], and as phases 6-7 in [[Execution Plan]] section 4. Split deliberately: **CP8 contains no model work at all.** The reason is that an inspection outcome currently has nowhere to go -- no schema field, no endpoint, no store -- and you cannot train on data you never captured. CP8 also forces an architectural decision the app has so far avoided: every artifact today is rebuildable from source by `build_snapshot()`, and a human inspection judgement is the first piece of state that is not. It has to live where a rebuild cannot erase it, and that is a design decision, not an implementation detail to trip over later.

Two guards written into CP8/CP9 on purpose: the outcome enum must record observable facts ("work not found at site", "quantities differ from record") and never verdicts like "fraud" or "clean", because the enum decides what the system can ever learn and a loose one re-imports the accusation framing the product refuses; and precision-at-quota must be suppressed below a stated minimum `n`, the same discipline `MIN_PEER_GROUP_N` already enforces, because a precision figure computed on four inspections is worse than no figure. CP9 requires the minimum outcome count be agreed *before* results are seen, so the threshold cannot be chosen to flatter the outcome.

**Left open deliberately, with reasons:** LAN-address CORS (widening to private IP ranges is a bigger hole than the case warrants); zero test coverage on 2,835 lines of TypeScript, including the two cross-language mirrors whose own docstrings name drift as a live risk -- flagged as the top remaining HIGH, not fixed, because standing up a test runner was not what was asked for.

---

### 2026-09-03, 19:55 -- H2 closed by locking the three TS-Python mirrors, plus two decisions to record cleanly

User asked to derive multi-model reasoning and "continue until the project is complete." Two things had to be said before anything got done: full completion cannot happen in this session (CP1 waits on the user-only `getTilesReportData` capture, CP7 waits on a second human and the pitch slot length, CP8/CP9 sit behind CP1), and CP1 itself might not need the user at all if Rung 3 or 4 of the acquisition ladder can be tried first. Started there.

**Then reversed on Rung 3/4, and it is worth recording why.** `rungs.py`'s own docstring says: *"Build this only once Rung 1 is confirmed permanently dead -- right now it is blocked on parameters, not dead, so Rung 2 is not yet warranted."* That reasoning holds for Rungs 3 and 4 too. Jumping to a fallback data source now, because the primary one takes a captured request body, is exactly the substitution the ladder was designed to sequence *against*. Also: Rung 3 (Empowered Indian) and Rung 4 (data.gov.in) are aggregate/state-level sources whose exposure of per-work `implementing_agency` and `vendor_name` is unproven, and without both fields the fund-flow graph has no data to render. Parked, correctly. The data spike cost me a couple of tool calls, which is the right price for verifying rather than assuming.

**Pivoted to H2 -- lock the three TS-Python mirrors.** First attempt was `npm install -D vitest@^2`, which introduced **5 vulnerabilities including 1 critical** into a project I had certified clean in the same session. Removed immediately; the second attempt (`vitest@latest`) hit an ERESOLVE against the Next 16 / React 19 tree, and I initially misread its silent failure as success. Cleaned up, checked real state (nothing in package.json, nothing in node_modules, audit 0), and rethought.

**The reframe:** the H2 finding was "0 tests across 2,835 TS lines". Read literally, it invites standing up a JS test runner in a bleeding-edge Next tree to cover UI wiring already verified live. Read for the actual failure mode it names, the real risk is narrower: three TS files hand-mirror Python constants and algorithms, and the mirrors' own docstrings name drift as live. `risk-weights.ts` says outright *"pipeline/tests/risk/test_rank.py is the place to add the assertion that catches that"*. A Python test that reads the TS as text and asserts the constants match catches the same drift, uses tools already installed, and does not open a dependency can I've now proven bites.

Also caught a third mirror the earlier review missed: `web/lib/peer-group.ts:51` has a bare literal `30` for `MIN_PEER_GROUP_N`. Same drift class; found while grepping for others before writing the test, added to the coverage.

**New `pipeline/tests/test_web_mirror_drift.py`, 16 tests, no new dependency.** Covers all three mirrors. The financial-year mirror is verified two ways deliberately: structural regex checks the TS source encodes the invariants (April cutoff via `getMonth() >= 3`, sanction_date preferred over last_updated, `padStart(2, "0")`), and a truth table of 9 edge dates drives Python's `financial_year_of` to catch off-by-one bugs a correctly-shaped TS function could still have. The truth table includes `2099-12-31 -> "2099-00"` for the century-rollover `%100` pad.

**Verified by injected drift, not just by "it passes on today's code."** Temporarily flipped each of the three constants on the TS side -- `cost_outlier: 30 -> 31`, `peerGroup.n < 30 -> < 25`, `getMonth() >= 3 -> >= 4` -- each triggered exactly the right test failure with a specific diagnostic, reverted, and the full 16 passed again. That is the meta-test that says the drift detector is real.

**One deliberate boundary named:** `web/lib/vendor-concentration.ts` (the Fund Flow computation) is not covered. It does not mirror a Python constant, it computes something the Python side does not compute at all, so this test class does not apply. Its correctness was proven earlier today against a standalone Python recomputation from the raw `/api/graph` JSON (see 2026-09-03 13:05 entry); a proper unit test would need either a JS runner or a hand-ported Python equivalent. Left honestly open, not silently.

**Also cleaned a small deprecation as it appeared** rather than after the whole run: pytest 10 removes class-scoped fixtures defined as instance methods; refactored to plain per-test file reads (cheap, one warning gone).

**Verification:** 163 pipeline tests (was 147, +16 new), 25 API tests, tsc clean, next build succeeds, `npm audit` back to 0 vulnerabilities.

**Now honestly done for this session.** The remaining unticked plan items all fall into categories this session cannot advance further:

- CP1: user-only capture (see `04 Prototype/Logbook` 2026-09-01 19:45 entry for the exact next action).
- CP2/CP3/CP4: gated by CP1 -- built and tested, but their "against real records" clauses cannot pass on fixtures.
- CP6: same, its one open item.
- CP7: needs a second human, a pitch slot length recorded nowhere, and one unbroken timed run.
- CP8/CP9: sit behind CP1 (an inspection recorded against a fixture work_id measures nothing) and are correctly scoped as future phases, not deferred work.

Two things the user themselves might reasonably want next, both starter tasks, not this session's work: capturing the request body, or scoping CP8's outcome-enum in a whiteboard session before it becomes code.

---

### 2026-09-04, 10:35 -- HANDOFF: CP1 data unlocked, adapter not written, session handing to Opus 5

**Status of session:** interrupted mid-work. User captured the real MPLADS request body, session used it to pull three tiles of live data to disk, mapped the categorisation problem, then handed off before writing the adapter. Everything the next session needs to complete CP1 is on disk. Nothing has been committed. No source files have been edited. Data files are in `data/raw/`, which is gitignored (see `data/raw/.gitignore`), so a stray `git add -A` will not sweep them into the repo.

**Correction to record first, because it changes existing code:** `rungs.py`'s `Rung1LiveApi` docstring and my earlier 2026-09-01 19:45 Logbook entry both said `body: {"combo": <int>, "key": "<string>"}`. **Wrong.** Real format is `body: {"combo": "0,0,0,2", "key": "<tile name>"}` -- combo is a comma-separated STRING, not an integer. That is why every combo/key pair tried in the earlier session returned `Total_Amt: 0.0`: they sent integers. The `"0,0,0,2"` string encodes (Lok/Rajya, tenure index, ..., tile index) -- exact decoding not needed, the string works verbatim. Fix rungs.py's docstring to match.

**Working `key` values, all with `combo: "0,0,0,2"`:**
- `"Works Recommended"` -> 106,294 rows, per-work
- `"Works Sanctioned"` -> 79,068 rows, per-work (the primary source for CP1)
- `"Works Completed"` -> 34,258 rows, per-work, subset of Sanctioned (join by `WORK_RECOMMENDATION_DTL_ID`)
- `"Expenditure on Completed and On-going Works as on Date"` -> 72,660+ rows, per-expenditure-event (multiple rows per work_id)
- `"Allocated Limit for Hon'ble MPs"` -> per-MP allocated amounts

**Files sitting on disk (all in `05-App/data/raw/`, gitignored):**
```
mplads-sanctioned.json           62M    79,068 rows   clean
mplads-completed.json            22M    34,258 rows   clean
mplads-expenditure.json          52M    truncated by server mid-record
mplads-expenditure-salvaged.json 50M    72,660 rows   parsed from the truncated response, ready to use
```
Plus the source HAR at `/Users/krish/Downloads/mplads.mospi.gov.in.har` (189 MB) with the original captured payloads. Do not re-download from HAR unless something looks wrong -- the parsed .json files above already have what is needed.

**Session cookies almost certainly expire soon.** Session ID at time of pull: `cZLjA4tqSBMB7_kk6rXyhuUwMFdm40qoiOEhE0HS.jboss_8081`. The three curl calls in this session ran ~30 minutes after user's original browser capture, all returned 200. Expect them to die within hours. When they do, the fix is another `getTilesReportData` capture from the user; the cURL shape is the same, only the JSESSIONID cookie changes. Record that fresh cURL when it happens; do not embed cookies in committed code.

**Server truncates Expenditure responses.** Fresh curl for Expenditure returned 200 with `Content-Length` unset (chunked encoding), 54,151,559 bytes written before the connection ended mid-record at record ~72,661. The salvaged file has the first 72,660 complete records. Not a client-side timeout -- the exact same truncation pattern appeared in the HAR earlier, well within its 2-minute page load. This is a real server-side limitation of this endpoint at full-national scale; either (a) accept the salvage as-is (72k out of ~probably-73k rows is fine for CP1), (b) paginate/narrow the pull by state or tenure, or (c) contact MoSPI. For CP1, accept the salvage.

**Row shapes -- what each tile actually provides:**

*Sanctioned (`data/raw/mplads-sanctioned.json`)* -- 79,068 rows, 22 fields:
`ACTIVITY_NAME, ATTACH_ID, CONSTITUENCY, CONSTITUENCY_ID, FILE_STATUS, FLAG, HOUSE_OF_PARLIAMENT, IDA_NAME, LETTER_NO, MP_NAME, RECOMMENDATION_DATE, SANCTION_AMOUNT, SANCTION_DATE, STATE_NAME, Sno, TENURE, TENURE_END_DATE, TENURE_START_DATE, WORK_CATEGORY, WORK_DESCRIPTION, WORK_RECOMMENDATION_DTL_ID, WORK_STAGE`

All 79,068 have unique `WORK_RECOMMENDATION_DTL_ID` (integer, use as primary key). All have `SANCTION_DATE` in `DD-MMM-YYYY` format (e.g., `"09-Jul-2024"`) with no nulls. `WORK_STAGE` distribution: `Physical Inspection`: 34,184 / `Sanction`: 20,227 / `Vendor Identification`: 11,601 / `Work partially Completed`: 8,027 / `Work Completed`: 4,207 / `Time Estimation`: 822. `SANCTION_AMOUNT` no nulls, range ₹2.46 to ₹4.97 crore. `WORK_CATEGORY` is coarse (`Normal/Others` for 98%) -- do NOT use it as the peer-group category; use ACTIVITY_NAME instead (see below).

*Completed (`data/raw/mplads-completed.json`)* -- 34,258 rows, 16 fields, adds `ACTUAL_AMOUNT`, `ACTUAL_END_DATE`, `AVERAGE_RATING`, `WORK_ID`. Every completed `WORK_RECOMMENDATION_DTL_ID` also appears in Sanctioned. But `WORK_STAGE="Work Completed"` in Sanctioned only marks 4,207 works, not 34,258 -- so **do NOT rely on WORK_STAGE alone to identify completed works; join with the Completed tile explicitly**.

*Expenditure salvaged (`data/raw/mplads-expenditure-salvaged.json`)* -- 72,660 rows, 20 fields, per-expenditure-event (multiple events per work). Adds `VENDOR_NAME`, `VENDOR_ID`, `FUND_DISBURSED_AMT`, `EXPENDITURE_DATE`, `WORK_STATUS` (values include "Payment In-Progress", "Payment Success"). Aggregate `FUND_DISBURSED_AMT` grouped by `WORK_RECOMMENDATION_DTL_ID` -> per-work expenditure; take the modal VENDOR_NAME per work_id for the vendor_name field.

**The activity/category mapping problem, unsolved.** `normalized_record.schema.json` fixes `work_category` to a 7-value enum: `Road, Drinking Water, School, Health, Community Infrastructure, Electricity, Sanitation`. MPLADS returns 112 distinct activity strings extractable from `ACTIVITY_NAME` (regex `^WS/\s*MP\d+/\d{4}-\d{4}/\d+-(.+)$` captures 100% of them). Top activities include "Construction of roads...", "Lighting of public spaces", "Street lights", "Installing tube-wells", "Purchase of prosthetics/wheel chairs", "Purchase of ambulances", "Development of playgrounds", "Setting up crops conservation facilities" (agriculture has no bucket -- least-wrong is Community Infrastructure). Every activity needs a deterministic keyword rule mapping it into one of the 7 categories, checked most-specific first. Draft mapping written mentally, not yet in code:
- **Road**: road, culvert, bridge, pathway, footpath, cycle track, staircase, railway platform, FOB
- **Drinking Water**: water, tube-well, borewell, hand pump, tanker, drinking, irrigation, pond, rainwater
- **School**: school, college, library, book, anganwadi, creche, educational, training equipment/institution, laboratory
- **Health**: hospital, PHC, dispensary, health, veterinary, prosthetic, wheel chair, ambulance, medical, FWC, ANM
- **Electricity**: light, electricity, energy (non-conventional included)
- **Sanitation**: toilet, drain, gutter, sewer, garbage, effluent, sanitary, biodigester, night soil
- **Community Infrastructure**: everything else (community centers, halls, parks, playgrounds, stadiums, gyms, CCTV, benches, bus-sheds, security gates, night shelters, heritage, crematoriums, animal shelters, govt offices, tree plantation, forest, radio, fire tenders, everything ambiguous)

The mapping is judgement-heavy at the margins. Do it as a keyword-priority list in code, land it in a new module, and add a test that asserts 100% of the 112 real activities get bucketed to one of the 7 (no `Normal/Others` leaking through as-is, no `KeyError`, no `Uncategorised`).

**Peer-group availability, computed on the real data (this is huge for CP2/CP5).** With the corrected activity extraction, keying (activity, state, financial_year): 2,984 distinct groups, of which **441 groups (containing 65,953 works, 83.4%) meet the MIN_PEER_GROUP_N=30 floor.** Fallback (activity, FY) national: 147 groups covering 77,766 works (98.4%). Every complaint in the 09-03 review about "peer groups too small, no flags fire, reason lines never render" evaporates the moment the adapter lands and CP1 unblocks.

**What the next session should do, in order:**

1. **Write `pipeline/src/nidhinetra_pipeline/ingest/mplads_adapter.py`** -- pure function that takes the three parsed lists (sanctioned, completed, expenditure) and returns `list[dict]` in the schema shape. Field mapping:
   - `work_id = str(WORK_RECOMMENDATION_DTL_ID)` (schema wants string, source is int, no collisions)
   - `state = STATE_NAME`
   - `constituency = CONSTITUENCY`
   - `mp_name = MP_NAME`
   - `tenure = TENURE`
   - `implementing_agency = IDA_NAME` (full string with `(...)` suffix -- that IS what the source has)
   - `vendor_name = <modal VENDOR_NAME from Expenditure join>` or null
   - `work_category = <keyword-mapped from ACTIVITY_NAME>` (see mapping above; must be one of the 7 enum values)
   - `sanctioned_amount_inr = SANCTION_AMOUNT`
   - `expenditure_amount_inr = <sum of FUND_DISBURSED_AMT for this work_id from Expenditure join>` or 0.0 (schema requires numeric, min 0; use 0 not null when no expenditure recorded)
   - `sanction_date = parse "09-Jul-2024" -> "2024-07-09"` (Python: `datetime.strptime(v, '%d-%b-%Y').date().isoformat()`)
   - `completion_status`: `"Completed"` if work_id in Completed tile, else `"In Progress"` if WORK_STAGE in {`Physical Inspection`, `Work partially Completed`}, else `"Sanctioned"` for {`Sanction`, `Vendor Identification`, `Time Estimation`}. Never emit `"Recommended"` from Sanctioned data -- Recommended is a different tile entirely.
   - `last_updated = <today's ISO date>` (the snapshot capture date, not per-record)
   - `source_rung = 1`
2. **Wire it into `Rung1LiveApi.try_fetch()`** in `pipeline/src/nidhinetra_pipeline/ingest/rungs.py`. Two options:
   - (a) Read the three cached files from `data/raw/mplads-*.json` if present. Cleanest for now, session-cookie-independent. Deferred fresh fetching to a later refactor.
   - (b) Fetch live via `mplads_api.py` with the cookies passed in. Requires session refresh flow, real config for cookie/header storage. Not needed for CP1.
   Do (a). Update `mplads_api.py`'s docstring and `rungs.py`'s docstring accordingly. Remove the `RungBlockedError` and unblock Rung 1.
3. **Fix the `combo: <int>` -> `combo: "0,0,0,2"` (string) correction** in `rungs.py` docstring, `mplads_api.py` if it hardcodes the shape anywhere, and the 2026-09-01 19:45 Logbook entry (append a correction, do not rewrite -- append-only).
4. **Add tests**:
   - `pipeline/tests/ingest/test_mplads_adapter.py` -- feed a small hand-crafted (or subset of real) sanctioned+completed+expenditure trio, assert every output record schema-validates, assert categories all land in the 7-enum, assert vendor and expenditure join correctly, assert completion_status derivation is right for each WORK_STAGE case.
   - Update `pipeline/tests/ingest/test_rungs.py` -- Rung1 no longer raises, and with cached files present returns >0 records.
5. **Run the full ladder end to end**: `python -m nidhinetra_pipeline.cli build`. Expect ≥ 79,068 normalized records land in `data/raw/<timestamp>.json` via the atomic swap. Then `build_snapshot()` reads that latest cached file, re-runs the risk engine, and produces new works.parquet / scored.parquet / graph.json / manifest.json with real-data source_rung=1 stamps.
6. **CP1 gate items to close**:
   - "≥500 real records acquired" -> 79,068
   - "Which rung succeeded is recorded in [[Logbook]]" -> Rung 1
   - "source_rung is set on every record" -> 1
   - "Output passes the CP0 validator against §3.1" -> `contracts/validate.py` should pass
   - "Cached snapshot written to disk via an atomic swap" -> already works via cache.write_snapshot
   - "A second pull, separated from the first by real time" -> defer; needs a second capture session with fresh cookies from user. **Do not** fake this by re-running the adapter on the same cached files.
7. **Cascade check** -- after CP1 lands:
   - CP2: run `score_all` on the 79,068. Peer groups will actually populate now (441 groups >= 30). Real flags will fire on real works. Record counts by flag type in the Logbook.
   - CP3: `build_fund_flow_graph` on the same set. With 34,258 vendors distributed across MPs and agencies, real concentration clusters will exist.
   - CP4: API already serves whatever `data/snapshot/*` contains; no code change, just rebuild the snapshot.
   - CP6 item 1 ("real pull from MPLADS succeeds on demand and the data-age label advances") -- this cascades too, since the refresh endpoint just re-runs build_snapshot.
8. **Also add to `data/raw/.gitignore`** if not already there: `mplads-*.json` -- these 190 MB combined of raw responses should stay out of the commit.

**Handoff caveats -- things the next session should not assume:**
- Session cookies WILL be dead by the time the next session starts. Do not build anything that requires calling the endpoint live in tests; use the cached files.
- Do not commit the raw data files. They are large, they belong in `data/raw/` which is gitignored, and re-pulling them requires the cookies.
- Do not lower `MIN_PEER_GROUP_N` from 30 to make more things flag. The real-data peer-group math above shows 441 groups qualify at 30 -- lowering it weakens a real statistical guarantee to make a demo look better and defeats the whole point of the "hill road costs more" defense (Viva Brief section 07).
- Do not fabricate `expenditure_amount_inr` for works with no expenditure record. Zero IS the honest value for a work at WORK_STAGE=Sanction (no vendor yet, no payments made). What is NOT honest is `expenditure_amount_inr = SANCTION_AMOUNT` for works at `Physical Inspection` -- for those, use the actual sum from the Expenditure tile, or 0 if that work has no rows in Expenditure (which itself is the story: sanctioned N months ago, no payments -- that's what `stalled_work` detector exists to catch).
- The `constituency` field in Sanctioned looks reliable (has values on every sample seen), but do a null-check in the adapter and emit a schema-valid fallback rather than crashing.

**One user-facing item that stays open:** CP7 still needs the pitch slot length (recorded nowhere), the timed run, and a second human. See [[NEXT-STEPS]] steps 3, 5, 6.

**Session interrupted here.** Nothing has been committed since `5dcbd0a` (docs: NEXT-STEPS.md). Working tree state at handoff: only untracked additions in `data/raw/` (four `.json` files) and this Logbook entry pending. No source files modified.

---

### 2026-09-04, 17:10 -- CP1 closed. Rung 1 live, 79,068 real works, CP2/CP3/CP4 cascaded

Picked up the 10:35 handoff. Everything it said was on disk was on disk and parsed. Its plan was right in outline and wrong about one thing, which turned out to matter a lot.

**Correction to the correction.** The handoff said step 5 would be "run `cli build`, then `build_snapshot()` reads that latest cached file". It does not. `build_snapshot()` had `_load_raw_records()` reading `WORKS_FIXTURE_PATH` unconditionally with `FIXTURE_SOURCE_RUNG = 5` and `SOURCE_LABEL = "cp0_fixtures"` as constants. So the first end-to-end run wrote 79,068 real rung-1 records to `data/raw/` and then rebuilt the snapshot from the 20-row fixture anyway, reporting `cp0_fixtures` while the API served demo data. Invisible for as long as every path led to the fixture; a live lie the moment rung 1 worked. That was a fourth work item the handoff did not know about, and it is the kind of bug that only exists in the gap between "the pull works" and "the pull is what you are looking at".

**The adapter.** New `ingest/mplads_adapter.py` joins Sanctioned (79,068) + Completed (34,258) + Expenditure (72,660 payment events) on `WORK_RECOMMENDATION_DTL_ID`. Decisions worth recording because they were judgement, not mechanics:

- **`work_category` mapping, and the mistake I made in it.** The schema fixes seven values; MPLADS publishes 112 activity strings and a `WORK_CATEGORY` column that says "Normal/Others" on 98% of rows. Mapped with an ordered keyword list, first match wins. I got the order wrong on the first pass: `"Construction of roads, link roads, pathways or any other road with or without drainage system"` -- 18,248 works, the single largest activity in the country -- contains "drainage", and my Sanitation rule matching "drain" ran before Road. Result: 23% of every work in India classified as sanitation, and Road sitting at 4.3%. **My own comment two lines above the list warned about exactly this and I shipped it anyway.** Caught by checking the output distribution against raw activity counts rather than re-reading the rules, which is the only reason it did not survive into the snapshot. Only two of the 112 activities were ambiguous at all; the second (`flood control embankments ... roadsides`, 506 works) fits neither Road nor Drinking Water and now has an explicit Community Infrastructure rule rather than being left to whichever rule happened to run first.
- **`tenure`.** Schema wants `^\d{4}-\d{4}$`; the source says "18th Lok Sabha". Derived from the tenure boundary timestamps -> "2024-2029". Found by the schema rejecting record 0, which is the validator doing its job.
- **`expenditure_amount_inr`.** Only `Payment Success` rows count. `Payment In-Progress` is committed, not disbursed, and counting it would suppress `stalled_work` on precisely the works whose money is stuck mid-disbursement -- the case that detector exists for.
- **`last_updated`.** First version used the snapshot date for every row. Correct-looking, useless: every record equally fresh, the Days stale column read 0 on all 79,068, and `stalled_work`'s no-update fallback had nothing to measure. Now the latest payment date, falling back to sanction date. A work with no payments since sanction is exactly the case the detector should see.
- **Districts: still not emitted.** Same reasoning as 09-03. The graph has no district node and MP nodes key on `mp_name`.

**Two latent bugs the real data surfaced, neither mine originally, both real:**
- `cache.latest_good()` globbed `*.json` and sorted reverse-lexicographically. `data/raw/` now holds two kinds of file -- `<timestamp>.json` snapshots and `mplads-*.json` raw tiles -- and the tile names sort after any timestamp, so it returned a raw dashboard response as "the latest snapshot" and `build_snapshot()` tried to read `source_rung` off it. Its docstring already claimed it was defensive about stray files; it only checked they parsed as JSON. Now matches the snapshot filename pattern.
- `api/snapshot.py` honoured its own `SNAPSHOT_DIR` on reads but forwarded `None` on writes, so a rebuild always wrote to the *pipeline's* default. Repoint the API at another directory and it would read the new one and write the old.

**A test suite that destroyed real data.** `api/tests/conftest.py` called `build_snapshot()` with no arguments, so running `pytest api/` rebuilt the operator's real snapshot from the fixture -- replacing 79,068 live records with 20 demo rows. Harmless while every path produced identical fixture output; genuinely bad once it did not. Now builds into a temp directory with `db.SNAPSHOT_DIR`, `api_snapshot.SNAPSHOT_DIR` and a new `api_snapshot.RAW_DIR` repointed at it. Suite went from 13.7s to 0.4s as a side effect, because it stopped rebuilding 79k records per run.

**CP2/CP3/CP4 cascaded exactly as the plan said they would.** No code changes needed in the risk engine, the graph builder or the API -- they had been correct all along and starved of data. 23,800 flagged (30.1%), all four detectors firing, peer groups n=30..4,584, ranks gapless. The reason sentences the fixture could never produce now render for real: *"Cost is 8.8x the median for road works in this state. Sanctioned 13 months ago, 10 percent spent. Agency holds works in 4 districts, 4 MPs."* against peer group *"Road works, Uttar Pradesh, 2025-26", n=2,213*. `MIN_PEER_GROUP_N` was not lowered; the 09-03 review's worry about it was a fixture-size problem, not a threshold problem, exactly as argued at the time.

**Independent cross-check of the whole join:** the adapter produces 44,810 works under implementation. The dashboard's own aggregate tile said 44,480 on 09-01. Two numbers computed by completely different paths, 0.7% apart. That is the join being right, not a coincidence.

**Three frontend bugs, all the same shape, all only visible at scale.** Every one was a figure describing the whole workload being derived from the 200 rows the table had fetched:
- The summary strip read **"200 works under implementation, 200 flagged, 100%"** against a real 44,810 and 18,093. These are the four numbers a judge reads first. Now taken from `/api/stats/summary`, which computes them over every record; the endpoint gained three denominators for the context lines.
- The quota sentence put the ten percent obligation at **rank 20**. Ten percent of 44,810 is 4,481. "Which ten percent" is the entire product claim, so this was the worst of the three.
- The Fund Flow graph rendered **5,695 SVG nodes into a graph 164,778px tall** -- 1.6km of scrolling. The threshold filter was working correctly and matching 4,845 of 16,854 vendors, which is correct filtering and useless output. A view whose whole purpose is making concentration visible was burying it in bulk. Now draws the 25 most concentrated (250 circles, 5,318px) and says so on screen, rather than truncating silently.

The filtered case of the quota figure is still wrong and is named in the code rather than papered over: filters run client-side over the fetched page, so a filtered total counts only matches within it. The API already supports server-side `state`/`year`/`category`/`flag` filters -- verified working, `state=Bihar` returns 4,545 and compounds correctly with `flag=stalled_work` to 409 -- so moving the filter bar onto them is the real fix and is not attempted here.

**Also honest about what the graph contains:** the most concentrated "vendors" include `Executive Engineer` (a job title) and `DINESH KUMAR` (a personal name). That is a finding about the portal's vendor field, not about those works, and it belongs in the Logbook rather than on a slide as a fraud signal.

**Verification:** pipeline 223 passed (+58 this session: 47 adapter, 7 source-selection, 4 rung), API 26 passed, `contracts/validate.py` OK, tsc clean, eslint 0 errors, `next build` succeeds, and every figure quoted above was read back off the running API or the rendered page rather than inferred.

**Status:** CP1 4 of 5, CP2 done, CP3 done, CP4 done, CP6 3.5 of 4. Two things remain and both need a human:
- CP1's second pull needs a fresh browser JSESSIONID. Re-running the adapter over the same cached tiles would give a byte-identical "second pull" and a rank delta of zero, which is fabrication with a timestamp on it.
- CP6's "on demand" half: `POST /api/refresh` rebuilds from the last cached pull, it does not re-pull from MPLADS. Marked partial rather than ticked, because a judge asking "does that button fetch new government data" must get "no", and the checklist should say so before they ask.

---

### 2026-09-05, 10:45 -- /plan-eng-review on CP6/CP8/CP9. Enum decided, CP6's "needs a session" claim disproven, one live probe run

Full scope, all four review sections, on the three not-yet-built phases. CP0-CP5 untouched -- already shipped, already reviewed once (2026-09-01), verdict from that review closed out (its blocker, the data spike, resolved 2026-09-04).

**Six decisions locked, interactively, one AskUserQuestion per issue:**
- CP6: before building any auth/session code, probe first whether `getTilesReportData` actually needs a session at all. Two sibling endpoints (`getStateData`, `getTilesData`) work with zero cookie handling; the "needs a JSESSIONID" claim traced only to "the working request came from a captured browser cURL", never to an isolated test.
- CP8: adopt [[NEXT-STEPS]] item 4's 6-value enum as canonical over a rougher, differently-worded list that had drifted into [[Checkpoints]] separately.
- CP8: outcome records freeze `inspection_rank_at_time` and `risk_score_at_time` at write. Ranks reshuffle between pulls (see CP1's still-open second-pull item) -- precision-at-quota computed from a live join would silently change its own answer after every rebuild.
- CP8: outcomes persist in a new SQLite file (`data/outcomes/outcomes.db`), not Parquet-append or JSONL, for a native `UNIQUE(work_id, inspected_on)` constraint and zero new dependency.
- CP9: `MIN_OUTCOMES_FOR_REWEIGHT = 30`, matching the existing `MIN_PEER_GROUP_N` precedent, with a separate higher placeholder for supervised-classification eligibility so the two gates can't be conflated.
- Frontend: stand up vitest + React Testing Library for the whole `web/` app now (currently zero test files, zero config -- a prior attempt was abandoned, per an earlier commit referencing "the vitest false start"), backfilling the existing components alongside the new CP8 capture component, not scoped narrowly to just the new piece.

**Then the CP6 probe actually ran, live, against the real endpoint -- and disproved its own premise.** Three requests, one each: (1) plain POST, no cookie, no browser headers -- full connection timeout, 0 bytes, no HTTP status. (2) Bootstrapped a genuinely fresh session first (`GET dashboard.html`, captured a real `JSESSIONID` plus a `TS01d11681`-prefixed cookie -- the naming pattern of a WAF/bot-mitigation layer, not an app session) and retried with it attached -- identical timeout. (3) Same cookie plus a full realistic Chrome header set (User-Agent, Accept, Origin, `sec-fetch-*`) -- identical timeout again. Two plain GETs to the dashboard HTML page, run before and interleaved with these, both succeeded in ~0.3s. Three for three on the POST, zero variance: this reads as a WAF/anti-automation block or tarpit on this specific data endpoint, not a missing session -- the thing CP6 has said since 09-04 ("needs a browser JSESSIONID that expires within hours") is not what today's evidence shows. Stopped at three attempts to stay polite to a public government server. Genuinely unresolved: whether a real browser's TLS fingerprint (Playwright, rung 2) clears this, or whether it's an IP-based block on automated/datacenter origins that would hit Playwright too if run from an environment like this one -- meaning 2026-09-04's success may have depended on a residential/office network, not a browser per se. Next step to disambiguate: run the same three-request sequence from an actual browser session or a non-datacenter IP.

**Written into the vault, not just decided in chat:** [[Checkpoints]] CP6/CP8/CP9 updated with all of the above (the probe writeup lives there in full); [[NEXT-STEPS]] item 4 marked decided, pointing back at Checkpoints as the now-canonical enum source; new `contracts/inspection_outcome.schema.json` frozen; `ingest/mplads_api.py`'s `get_tiles_report_data` docstring and signature fixed (`combo: int` -> `combo: str`, "STILL BLOCKED" on parameters corrected to reflect the real, current blocker, since the parameter shape itself has been solved since 09-04 and this file never said so).

**Outside voice:** dispatched to an independent subagent (no Codex CLI on this machine), still running as this entry is written. Findings to be folded in and logged separately once it reports.

**Status:** CP8's design is locked and buildable -- schema frozen, storage decided, rank-freeze decided. CP6 is *more* open than before this session, not less: the actual blocker is now named accurately instead of assumed. Implementation (SQLite store, `POST /api/inspections`, vitest setup, CP9 constants) queued next.

---

### 2026-09-05, 11:40 -- CP8 built: contract, store, endpoint, UI, all tested. Outside voice caught 3 more problems, 2 fixed same session

Continuation of the 10:45 entry. That review's 6 decisions got built, then an independent subagent (no Codex CLI on this machine, fell back to a Claude subagent per the skill's own rule) found three more problems -- two in the original CP8 spec, one in this session's own D5 decision -- and a fourth, unrelated, severe bug. Presented all four to the user via AskUserQuestion; three were confirmed and built this session, the fourth (rest of a fifth, truncated finding) is still being retrieved from the subagent as this entry is written.

**Built, tested, wired in:**
- `contracts/inspection_outcome.schema.json` -- frozen. Enum, `notes`, `inspection_rank_at_time`/`risk_score_at_time`, and (see corrections below) `cutoff_rank_at_time`, `population_n_at_time`, `in_control_sample`, `_issue_mapping`.
- `nidhinetra_pipeline.outcomes.store` -- SQLite, `UNIQUE(work_id, inspected_on)`, 11 tests including the literal CP8 acceptance test (record → full rebuild → still readable).
- `POST /api/inspections` -- 404/400/409 on unknown work/bad enum/duplicate, rank+score+cutoff+population all looked up server-side, never trusted from the client, 7 tests.
- `InspectionCapture.tsx`, wired into `DetailPanel.tsx` after the fund-flow link. 97% coverage. New this pass: a control-sample checkbox.
- Fixed a stale docstring in `mplads_api.py` (combo was `int` in the docs, `str` in reality since 09-04).
- Frontend test infra stood up clean: vitest 5 + React Testing Library + `@testing-library/jest-dom`, 0 vulnerabilities. The earlier "false start" (`04 Prototype/Logbook.md`, prior entry) was vitest v2 (5 vulns, 1 critical) and an unpinned `@types/node` causing an ERESOLVE against Next 16/React 19 -- current pinned versions plus `@types/node@^24` (matching the real installed Node major, not just "latest") resolved clean.

**Outside voice, 3 confirmed and built:**
1. **Precision-at-quota had no real control group.** "Inside cutoff vs. outside cutoff" is structurally broken -- nothing is ever recommended for inspection outside the cutoff, so that denominator is empty forever, and `NidhiNetra Viva Brief.html:459` already commits to the correct design instead ("more problems than a random sample"). Fixed: `in_control_sample` field + a checkbox in the capture UI. The aggregation/display itself is still not built.
2. **The enum -> "had an issue" mapping was an unfrozen free parameter**, swinging the metric roughly 20% to 80% depending on how `documentation_incomplete`/`agency_unresponsive`/`duplicate_of_another_work` get classified. Fixed: `_issue_mapping` frozen in the schema itself, `agency_unresponsive` mapped to `null` (inconclusive, excluded from the denominator -- no inspection of the work actually happened) rather than forced into true/false.
3. **My own D5 decision (previous entry) had a population mismatch.** `inspection_rank` spans all 79,068 works (`rank.py` has no completion_status filter, verified by re-reading it); the quota cutoff spans only the 44,810 works under implementation (`routers/stats.py`, `web/lib/data.ts`). Freezing only `inspection_rank_at_time` compared two different populations. Fixed: also freeze `cutoff_rank_at_time` + `population_n_at_time`, computed server-side by a new `_population_and_cutoff()` that deliberately reuses `stats.py`'s `UNDER_IMPLEMENTATION` constant rather than redefining the population a third time.
4. **Separate, severe, pre-existing:** `data/raw/` gitignored + single-disk means a second machine's first Refresh click silently replaced the real 79,068-row snapshot with the 20-row demo fixture. Fixed: `build_snapshot()` now raises `SnapshotDowngradeError` rather than committing a rebuild whose resolved rung is worse than the current manifest's, `force=True` to override intentionally. 5 new tests. This is the exact failure mode the planned second-person dry run (on someone else's machine, by design) would have hit.

**Also independently flagged and resolved:** two of the graphify extraction subagents (separately, reading unrelated SVG icon files) both flagged `web/AGENTS.md`/`CLAUDE.md` as a likely prompt injection -- reasonable instinct, verified false: `node_modules/next/dist/docs/01-app/02-guides/ai-agents.md` documents this exact auto-generation behavior as a real Next.js 16.3+ feature, `generate-agent-files.js` contains the identical text, and the files landed in a normal feature commit (`8d1e24f`). No action needed.

**Verification:** pipeline 239 passed (+16 this session: 5 downgrade-guard, 4 issue-mapping/control-sample, others from the earlier CP8 pass), API 33 passed (+9), ruff clean on every touched file, web: 12/12 vitest passed, tsc clean, eslint 0 new issues, 97% coverage on the new component.

**Status:** CP8's recording half is fully built and tested. Precision-at-quota's *design* is now correct; its *computation and display* are not built. CP6 has a second, independent fix landed (the downgrade guard) alongside the still-open session/WAF question from the earlier entry. Outside voice's fifth finding (truncated) and closing assessment of CP8's overall scope are still being retrieved as this entry is written -- will get their own note once they land.

---

### 2026-09-05, 12:05 -- Outside voice's full report landed: 8 more findings, a right-sizing verdict, CP8 closed

Continuation of the 11:40 entry -- the subagent's report had been truncated mid-transmission; the retry came back complete (12 findings total, 4 already covered). Presented findings 6, 7, 9 plus the right-sizing verdict to the user via three AskUserQuestion calls; all recommended options accepted. Findings 5 (residual), 8, 11, 12 were mechanical fixes with no real alternative, applied directly.

**Right-sizing accepted: CP8 is now closed, CP8b split off.** The recording loop (contract, store, endpoint, on-screen capture) is CP8, done. Precision-at-quota's actual aggregation and display -- which would read "suppressed, n below minimum" on any realistic demo day regardless of what gets built -- is CP8b, explicitly scoped and explicitly deferred. Checkpoints.md now says this outright rather than leaving CP8 looking unfinished.

**Schema hardened further, same session's own decisions revised in light of sharper findings:**
- **work_id orphan risk (#6):** `work_id` stability across pulls was asserted in `mplads_adapter.py`, never observed -- there's been exactly one real pull. Denormalized `state`/`constituency`/`implementing_agency`/`work_category`/`sanctioned_amount_inr` onto the outcome row so an orphaned record stays human-readable and hand-rematchable if the portal ever reissues IDs.
- **Inspector identity (#8):** added required `inspector_id`. The deck promises "reviewers train the model" (plural); the schema had no way to say which reviewer. No auth exists in this prototype, so this is self-reported initials, not a verified identity -- still required, so disagreement between reviewers is at least visible. Remembered across visits via localStorage in the capture UI so it's typed once per sitting.
- **Duplicate-key redesign (#9):** `UNIQUE(work_id, inspected_on)` picked "rejected" when CP8's own wording always allowed "rejected or explicitly versioned," and blocked a real case -- agency unresponsive in the morning, a different inspector gets access that same afternoon. Redesigned to a surrogate `outcome_id` primary key, `UNIQUE(work_id, inspected_on, inspector_id)`, and a nullable `supersedes` pointer for explicit amendments.
- **CP9's retraining gate (#7), this session's own D7 decision reversed:** `MIN_OUTCOMES_FOR_REWEIGHT=30` reused `MIN_PEER_GROUP_N`'s precedent for a fundamentally different purpose -- gating *model selection* with a floor sized for a *descriptive* statistic. 30 minus a holdout is 8-10 test points; any reweighting "wins" on that by noise. "Same number, already defensible to a judge" was memorable, not statistically justified, and the outside voice was right to separate the two. CP9 now has no retraining gate at all: report the observed rate with a Wilson interval, keep detector weights frozen.

**Mechanical fixes, no real alternative, applied directly:**
- `test_mplads_api.py:163` (and two more call sites in the same file) still asserted the debunked integer `combo` form -- fixed to the real string form, so a future reader trusts the test as documentation of the request shape rather than re-learning the original bug.
- Checkpoints.md's CP8 header said "Blocked by: CP1" -- stale since 2026-09-04, when real `work_id`s landed. Corrected.
- `NidhiNetra-Pitch-Script.md`/`.html`, step five: "an officer confirms it or rejects it" contradicted the CP8 enum's deliberate refusal of verdicts. Changed to "records what the inspection actually found."

**Also resolved:** two graphify extraction subagents independently flagged `web/AGENTS.md` as a likely prompt injection while reading unrelated SVG files. Verified false: `node_modules/next/dist/docs/01-app/02-guides/ai-agents.md` documents this exact Next.js 16.3+ auto-generation behavior, the generator script contains identical text, and the files landed in a normal feature commit. Good instinct, correct to flag and not act on it, no actual issue.

**Verification:** pipeline 241 passed, API 35 passed, web 14/14 vitest passed (96%+ coverage on `InspectionCapture.tsx`), tsc clean, eslint 0 errors (1 pre-existing unrelated warning), ruff clean on every touched file.

**Status:** CP8 closed. CP8b and CP9 both re-scoped and correctly described as not started. CP6's WAF-vs-IP-block question and CP7's human-only items (pitch slot length, second-person dry run) remain the actual open work, and are exactly where this session's own right-sizing verdict says effort should go next.

---

### 2026-09-05, 12:15 -- NEXT-STEPS.md rewritten in plain language, session closed out

Last item of the day. [[NEXT-STEPS]] rewritten at the user's request ("baby language, step by step") -- same file, same purpose, simpler voice. Down to 5 items, each a literal action:

1. Recapture the dashboard (DevTools steps, unchanged from the original capture) -- serves two purposes at once: a fresh pull for CP1's still-open second-pull item, and the raw material for item 2.
2. One `curl` command to run from the user's own Terminal, no cookie, same request this session's CP6 probe already sent from this machine's network three ways. If it works from the user's home/office network but hung from here, that is direct evidence of an IP-origin block rather than anything about sessions or headers -- and means the fix for CP6's "on demand" half is far cheaper than the docs previously implied. If it also hangs there, that's real evidence toward needing Playwright (rung 2) instead.
3. Pitch slot length -- unchanged, still open, still the one number that unblocks CP7's calendar.
4. Second-person dry run -- unchanged, still open, still needs scheduling.
5. The unbroken timed run -- unchanged, sequenced after 3 and 4.

Nothing here is new work; it's the same handful of items from the earlier version, re-sequenced and re-worded now that CP8's build is done and there's nothing else left blocking on code.

**Full session arc, for whoever reads this cold:** started as a `/plan-eng-review` on CP6/CP8/CP9. Six decisions locked interactively (D3-D9), then a live CP6 probe that disproved its own premise (not a cookie problem). Built CP8's full recording loop -- schema, SQLite store, `POST /api/inspections`, on-screen capture UI, vitest stood up clean for the whole frontend. An independent outside-voice pass (Claude subagent, no Codex CLI on this machine) then found 12 issues across two rounds -- 8 confirmed and fixed this same session (D10-D15), including a severe pre-existing bug (Refresh silently downgrading real data to the demo fixture on any second machine) and two corrections to this session's own earlier decisions (the CP1-population rank mismatch, and CP9's statistically-too-small retraining gate, reversed in favour of a report-only design). Right-sized CP8/CP8b per the outside voice's closing verdict. Also ran `/graphify` twice (full catch-up from a Sep-1 baseline, 1,133 nodes/2,102 edges/64 communities) and cleared a false-positive prompt-injection flag two subagents independently raised against a genuine Next.js 16.3+ file.

**Verification, cumulative, all green at session end:** pipeline 241/241, API 35/35, web 14/14, tsc clean, eslint 0 errors, ruff clean on every touched file, CP0 validator + self-test both pass.

**Status:** CP8 closed. CP8b and CP9 re-scoped. Vault (Checkpoints, NEXT-STEPS, this file) fully current as of this entry. Nothing left that isn't either CP8b (deferred by design), CP6's open network question, or one of NEXT-STEPS' five human-only items.

---

### 2026-09-05, 19:15 -- Round 1 result: qualified. Backlog committed, CP6 built (no cookie-copying, ever), full live verification, Technical Deep-Dive written

**Qualified for round 2.** The user confirmed the same day: round 1 (2026-09-02) passed, result landed today. Round 2 is a different format entirely -- a live demo of the app on real data, plus a detailed judge-facing walkthrough of the tech stack, algorithms, and pipeline. This changes what CP7 prep needs to be; [[NidhiNetra-Pitch-Script]] was written for a shorter, slide-only, 5-speaker format and still names tech that was never built (see 2026-09-02 entries above) -- it is not the right document for this round.

**A caution surfaced and acted on immediately, worth recording plainly.** Asked whether to "use an AI model and fine tune it" to have training results to show a more technical panel. Declined, with reasons, rather than building it: no labelled fraud data exists for this scheme (a defended, load-bearing fact of this project, not a gap), and CP9 was redesigned earlier this same day to drop a retraining gate entirely because the realistic number of real inspection outcomes by any presentation date cannot support a statistically honest result. A rushed fine-tune, presented to a panel that has explicitly said it will probe the stack in detail, is close to the highest-risk move available -- the submitted PPT already made an adjacent mistake once (claiming DBSCAN/SHAP/Sentence-BERT/OpenCV that were never built), and Logbook 2026-09-02 already names that gap a live credibility risk. The honest alternative was already sitting in the codebase and needed no invention: `risk/detectors.py`'s `ensemble_scores()` is a real, genuinely-fit IsolationForest + LocalOutlierFactor anomaly ensemble, run on the real 79,068-record dataset every build, capped at 20% of the final score by deliberate design (`ENSEMBLE_COMPONENT_WEIGHT = 20.0`) so the explainable rule-based reasons always dominate. Written up in full in the new [[Technical Deep-Dive]] rather than fabricated fresh.

**The uncommitted backlog from the last several sessions is now fully committed**, in the same fine-grained style as the rest of this repo's history rather than one large commit: the `SnapshotDowngradeError` fix, the full CP8 recording loop, a follow-up fixing `ApiUnreachableError` to carry an HTTP status (missed alongside the main CP8 commit, caught before it mattered), the `mplads_api` combo docstring/test fix, the pitch-script verdict-language fix, the day's docs, and the graphify rebuild. One real slip along the way: the `ApiUnreachableError`-status follow-up commit accidentally also swept in the vitest-standup files (package.json, vitest.config.mts, MissingField.test.tsx) because they were staged from an earlier step -- not wrong content, just an inaccurate commit message that undersells what it contains. Not fixed by amending (this repo's own standing rule is new commits, not amends), named here instead so it isn't silently lost.

**CP6 built for real, not just diagnosed.** The 2026-09-05 network-origin conclusion (this environment specifically is blocked, not sessions or headers) got one more independent empirical test before building anything: a research pass used `curl_cffi` to impersonate real Chrome and Safari TLS fingerprints, from this same blocked sandbox, with a session cookie acquired automatically (zero human input) via a plain GET first. Both profiles still hung identically on the actual data POST -- ruling out browser-fingerprint detection as the mechanism and reinforcing that this is IP/network-origin classification, which no code running from a cloud/CI/sandbox environment can get past, curl impersonation included.

The actual fix needed no cookie-copying at all, which was the explicit, non-negotiable requirement (never visible to judges, never touched during a demo). `MpladsClient` gained `warm_session()` (a plain GET that lets the client's own cookie jar pick up a fresh session automatically, exactly like a browser) and `get_tiles_report_data_raw()` (the same request as the existing typed method, but returns the raw `{"<tile>": "<json string>"}` wrapper unvalidated -- exactly the shape `ingest/mplads_adapter.py`'s `_unwrap()` already reads, so a live pull needs no reshaping to persist). A new `pull-live` CLI command chains them across all three tiles and writes them atomically as a group -- 12 new tests, including the core safety property proven directly: a simulated failure on any one tile leaves `data/raw/` completely untouched, not a partial set of two fresh tiles and one stale one. Does not touch `Rung1LiveApi` or `run_ladder()` -- it refreshes the cache they already read from. **Honestly unverified in one specific way, named rather than glossed over:** no one has seen this command get a real 200 response yet, because the tarpit above means it categorically cannot be tested from here. That one confirmation run, from the user's own machine, is the only thing standing between "tested against mocks" and "proven against the real endpoint" -- everything else about it (atomicity, failure handling, output shape) is verified now.

**A real dead import caught by the CP8 commits' own eslint run**, unrelated to any of the above: `DetailPanel.tsx` imported `categoryPhrase` and never used it, left over from the CP8 wiring pass. Fixed, verified clean.

**Full live verification, not just automated checks, because harming the frontend was named explicitly as unacceptable.** Booted both servers against the real 79,068-record snapshot and drove a real headless browser through the actual CP8 flow for the first time since it was built: Inspection List (real summary strip, real quota sentence) -> rank 1's detail panel (risk breakdown 30+25+20+9=84, matching the documented weights exactly) -> peer-group sentence -> Record Inspection -> filled the required outcome and initials fields -> Save button correctly stayed disabled until they were filled -> submitted -> "Inspection recorded." -> Fund Flow page. Zero console errors across the entire run. The one real row this test wrote into the actual `data/outcomes/outcomes.db` (work_id 220829, inspector `TEST-QA`) was deleted afterward to restore the honest pre-test state -- no real inspection has actually been recorded yet.

**[[Technical Deep-Dive]] written** -- the judge-facing document this round actually needs: the real five-stage pipeline with real numbers (79,068 works, 23,800 flagged with the exact per-detector breakdown, the 30/25/25/20/20 weight structure, the real ensemble model's exact hyperparameters, the 18,144-node fund-flow graph), the CP6 diagnostic story told as a strength rather than hidden, and a prepared-answers section built to survive exactly the kind of detailed technical probing this round has been described as doing.

**Still open, unchanged in kind though the stakes are higher now:** the pitch/demo slot length for round 2 (still not recorded anywhere), whether [[NidhiNetra-Pitch-Script]] gets retired or rewritten for the new format (not decided, not touched), a second person for the dry run, and the one live confirmation that `pull-live` works against the real endpoint from a real network.

**Verification:** pipeline 288 passed (+12 this session), ruff clean on every file touched this session (32 pre-existing findings elsewhere in the pipeline noted, not touched -- out of scope), web 14/14 vitest passed, tsc clean, eslint clean (one dead import found and fixed), `next build` succeeds, full live browser walkthrough with zero console errors, both dev servers stopped cleanly afterward.

### 2026-09-08, 15:45 -- Shortlisted. Round-2 PPT rebuilt from primary sources; four of our own numbers found wrong and corrected

**Shortlisted, and the PPT can be resubmitted.** This reopens something [[Logbook]] 2026-09-05 recorded as permanently unfixable: the round-1 deck claimed DBSCAN, Sentence-BERT, OpenCV, SHAP, Airflow, Postgres+PostGIS and Leaflet, none of which exist. That divergence was logged as a live credibility risk we would have to talk around. We no longer have to -- slide 17 of the new deck states it as a table, promise by promise, with the honest engineering reason for each.

**The statutory claim is now sourced, and it got sharper in the process.** The project's central thesis had been carrying an uncited "guidelines require 10% inspection". Read directly from the MPLADS Guidelines (2nd edition, 14 March 2023; in force 1 April 2023): **clause 4.5.2** -- "They shall inspect at least 10% of the works under implementation every year" -- where "They" is the District Authority per section 4.5. Three neighbouring clauses matter and must never be conflated with it: 4.4.1 (State Nodal officials, minimum 1% *by value* per district), 4.6.2 (Implementing Agencies, 100%), and 4.4.2 (third-party inspection).

**4.4.2 is the find.** It prescribes sampling criteria in detail -- all works over Rs 25 lakh compulsorily, 50% of works between Rs 15-25 lakh, plus at least 50 more "involving the judicious balance of various parameters like cost, works in the area predominantly inhabited by Scheduled Caste and Scheduled Tribes, works of Societies, Trusts...". Clause 4.5.2 prescribes nothing about selection. The guidelines demonstrably know how to mandate a sampling rule and deliberately do not for the District Authority's 10%. That contrast is the strongest argument the project has, and it is a primary-source argument rather than an assertion.

**Four numbers in our own documents were wrong, found by recomputing rather than re-reading.** (1) The [[Technical Deep-Dive]] detector table had `agency_concentration` at 25 and `expenditure_mismatch` at 20; `risk/rank.py` has them the other way round. (2) It claimed 441 peer groups clearing the n>=30 floor covering 83.4% of works; the current snapshot gives 585 groups formed, 290 clearing, 97.0% covered -- the old figures were from a superseded snapshot. (3) It said "4,845 vendors are paid on works recommended by 3 or more MPs". That number is real but is a *two-hop reachability* count through agencies; counted strictly on direct MP recommendation it is 79 vendors and 117 agencies. Both are true and answer different questions, so the deck and the Deep-Dive now always say which is meant. (4) Most consequentially, the 10% quota had been computed against all 79,068 works (7,907). Clause 4.5.2 measures it against works *under implementation* -- 44,810, so **4,481 inspections a year**. Recomputed on the correct base the targeting story is stronger, not weaker: 100% precision inside the quota against a 40.4% base rate, 2.48x lift, all 1,907 multi-flag works captured, Rs 525 crore of Rs 2,497 crore at risk covered.

**A supervised model, on a question the data can actually answer.** The 2026-09-05 refusal to fabricate a fraud classifier stands and is restated on the slide itself. But `completion_status` is a real observed label, so "will this work still be incomplete?" supports a real evaluation. Cohort of 13,646 works sanctioned Jul 2024 - Mar 2025, temporal split (train 5,108 / test 8,538, no shuffling), three leakage traps closed deliberately: expenditure excluded (post-sanction), the agency prior computed only from pre-cutoff works and smoothed, exposure held constant by fixing the sanction window. Logistic regression reaches ROC-AUC 0.729 / PR-AUC 0.438 against a 0.231 base rate, lift@10% 2.30; Platt calibration cuts Brier from 0.179 to 0.164. **Logistic beat gradient boosting** (0.697) -- 5,108 rows and six features do not need a booster, and the deck says so rather than hiding it. The strongest coefficient by more than double is `agency_prior` at +2.64: *which* work it is matters less than *who* is building it, which independently corroborates the agency_concentration detector's premise from a completely different direction.

**The hyperparameter a reviewer would attack turns out not to matter, and we can prove it.** Sweeping `contamination` from 0.01 to 0.5 across both ensemble models on the real snapshot leaves `score_samples` and `negative_outlier_factor_` bit-identical, Spearman exactly 1.0, ensemble Jaccard@1000 exactly 1.000000, max difference 0.000e+00. It only moves `offset_`, the cut-point for `predict()`, which this pipeline never calls. The ranking is provably invariant to it. The honest counterpart is on the same slide: `random_state` genuinely does move the ranking (~10% of the top-1000 set differs between seeds), `n_estimators` damps it (50 -> 0.797, 100 -> 0.848, 200 -> 0.898, 400 -> 0.916, 800 -> 0.918), which retroactively justifies the existing choice of 200 over sklearn's default 100 with measurement rather than assertion, and names the residual seed sensitivity as a real limitation.

**Reproducibility made literal.** Slide 18 claims every figure in the deck can be regenerated from the repository. Three scripts were written to make that true rather than aspirational: `scripts/deck_figures.py` (every quantitative claim, from the committed snapshot), `scripts/hyperparameter_sensitivity.py` (the contamination and seed sweeps), `scripts/delay_model.py` (the supervised run). Deck figures were then corrected to match what the committed scripts actually print -- two tables had been carrying numbers from scratch runs with slightly different parameters, which would have failed exactly the "run it in front of us" test the slide invites.

**Deck structure, corrected mid-build.** It was first built as one 18-slide file on the assumption that the template requirement was unknown. The user then confirmed the **6-page SIH template is mandatory**, so it was rebuilt as two files. The submission (`NidhiNetra - SIH26102 Round 2.pptx`) is exactly 6 slides and was produced by editing the round-1 template file *in place* -- same master, same SIH artwork, same footer placeholders, same section headings -- so compliance is structural rather than imitated; only the body text of each slide was replaced, and the slide-3 flow nodes were relabelled INGEST/STANDARDIZE/DETECT/EXPLAIN/REVIEW to ACQUIRE/NORMALISE/SCORE/GRAPH/SERVE to match the real pipeline. The 12 technical slides became a separate, unsubmitted `NidhiNetra - SIH26102 Technical Annexe.pptx`, numbered 8-18 so the two read as one document, for turning to during Q&A. Built for a **10-minute slot** (now known, closing a NEXT-STEPS item open since 2026-09-04): slides 1-6 plus the live demo are spoken, and Act 2 exists so that a judge's question is answered by turning to a slide rather than talking. Team name **Tech Bashers**; Team ID still a placeholder on slide 1.

**Research agents lost to session limits, twice**, after they had downloaded the primary sources but before they wrote their reports; the scratchpad was then wiped. The MPLADS clauses survived because they had been read and quoted directly into the working transcript before the loss. `mplads.gov.in` also times out from this environment -- the same network-origin block CP6 diagnosed for the API -- so the guidelines PDF could not be re-fetched here and should be re-downloaded from the user's own network as backup evidence.

**Verification:** all 18 slides rendered to PNG and inspected individually; three layout bugs found visually and fixed (two-line kickers colliding with the rule, a clipped final table row, a bullet grazing the footer); programmatic geometry check clean apart from one harmless full-bleed divider; `scripts/deck_figures.py` reproduces every deck number exactly; both analysis scripts run green from `05-App/`.

**Still open:** the live `pull-live` confirmation from a real network (unchanged), a second person for the dry run, one full timed run against the 10-minute slot, the Team ID on slide 1, and whether [[NidhiNetra-Pitch-Script]] is now retired outright given this deck supersedes it.

### 2026-09-08, 21:10 — the actual submitted deck, and what it changed

**The `.pptx` in `03 Build Plan/` was never the file that was submitted.** The user supplied `submittedppt.pdf` (27 Aug 21:04); the repo's `NidhiNetra - SIH26102 Idea Submission.pptx` is 26 Aug 17:11 and differs from it in three ways. The submitted version (1) replaced the template's `IDEA TITLE` label on slide 2 with **NidhiNetra**, which is the correct use of that placeholder; (2) **deleted the entire "Technologies to be used" paragraph from slide 3**, leaving that page answering the technology question with nothing but a box diagram; and (3) filled the team ovals with **TechBashers**, one word. Round 2 had been built from the older file and so inherited the `IDEA TITLE` label and a spaced "Tech Bashers". Both corrected. Slide 1 of the submitted deck also shipped with *both* `[to be added after SIH portal registration]` placeholders still in it.

**One of our own numbers was wrong, and it was the kind a judge catches.** Slide 5 read "₹525 crore of the ₹2,497 crore sanctioned but not yet spent". ₹2,497 crore is `pool.sanctioned_amount_inr.sum()` — the sanctioned value of the under-implementation pool, not the unspent part of it. The unspent figure is ₹1,593 crore, of which ₹403 crore falls inside the ranked quota. The corrected line is also the stronger one: **25.3% of unspent money inside a 10% sample, a 2.53× concentration**, against 21.0%/2.10× for sanctioned value. The annexe carried the same mislabel on a stat tile and now reports both rows explicitly.

**The lost research was recovered from claude-mem.** The agents that died on session limits had written their observations before dying. Retrieved and now cited on slide 6: the World Bank *Fraud and Corruption Awareness Handbook* (2013) definition of a red flag as "an indicator of possible fraud or corruption"; the Open Contracting Partnership's 2024 guide, whose "the indicator signals a risk – it is not evidence that illicit behavior is present" is almost verbatim this project's own stance, and whose recommended ranking method is counting flags per unit of analysis — i.e. what the risk engine already does; the Indonesian result where red-flag prioritisation cut the rejection rate of filed complaints from 78% (2021) to 39% (2022); Ukraine's 35 state + 40 civic risk indicators in ProZorro/DoZorro; Brazil CGU's "trilhas de auditoria" feeding SGTA, which watches post-award execution rather than bidding and is therefore the closer analogue; eSAKSHI's mandatory stage-wise geo-tagged photographs; and CAG's CDMA as the institutional route. This converts the project's honesty position from a self-imposed constraint into conformance with international practice.

**The round-1 overpromise is now owned on the submitted page, not just in the annexe.** Slide 3 carries one line naming DBSCAN, Sentence-BERT and OpenCV as deliberately dropped, with the reason: the public MPLADS API serves no images and no embeddable free text, and the geo-tagged photographs live in **eSAKSHI**, a separate system. Naming eSAKSHI matters — it turns "we didn't build it" into "we know exactly where that data is and why we cannot reach it", and it doubles as the roadmap hook. The annexe's correction table was updated to the same wording.

**Slide 2 reframed so it claims the problem statement rather than appearing to disclaim it.** It had opened "NidhiNetra does not detect fraud", which is true and rhetorically strong but reads as retreat from a PS whose title asks for fraud detection. It now leads with the statutory insight — the inspections are already mandatory, the law never says which works — and then states plainly that anomalies and inefficiency are detected and scored while fraud is a determination an officer makes on site. Same honesty, no apparent retreat.

**Verification:** all 6 submission slides and all 12 annexe slides re-rendered and inspected; team oval fixed (11pt with trimmed insets, one line); annexe table row height reduced where the added unspent row collided with its caption; programmatic geometry check clean; `deck_figures.py` and `delay_model.py` re-run and both reproduce every quoted figure exactly (LR ROC-AUC 0.729, PR-AUC 0.438, lift@10% 2.30, base rate 0.231, `agency_prior` +2.636). A PDF preview of the submission sits beside the .pptx.

**Still open:** Team ID on slide 1 — and the exact registered spelling of the team name, since the submitted ovals say `TechBashers` while the portal field on slide 1 was never filled.

**The deck was verified against the wrong renderer, and the user caught it.** Every layout check up to this point used LibreOffice (`soffice --convert-to pdf`), because that is what is scriptable from here. PowerPoint sets the same text materially taller and, unlike LibreOffice, applies the master's hanging indent to wrapped lines — so headings that fitted one line locally wrapped and indented in PowerPoint, and slides 2 and 3 overflowed, slide 3 running straight through the flow diagram. The PDF preview looked right precisely because LibreOffice had generated it. **PowerPoint is installed on this machine and is scriptable**, so the fix was to render through it instead: `osascript` → `open`, `save p in POSIX file "..." as save as PDF`, `close saving no`, then `pdftoppm`. One catch: PowerPoint's sandbox refuses to write into the deep scratchpad path, so the export must go to `/tmp`. Rebuilt against that renderer — body 14→11pt, headings 26→18pt, `marL`/`indent` forced to 0, body boxes enlarged into the space each slide actually had, slide 3's flow strip dropped to 6.14", and four paragraphs trimmed of material the annexe already states in full. All six pages now clear the footer band, confirmed both visually and by scanning for ink above it. The annexe needed no changes — it positions every box absolutely instead of using template placeholders, so it was never exposed to the difference. **The preview PDF shipped alongside the .pptx is now PowerPoint's own export, so what the user reads is what a judge opens.**

---


---


Back to [[PRD]] · [[Execution Plan]] · [[Checkpoints]] · [[00 Dashboard|Dashboard]]

### [2026-09-08 21:30] [Agent tag: A6] [Type: decision]
**What:** Codex resumed the project from the repository record, preserved every existing uncommitted document/deck/script, and moved the working tree from `main` to `codex/finish-nidhinetra`. The completion pass is using `NIDHINETRA-ULTRA-REVIEW.md` as the correctness baseline and will maintain this Logbook plus `chatgpt_terra_log.md` after each implementation unit.
**Why:** There was no saved gstack checkpoint, and the latest audit proves the remaining work is not new presentation polish: active-only ranking, source-completeness handling, honest labels/amounts, national server-side querying, and reproducible demo commands are the next defensible engineering gates. A branch keeps that work isolated without discarding the user's current uncommitted round-2 materials.
**Verification:** Read the complete checkpoint/log/audit set; fresh baseline is 288 passing Python tests, 14 passing frontend tests, clean TypeScript, ESLint exit 0 with four warnings, and 49 Ruff findings. No application source had changed before this entry.

### 2026-09-13, 12:00 -- Frontend redesign shipped against the pinned reference; four real bugs found and fixed; project prepared for its first GitHub push

**The redesign against `NidhiNetra_Vidhi.png` is complete.** Backend gained `policy.py` (the quota rule in one place), server-side scope/search/facets on `/api/works`, and an inspections-report endpoint with Wilson-interval comparisons. `contracts/strings.json` gained the copy for every new surface. `DESIGN.md` and `PRODUCT.md` were written from scratch as the design system's canonical record. The header, dashboard, inspection list, detail panel, fund-flow graph and reports page were all rebuilt against the reference; the old hover-dot background field was removed per the user's first instruction.

**Four real, verified bugs were found by driving the actual browser, not by inspecting code, and fixed:** (1) `DetailPanel` was the one place in the app that skipped the established `displayName()` casing convention, rendering raw ALL-CAPS government fields next to properly-cased text everywhere else on the same panel. (2) At 390px, the whole page -- not just the table -- scrolled horizontally to 1045px; the cause was the table's `.sr-only` caption (`position: absolute`, no explicit offset, per the standard visually-hidden technique) resolving its static position against the table's 74rem internal width with no positioned ancestor to contain it, so it escaped straight to the viewport. Fixed with `position: relative` on the scrolling wrapper. (3) The same class of bug on `/fund-flow`: the mobile breakpoint collapsed a two-column grid to a bare `1fr`, whose automatic minimum is its content's min-content size; fixed with `minmax(0, 1fr)`. (4) `Pagination`'s button row had no `flex-wrap` and overflowed ~42px past 390px; fixed by adding it. All five pages were reverified at exactly `document.documentElement.scrollWidth === 390` on a 390px viewport afterward, not just visually.

**The Specimen Sheet was removed from the shipped frontend, by the user's decision.** It was a live design-token inspector built as one of the reference's five nav tabs; the user judged it a development aid rather than a product view for an officer or a judge. The route, its component, its nav entry, and its entire `strings.json` block were deleted; `PRODUCT.md` now names four real surfaces (Dashboard, Inspection List, Fund Flow, Reports), and the design tokens it displayed still live in `DESIGN.md`. `tsc`, ESLint, Vitest and `next build` were all re-verified clean after the removal.

**`DESIGN.md` was audited against the shipped CSS and corrected where it had drifted:** the display-font clamp, the KPI tile size (52px, not the documented 48px) and its icon size, the active nav tab's icon-fill rule (undocumented until now), and two responsive breakpoint numbers (1200px and 1280px, not 1100px and 1024px) were all brought in line with what actually renders.

**The project was prepared for its first push to `github.com/Krishpotanwar/NidhiNetra`.** `krish.txt`/`krish.txt.pub` were not in `.gitignore` and showed as untracked; that was the first fix, before anything else, since a stray broad `git add` would have staged a private key into a public repository. The key was then moved out of the working tree entirely (never read or printed) and confirmed working against GitHub before the repository's own remote was configured. A root `README.md` was written (problem statement, ranking method, full tech stack, screenshots, run instructions) alongside a corrected `05-App/README.md` (the old one described CP0-era status and a `make demo` target that called a script which no longer exists anywhere in the tree -- `demo` now runs the API and web servers directly instead).

**Verification:** `tsc --noEmit`, ESLint, and Vitest (14/14) all clean; `next build` produces 7 static routes with zero errors; a Web Interface Guidelines pass (icon-only buttons, `outline: none` replacements, `<div onClick>`, raw `<img>`, `transition: all`) found no violations; total production JS is 1.1MB across chunks, 2.5MB static output overall.
