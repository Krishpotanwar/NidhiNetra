---
tags: [sih2026, prototype, technical-deep-dive]
ps: SIH26102
solution_name: NidhiNetra
date: 2026-09-05
---

# Technical Deep-Dive — for the qualifying round

**Why this file exists:** round 1 was slides and a pitch. Round 2 is different — live app on real data, plus a detailed walkthrough of the tech stack, the algorithms, and the pipeline. [[NidhiNetra-Pitch-Script|The existing pitch script]] was written for the first format and still names tech that was never built (DBSCAN, SHAP, Sentence-BERT, OpenCV — see [[Logbook]], 2026-09-02, for the full story of why). This file is the honest, current, technically deep version: what is *actually* built, with real numbers off the real 79,068-record dataset, verified live today.

**One rule for this round, stated up front because it matters more here than anywhere else:** do not improvise a trained or fine-tuned model to have "training results" to show. No labelled fraud data exists for this scheme — that is a documented, defended, load-bearing fact of this project, not a gap to paper over. [[Checkpoints]] CP9 was redesigned *the same day this file was written* to drop a retraining gate entirely, because a sharper statistical read showed that the number of real inspection outcomes realistically available by any presentation date (a handful) makes any reweighting result win by noise, not signal. A technical panel that says up front they will probe the stack in detail is the panel most likely to ask the follow-up question a rushed model has no honest answer to. The good news, covered below: there is already a real, honestly-fit ML component in the pipeline. Show that instead.

**Related reading:** [[PRD]] · [[Execution Plan]] · [[Checkpoints]] · [[Logbook]] · [[NidhiNetra Viva Brief]] · [[NidhiNetra-Pitch-Script]]

---

## 1. The thesis, in one paragraph

NidhiNetra does not detect fraud. It ranks an inspection queue that already legally exists: MPLADS Guidelines (April 2023), clause 4.5.2, require District Authorities to physically inspect at least 10% of works under implementation every year, with no selection method specified. The contrast that makes this argument sharp: clause 4.4.2 *does* prescribe sampling criteria for third-party inspection (all works over Rs 25 lakh, 50% of those between Rs 15-25 lakh, plus at least 50 more balanced across cost and SC/ST areas). The guidelines know how to mandate a sampling rule; for the District Authority's 10% they deliberately do not. Today that choice is effectively arbitrary. NidhiNetra ranks all 79,068 real MPLADS works by risk, so the mandatory 10% inspection quota -- 4,481 inspections a year, since clause 4.5.2 measures the 10% against the 44,810 works *under implementation*, not against every work on the portal -- lands on the works most worth a human's time — and every inspection outcome that comes back becomes the labelled training data this problem does not currently have.

This reframe is why "no labelled data" is not a weakness of the pitch — it is the second half of the product's own thesis. The system exists specifically because that data doesn't exist yet.

## 2. Architecture at a glance

Five real stages, each independently tested (288 passing Python tests, 14 passing frontend tests as of this session):

```
MPLADS live API  ->  Adapter/Normalize  ->  Risk Engine  ->  Graph Builder  ->  API + Frontend
  (ingest/)          (ingest/mplads_       (risk/)           (graph/)          (api/, web/)
                       adapter.py,
                       normalize/)
                                                 |
                                                 v
                                     Inspection outcomes (CP8)
                                     -- durable, non-rebuildable
                                     human judgement, feeds CP9
```

Every stage below is real, running code, not a diagram of intent. Line counts and function names are given so a judge who asks "show me" can be shown, not told.

## 3. Stage 1 — Data acquisition

**The five-rung fallback ladder** (`ingest/rungs.py`): tries the live MPLADS REST API first, falls through toward progressively lower-resolution public sources, and only ever falls to a clearly-labelled demo dataset as the last resort — never silently. `source_rung` is stamped on every single record, so the UI always knows and states where its data actually came from.

**Rung 1 is live**, and getting it there is a real diagnostic story worth telling in full, because it demonstrates the kind of debugging rigor a technical panel is actually listening for:

- The MPLADS dashboard (`mplads.mospi.gov.in`) exposes an undocumented, unauthenticated REST API. Found by reading the dashboard's own network traffic, not by guessing.
- The blocking bug for weeks was not the endpoint — it was the request shape. `getTilesReportData` needs `{"combo": "0,0,0,2", "key": "<tile name>"}`, and `combo` has to be a comma-separated **string**. Every earlier attempt sent it as an integer and silently got `Total_Amt: 0.0` back — a wrong-shape request that looked like a dead endpoint. Caught by a human capturing the real request body from a browser's Network tab.
- Three tiles (Works Sanctioned, Works Completed, Expenditure) are joined on `WORK_RECOMMENDATION_DTL_ID` to produce **79,068 real work-level records** — the actual dataset the live demo runs on, not a sample.
- **A second, separate diagnostic story, resolved today:** even with a perfectly valid, freshly-captured browser session, automated calls to that same endpoint were tarpitting — full connection timeout, zero bytes, no HTTP status — while plain page loads succeeded instantly. The session cookie's name (`TS<hex>`) is F5 BIG-IP's bot-mitigation signature. Tested directly with real Chrome and Safari TLS fingerprints (via `curl_cffi`) from the same blocked network: still blocked, which rules out "needs to look more like a browser" and points to network-origin classification (cloud/datacenter IPs) instead. **The fix needed no cookie-copying at all** — a new `pull-live` pipeline command bootstraps its own session automatically (a plain GET the way any browser does, cookie jar persists automatically) and fetches all three tiles with zero credential input, atomically, with a full test suite. It only needs to run once, from an ordinary network, a few minutes before a demo — never on stage.

This is a genuinely good story for "explain your pipeline in detail": it shows real systems debugging (distinguishing a session problem from a network-origin problem, empirically, not by assumption), and a real engineering response (autonomous fetch, atomic writes, tested failure modes) rather than a workaround.

## 4. Stage 2 — Adapter and normalization

MPLADS publishes 112 distinct free-text activity strings and a `WORK_CATEGORY` column that says "Normal/Others" on 98% of rows — useless for grouping. The adapter (`ingest/mplads_adapter.py`) maps every activity string onto one of seven categories via an ordered, most-specific-first keyword rule list.

**A real bug worth telling, because "we caught our own mistake" reads better than "everything worked first try":** the first version of that rule list put a Sanitation rule (matching "drain") before the Road rule. The single largest activity in the country — "Construction of roads... with or without drainage system," 18,248 works — contains the word "drainage," so 23% of every work in India was classified as sanitation on the first pass. Caught by checking the output category distribution against the raw activity-string counts, not by re-reading the rule and assuming it was right. Reordered; verified against all 112 real activity strings with a test that fails if any of them fall through uncategorized.

Other real, defensible judgement calls made here: completion status is derived from an explicit join against the Completed tile (not the coarser `WORK_STAGE` field, which under-reports completion by 8x); only settled (`Payment Success`) disbursements count toward expenditure, so a work with money stuck mid-payment still reads as under-spent — which is exactly the case the stalled-work detector exists to catch, not a case to hide from it.

## 5. Stage 3 — The risk engine (rules + the real ML component)

This is the section to slow down on. It has both an explainable rule engine and a genuine, honestly-fit unsupervised model — and the *design decision* connecting them is the strongest technical answer in the whole project.

### 5.1 Four rule-based detectors, weighted and capped

| Detector | Weight | What it catches |
|---|---|---|
| `cost_outlier` | 30 | Cost is an extreme multiple of the peer-group median |
| `stalled_work` | 25 | Sanctioned long ago, little or no spend since |
| `expenditure_mismatch` | 25 | Spend pattern inconsistent with the work's stated stage |
| `agency_concentration` | 20 | One implementing agency spans an unusual number of MPs/districts |

Weights sum to a maximum of 80 points, hard-capped — deliberately leaving headroom that only the ML component below can fill, never the reverse.

**Peer groups are the actual defence against "a hill road costs more than a plains road."** Every cost comparison happens inside a `(work_category, state, financial_year)` group, and a group must contain **at least 30 works** (`MIN_PEER_GROUP_N = 30`, `risk/peer_groups.py`) before any cost-based flag is even allowed to fire — a real statistical floor, enforced in code and by a schema constraint, not a suggestion. On the real dataset: 585 groups form, 290 clear that floor, covering 97.0% of all works. On the current live snapshot, **23,800 of 79,068 works (30.1%) are flagged**, breaking down as: `stalled_work` 14,022 · `agency_concentration` 9,934 · `cost_outlier` 1,611 · `expenditure_mismatch` 301. No threshold was tuned to produce these numbers — they are what the real data does.

Every flagged work gets a real, computed sentence, not a template with blanks: *"Cost is 8.8x the median for road works in this state. Sanctioned 13 months ago, 10 percent spent. Agency holds works in 4 districts, 4 MPs."* — verified live today against a real ranked record.

### 5.2 The real ML component: an unsupervised anomaly ensemble

`risk/detectors.py`'s `ensemble_scores()` — this is the honest answer to "show us your model":

- **Features** (four, per work): `log1p(sanctioned amount)`, `log1p(spent amount)`, spend ratio (capped at 5x to stop one extreme outlier from flattening every other record's scaled value), and months elapsed since sanction.
- **Scaling:** `sklearn.StandardScaler`, fit fresh on each batch.
- **Two models, genuinely fit on the real data, every build:**
  - `IsolationForest(n_estimators=200, contamination=0.1, random_state=42)`
  - `LocalOutlierFactor(n_neighbors=20, contamination=0.1)`
- Both anomaly signals are min-max normalized to `[0, 1]` and averaged into one ensemble score per work.
- **Degenerate-batch handling, stated because it shows the same rigor as the peer-group floor:** a batch under 2 records cannot support either model meaningfully, so the ensemble contributes exactly `0.0` and the score falls back entirely to the four named rules — a deliberate, tested fallback, not an unhandled edge case.

**The weighting decision, and why it is the strongest answer in this section:** the ensemble score contributes **at most 20 of the final 100 points** (`ENSEMBLE_COMPONENT_WEIGHT = 20.0`, `risk/rank.py`), hard-capped, and it is *never* allowed to be the reason a work ranks highly on its own — it only nudges ordering within and around what the explainable rules already found. This is a real, deliberate engineering trade-off: an unsupervised anomaly model can be genuinely useful signal, but a government officer being sent to inspect a specific work needs a reason they can act on and argue with, not a probability out of a model neither they nor a judge can audit. Capping the model's influence is not a limitation the team ran out of time to fix — it is the correct call for this specific institutional use case, made on purpose, and it is defensible against exactly the "why not deep learning" question this round is expected to ask.

## 6. Stage 4 — Fund-flow graph and concentration detection

`graph/build_graph.py` builds a three-tier MP → Implementing Agency → Vendor graph from the same real dataset: **18,144 nodes** (536 MPs, 754 agencies, 16,854 vendors), **18,959 edges**. `find_concentration_clusters()` identifies vendors or agencies tied to an unusual number of distinct MPs — **4,845 vendors are reachable from 3 or more distinct MPs through the agencies that pay them** -- a two-hop count over the graph, which is the figure the graph itself reports. Counted strictly, on works recommended directly by 3 or more MPs, it is 79 vendors and 117 agencies. Both are true and they answer different questions; always say which one is meant. The most concentrated vendor node reaches 18 MPs across 23 works.

**An honest caveat worth stating out loud, because it is a stronger answer than hiding it:** some of the most "concentrated" entries in that graph are `Executive Engineer` (a job title, not a vendor) and personal names entered inconsistently. That is a finding about the quality of the portal's free-text vendor field, not a finding about those specific works, and the team says so rather than dressing up a data artifact as a fraud signal.

## 7. Stage 5 — API, snapshot pipeline, and safety design

Every artifact the frontend reads (`works.parquet`, `scored.parquet`, `graph.json`, `manifest.json`) is produced by `build_snapshot()` through a stage-everything-then-commit-everything discipline: every file is written to a temp path, read back and validated, and only renamed into place once *all four* have succeeded — so a failure partway through a rebuild can never leave the API serving an internally inconsistent mix of old and new data.

**A real, severe bug found and fixed this session, worth naming because it shows the team audits its own safety claims rather than assuming them:** because the raw acquisition cache is gitignored (single-disk) but the committed snapshot is real data, a second machine's very first click of "Refresh" used to silently replace 79,068 real records with a 20-row demo fixture — no error, no warning. `build_snapshot()` now raises a dedicated `SnapshotDowngradeError` and the API returns a clear 409 rather than downgrading silently. Verified today: the guard is real code, not a comment, and it is covered by five tests that inject the exact failure and confirm the refusal.

The frontend never shows a raw error or a blank screen: killing the API, killing the network, and a hung connection were each tested live earlier in this project's history, and each correctly falls back to the last good cached data with its true age shown, never silently going stale-looking-fresh and never crashing.

## 8. The feedback loop (CP8), and why CP9 deliberately does nothing yet

Built and verified live today. An inspecting officer records one of six **observable, non-verdict** outcomes against a specific work — never "fraud," "clean," or "verified," by design (`contracts/inspection_outcome.schema.json`):

`work_present_and_matches` · `work_present_but_differs` · `work_not_found_at_site` · `documentation_incomplete` · `duplicate_of_another_work` · `agency_unresponsive`

Each recorded outcome freezes the work's rank and risk score **at the moment of inspection** (ranks reshuffle on every rebuild, so comparing today's outcome against tomorrow's rank would silently change its own answer), plus which inspection-quota cutoff and population it was judged against, and whether it was a targeted pick or a random control-sample check (`in_control_sample`) — the actual comparison group the Viva Brief already promises a judge ("do we find more problems than a random sample?"). Stored in SQLite, independent of the rebuildable snapshot pipeline, because a human judgement is the one piece of state in this whole system that cannot be regenerated if lost.

**The strongest single line for this round:** *"We built the exact mechanism to collect the labelled data this problem doesn't have yet, and we are refusing to pretend we already have enough of it to train on. When there is enough, the report-only precision figure and the mechanism above are already sitting there ready — we designed for that day without faking that it's already here."*

## 9. Prepared answers — the questions this round is built to ask

**"Show us your training results."**
There isn't a supervised model to show a training curve for, and building one now, on data that cannot support it, would be a worse answer than this one. What we can show: the Isolation Forest / LOF ensemble's real behavior on the real 79,068-record dataset (section 5.2) — genuinely fit, every build, capped at 20% of the score by design. And the mechanism (CP8) that is actively collecting the labelled data a supervised model would eventually need.

**"Why not deep learning / a fine-tuned model?"**
Three reasons, all real constraints, not excuses: every flag has to be explainable to a government officer who will act on it, in language they can argue with — a rule-weighted score with a peer-group sentence does that; a probability out of a fine-tuned net does not, without a second explanation layer bolted on top. There is no labelled fraud data for this scheme, so there is nothing to fine-tune *against* honestly. And it has to run on infrastructure the government already has, not a GPU cluster.

**"How do you measure accuracy with no ground truth?"**
Two ways, both already designed. Precision at the inspection quota — of the works actually inspected inside the risk-ranked cutoff, what fraction had a real issue, compared against the same rate in the random control sample — reported with a minimum-`n` suppression (same discipline as the peer-group floor: a rate computed on four inspections is worse than no rate at all). And, as a bootstrap sanity check only, replaying CAG/RTI-documented cases hand-matched to real `work_id`s — stated explicitly as a small spot-check with its own `n`, never as a training set.

**"Cost varies for legitimate reasons — hill roads cost more than plains roads."**
Agreed, which is exactly why nothing is ever compared against a national average. Every cost comparison happens inside a `(category, state, financial_year)` peer group with a hard 30-work minimum before it's allowed to fire at all.

**"How is this different from a monitoring dashboard / from CAG's own audits?"**
CAG's audit cycle is retrospective and roughly decadal in practice; this is a continuous, prospective ranking of the inspection queue that already exists by law. A monitoring dashboard shows what happened; this decides what's worth a human's next inspection, with a stated reason, and turns that inspection's result into a label — which is the thing the space currently lacks.

**"What happens when the model is wrong?"**
Nothing accusatory, by construction. Every output is a ranked recommendation with a plain-language reason attached — never a verdict — reviewed by a human before anything is recorded, and the officer's actual finding (including "nothing was wrong here") is what gets stored and eventually counted.

## 10. Suggested live-demo sequence

Verified working, live, today, on the real 79,068-record dataset, zero console errors:

1. **Inspection List** loads — real summary strip (44,810 works under implementation, 18,093 flagged, real rupee totals), real quota sentence ("the ten percent obligation falls at rank 4,481").
2. Open **rank 1** — a real flagged work (Road work, Azamgarh, UP). Point at the risk breakdown: *Cost outlier 30, Stalled work 25, Agency concentration 20, ensemble 9 = 84* — every point accounted for, nothing hidden.
3. Point at the **peer-group sentence** — "Compared against 2,213 road works, Uttar Pradesh, 2025-26" — this is the direct, on-screen answer to the hill-road objection.
4. Click **View fund flow** — the MP → Agency → Vendor graph, filtered to this work's own cluster.
5. Click **Record inspection** — walk through the six-option outcome enum, the required inspector initials, the control-sample checkbox. Submit one live if the demo allows it — the "Inspection recorded" confirmation is real, and the row is durably stored in SQLite, independent of the snapshot.
6. If time allows: the **Refresh** control, and a plain statement of what it honestly does and doesn't do (rebuilds from the last real pull; a live re-pull is a separate, tested, pre-demo step — section 3 above is the answer if asked why).

---

Back to [[Checkpoints]] · [[Execution Plan]] · [[Logbook]] · [[NEXT-STEPS]] · [[00 Dashboard|Dashboard]]
