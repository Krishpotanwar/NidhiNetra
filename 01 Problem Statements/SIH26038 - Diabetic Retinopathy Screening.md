---
tags: [sih2026, problem-statement]
ps: SIH26038
org: MathWorks
theme: Clean & Green Technology
refined_score: 7
---

# SIH26038 — Explainable AI for Diabetic Retinopathy Screening in Rural India

**Organization:** MathWorks
**Theme:** Clean & Green Technology · **Category:** Software
**First-pass scores:** impact 8/10, feasibility 9/10, differentiation 7/10, overall 8/10
**Refined score (after reading official description):** 7/10
**Official description found on sih.gov.in:** True

## Verdict
Still a reasonable pick, but meaningfully more constrained than the title-only score suggested: the problem is genuinely software-only (public datasets — APTOS, IDRiD, DRIVE, Messidor-2 — no hardware, no lab equipment, no classified data) and the rural-healthcare-access impact story is real and judge-legible, so it clears the team's hard gates. What the full spec adds, though, is (a) an explicit MATLAB/Simulink toolchain from the sponsor that a pure web/Python/cloud team must actively work around (e.g., via an ONNX-to-MATLAB bridge demo) to avoid looking stack-noncompliant to MathWorks judges, and (b) a clinical-grade scope — multi-lesion segmentation, hard sensitivity/specificity thresholds, and a separate Simulink resource-planning model — that is considerably larger than a standard 'DR classifier + Grad-CAM' hackathon build and demands hard, clearly-communicated descoping. Combined with DR screening being one of the most oversaturated ML demo problems around, this pulls the refined score down from the naive 8 to a 7: worth pursuing only if the team commits early to descoping honestly, leans on the rural-deployment/workflow angle for differentiation, and is willing to spend a few hours on a token MATLAB/Simulink component to hedge the sponsor-fit risk.

## Full summary (from official portal + reassessment)
Verified official listing on sih.gov.in/sih2026PS (row 38, PS ID 26038, Category: Software, Deadline: 20 September 2026). Full verbatim sections retrieved directly from the live portal record:

BACKGROUND: "India has over 77 million diabetic adults - the second highest globally. Diabetic Retinopathy (DR) affects ~18% of this population and is a leading cause of preventable blindness. Early screening can prevent 90% of vision loss, but India has only ~1 ophthalmologist per 100,000 rural population, making mass manual screening infeasible. Existing AI solutions function as black boxes, lack clinical validation rigor, and fail with variable image quality from portable fundus cameras in field conditions."

DESCRIPTION: Explicitly framed as "Design a MATLAB-based retinal image analysis pipeline" with 5 required components: (1) Image Quality Assessment/Enhancement (CLAHE, illumination normalization, denoising, reject/recapture logic), (2) Retinal Structure Segmentation (optic disc/fovea, vessels, microaneurysms, exudates, hemorrhages, neovascularization), (3) DR Severity Grading on the International Clinical DR scale (0-4) with required >90% sensitivity / >85% specificity for referable DR, (4) Explainability Module (Grad-CAM, lesion-level evidence, calibrated confidence, <30s ophthalmologist validation), (5) Simulink Workflow Simulation modeling the telemedicine pipeline (acquisition rates, bandwidth, throughput, review capacity) for district programs serving 100,000+ patients/year. Named "Tools": Image Processing Toolbox, Computer Vision Toolbox, Deep Learning Toolbox, Medical Imaging Toolbox, Simulink, Statistics and Machine Learning Toolbox — i.e., an entirely MATLAB/Simulink toolchain.

EXPECTED SOLUTION: "A working prototype demonstrating: DR classification with >90% sensitivity and >85% specificity for referable DR; explainable Grad-CAM outputs rated as clinically useful; a Simulink model optimizing screening resource allocation; and validation against published benchmarks showing the integrated pipeline outperforms any single technique approach."

DATASET LINKS provided officially: APTOS 2019 (Kaggle), IDRiD (IEEE DataPort, includes lesion segmentation masks), DRIVE (vessel extraction), Messidor-2 — confirming public data access, no lab/hardware/classified data needed.

REASSESSMENT: The full scope does NOT need hardware, lab equipment, or classified data — everything sits on public datasets and is software-only, so it clears the team's hard constraints. But it is meaningfully harder and more domain-heavy than the title suggested: it demands multi-structure clinical-grade segmentation (not just classification), sub-pixel microaneurysm detection, hard sensitivity/specificity thresholds, AND a separate Simulink systems-simulation deliverable — roughly 3-4x the scope of a typical "photo in, grade out" DR hackathon demo. The single biggest hidden factor invisible from the title: this PS is sponsored and toolchain-specified entirely by MathWorks, whose evaluators will likely expect at least partial MATLAB/Simulink usage (Deep Learning Toolbox does support importing ONNX models, so a team could train in PyTorch and bridge into MATLAB for the demo, but this is real extra scope/risk for a team with no stated MATLAB experience). DR classification from fundus images is also one of the most oversaturated ML/Kaggle problems in existence, so judges will have seen many similar demos; differentiation must come from the rural-deployment/UX/workflow layer, not the model itself.

## Realistic MVP scope (36hr build)
- Fundus image quality gate: OpenCV-based blur/illumination/field-of-view check with CLAHE enhancement for borderline images and a reject-with-recapture-feedback message for ungradeable photos
- DR severity classifier (0-4 ICDR scale) via transfer learning (EfficientNet/ResNet/Inception) fine-tuned on combined APTOS + IDRiD, reporting sensitivity/specificity on a held-out split (aim close to, not necessarily hitting, the >90%/>85% bar)
- Grad-CAM explainability overlay on the fundus image plus a calibrated confidence score, so a health worker sees WHY the model flagged a case
- Lightweight lesion-highlighting layer using IDRiD's segmentation-annotated lesions (microaneurysms/hemorrhages/exudates) via a simple U-Net or classical thresholding, framed as supporting visual evidence rather than clinically validated full segmentation
- Health-worker-facing web app (or PWA/Flutter) for capture/upload, showing grade + heatmap + referral recommendation (auto-refer for Level 2+) and a per-patient case history log
- Cloud backend (FastAPI) serving the model plus a simple PHC/ASHA-worker dashboard substituting for the Simulink ask — e.g., a screening-throughput vs. referral-load chart — explicitly called out in the pitch as a software-equivalent stand-in for the full Simulink resource-planning model

## Suggested tech stack
- Python + PyTorch or TensorFlow/Keras for transfer-learning DR classifier (EfficientNet-B0/ResNet50)
- OpenCV for preprocessing (CLAHE, blur/illumination quality checks)
- pytorch-grad-cam or tf-keras-vis for the explainability heatmaps
- Optional: export trained model to ONNX and demo a short MATLAB Deep Learning Toolbox import + Image Processing Toolbox preprocessing snippet (MATLAB Online is free) to partially satisfy the MathWorks tool expectation without building the whole pipeline in MATLAB
- FastAPI (or Node/Express) backend serving inference + case-record APIs
- PostgreSQL or Firebase Firestore for patient/case records; S3/GCS/Firebase Storage for images
- React (web) or Flutter/React Native (mobile-first, low-bandwidth-tolerant) frontend for the health-worker app
- Docker + free-tier cloud deploy (Render/Railway/GCP/AWS); JWT auth for health workers

## Risks
- Sponsor tool-stack mismatch: the PS is written entirely around MathWorks' own toolboxes (Image Processing, Computer Vision, Deep Learning, Medical Imaging, Simulink) and explicitly asks for a 'MATLAB-based' pipeline plus a Simulink workflow model — a web/Python/cloud-only team risks being marked down by MathWorks judges for stack non-compliance unless they budget hours for at least a partial MATLAB/Simulink bridge demo, which is real added scope with no guaranteed payoff
- Scope inflation beyond a 36-hour build: the Expected Solution bar is clinical-grade — multi-lesion segmentation (vessels, microaneurysms, exudates, hemorrhages, neovascularization) at near sub-pixel accuracy, hard >90%/>85% sensitivity/specificity thresholds, calibrated confidence, AND a separate systems-simulation deliverable — roughly 3-4x a typical 'photo-in, grade-out' hackathon demo, so the team must aggressively descope and be explicit in the pitch about MVP vs. full ministry ask or risk looking like they missed most of the brief
- Oversaturation and judge fatigue: DR screening from fundus images (especially on APTOS/IDRiD) is one of the most repeated ML/Kaggle/hackathon problems anywhere, so dozens of past teams and judges will have seen near-identical 'CNN + Grad-CAM' demos; differentiation has to come from the rural-deployment/health-worker-workflow/referral-triage layer rather than the classifier itself, and a merely competent model will read as a dataset resubmission

---
Back to [[Shortlist]] · [[Final Recommendation]] · [[00 Dashboard|Dashboard]]
