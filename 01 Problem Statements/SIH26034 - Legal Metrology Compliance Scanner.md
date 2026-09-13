---
tags: [sih2026, problem-statement]
ps: SIH26034
org: Ministry of Consumer Affairs, Food & Public Distribution
theme: Agriculture, FoodTech & Rural Development
refined_score: 8
---

# SIH26034 — Software System to check compliance of Packaged Commodities under Legal Metrology(Packaged Commodities) Rules, 2011 by scanning products, images and labels.

**Organization:** Ministry of Consumer Affairs, Food & Public Distribution
**Theme:** Agriculture, FoodTech & Rural Development · **Category:** Software
**First-pass scores:** impact 7/10, feasibility 9/10, differentiation 8/10, overall 8/10
**Refined score (after reading official description):** 8/10
**Official description found on sih.gov.in:** True

## Verdict
Strong pick. The full official text confirms rather than undermines the title-only read: this is a bounded, software-only OCR-plus-rules-engine problem against a fixed, publicly available legal checklist, with zero dependency on hardware, lab equipment, or restricted data — well within a web/AI/cloud team's skill set and buildable as a convincing demo in 36 hours. The score doesn't move higher than 8 because two real risks survive the deep-dive: the label-only "dataset" means the team must manually curate its own demo images, and the mandated font-size/readability check is only approximable from a photo without a physical scale reference, so the team must be disciplined about scoping and honest about that limitation with judges. Combined with the fact that "scan a label, run OCR, flag violations" is a familiar hackathon shape that many other teams may also reach for, the differentiator should be the specific depth of the Legal Metrology checklist, a polished enforcement dashboard, and ideally an e-commerce-listing-scan angle (the background text explicitly calls out e-commerce platforms) rather than the base OCR pipeline itself.

## Full summary (from official portal + reassessment)
sih.gov.in itself returned a 403/blocked both WebFetch and the browser tool (Azure App Gateway blocked automated access), and the page is a client-rendered SPA that doesn't expose full PS text to a scraping fetch anyway. I recovered the verbatim official listing from a mirrored copy of the official "SIH 2026 - Software & Hardware Problem Statements" catalogue (a 342-page compiled PDF of all 226 PS, hosted at a third-party mirror), cross-checked the PS number, exact title wording, organization, and theme against the prompt — all match exactly, so I'm confident this is the real DoCA text, not a paraphrase.

Full official text (verbatim, condensed for space):
BACKGROUND: Packaged commodities sold via retail, supermarkets and e-commerce must bear mandatory declarations under the Legal Metrology Act 2009 and LM(PC) Rules 2011 — manufacturer/packer/importer name & address, net quantity, MRP, month/year of manufacture, consumer care details, etc. Manual inspection by enforcement agencies is time-consuming given product volume/variety; missing declarations, wrong font sizes, and improper MRP declarations are common. Scope exists for a system that scans labels/package images/listings to flag violations.
DESCRIPTION: App must scan label/product images, detect mandatory declarations, check correctness/completeness/placement, check readability & font-size requirements, flag missing/non-compliant declarations, generate compliance reports, maintain a scan repository, and give enforcement dashboards.
EXPECTED SOLUTION: web and/or mobile app; automated extraction+validation of declarations; rule-based checking against LM(PC) Rules 2011; PDF/editable compliance reports; monitoring dashboard; search/retrieval of past scans; technical/architecture documentation.
KEY FUNCTIONAL REQUIREMENTS: image upload/scan; declaration extraction+detection; font-size/readability analysis; detection of missing/misleading/non-standard declarations; report generation; photo evidence attachment; scan/inspection repository; role-based auth; compliance dashboard; PDF/editable export.
DATASET LINK given is NOT a labeled image dataset — it's just links to the Legal Metrology Act page and the Rules text itself (consumeraffairs.gov.in). No official "Technology Stack" field was listed for this PS (unlike some other PS entries in the catalogue).

This confirms and sharpens the title-only read: it is a clean, self-contained CV/OCR + rules-engine + dashboard problem. Nothing in the full text implies hardware, lab equipment, or restricted/classified data — the "dataset" is literally public statute text, and product label photos are trivially self-sourceable (any packaged good on a store shelf or at home). The one genuinely hard sub-requirement is font-size/readability compliance, since the Rules specify minimum print height in millimetres relative to package size — that requires physical-scale calibration that a bare photo doesn't give you, so an honest team must scope this down to an approximate/relative check rather than a legally certifying measurement.

## Realistic MVP scope (36hr build)
- Web app (mobile-responsive/PWA) letting a user upload or capture a photo of a packaged product's label
- OCR + layout extraction pipeline (cloud OCR API or open-source OCR, or a vision-LLM prompt) that pulls out text blocks with bounding boxes from the label image
- Rule engine that checks presence/format of a fixed subset of mandatory declarations: manufacturer name & address, net quantity + unit, MRP (with 'inclusive of taxes' wording), month/year of manufacture, consumer-care contact details
- Approximate font-size/readability heuristic (relative text-height-to-image or to a package-edge/reference-object calibration) clearly labeled as indicative, not a certified measurement
- Auto-generated compliance report (pass/fail per rule, violation summary, confidence notes) exportable as PDF, plus a searchable repository of past scans
- Enforcement-official dashboard with role-based login showing scan history, flagged violations, and basic filters/search

## Suggested tech stack
- Frontend: React/Next.js web app (responsive/PWA) with camera/file-upload capture
- OCR/Vision: Google Cloud Vision API or AWS Textract for fast reliable text+bbox extraction (fallback: PaddleOCR/Tesseract/EasyOCR for an offline path); optionally a multimodal LLM (GPT-4V/Gemini/Claude vision) for direct field extraction to save engineering time
- Backend: Python FastAPI (or Node/Express) hosting the rule-engine/validation logic and REST APIs
- Rule engine: Python regex + simple NER/keyword matching mapped to a hardcoded LM(PC) Rules 2011 checklist
- Database: PostgreSQL or Firebase Firestore for scan records and violation history
- Storage: S3-compatible bucket or Firebase Storage for uploaded label images
- Auth: Firebase Auth or JWT-based role-based access (consumer vs enforcement officer)
- Reporting: pdfkit/reportlab/jsPDF for compliance-report generation and export
- Deployment: Vercel/Netlify (frontend) + Render/Railway (backend), Dockerized for portability during demo

## Risks
- No labeled training/eval dataset is provided — the official 'Dataset Link' is just the statute text, not sample label images or ground-truth violations, so the team must self-collect and hand-annotate a small demo set, which may look thin under judge scrutiny about real-world scale/generalization
- Legally-precise font-size/mm compliance checking is not reliably derivable from an arbitrary photo without a physical size reference, so this requirement can only be approximated (relative sizing or an in-frame reference object/coin) — must be scoped down and explicitly caveated rather than oversold as a certifying check
- High oversaturation risk: 'photograph a label -> OCR -> rule-check -> report' is a very common hackathon/product pattern (nutrition-label scanners, invoice/KYC scanners, etc.), so many competing SIH teams will likely pitch visually similar demos — differentiation has to come from checklist depth, e-commerce-listing support (scanning a product page URL, not just a physical photo), and enforcement-dashboard UX rather than the base OCR idea

---
Back to [[Shortlist]] · [[Final Recommendation]] · [[00 Dashboard|Dashboard]]
