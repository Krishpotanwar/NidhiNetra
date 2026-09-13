---
tags: [sih2026, prd, prototype]
ps: SIH26102
solution_name: NidhiNetra
---

# PRD — NidhiNetra Prototype

**Problem statement:** [[SIH26102 - MPLADS Anomaly Detection]] · **Plan:** [[Execution Plan]] · **Gates:** [[Checkpoints]] · **Log:** [[Logbook]] · **Design:** `NIDHINETRA-DESIGN-BRIEF.md` (vault root)

> **Rewritten 2026-08-31** after a hard-diagnostic `/office-hours` pass. The product thesis changed. If you read an earlier version of this file, the user, the pitch, and the must-have list are all different now.

> **Kid version:** this page answers "what are we building, and how do we know it's done?" The Execution Plan answers "who does what, in what order." Checkpoints answers "are we there yet?" Logbook answers "what happened?"

---

## 1. The thesis, in one paragraph

By law, District Authorities must physically inspect **at least 10% of MPLADS works under implementation every year**. Nothing tells them *which* 10% to pick, so the selection is effectively arbitrary and roughly **90% of works are never physically inspected at all**. NidhiNetra ranks the works by risk and hands the officer a prioritised inspection list.

**NidhiNetra is an inspection-targeting system, not a fraud detector.** That distinction is the entire product and it must survive into every slide, every screen, and every label.

### Why this framing beats "AI fraud detection"

| | Fraud-detection framing | Inspection-targeting framing |
|---|---|---|
| Adoption | Proposes a new process, needs new authority | Slots into a legal duty that **already exists** |
| "How is this different from CAG?" | Hard to answer | CAG is a retrospective ~decadal sample. This is a continuous prospective ranking that feeds the annual duty. |
| False positives | An accusation against a real person | One inspection visit, which is the point |
| Ground truth | We have none, and can't get it | **Inspection outcomes come back as labels.** The system generates the training data it currently lacks. |

That last row is the strongest thing in the whole project. Say it out loud in the pitch.

## 2. The one user

**A senior officer at MoSPI (Ministry level).** One user, not four.

Their bad day: a Parliamentary Question or a CAG report names MPLADS leakage and they have no data ready to respond.

**Why the Ministry and not the District Collector** (who has the sharper personal pain): the fund-flow graph is **structurally meaningless below national scale**. A single district has too few agencies and vendors for concentration patterns to exist. Choosing a district-level primary user would have forced us to discard the only real differentiator.

The District Collector is not gone. They are **beat 3 of the demo**: open on the national view, zoom into one flagged cluster, then say "and this is the screen the Collector gets." One primary user, one narrative hop.

## 3. Scope

### Must ship (M1 to M6)

| # | Feature | Done when |
|---|---|---|
| **M1** | Data pipeline produces normalized MPLADS records | ≥500 real records, schema-valid against [[Execution Plan]] §3, cached snapshot on disk |
| **M2** | Risk engine ranks every work | Runs on 100% of records; ≥3 flag types actually fire on real data; **stalled/idle funds is one of them** |
| **M3** | Every flag carries a plain-language reason **and its peer group** | 100% of flagged records show both. The stated peer group ("compared against 289 road works, Bihar, 2023-24") is not optional — it is what defeats the "a hill road genuinely costs more" objection |
| **M4** | **The Inspection List screen** — the hero | Ranked table, filters, reason column, drill-down. This is the product. If everything else broke and this worked, the demo still lands |
| **M5** | Fund-flow graph as the drill-down | Renders from real data, surfaces ≥1 real concentration cluster, reachable from a flagged row |
| **M6** | Live data with a resilient fallback | App pulls real MPLADS data on a schedule and on demand. A failed or slow pull shows the last good data with its true age, never an error and never a blank screen |

### Nice to have, only after M1 to M6 pass

- National choropleth risk map (**demoted from must-have** — every competing team will build this; it is context-setting, not the argument)
- Trend charts
- LLM-written explanations (templated ones already satisfy M3)
- Mocked alert-to-nodal-authority notification
- Predictive forecasting

### Explicitly out of scope

Auth and user accounts · real notification delivery · production security hardening · mobile · any data beyond the public MPLADS dashboard · **a supervised fraud classifier** (no labels exist; claiming one is a credibility failure).

## 4. Non-functional requirements

- **Framing discipline is a UI constraint, not a slide footnote.** Buttons say "Flag for inspection," never "Report fraud." Nothing is ever shown as green, because green means "verified clean" and nothing here is verified clean, only unflagged. Full copy rules in the design brief.
- **Live, with a floor under it.** The screen shows real fetched government data, refreshed on a schedule and on demand. Judging-day wifi failure must not be able to kill the demo, so a failed pull falls back to the last good data and states its age plainly. Offline-only was rejected on 2026-09-01: an oversight instrument that cannot see live data is not an oversight instrument.
- **Explainability beats accuracy theatre.** A flag with a correct, legible reason beats a better model with an opaque score.
- **Desktop-first, projector-legible.** The real user is at a desk; the real demo is on a projector at the back of a room.

## 5. Open risks

| Risk | Severity | State |
|---|---|---|
| Data acquisition | ~~HIGH~~ **LOW** | **Resolved 2026-08-31.** A public unauthenticated REST API was found on the MPLADS dashboard, including work-level endpoints. See [[Logbook]] and `NIDHINETRA-DESIGN-BRIEF.md` Part C. The five-rung ladder in [[Execution Plan]] §2 remains as backup. |
| No labeled fraud ground truth | MEDIUM | **Now a feature**, see §1. Inspection outcomes become labels. |
| "Anomaly dashboard on govt data" is the most saturated SIH archetype | MEDIUM | Mitigated by the inspection-targeting reframe and the fund-flow graph. Both must survive time pressure. |
| Six parallel agents, one human reviewer | MEDIUM | Human is the integration bottleneck. Controlled by the open-stream cap in [[Execution Plan]] §5. |
| Internal round date unknown | MEDIUM | **Open.** Fill the date table in [[Execution Plan]] §6. |

## 6. Definition of done

M1 to M6 all ticked in [[Checkpoints]], and the demo script runs start to finish with **zero crashes**, watched once by someone who did not build it. Run it twice: once on the network to show a live pull, and once with the network disabled to prove the fallback holds and the data-age label tells the truth.

---
Back to [[Execution Plan]] · [[Checkpoints]] · [[Logbook]] · [[00 Dashboard|Dashboard]]
