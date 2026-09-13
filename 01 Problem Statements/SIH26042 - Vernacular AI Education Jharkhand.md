---
tags: [sih2026, problem-statement]
ps: SIH26042
org: Governmcnt of Jharkhand
theme: Smart Education
refined_score: 6.5
---

# SIH26042 — Al-Powered Vernacular Pedagogy and Real-Time Translation Tool for Mother Tongue-Based Primary Education

**Organization:** Governmcnt of Jharkhand
**Theme:** Smart Education · **Category:** Software
**First-pass scores:** impact 8/10, feasibility 8/10, differentiation 7/10, overall 8/10
**Refined score (after reading official description):** 6.5/10
**Official description found on sih.gov.in:** True

## Verdict
This is a genuinely high-impact pick — it targets a real, currently-active state programme (PALASH MTB-MLE) with a well-documented bottleneck and a concrete beneficiary count (5,000+ schools), and stays entirely within software/AI/mobile territory with no hardware or classified-data blockers. But the full spec is noticeably harder than the title suggested: it explicitly demands real tribal-language (Ho/Mundari/Santhali) translation, sub-3-second real-time voice dialogue, and fully offline operation on a 2GB-RAM Android tablet — a combination that is not realistically achievable end-to-end in 36 hours given how little digital NLP infrastructure exists for these languages. It's still a strong pick, but only if the team deliberately descopes to one language (Santhali), builds the curriculum/worksheet-generation and offline-content-caching pieces for real (these are honestly achievable and are where most of the demo-able value lives), and treats the live voice-to-voice + full on-device offline requirement as a clearly-labeled cloud-based proof-of-concept with a stated hardware-optimization roadmap rather than something to fake as fully compliant. Recommended: pick it, but plan the pitch and demo script around that honest scoping from day one.

## Full summary (from official portal + reassessment)
Found the full official listing on sih.gov.in (the site renders all 226 PS as hidden Bootstrap modals in one large HTML page — a plain WebFetch/markdown conversion truncates around PS26025, so I downloaded the raw HTML with curl and grepped for SIH26042 directly).

Background (verbatim, paraphrased for length): Jharkhand's PALASH Mother Tongue-Based Multilingual Education (MTB-MLE) programme has improved foundational literacy among tribal children, but scaling is bottlenecked by a shortage of teachers who speak Ho, Mundari, and Santhali — tribal languages with very limited digital NLP resources. Most teachers posted to tribal-area schools are Hindi-medium trained. Over 5,000 tribal-area primary schools are affected.

Description (the actual build spec, and this is where the title undersells the difficulty): build an AI-assisted translation + curriculum-generation suite so a Hindi-speaking teacher with zero tribal-language training can deliver MTB-MLE instruction in Ho, Mundari, or Santhali. Hard requirements stated explicitly: (1) an NLP engine that translates Hindi FLN curriculum content (lesson scripts, activity instructions, assessment prompts) into accurate TEXT and SYNTHESISED AUDIO in the target tribal language; (2) a real-time voice-to-voice translation feature for live classroom dialogue with latency not exceeding 3 seconds; (3) auto-generated bilingual worksheets and visual flashcards aligned to the NIPUN Bharat FLN outcomes framework; (4) the entire app must run fully OFFLINE on a ≤2GB RAM, Android 9+ tablet after one-time content sync, because target schools lack reliable internet.

Expected Solution: a working app demoing Hindi-to-tribal-language translation (minimum one tribal language is acceptable at prototype stage), sub-3-second real-time voice translation, auto-generated bilingual worksheets, and full offline operation on a low-end Android tablet — submitted with a demo video and GitHub repo.

Critical reassessment: the title-only first pass (8/8/8/7) was too optimistic on feasibility. Nothing here requires hardware fabrication, IoT, lab science, or classified data — it stays squarely in software/AI/mobile territory, so the team's skill set is technically in-scope. But the *literal* spec is materially harder than "orchestrate Bhashini/IndicTrans2": (a) Ho and Mundari are not scheduled languages and have essentially zero usable parallel corpora, ASR, or TTS voices anywhere, including Bhashini; Santhali is a scheduled language with a little more support but is still thin, and uses the Ol Chiki script, which most tooling and fonts don't handle well; (b) "real-time voice-to-voice, sub-3-second latency, fully offline, on a 2GB-RAM Android 9 device" is a genuine on-device ML engineering problem (chained ASR→MT→TTS, quantized, no cloud) that is very unlikely to be honestly achievable end-to-end in 36 hours for any of these three languages, let alone with production-quality translation; (c) since "minimum one tribal language" and full offline operation are both stated as the explicit bar for the expected solution, judges who've read the actual PS (not just the title) will notice if a team quietly demos on a laptop with cloud APIs and calls it done. The safe path is to be transparent: build a real but narrowly-scoped prototype (one language, curated vocabulary, cloud-based pipeline for the live demo) and present the offline/on-device path as a clearly-labeled next phase rather than something silently faked.

## Realistic MVP scope (36hr build)
- Pick Santhali only as the demo language (best-supported of the three; Ho/Mundari get only a stated roadmap slide, not a live demo) and build a Hindi→Santhali text translator scoped to FLN/NIPUN Bharat classroom vocabulary — use Bhashini API/IndicTrans2 where it covers Santhali, backstopped by a curated glossary + few-shot LLM translation for gaps, with the approximation clearly disclosed
- Curriculum-to-worksheet generator: ingest a sample Hindi FLN lesson and auto-generate a bilingual (Hindi+Santhali) worksheet and 3-5 visual flashcards mapped to NIPUN Bharat learning outcomes, via an LLM content pipeline — this is pure text/web work and is the most reliably buildable feature
- TTS narration of the generated worksheet/flashcard text in Hindi and (best-effort) Santhali using an available Indic TTS or a fallback voice, to make the classroom-audio angle demoable even if imperfect
- A scripted 'live' voice-to-voice demo: teacher speaks a pre-agreed Hindi classroom phrase, pipeline does ASR (Hindi) -> MT -> TTS (Santhali) via cloud APIs within a few seconds, framed honestly as 'cloud demo today, on-device roadmap next' rather than claiming true sub-3s offline compliance
- A simple Android/PWA app shell with local caching (SQLite/Room or IndexedDB) that lets a teacher download a day's worksheets, flashcards, and pre-rendered audio while online, then browse/use that cached content with zero connectivity — this genuinely satisfies 'offline access to content' without needing on-device live translation
- A lightweight teacher/admin web dashboard to upload Hindi lesson content, trigger generation, review/approve translated output before it reaches a device, and push it to the offline cache — gives judges a full-loop story from curriculum ingestion to classroom use

## Suggested tech stack
- Frontend teacher dashboard: React or Next.js (web) for content upload/review/approval
- Mobile/offline client: Flutter or a installable PWA with service-worker + IndexedDB (or native Android/Kotlin with Room DB) for the offline-cache demo on a low-end device
- Backend/orchestration: Python FastAPI (or Node/Express) coordinating the ASR->MT->TTS pipeline and content-generation jobs
- Translation: Bhashini API / AI4Bharat IndicTrans2 for Hindi<->Santhali where supported; an LLM (Claude/GPT/Gemini) with a curated Santhali glossary and few-shot prompting as a fallback/backstop for classroom-specific vocabulary
- ASR: Whisper (cloud or Whisper-tiny quantized on-device) for Hindi speech input
- TTS: AI4Bharat Indic-TTS or a cloud TTS provider for Hindi audio; best-effort/approximate synthesis for Santhali, clearly labeled as prototype quality
- Content generation: LLM-based pipeline (prompt templates keyed to NIPUN Bharat/FLN outcome tags) to produce bilingual worksheets and flashcard text/images
- Cloud/infra: Firebase or a small AWS/GCP setup for auth, content storage, and sync between the dashboard and the offline client
- Optional stretch: TensorFlow Lite / ONNX Runtime Mobile to show one real on-device quantized model (even a toy one) as proof-of-concept for the offline roadmap, without pretending the whole pipeline runs that way

## Risks
- Low-resource language wall: Ho and Mundari have essentially no usable NLP/ASR/TTS resources anywhere (not even Bhashini), and Santhali (Ol Chiki script) is only marginally better-supported — any live translation demo will be narrow/curated rather than general-purpose, and a judge or reviewer with any familiarity with these languages could immediately spot rough or wrong output
- Spec-vs-demo credibility gap: the official expected outcome explicitly requires real-time sub-3-second voice translation running fully offline on a 2GB-RAM Android 9 tablet — a genuinely hard on-device ML systems problem that is very unlikely to be honestly built in 36 hours; teams that quietly demo on a laptop with cloud APIs risk being called out by judges who've read the actual PS text, so the team must proactively frame the cloud demo as a staged roadmap rather than claim full compliance
- Pedagogical/translation validation risk: without access to a native Ho/Mundari/Santhali speaker or a linguist, the team cannot verify that generated translations and NIPUN-Bharat-aligned worksheets are actually correct or age-appropriate, risking an embarrassing on-stage translation error in front of an education-department jury

---
Back to [[Shortlist]] · [[Final Recommendation]] · [[00 Dashboard|Dashboard]]
