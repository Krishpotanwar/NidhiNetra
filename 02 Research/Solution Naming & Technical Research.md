---
tags: [sih2026, research, naming]
ps: SIH26102
---

# Solution Naming & Supporting Technical Research
*Compiled 2026-08-26 for same-day solution-name submission.*

## 🏆 Recommended name: **NidhiNetra**

**नीधि नेत्र — "The Fund's Eye" / "Eye on the Fund"**

- **Nidhi** (निधि) = fund / treasure / deposit — the exact word used for pooled government funds in Indian legal and financial usage (it's literally the term behind "Nidhi Company," an RBI-recognized deposit-taking NBFC category, so the word already carries a real "public money" connotation for Indian judges).
- **Netra** (नेत्र) = eye — stands in for the AI's continuous, automated "watching" of expenditure data (anomaly detection = machine vision over money, not text).
- Reads naturally as one word, is easy to say out loud in a pitch, and the literal translation ("Eye on the Fund") doubles as your one-line tagline without needing a separate slogan.
- **Trademark/collision check:** searched web-wide — no existing company, app, or government portal uses this name. The only hits are coincidental people named "Nidhi Netra" (a private individual), which is not a conflict.

**Suggested tagline:** *"NidhiNetra — an AI eye on every rupee MPLADS spends."*

### Why this beats the obvious alternatives
Government-tech naming in India leans hard on a small set of words — I checked the most likely candidates before landing here, specifically to avoid submitting a name that reads as derivative to judges who've seen a hundred SIH decks:

| Candidate | Verdict | Reason |
|---|---|---|
| Rakshak / Raksha-anything | ❌ Avoid | Heavily saturated — RakshaLink (UPI scam app), RakshaAI (scam detector), Rakshak Subidha (security firm) all already exist and are fraud/security products specifically |
| Chakshu | ❌ Avoid | Already the real, live name of DoT's Sanchar Saathi citizen fraud-reporting facility — direct collision with a well-known government product |
| NirikshaAI | ❌ Avoid | Already a live company (niriksha.ai, an AI observability platform) and a second "Nirikshan AI" also exists — real trademark collision risk |
| Prahari | ⚠️ Risky | Used by multiple small government apps already (Bankura Police's citizen-safety "Prahari" app, Karnataka's "e-Prahari," and — most awkwardly — UP PWD's "Prahari (Bid Evaluation)" module for public-works bidding, which is uncomfortably close to our own works/expenditure domain) |
| Setu / Drishti | ❌ Avoid | Generically overused across Indian gov-tech (Aarogya Setu, and "Drishti" is a common name for CCTV/vision-analytics startups) — won't read as distinctive |
| FundGuard / GraphGuard (plain English) | ✅ Safe fallback | Clean, zero collision, but generic-sounding next to a room of "XGuard"/"XShield" hackathon names |

## Backup names (in order of preference)
1. **VigilKosh** (Vigilance + Kosh/treasury) — zero collisions found, strong "vigilance" framing that mirrors India's actual Central Vigilance Commission language.
2. **KoshNetra** (Treasury + Eye) — same "Netra" logic as the primary pick, swaps Nidhi for Kosh; use if you want the fund-flow-graph angle to feel more "central treasury oversight" than "MP-level fund" oversight.
3. **AarthikNetra** (Economic/Financial + Eye) — broader, more formal-sounding, good if you want a name that could scale beyond MPLADS in the pitch's "future scope" slide.
4. **FundGuard AI** — plain-English fallback if the team prefers a fully international-sounding name for the submission form.

## Official problem statement — verified text (for reference)
Confirmed against the SIH 2026 master PDF catalogue and sih.gov.in. Org: **MoSPI**, Dept: Data Informatics & Innovation Division (DIID). Category: Software. Full background/description/expected-solution text is already captured in [[SIH26102 - MPLADS Anomaly Detection]] — not repeated here.

## MPLADS data source — what's actually available (critical for Day 1)
- Public dashboard: **mplads.mospi.gov.in/digigov/dashboard.html** (the "MPLADS-Dashboard") — public, no login, aggregate works-recommended/sanctioned/completed figures, filterable by tenure/state/constituency/MP.
- The dashboard sits on top of the **MPLADS–eSAKSHI** portal (live since 1 April 2023), which is the actual system-of-record: MPs recommend works and earmark funds → District Authorities sanction works and assign Implementing Agencies → Implementing Agencies raise vendor payment requests and **upload photographs + sanction-order documents at each payment stage**. Data updates in real time as each stakeholder logs in and acts. ([PIB press release](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2235932&reg=3&lang=2), [Vikaspedia](https://en.vikaspedia.in/viewcontent/e-governance/online-citizen-services/mplads%E2%80%93esakshi-web-portal))
- No public bulk CSV/API was found or advertised anywhere (PIB, Vikaspedia, IASPoint, or the portal itself) — confirms the earlier risk assessment: **budget hours 1–6 for scraping/XHR discovery**, not for waiting on an official data dump.
- **Prior art worth citing in the deck:** [Empowered Indian](https://empoweredindian.in/mplads) already runs a public MPLADS visualization dashboard from government data — worth a quick look before the build starts, since if they've solved the data-access problem, their approach (or even their dataset) could shortcut your Day-1 risk. Also worth a name-check as an existing "MPLADS transparency" player so your pitch can explicitly say how you go further (anomaly detection + fund-flow graph vs. their plain visualization).
- **Accountability Initiative's PAISA** methodology (India's largest citizen fund-tracking framework, spanning education/health/panchayat spending) is good precedent to cite for "why fund-flow tracking matters" — not a direct data source for MPLADS, but strong credibility backing for the problem framing.

## Precedent: AI-for-fraud is already a proven Indian government playbook
Strong slide material — this is not a speculative approach, it's the same method already deployed at scale by other Indian government bodies, which pre-empts the "will this actually work / has anyone tried this" judge question:

- **ADVAIT** (CBIC) and **BIFA** (DGGI) — both operational AI/analytics platforms already used to detect anomalies, fraud patterns, and circular trading in GST filings.
- **GSTN AI risk profiling** — builds supplier/buyer/intermediary relationship graphs to catch fake-invoice networks and shell entities; in FY2024-25 alone this flagged **10,700+ fake GSTIN registrations** and blocked **₹36,000+ crore** in bogus input-tax-credit claims. This is the single best real-number citation for a "fund-flow graph catches what row-level checks miss" slide, and it directly validates your MP↔agency↔vendor graph approach.
- **CBDT (Income Tax)** — builds a full transactional graph per taxpayer and runs anomaly detection across seven distinct data layers, generating a risk score per case rather than a binary fraud/no-fraud label — exactly the "risk flags for human review" framing already locked in for this pitch (see [[SIH26102 - MPLADS Anomaly Detection]]).

Use these three as a single slide: *"India's government already runs this exact playbook (GST, Income Tax) — MPLADS is the next scheme that needs it, and no one has built it yet."*

## Sources
- [PIB: Revamped public dashboard of MPLADS eSAKSHI portal](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2235932&reg=3&lang=2)
- [Vikaspedia: MPLADS–eSAKSHI web portal](https://en.vikaspedia.in/viewcontent/e-governance/online-citizen-services/mplads%E2%80%93esakshi-web-portal)
- [MPLADS Dashboard (live)](https://mplads.mospi.gov.in/digigov/dashboard.html)
- [Empowered Indian — MPLADS Dashboard](https://empoweredindian.in/mplads)
- [Accountability Initiative — PAISA](https://accountabilityindia.in/toolkits/)
- [Sanchar Saathi — Chakshu facility](https://sancharsaathi.gov.in/sfc/)
- [TaxGuru: AI in GST Administration — Risk Assessment & Fraud Control](https://taxguru.in/goods-and-service-tax/artificial-intelligence-gst-administration-enhancing-risk-assessment-frauds-control.html)
- [Business Standard: CBDT using AI tools to boost income-tax compliance](https://www.business-standard.com/economy/news/cbdt-ai-tools-boost-income-tax-compliance-nudge-ravi-agrawal-125072400520_1.html)
- [Apna Okaca: How India's Income Tax Dept uses AI to monitor high-value transactions](https://www.apnokaca.com/posts/how-india-s-income-tax-dept-uses-ai-to-monitor-high-value-transactions)

---
Back to [[SIH26102 - MPLADS Anomaly Detection]] · [[Final Recommendation]] · [[00 Dashboard|Dashboard]] · next: [[03 Build Plan/Build Plan|Build Plan]]
