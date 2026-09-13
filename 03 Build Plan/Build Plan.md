---
tags: [sih2026, build-plan]
ps: SIH26102
solution_name: NidhiNetra
---

# Build Plan — NidhiNetra

**Problem statement:** [[SIH26102 - MPLADS Anomaly Detection]] · **Proposed solution name:** NidhiNetra ("Eye on the Fund") — see [[Solution Naming & Technical Research]] for naming rationale and alternates.

## One-line pitch
*NidhiNetra is an AI-powered monitoring platform that turns raw MPLADS expenditure and work-execution data into risk-ranked, explainable alerts — flagging cost overruns, stalled works, and suspicious fund-flow patterns for MPs, State/District authorities, and the Ministry, before they become confirmed cases of misuse.*

## Scope (MVP vs stretch)
**MVP (must work live in the demo):**
1. ETL pipeline pulling sanctioned-works, expenditure, and completion-status records from the public MPLADS dashboard (scraper/XHR-discovery — see Data section)
2. Unsupervised anomaly-detection engine (Isolation Forest + peer-group z-scores) flagging cost-per-work outliers, stalled works, and expenditure/utilization mismatches
3. Fund-flow relationship graph (MP ↔ implementing agency ↔ vendor) surfacing concentration and duplicate-work patterns
4. Composite risk-scoring leaderboard by constituency/agency, each flag with an explainable feature breakdown ("why flagged")
5. Interactive dashboard: state/MP/year filters, choropleth risk map, drill-down to individual flagged records, trend charts

**Stretch (only after MVP is fully working):**
- LLM-generated plain-language explanation of each anomaly for non-technical officials
- Mocked "auto-alert to nodal authority" notification to demonstrate the decision-support loop
- Predictive trend forecasting (Prophet/statsmodels) for early-warning framing

## Architecture
```
[MPLADS eSAKSHI public dashboard]
        │  (scraper / XHR endpoint discovery — Playwright headless)
        ▼
[ETL layer] → normalize → [Postgres/DuckDB store]
        │
        ├─→ [Anomaly Engine: Isolation Forest / LOF / z-score, scikit-learn/PyOD]
        ├─→ [Fund-Flow Graph: NetworkX — MP / Agency / Vendor nodes]
        └─→ [Composite Risk Scorer] → risk-ranked leaderboard
                │
                ▼
     [FastAPI backend] ──serves──▶ [React/Next.js dashboard]
                                     - choropleth risk map (Leaflet/Mapbox GL)
                                     - trend charts (Recharts/Nivo)
                                     - drill-down record view
                                     - (stretch) LLM "why flagged" explainer
```

## Tech stack
- **Frontend:** React/Next.js + Tailwind + shadcn/ui, Leaflet/Mapbox GL, Recharts/Nivo
- **Backend/API:** FastAPI (Python)
- **ML/Analytics:** pandas, scikit-learn (Isolation Forest, LOF, DBSCAN) or PyOD, NetworkX, statsmodels/Prophet (stretch)
- **Data ingestion:** Python requests/BeautifulSoup, or Playwright headless if the dashboard requires JS rendering
- **Storage:** Postgres (Supabase/Railway) or DuckDB
- **LLM (stretch):** OpenAI/Anthropic API for plain-language flag explanations
- **Deployment:** Vercel (frontend) + Render/Railway (backend+DB), Docker for the demo

## Datasets / data access
- Primary: [MPLADS public dashboard](https://mplads.mospi.gov.in/digigov/dashboard.html) — no bulk API, filterable by tenure/state/constituency/MP; **Day 1 priority is discovering the underlying XHR/JSON calls or standing up a scraper.**
- Reference/credibility: [Empowered Indian MPLADS dashboard](https://empoweredindian.in/mplads) (existing public viz — worth checking for a shortcut or comparison), [Accountability Initiative PAISA](https://accountabilityindia.in/toolkits/) (methodology precedent).
- Full technical detail in [[Solution Naming & Technical Research]].

## Timeline
| Phase | Window | Focus |
|---|---|---|
| Idea submission | **Today (2026-08-26)** | Lock solution name (NidhiNetra) + one-line pitch |
| Presentation prep | Now → internal round | Build slide deck: problem, solution, architecture, feasibility, impact, demo mockup |
| Internal hackathon / build | TBD | Hours 1–6: data acquisition (scraper). Hours 6–20: anomaly engine + graph. Hours 20–30: dashboard + integration. Hours 30–36: polish + demo script rehearsal |
| Official idea submission (SIH portal) | ~~2026-09-20~~ **Done, ~2026-08-31** | This row's date was wrong -- corrected 2026-09-02 once the user confirmed the actual portal submission happened days earlier than this table assumed. The PPT is locked; see [[04 Prototype/Logbook|Logbook]] 2026-09-02 for a known inconsistency between it and later prototype docs, caught after the fact. |
| Grand finale prep | After shortlist announcement | Refine based on internal-round judge feedback |

## Team roles (fill in with actual names)
- **Data/ETL lead** — scraper, XHR discovery, data normalization (the single highest-risk role — should be the strongest backend person)
- **ML lead** — anomaly detection models, risk scoring, fund-flow graph construction
- **Frontend lead** — dashboard, map, charts, drill-down UX
- **Presentation/PM lead** — deck, pitch narrative, demo script, judge Q&A prep

## Demo script (draft)
1. **Hook (30s):** MPLADS moves thousands of crores across thousands of local works every year — with almost no automated oversight. Show a real stat (from research: GSTN's AI caught ₹36,000cr+ in fraud once graphs were applied to fund flows — MPLADS has never had this).
2. **Problem → Solution (1 min):** Show the MPLADS dashboard as-is (manual, non-analytical) → contrast with NidhiNetra's risk leaderboard.
3. **Live/recorded demo (2–3 min):** Load real scraped data → show anomaly flags appearing → drill into one flagged work with its "why flagged" breakdown → show the fund-flow graph highlighting a suspicious agency/vendor cluster → show the choropleth risk map.
4. **Why this is credible, not hype (30s):** Cite the GST/CBDT AI-fraud precedent slide — this is a proven government playbook, applied to a scheme that's never had it.
5. **Impact & next steps (30s):** Framed as decision support ("risk flags for human review"), not automated accusation — rollout path to State Nodal Authorities and the Ministry.

---
Back to [[Final Recommendation]] · [[Solution Naming & Technical Research]] · [[00 Dashboard|Dashboard]]
