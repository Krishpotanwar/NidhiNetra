# NidhiNetra

SIH 2026 · SIH26102 · Ministry of Statistics and Programme Implementation.

An inspection-targeting system for MPLADS. District Authorities must
physically inspect at least 10% of works under implementation every year,
and nothing tells them which 10%. NidhiNetra ranks that already-mandated
queue and states, in plain language, why each work is on it. It never
accuses anyone of fraud.

Project overview, screenshots, and full tech stack: [`../README.md`](../README.md)
Full explanation, from zero: [`04 Prototype/Understanding NidhiNetra.html`](../04%20Prototype/Understanding%20NidhiNetra.html)

## Status

Contracts frozen, `make validate` passes with self-tests. Pipeline (ingest,
normalize, risk scoring, fund-flow graph, snapshot) runs end to end. The
API's works/stats/inspections/graph/refresh routers are implemented and
tested. The frontend's four real pages (Dashboard, Inspection List, Fund
Flow, Reports) are built against the pinned design reference, `tsc`,
ESLint, and Vitest pass clean, and `next build` produces a clean static
production build. See [`04 Prototype/Logbook.md`](../04%20Prototype/Logbook.md)
for the dated build history.

## Run it

```bash
make validate   # prove the contracts and fixtures are internally consistent
make contracts  # generate pydantic + TypeScript from the JSON Schemas
make api        # FastAPI dev server, port 8000
make web        # Next.js dev server
make demo       # both, wired together, against the current snapshot
```

## Layout

```
contracts/       the frozen data shape and copy. Read this before touching code.
pipeline/         A1 ingest, A2 risk scoring, A3 fund-flow graph
api/              A4 FastAPI, reads pipeline output
web/              A5 Next.js frontend
data/snapshot/    committed. What the demo runs from if a live pull fails.
scripts/          analysis and deck-figure generation, not part of the running app
```

## The one rule that matters most

Every user-visible string comes from `contracts/strings.json`. No agent
invents copy. See `contracts/strings.json`'s `lint.banned_literal` and
`lint.banned_derived` for the
words that must never reach a screen.
