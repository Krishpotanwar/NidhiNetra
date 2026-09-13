---
tags: [sih2026, problem-statement]
ps: SIH26102
org: MoSPI
theme: Miscellaneous
refined_score: 8
---

# SIH26102 — Development of an AI-powered system to detect anomalies, fraud, and inefficiencies in MPLAD Scheme implementation regd.

**Organization:** MoSPI
**Theme:** Miscellaneous · **Category:** Software
**First-pass scores:** impact 9/10, feasibility 8/10, differentiation 8/10, overall 8/10
**Refined score (after reading official description):** 8/10
**Official description found on sih.gov.in:** True

## Verdict
This remains a strong pick after reading the full official scope: it is genuinely software-only (no hardware/IoT/embedded, no classified data), the MPLADS dashboard is real public government data, and the request — detect trends/anomalies/cost-overruns/duplicate-works and surface them via risk-based alerts and decision-support dashboards — maps almost one-to-one onto an unsupervised anomaly-detection + fund-flow-graph + interactive-dashboard build that a web/AI/cloud team can realistically finish in 36 hours. The one meaningful gap between the first-pass and full-scope read is that the "dataset" is a JS-driven searchable dashboard rather than a downloadable bulk file, so the team's very first hours should go into either finding an underlying JSON endpoint or standing up a scraper — solve that early and the rest (ML flags, graph, dashboard) is well within reach; fail to solve it and the whole build stalls. Recommend proceeding, budget the first 4-6 hours explicitly for data acquisition, and pitch outputs as explainable "risk flags for human review" rather than as proven fraud detection to stay credible with judges who know the domain.

## Full summary (from official portal + reassessment)
Verified via the official "SIH 2026 – Software & Hardware Problem Statements" master PDF catalogue (sih.gov.in content mirrored at sih-2026-problem-statements.shaikrohit187.workers.dev/public/pdfs/SIH_2026_All_PS.pdf; the live sih.gov.in/sih2026PS page only render-paginates the first ~25 PS via WebFetch, so the full catalogue PDF was used as the authoritative source). PS 26102, Org: MoSPI / Department: Data Informatics & Innovation Division (DIID), Category: Software, Theme: Miscellaneous. Dataset link given in the official listing: https://mplads.mospi.gov.in/digigov/dashboard.html (confirmed live — a public, no-login dashboard showing aggregate works-recommended/sanctioned/completed rupee figures with search filters by tenure, state, constituency and MP name; no bulk CSV/API is advertised, and online-recommendation data only goes back to April 2023, so historical depth is limited). No "Technology Stack" field was listed for this PS. Official text (verbatim): BACKGROUND — "MPLADS is a Central Sector Scheme under which Hon'ble Members of Parliament recommend developmental works for creation of durable community assets and provision of basic civic amenities. The Scheme involves large-scale fund utilization and execution of thousands of works across the country through multiple implementing agencies and administrative authorities. Given the volume and complexity of financial and project-related data generated under the Scheme, there is a need for an AI-powered solution that can leverage machine learning and advanced analytics to detect trends and anomalies in expenditure patterns, fund utilization, cost estimates, and work execution, thereby enabling early identification of potential fraud, inefficiencies, and non-compliance while enhancing transparency, accountability, and effective monitoring of MPLADS works." DESCRIPTION — "Develop an AI-powered monitoring and analytics platform for MPLADS that leverages ML, AI, and advanced data analytics to identify trend, anomalies, irregularities, and potential fraud in fund utilization and project execution. The solution should analyze data relating to sanctions, expenditures, cost estimates, work progress, payments, and asset creation to detect unusual patterns, cost overruns, duplicate works, delayed projects, and deviations from established norms. The system should generate risk-based alerts, predictive insights, and decision-support dashboards for Members of Parliament, State Nodal Authorities, District Authorities, and the Ministry. The platform should also facilitate automated compliance monitoring, trend analysis, and early warning mechanisms..." EXPECTED SOLUTION — "...an AI-powered platform that helps monitor MPLADS works and fund utilization... By analyzing data related to project approvals, expenditures, payments, work progress, and completion status, the system should be able to identify unusual patterns, delays, cost overruns, duplicate works, and potential cases of misuse of funds. It should automatically generate alerts and highlight high-risk cases... provide easy-to-understand dashboards and insights to MPs, State Nodal Authorities, District Authorities, and the Ministry, enabling them to make informed decisions and take timely corrective action." No supervised "fraud" ground-truth labels exist anywhere in this description or the public portal — the ask is unsupervised/heuristic anomaly and outlier detection framed as "risk flags," not confirmed-fraud classification.

## Realistic MVP scope (36hr build)
- ETL/scraper pipeline pulling sanctioned-works, expenditure, and completion-status records from the public MPLADS dashboard (or its underlying XHR/JSON calls if discoverable) by state/constituency/MP, normalized into a Postgres/DuckDB table
- Unsupervised anomaly-detection engine (Isolation Forest / Local Outlier Factor / peer-group z-scores) flagging cost-per-work outliers, stalled works (sanctioned-but-not-executed beyond a threshold), and expenditure-vs-utilization mismatches
- Fund-flow / relationship graph (NetworkX + graph viz) linking MPs, implementing agencies, and vendors/contractors to surface concentration patterns and possible duplicate-work clusters
- Composite risk-scoring leaderboard ranking constituencies/agencies by combined anomaly signals, each with an explainable 'why flagged' feature breakdown
- Interactive web dashboard (filterable by state/MP/year) with a state-wise choropleth risk map, drill-down to individual flagged work records, and trend charts
- Optional stretch: LLM-generated plain-language explanation of each flagged anomaly for non-technical officials, and a mocked 'auto-alert to nodal authority' notification to demo the decision-support loop

## Suggested tech stack
- Frontend: React/Next.js + Tailwind + shadcn/ui
- Mapping/Charts: Leaflet or Mapbox GL for state/constituency choropleth, Recharts/Nivo for trend charts
- Backend/API: FastAPI (Python) to keep ML and API in one language
- ML/Analytics: pandas + scikit-learn (Isolation Forest, LOF, DBSCAN) or PyOD for ensemble anomaly detection, NetworkX for fund-flow graph construction, statsmodels/Prophet for time-series trend flags
- Data ingestion: Python requests/BeautifulSoup or Playwright (headless) to scrape/paginate the MPLADS dashboard given the lack of a public bulk API
- Storage: Postgres (Supabase/Railway) or DuckDB for a lightweight local-first analytics store
- LLM layer (optional): OpenAI/Anthropic API for natural-language 'why this was flagged' explanations
- Deployment: Vercel (frontend) + Render/Railway (backend+DB), containerized with Docker for the demo

## Risks
- Data-access friction (HIGH): the official dataset link is a JS-rendered, no-login dashboard with search filters, not a bulk CSV/API — the team must reverse-engineer an underlying JSON endpoint or build a scraper under time pressure, and even then online-recommendation data only covers post-April-2023, capping the trend-analysis story and Rajya Sabha coverage similarly limited
- No labeled fraud ground truth (MEDIUM): the ask is inherently unsupervised/heuristic anomaly detection, not classification against real confirmed-fraud cases, so the team must carefully frame outputs as 'risk flags' rather than 'detected fraud' — conflating the two in the pitch will read as naive to any domain-aware judge, since a genuinely expensive project in a remote/hilly constituency can look like a false-positive cost outlier
- Oversaturation and generic-solution risk (MEDIUM): 'anomaly-detection dashboard on a government fund-utilization dataset' is one of the most common SIH software archetypes: many competing teams will submit a similar Isolation-Forest-plus-dashboard build, so differentiation requires visible extra effort (a working live scraper on real current data, the fund-flow network-graph angle, or clear explainability) rather than a purely templated outlier-flag demo

---
Back to [[Shortlist]] · [[Final Recommendation]] · [[00 Dashboard|Dashboard]]
