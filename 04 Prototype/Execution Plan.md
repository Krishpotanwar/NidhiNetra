---
tags: [sih2026, plan, prototype]
ps: SIH26102
solution_name: NidhiNetra
---

# Execution Plan — NidhiNetra

**What/why:** [[PRD]] · **Gates:** [[Checkpoints]] · **Log:** [[Logbook]] · **Design:** `NIDHINETRA-DESIGN-BRIEF.md` (vault root)

> **Rewritten 2026-08-31.** Adds the data-acquisition fallback ladder (§2), a calendar (§6), and an open-stream cap (§5). Priorities now follow the inspection-targeting reframe in [[PRD]].

> **Kid version:** six agents work on six pieces at once instead of one agent doing everything in order. That only works if everyone agrees up front on the exact shape of the data passed between them. That agreement is §3. Skip it and the pieces will not fit at the end.

---

## 1. Workstreams

| Agent | Owns | Starts | Blocks |
|---|---|---|---|
| **A1 Data** | Acquisition ladder (§2), normalization, cached snapshot | Day 1, immediately | A2, A3, A4 |
| **A2 Risk Engine** | Isolation Forest / LOF / peer-group z-scores, composite score, plain-language reasons | Day 1 on fixtures | A4 |
| **A3 Graph** | NetworkX MP↔Agency↔Vendor graph, concentration detection | Day 1 on fixtures | A4 |
| **A4 API** | FastAPI serving §3.4 contract | Day 1 on fixtures | A5 |
| **A5 Frontend** | **The Inspection List first**, then drill-down, then graph view | Day 1 on fixtures | Nothing |
| **A6 Integration** | Fixtures, [[Checkpoints]], [[Logbook]], offline mode, demo rehearsal | Day 1, runs throughout | Nothing |

**Nobody waits for A1.** A2, A3, A4, A5 all start immediately against **fixture data** shaped exactly like A1's real output. That is the whole reason §3 exists. It converts one long chain into five parallel streams.

**A6's Day-1 job, before anything else:** ship 20 fake-but-realistic fixture rows matching §3.1, §3.2, §3.3. Everyone else is blocked until those exist.

## 2. Data acquisition — the fallback ladder

**This was the plan's worst hole.** The previous version said "cached snapshot" as the safety net, which silently assumed the scrape succeeds at least once. It might not. MPLADS publishes no bulk API.

A1 works **down** this ladder and stops at the first rung that yields ≥500 usable records. Log which rung succeeded in [[Logbook]].

| Rung | Approach | Effort | Notes |
|---|---|---|---|
| **1** | Discover the underlying XHR/JSON endpoints behind `mplads.mospi.gov.in/digigov/dashboard.html` via browser devtools network tab | Hours | Best case by far. Clean JSON, paginated, no parsing. **Try this first, it is often 20 minutes of work.** |
| **2** | Playwright headless scrape of the rendered dashboard, paginating by state and constituency | 1 day | Reliable but slow and brittle to markup changes |
| **3** | [Empowered Indian](https://empoweredindian.in/mplads) — an existing public MPLADS visualization | Hours | They already solved this data problem. Check their approach or dataset before building your own. Credit them. |
| **4** | `data.gov.in` MPLADS datasets, plus Lok Sabha and Rajya Sabha Q&A answers, which routinely contain tabular MPLADS figures | 1 day | Lower resolution, but real and citable |
| **5** | Hand-curated seed dataset from published CAG reports and dashboard exports, **clearly labelled in the UI as a demo dataset** | 1 day | Last resort. Honest labelling is mandatory. A demo on labelled sample data is respectable; a demo on unlabelled fake data that a judge catches is fatal. |

**Hard rule:** whichever rung succeeds, A1 immediately writes a **cached snapshot to disk**. Everything downstream reads the snapshot, never the live source. That snapshot is the offline demo (M6).

## 3. Contracts — freeze before any code (this is CP0)

### 3.1 Normalized record (A1 → everyone)
```json
{
  "work_id": "string, unique",
  "state": "string",
  "constituency": "string",
  "mp_name": "string",
  "tenure": "string, e.g. 2024-2029",
  "implementing_agency": "string",
  "vendor_name": "string or null",
  "work_category": "string, e.g. Road / Drinking Water / School / Health",
  "sanctioned_amount_inr": "number",
  "expenditure_amount_inr": "number",
  "sanction_date": "YYYY-MM-DD or null",
  "completion_status": "Recommended | Sanctioned | In Progress | Completed",
  "last_updated": "YYYY-MM-DD",
  "source_rung": "integer 1-5, which acquisition rung produced this"
}
```

### 3.2 Risk-scored record (A2 → A4)
```json
{
  "work_id": "string, matches 3.1",
  "inspection_rank": "integer, 1 = inspect first",
  "risk_score": "number 0-100",
  "flags": ["cost_outlier", "stalled_work", "expenditure_mismatch", "agency_concentration"],
  "why_flagged": {
    "cost_outlier": "Cost is 3.2x the median for road works in this state.",
    "stalled_work": "Sanctioned 14 months ago, zero expenditure recorded."
  },
  "peer_group": {
    "label": "Road works, Bihar, 2023-24",
    "n": 289
  }
}
```
`peer_group` is **mandatory on every flagged record**, not optional. It is what defeats the "a hill road genuinely costs more" objection, and it is a visible UI element, not metadata.

### 3.3 Fund-flow graph (A3 → A4)
```json
{
  "nodes": [{"id": "string", "type": "MP | Agency | Vendor", "label": "string", "risk_weight": "number"}],
  "edges": [{"source": "id", "target": "id", "work_count": "number", "total_amount_inr": "number", "flagged_work_count": "number"}]
}
```

### 3.4 API (A4 → A5)
- `GET /api/works?state=&year=&category=&flag=` → paginated §3.2 records, **sorted by inspection_rank**
- `GET /api/works/{work_id}` → full detail, one record
- `GET /api/graph?agency=&vendor=` → §3.3 subset
- `GET /api/stats/summary` → works under implementation, flagged count, total ₹ flagged, ₹ idle beyond 12 months

## 4. Phases

| Phase | What happens | Gate |
|---|---|---|
| **0 Contracts** | A6 ships fixtures, everyone reads §3, repo scaffolded | CP0 |
| **1 Parallel build** | A1 works the ladder. A2, A3, A4, A5 build on fixtures **simultaneously** | CP1 |
| **2 Real models** | A2 and A3 run on A1's real output | CP2, CP3 |
| **3 Wiring** | A4 swaps fixtures for real outputs behind the same contract | CP4 |
| **4 Frontend live** | A5 points at the real API. If §3 held, this is a config change, not a rewrite | CP5 |
| **5 Hardening** | Offline mode, dry runs, timing | CP6, CP7 |
| **6 Feedback loop** | Inspection outcomes get a contract, a store that survives a snapshot rebuild, an endpoint, an on-screen way to record one, and precision-at-quota measured from them. **No model change.** | CP8 |
| **7 Learning** | Detector reweighting measured against the frozen 30/25/25/20 baseline on held-out outcomes. Supervised classification stays gated until confirmed cases accumulate. | CP9 |

**Phases 6 and 7 added 2026-09-03.** They were promised in three places -- the deck (*"reviewers train the model, not the reverse"*, *"save supervised classifiers for once confirmed cases pile up"*), `Understanding NidhiNetra` part 4, and the PRD's *"inspection outcomes come back as labels"* -- but existed in no plan. Split into two phases on purpose: phase 6 is a data-capture and measurement problem with no model in it, phase 7 is the model work, and collapsing them invites retraining on a handful of outcomes. Both sit behind CP1: an inspection recorded against a fixture work_id measures nothing.

## 5. Integration controls (because one human reviews six streams)

Six agents do not reduce your review load, they multiply it. Controls:

- **Maximum 3 open streams at once.** Never review six things simultaneously. Suggested waves: A1+A6 → A2+A3 → A4+A5.
- **Review at checkpoint boundaries, not continuously.** An agent runs to its checkpoint, then you review once.
- **Contract violations are auto-reject.** If output does not validate against §3, it goes back without discussion. Write the validator on Day 1.
- **You must be able to explain every line to a judge.** Code you cannot defend under questioning is a liability, not an asset.

## 6. Calendar

**Correction, 2026-09-02:** every date below through "Official SIH portal submission" was sequenced backwards from **2026-09-20** as the portal deadline. That date was wrong. The user confirmed the actual submission happened ~2026-08-31, roughly three weeks earlier than this table assumed, and the PPT is now locked. The CP0-CP7 dates in this table were never re-anchored to a real external deadline after that -- they are aspirational pacing, not tied to anything binding. The one real known constraint is still the internal round date, which remains unknown (see the row below). Do not treat any date in this table as a hard deadline until that is found out and the table is rebuilt against it.

| Milestone | Date | Status |
|---|---|---|
| Idea submission PPT | 2026-08-26 | ✅ Delivered |
| Prototype planning | 2026-08-31 | ✅ Done |
| Data spike, capture the listing request | 2026-09-01 | ◐ Partial. Aggregates confirmed live, work-level still blocked |
| CP0 contracts frozen | 2026-09-03 | ☐ Date not re-anchored, see correction above |
| CP1 real data flowing | 2026-09-05 | ☐ Date not re-anchored, see correction above |
| CP2 risk engine, CP3 graph | 2026-09-08 | ☐ Date not re-anchored, see correction above |
| CP4 API serving real data | 2026-09-10 | ☐ Date not re-anchored, see correction above |
| CP5 frontend live | 2026-09-13 | ☐ Date not re-anchored, see correction above |
| CP6 live pull and fallback | 2026-09-15 | ☐ Date not re-anchored, see correction above |
| CP7 dry run passed | 2026-09-17 | ☐ Date not re-anchored, see correction above |
| Buffer | 2026-09-18 to 09-19 | ☐ Do not spend this early |
| **Internal round** | **______** | ☐ **Still unknown. Find this out, it compresses everything above** |
| ~~Official SIH portal submission~~ | ~~2026-09-20~~ | ✅ **Actually done, ~2026-08-31** |

Work backwards from the internal round once known. CP7 must land at least 2 days before it, and the buffer above is the first thing the internal round eats.

## 7. Stack

React/Next.js + Tailwind v4 + Radix primitives + **TanStack Table** (the ranked table is the product, do not hand-roll it) + Motion. FastAPI backend. pandas, scikit-learn, NetworkX. DuckDB or Postgres. Playwright for rung 2. Full frontend spec in `NIDHINETRA-DESIGN-BRIEF.md`.

## 8. The rule for every agent

After any checkpoint, fix, or decision: **update [[Checkpoints]]** and **append to [[Logbook]]**. Never skip the logbook entry, even for small fixes.

---
Back to [[PRD]] · [[Checkpoints]] · [[Logbook]] · [[00 Dashboard|Dashboard]]
