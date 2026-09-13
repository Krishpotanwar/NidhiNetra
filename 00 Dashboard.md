---
tags: [moc, sih2026]
---

# SIH 2026 — Home

Smart India Hackathon 2026. **Idea submission is done** — the PPT was submitted to the SIH portal around 2026-08-31, ahead of the 2026-09-20 date this vault previously tracked (that date was wrong/stale, corrected 2026-09-02 per the user). It cannot be edited now. The team's job from here is presenting, not revising the deck.

## Team profile (locked in 2026-08-25)
- **Skills:** Web/App development, AI/ML & Data Science, Cloud/Backend & DevOps
- **No hardware/IoT/embedded** — targeting **Software category only**
- **Win priority:** genuine government/social impact first, gated by real feasibility as a software-only hackathon build

## 🏆 The pick
**[[SIH26102 - MPLADS Anomaly Detection|SIH26102 — AI-powered anomaly/fraud detection for MPLAD Scheme]]** (MoSPI). Highest impact score of all 172 software PS, fully feasible with public data, real differentiator (fund-flow graph). Full reasoning: [[Final Recommendation]].

**Proposed solution name (submitted 2026-08-26): NidhiNetra** — "Eye on the Fund." Rationale + alternates: [[Solution Naming & Technical Research]].

**Idea-submission PPT drafted 2026-08-26, submitted to the SIH portal ~2026-08-31** — `03 Build Plan/NidhiNetra - SIH26102 Idea Submission.pptx`. Locked as-is; a known inconsistency between this deck and the later prototype docs (labeled-data claim, detection-stack claims) was found 2026-09-02 too late to fix -- see [[04 Prototype/Logbook|Logbook]], the 2026-09-02 10:05 and 10:15 entries, and the prepared bridging answer in `NidhiNetra Viva Brief.html` §07.

**Product thesis (revised 2026-08-31):** NidhiNetra is an **inspection-targeting system**, not a fraud detector. District Authorities must inspect ≥10% of MPLADS works every year and nothing tells them which 10%. We rank that existing, already-mandated queue. Full reasoning in [[04 Prototype/PRD|Prototype PRD]].

**➡️ To hand to a design tool: `NIDHINETRA-DESIGN-BRIEF.md`** (vault root, self-contained, paste-ready).

## Navigation

**Start here if you are new to the project or preparing to present**
- **`04 Prototype/Understanding NidhiNetra.html`** - the whole project explained from zero, one idea at a time, with a plain-language story for every technical concept. Read this first.
- **`04 Prototype/NidhiNetra Viva Brief.html`** - the same material as a quick reference, with exact wording for the hard questions.
- `NidhiNetra-Pitch-Script.md` - 5-speaker run of show, ~6 min.

**The plan**
- [[04 Prototype/PRD|Prototype PRD]] - what we are building and why, must-haves, done-when
- [[04 Prototype/Execution Plan|Execution Plan]] - 6 agent workstreams, data contracts, fallback ladder, calendar
- [[04 Prototype/Checkpoints|Checkpoints]] - CP0 to CP7 gates, tick and untick live
- [[04 Prototype/Logbook|Logbook]] - append-only build diary, never edited
- `.claude/plan/nidhinetra-app-build.md` - folder structure, frontend spec, subagent waves, eng review report
- [[04 Prototype/Design Review - Data Spike First|Design Review]] - the premise challenge that reordered the build

**Design and copy**
- **`NIDHINETRA-DESIGN-BRIEF.md`** - canonical design brief. Part A is the prompt, Part B the resource pack.
- [[04 Prototype/Copy Research - strings.json|Copy Research]] - draft `strings.json`, flag templates, banned-word list
- `05 Design Reference/NidhiNetra.dc.html` - the Claude Design render. Lines 15-490 are reusable token CSS.

**Decision trail**
- [[Final Recommendation]] - the pick, runner-up, and alternatives, with reasoning
- [[Shortlist]] - all 14 deep-dived candidates, ranked
- [[Solution Naming & Technical Research]] - name rationale, MPLADS data-access findings, govt AI-fraud precedents
- [[03 Build Plan/Build Plan|Build Plan]] - architecture, timeline, roles, demo script
- [[All Software Problem Statements]] - full list of 172 software PS

## Source
- `SIH_PS_26.xlsx` — official problem statement export, 226 total (172 Software / 54 Hardware)
