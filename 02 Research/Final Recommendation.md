---
tags: [sih2026, research, recommendation]
---

# Final Recommendation

Analysis: all 172 Software-category PS scored against team fit (web/app + AI/ML + cloud, no hardware, govt/social impact prioritized), top 14 deep-dived against their **verified official sih.gov.in descriptions**. Full ranking: [[Shortlist]].

## 🏆 Pick: [[SIH26102 - MPLADS Anomaly Detection|SIH26102 — AI-powered anomaly/fraud/inefficiency detection for MPLAD Scheme]]

**Organization:** MoSPI · **Refined score: 8/10** · **Impact: 9/10 — the single highest impact score of all 172 software PS**

### Why this one
- **Impact is the whole point, and it's real.** MPLADS (Members of Parliament Local Area Development Scheme) funds thousands of local infrastructure works — roads, schools, drinking water — every year. A working anomaly-flagging system is a genuine anti-corruption/governance-accountability tool, not a toy demo. It scored higher on impact than every other one of the 172 software problem statements, including the disaster-management and healthcare ones.
- **It's fully in your team's lane.** No hardware, no classified data, no domain science you don't have. It's ETL + unsupervised anomaly detection (Isolation Forest / peer-group z-scores) + a fund-flow relationship graph + a dashboard — squarely web/AI/cloud.
- **The data is genuinely public** (MPLADS dashboards are published by the government), which is what makes this rare: high impact *and* buildable, not one or the other.
- **It has a real differentiator.** Most teams building "anomaly detection on government data" stop at an outlier table. The fund-flow graph (MPs ↔ implementing agencies ↔ vendors) linking duplicate-work and concentration patterns is a genuinely more sophisticated, more visual angle than a flat dashboard — good for judges.

### The one thing to solve on day one
The official "dataset" is a JS-rendered searchable dashboard, not a downloadable file. **Budget the first 4–6 hours** to either find the underlying JSON endpoint or stand up a scraper — everything else (the ML, the graph, the UI) is comfortably within reach once you have data flowing. This is a solvable, known risk, not a surprise blocker.

### How to pitch it (important)
Frame outputs as **"risk flags for human review,"** not "detected fraud." There's no labeled fraud ground-truth to train against — the model surfaces statistical outliers (cost-per-work spikes, stalled works, expenditure/utilization mismatches), and a domain-aware judge will respect that framing far more than an overclaimed "we detect corruption" pitch.

Full build-out — MVP feature list, tech stack, and complete risk breakdown — in [[SIH26102 - MPLADS Anomaly Detection]].

---

## Runner-up: [[SIH26001 - AI Landslide Early Warning NER|SIH26001 — AI-Based Landslide Early Warning, North Eastern Region]]

**Organization:** MDoNER · **Refined score: 7/10** · **Impact: 8/10**

If you'd rather pitch **life-safety/disaster relief** than **governance/anti-corruption**, this is the strongest alternative. Real ministry ask, clear vulnerable beneficiary (NER hill communities), fully buildable from public data (Bhuvan DEM, GSI/NASA landslide catalogs, IMD/Open-Meteo rainfall) with a susceptibility-map + rainfall-risk-scoring + citizen-reporting build. The catch: this exact catalogue has *many* other disaster/landslide problem statements, so you're guaranteed company — differentiation has to come from a genuinely defensible risk-scoring methodology and a standout presentation, not just another heatmap-and-alerts clone. Details: [[SIH26001 - AI Landslide Early Warning NER]].

## Lower-risk alternative: [[SIH26034 - Legal Metrology Compliance Scanner|SIH26034 — Packaged Commodities Legal Metrology Compliance Scanner]]

**Organization:** Ministry of Consumer Affairs · **Refined score: 8/10**

If you want to minimize execution risk over maximizing impact ceiling: this is a tightly bounded OCR + rules-engine problem against a fixed legal checklist. No data-acquisition risk (you curate your own demo images), no domain-science gap, no sponsor tooling to hedge against. The impact story is real but narrower — consumer protection against mislabeled/short-weighted packaged goods — rather than the national-scale governance story of SIH26102. Details: [[SIH26034 - Legal Metrology Compliance Scanner]].

## High-impact but higher-risk options (bench, not first choice)

- **[[SIH26042 - Vernacular AI Education Jharkhand|SIH26042]]** — tribal-language (mother-tongue) primary education tool tied to a real, active state programme (5,000+ schools). Genuinely compelling social-equity story, but the full spec demands real Ho/Mundari/Santhali voice NLP and full offline operation on low-RAM devices — infrastructure that barely exists yet. Only pursue if you commit to descoping to a single language (Santhali) and pitch it honestly as a proof-of-concept.
- **[[SIH26038 - Diabetic Retinopathy Screening|SIH26038]]** — rural health screening with real preventable-blindness impact and abundant public datasets. The catch: it's sponsored by MathWorks and the official spec explicitly asks for a MATLAB/Simulink pipeline. A pure web/Python/cloud team risks being marked down by sponsor judges for stack mismatch unless you budget time for a token MATLAB/ONNX bridge.

## Bottom line
**Go with SIH26102.** It's the only problem statement in the entire software list where the impact ceiling and the feasibility floor are both this high at the same time — which is exactly what "best chance of winning while prioritizing real impact" means in practice. Keep SIH26001 as your backup pitch if the team feels more compelling building disaster-relief tech than governance tech.

See [[00 Dashboard|Dashboard]] · [[Shortlist]] · next: [[03 Build Plan/Build Plan|Build Plan]]
