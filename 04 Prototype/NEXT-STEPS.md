---
tags: [sih2026, prototype, next-steps]
owner: user
date: 2026-09-08
---

# Next steps — the simple version

**What this is:** everything left that only you can do. Nothing else is blocking the project right now. Do these in order.

**Related reading:** [[Checkpoints]] · [[Execution Plan]] · [[Logbook]] · [[Technical Deep-Dive]]

---

## 1. ~~Capture the dashboard again~~ — DONE 2026-09-05

Answered for good: it is not a cookie or login problem, it is this machine's network. Superseded by the `pull-live` command — see step 3.

---

## 2. ~~Find out how long you get to talk~~ — DONE 2026-09-08

**10 minutes.** And the 6-page SIH template is mandatory, so there are now two files:

- **`03 Build Plan/NidhiNetra - SIH26102 Round 2.pptx`** — 6 slides. This is the submission. It was built by editing the round-1 template file itself, so the SIH branding, footers and section headings are the originals, not copies. A `(preview).pdf` sits beside it if you just want to look at it quickly.
- **`03 Build Plan/NidhiNetra - SIH26102 Technical Annexe.pptx`** — 12 slides, numbered 8–18. **Not submitted.** Open it on your laptop during Q&A so a judge's technical question gets answered by turning to a slide instead of by talking.

---

## 3. Run the live pull from your own laptop (5 minutes, do this before the demo)

This is the one thing nobody has been able to test from my side, because this environment is network-blocked from that endpoint. From `05-App/pipeline`:

```
uv run python -m nidhinetra_pipeline.cli pull-live
uv run python -m nidhinetra_pipeline.cli build
```

If both succeed you have a fresh snapshot and the demo is running on data pulled that day. If `pull-live` fails, **nothing is broken** — it leaves the existing data completely untouched, and the demo still runs on the 2026-09-04 snapshot. Tell me either way.

---

## 4. Put your Team ID on slide 1 — and check the team-name spelling

Slide 1 says `[ add your SIH portal Team ID ]`. That is the **only** placeholder left. Worth knowing: the deck you actually submitted in round 1 shipped with *both* the Team ID and the Team Name still as placeholders, so filling this in is already a fix.

Team name is now **TechBashers**, one word — copied from the ovals on your submitted deck. If the portal has it registered as "Tech Bashers" with a space, tell me and I'll change all six slides plus the annexe footers in one go.

---

## 5. Re-download the guidelines PDF as backup evidence (2 minutes)

`mplads.gov.in` times out from my environment — the same block CP6 diagnosed. On your own network, save the **MPLADS Guidelines (April 2023)** PDF. If a judge questions clause 4.5.2, you want the document on your laptop. The clauses that matter are 4.5.2 (District Authority, ≥10% of works under implementation), 4.4.2 (third-party sampling criteria — the contrast that makes our argument), 4.4.1 (State Nodal, ≥1% by value) and 4.6.2 (Implementing Agency, 100%).

---

## 6. Find a second person and do one timed run (needs scheduling)

Someone who has **not** seen this project. They do not need to be technical. Run the whole thing start to finish with a clock against the 10-minute slot.

If it overruns: cut the Fund Flow page first. Keep the Inspection List — that is the one thing that must never be cut.

---

## 7. Decide what happens to the old pitch script

[[NidhiNetra-Pitch-Script]] was written for the round-1 format and still names tech that was never built. The new deck supersedes it. My recommendation is to retire it rather than rewrite it — but it is your call, and I have not touched it.

---

Back to [[Checkpoints]] · [[Execution Plan]] · [[Logbook]] · [[00 Dashboard|Dashboard]]
