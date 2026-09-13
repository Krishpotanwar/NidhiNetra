# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Primary: the inspecting officer.** District Authority officers and MoSPI MPLADS division officials who must choose which works to physically inspect. MPLADS guidelines (clause 4.5.2) require District Authorities to inspect at least 10 percent of works under implementation every year, and nothing tells them which 10 percent. They read dense documents all day, answer to Parliamentary Questions and audit, and plan inspections at a desk.
- **First viewers: the SIH 2026 Grand Finale jury** (problem statement SIH26102, Ministry of Statistics and Programme Implementation), watching a 10 minute live demo, often on a 1920x1080 projector. Confirmed 2026-09-11: the redesign serves both. It is the officer's working tool, presented well enough that the jury understands it in one screen.

## Product Purpose

NidhiNetra ranks every MPLADS work under implementation by inspection priority and states, in plain language with a number, why each work sits where it does. It turns the mandatory 10 percent inspection quota from an arbitrary pick into a defensible ranked list, then records what each inspection observed so the ranking can later be checked against reality.

Success: an officer opens the list, sees where the quota cutoff falls, opens a work, understands its reasons and its peer group, and records an inspection outcome without leaving the page.

## Positioning

It never accuses anyone. Every flag is a recommendation to inspect, never a finding. The score is explainable line by line (four named flags with fixed weights, plus a capped statistical component), every comparison names its peer group (category, state, financial year), and the list is scoped to exactly the population the legal quota covers.

## Operating Context

- **Data:** real MPLADS work records pulled from the public MPLADS dashboard API. Current snapshot 2026-09-04: 79,068 works, 44,810 under implementation, 36 states and union territories, 535 constituencies. Served offline from a committed Parquet snapshot through a local FastAPI, so a demo needs no network.
- **Workflow:** Dashboard overview, then the Inspection List (filter by state, year, category, flag), then a work's detail panel (score breakdown, peer group, fund flow link, record inspection), then Fund Flow (agency and vendor concentration), then Reports (recorded inspections).
- **Environment:** desktop first. Must hold on a 1920x1080 projector and stay legible from the back of a room; must also work on a laptop.

## Capabilities and Constraints

- Four surfaces, all real, none showing fabricated data: Dashboard, Inspection List, Fund Flow, Reports (recorded inspections). Confirmed 2026-09-11, revised 2026-09-12: the Specimen Sheet (a live design-token inspector) shipped as a fifth nav tab was a development aid, not a product view for an officer or a judge, and was removed from the frontend on request. The design system it displayed still lives in `DESIGN.md`.
- Every user-visible string lives in `05 App/contracts/strings.json`. Its lint lists are binding: never fraud, suspicious, corruption, verified, clean, confirmed anomaly, detected, and the rest of `lint.banned_*`. No em dash characters anywhere in the interface.
- Indian digit grouping on every number (1,72,961). Tabular figures on every number. The risk score (0 to 100) orders a queue; it is never a probability.
- The source has constituency, not district, and sanctioned value, not released value. Labels say what the field actually is.
- Work descriptions are not in the source data yet. Titles are composed from category and constituency and are never invented.
- No authentication exists. Officer identity is self-reported initials.
- Presenter mode (`?present=1`) may expose the designed data states (loading, empty) for a demo. It never appears in the officer's default interface. Confirmed 2026-09-11.
- Undecided: final spelling of the team name on any credit line; whether MoSPI supplies official emblem artwork.

## Brand Commitments

- Name: NidhiNetra (nidhi, fund; netra, eye). Logo: the tricolour eye with the Ashoka Chakra as its iris (`hihihi.png`, supplied by the user).
- Visual reference pinned by the user on 2026-09-11: `NidhiNetra_Vidhi.png` (dashboard) and `backgroundNidhinetra.png` (tricolour wave hero with India Gate).
- Government of India context appears as text marks: भारत सरकार, विकसित भारत समृद्ध भारत, सत्यमेव जयते. The State Emblem is not used, because the State Emblem of India (Prohibition of Improper Use) Act, 2005 restricts it.
- Taglines from the reference: "A closer look. A stronger India." "Data today. A stronger India tomorrow." "Data for people. Progress for India."
- Green belongs to the tricolour only. It never encodes risk, status or data, because green would claim "verified clean".

## Evidence on Hand

- Real snapshot: `05 App/data/snapshot/` (manifest 2026-09-04T11:37Z, source `mplads_live_api`).
- Risk engine, peer groups and fund-flow graph: `05 App/pipeline/`. API: `05 App/api/`.
- Earlier design brief: `NIDHINETRA-DESIGN-BRIEF.md`. Its product rules (framing, words, numbers, states, accessibility) still bind. Its visual prescriptions are superseded by the 2026-09-11 reference.
- No inspection outcomes are recorded yet. Reports must say so rather than show a number.
- There is one snapshot and no time series, so no trend deltas may be shown.

## Product Principles

1. A recommendation to look, never a verdict.
2. Every number is data, with its unit and its population named.
3. The reason sits on the row. The reason is the product's voice.
4. Honest states over pretty ones: loading, empty, missing and offline are all designed.
5. The officer's task comes first; the jury sees the same tool, well presented.

## Accessibility & Inclusion

WCAG 2.1 AA minimum on all text, including placeholders, helper text and focus rings. Full keyboard operation of the table, filters and detail panel. Reduced motion, reduced transparency and increased contrast are each handled. Relative units, so the layout scales with the reader's text size. English interface with Hindi context marks, each marked `lang="hi"`.
