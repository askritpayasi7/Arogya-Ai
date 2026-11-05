# Project Progress & Context Log

> **Note for AI Assistants & Developers**: This document tracks the continuous development state of the Health App. Read this document before beginning any work, and update it immediately after completing your tasks.

---

## 1. Project Overview & Vision
- **Objective**: Build an evidence-based health and food safety advisory system grounded in peer-reviewed scientific research papers and official FSSAI (Food Safety and Standards Authority of India) standards.
- **Current Phase**: Phase 7 (Admin PDF Hunter Real-Time Streaming, Dynamic Embedding-Determined Clinical Cross-Correlations, Structured Advisory Feed & Vital Category Sidebar) - **COMPLETED & VERIFIED**.
- **Core Technology Stack**:
  - **Language**: Python 3.10+ (tested on Python 3.13)
  - **Web Framework & UI**: FastAPI, Starlette Sessions, Jinja2, Tailwind CSS (CDN), Chart.js (CDN), NDJSON Server-Sent Streaming (`StreamingResponse`)
  - **Google Cloud & Fitness Integration**: Google OAuth 2.0 Authorization Code Flow, Google Fitness REST API (`com.google.step_count.delta`, `com.google.heart_rate.bpm`, `com.google.sleep.segment`) with multi-stream reconciliation (`estimated_steps` + `merge_step_deltas`)
  - **Movement Explorer & Historical Batches**: 30-day batched historical ingestion up to 180 days with early termination, persistent server-side disk cache (`data/user_cache/`), dynamic timeframe selector (7D/30D/90D/180D), and scrollable Historical Movement Journal
  - **Biometric Advisory Engine**: Personalized clinical correlation linking user sleep, steps, and heart rate to verified scientific papers with DOI citations
  - **Admin Control Portal**: Protected management console displaying research paper registry, downloaded PDFs, verified relationship audit reports, and interactive 5-phase real-time PDF Hunter streaming console
  - **AI Relationship Extraction**: Gemini API via `google-genai` (`gemini-2.5-flash`), with deterministic rule-based fallback for offline/testing modes
  - **Clinical Verification Framework**:
    - **Phase 1: Article-Level Checks**: 7-tier study design classifier (RCT, Meta-Analysis, Prospective Cohort, Case-Control, Cross-Sectional, Preclinical, Narrative) & automated RoB 2 / ROBINS-I risk of bias assessment.
    - **Phase 2: Relationship-Level Checks**: Laptop-friendly Ollama NLI (`llama3.2:1b`) with local deterministic polarity fallback, and statistical metric validation (HR/OR/RR, 95% CI null crossing detection, directional consistency).
    - **Phase 3: Group Evidence Synthesis**: Adapted GRADE framework evaluating cross-study consistency and directional agreement across biological concept pairs.
    - **Phase 4: Non-linear Scoring & Gating**: Composite base score $B$, calibrated logarithmic penalty $\Delta = 8.5 \cdot \ln(1 + P)$, hard gates, and automated gating status (Accepted, Provisionally Supported, Quarantined, Excluded).
  - **Relationship Models**: Structured `HealthRelationship` and `VerificationReport` schemas capturing detailed claim, methodology, and statistical evidence.
  - **Research Retrieval**: Europe PMC REST API (direct `/api/getPdf` endpoint), Crossref Works API, arXiv API, and offline registry with 4-tier resilient failover
  - **Vector Database**: ChromaDB (persistent local store) with automatic resilient MockEmbedding fallback on offline/Ollama outage
  - **Embedding Providers**: Ollama (`nomic-embed-text`) + Token-hashed deterministic mock fallback for testing
  - **Testing**: Pytest (100% test pass rate across 86 unit tests)

---

## 2. Milestone Roadmap & Status

| Milestone | Description | Status |
|---|---|---|
| **M1: Governance & Rules** | Create `rules.md` and initial `progress.md` tracking system. | ✅ Completed |
| **M2: Project Scaffolding** | Configure `pyproject.toml`, `requirements.txt`, `.gitignore`, `.env.example`, `README.md`. | ✅ Completed |
| **M3: Vector DB & Ollama Embeddings** | ChromaDB store wrapper with Ollama embedding client + mock fallback. | ✅ Completed |
| **M4: Ingestion & Document Processing** | Loaders and chunkers for research papers and FSSAI regulations. | ✅ Completed |
| **M5: Retrieval & Synthesis Engine** | Grounded query engine with strict citation attribution. | ✅ Completed |
| **M6: Terminal Execution Script** | `python -m health_app.terminal_runner` with check, ingest, query, fetch, retry, and extract modes. | ✅ Completed |
| **M7: Automated Test Suite** | Full pytest coverage for rules, vector DB, chunking, retrieval, and fetcher. | ✅ Completed |
| **M8: Interactive Launcher & Research Paper Fetcher** | Terminal launcher (`start.cmd`/`start.cms`), interactive menu, open-access paper retrieval, and persistent deduplication index. | ✅ Completed |
| **M9: Downloader Resilience & Missing PDF Recovery** | Resilient retry adapter, mirror fallback, accurate disk verification, interactive download retry prompt, and `--retry-downloads` recovery tool. | ✅ Completed |
| **M10: Europe PMC 403 Fix & Native Curl Bypass** | Direct `api/getPdf` URL translation, full browser navigation headers, `curl.exe` fallback, and flexible retry prompt (`y` / `r`). | ✅ Completed |
| **M11: Gemini AI Relationship Extraction Pipeline** | Granular chunking, Gemini relationship extraction, citation metadata attachment, terminal pretty-printer, automatic post-approval extraction, and `--extract-relationships`. | ✅ Completed (15/15 tests passed) |
| **M12: 4-Phase Clinical Verification & Anti-Hallucination Framework** | Article-level checks (RoB 2/ROBINS-I), laptop NLI (`llama3.2:1b`), statistical validation (95% CI null crossings), GRADE synthesis, non-linear scoring, automated gating, terminal audit cards, and verified relationship cache. | ✅ Completed (31/31 tests passed) |
| **M13: Web Health Dashboard & Google Fitness API Integration** | FastAPI dashboard on Port 8001, Google OAuth 2.0 flow with Fitness scopes, instant login redirect (<400ms), quick sync, 180-day background backfill, disk cache, and interactive Health App Movement Explorer. | ✅ Completed (52/52 tests passed) |
| **M14: Passed-Only Vector DB & Multi-Modal Personalization** | ChromaDB collection for verified relationships (ACCEPTED/PROVISIONALLY_SUPPORTED with score >= 70.0 only), user lifestyle onboarding questionnaire, 15-day rolling statistical calibration engine ($\mu \pm 1.5\sigma$, EWMA drift smoothing, two-tier state machine), dynamic context payload injection, and personalized biometric advisor. | ✅ Completed (63/63 tests passed) |
| **M15: Admin PDF Hunter & Dynamic Clinical Advisory Feed** | In-browser research paper idea search, sequential PDF download, chunk extraction, 4-phase clinical verification, ChromaDB passed-only indexing with live embeddings counter, dynamic embedding-determined disease/risk identification (e.g. elevated HR + low steps), Potential Causes, Risks, Action Plan, Medical Consultation Guidance, Signed with Credible Evidence footer, and customer dashboard feed with vital sidebar navigation and personalized summaries. | ✅ Completed (72/72 tests passed) |
| **M16: Prescription Vision Analyzer & Clinical Medical History AI Context** | Distinct page `/dashboard/prescriptions` with sidebar card & navbar links, OpenCV deskewing/CLAHE preprocessor, Gemini Vision multi-modal extraction (Doctor, Clinic, Date, Diagnoses, Medications), interactive verification screen with untick/edit, explicit clinical warning banner, strict zero-empty-fields omission rule, UserLifestyleProfile persistence, and AI BiometricAdvisor context injection. | ✅ Completed (93/93 tests passed) |
| **M17: 'Ask Clinical AI' Research Intelligence & Telemetry Consultant** | Interactive symptom & recovery consultation on dashboard, multi-modal context linking live vitals (HR anomalies, sleep deficit, steps) + medical profile (diagnoses, active meds, past prescriptions), ChromaDB vector search (`verified_relationships` & `research_papers`), Gemini 3.5 synthesis strictly quoting peer-reviewed paper titles, primary authors, publication years, DOIs, and verbatim evidence quotes, with deterministic fallback. | ✅ Completed (97/97 tests passed) |
| **M18: Aarogya AI / My Health OS Frontend Design Theme Migration** | Complete visual migration across all user, admin, prescription, onboarding, and auth views to the Aarogya AI design language (`front end todo/`), dark/light mode toggle with persistence, zero backend logic changes, 100% preservation of all data columns, research citations, and telemetry charts. | ✅ Completed (97/97 tests passed) |
| **M19: Gemini Quota Resilience, Multi-Key Failover & Route Optimization** | Solved 429 RESOURCE_EXHAUSTED via high-quota model fallback (`gemini-flash-lite-latest`, `gemini-3.5-flash-lite`), multi-key rotation, `.env` optimization, and `/api/sync/trigger` background route aliasing. | ✅ Completed (97/97 tests passed) |
| **M20: Ask AI Fast Vector Timeout & Complete Clinical Breakdown Rendering** | Reduced Ollama timeout to 3s with in-memory cooldown cache (4.3× test suite speedup), eliminated 15–30s request hangs, and updated `dashboard.html` / `app.py` to display complete clinical assessment, personal biomarker correlation, biological mechanisms with quotes, 3-step action plan, and cited research papers. | ✅ Completed (97/97 tests passed) |
| **M21: Knowledge Graph / Structured Query Engine** | Querying directly against verified cause-and-effect relationships for zero-hallucination health recommendations. | 📅 Planned Next |

---

## 3. Changelog & Session History

### Session: 2026-11-03 (Frontend Theme Migration to Aarogya AI / My Health OS)
- **User Request**:
  Migrate all frontend pages according to the newly designed mockups in `front end todo/` (`My Health OS · Aarogya AI.html`, `aarogya_admin.html`, `aarogya_ai_singin.html`, `aarogya_ai_login (1).html`, `aarogyaai.tsx`).
  Strict constraints:
  1. Purely GUI changes — zero modifications to backend business logic, route handlers, or API endpoints.
  2. Preserve 100% of all data columns, research quotes, study designs, risk of bias scores, baseline calibration parameters, prescription fields, and streaming logs without hiding or omitting anything.
  3. Seamlessly integrate features present in the system but not in the mockups (e.g. 180-day movement explorer, prescription hub, Ask Clinical AI, Hunter streaming progress).
  4. Restyle pages not present in mockups (`prescriptions.html`, `onboarding.html`) to match the new Aarogya AI design language.
- **Architectural & GUI Implementation**:
  1. **Global Base Shell (`src/health_app/dashboard/templates/base.html`)**:
     - Embedded Aarogya AI CSS custom properties (`:root` light and dark tokens: `--bg`, `--card`, `--ink`, `--mute`, `--line`, `--g`, `--g2`, `--amber`, `--red`, `--teal`, `--soft`, `--grad`).
     - Added global theme toggler script with `localStorage` persistence and `data-theme` attribute control.
     - Redesigned top navigation bar with the stylized Aarogya AI leaf SVG icon, brand title, responsive quick action pills, and theme toggle button.
  2. **Landing Page (`src/health_app/dashboard/templates/index.html`)**:
     - Implemented medical scanner line animation (`.scanner-line`) and subtle grid overlay (`.bg-grid`).
     - Added abstract human silhouette graphic with concentric pulse rings and floating biometric preview cards.
     - Modernized Google OAuth CTA (`/api/auth/google/login`) and Admin Portal access link (`/admin/login`).
  3. **Admin Portal Sign-In (`src/health_app/dashboard/templates/admin_login.html`)**:
     - Upgraded with Aarogya AI card styling, password visibility eye toggle (`#togglePw`, `#eyeOn`, `#eyeOff`), and security clearance badges.
  4. **User Dashboard (`src/health_app/dashboard/templates/dashboard.html`)**:
     - Transformed into "My Health OS by aarogya ai":
       - Responsive 248px sidebar rail (`aarogya-rail`) with mobile hamburger drawer and scrim.
       - Sidebar navigation items, user baseline progress footer (`Day X of 15 · baseline`), and brand motto `"It’s for you, not for everyone."`.
       - Top action bar with notification chip and subtitle.
       - Interactive greeting card with mood selector buttons and heartbeat telemetry animation.
       - 15-Day statistical calibration hero card with circular progress dial, day dots, rolling mean $\mu$, personal bandwidth $\mu \pm 1.5\sigma$, acute value, and z-score.
       - Today's Vitals grid (Resting HR, Daily Steps, Sleep Hours, SpO2/Embeddings).
       - Prescription Management Hub card with direct navigation to `/dashboard/prescriptions`.
       - Ask Clinical AI & Research Intelligence section with question input, chips, and citation cards.
       - Clinical Advisory Feed: full evidence cards with causal signatures (`X → modulates → Y`), personal metric observations, full quotes, study designs, risk of bias, and publication metadata.
       - 180-Day Movement Explorer: 7D/30D/90D/180D timeframes, Chart.js steps chart, summary metric cards, and movement journal log with filter.
       - Sleep Architecture Breakdown: weekly sleep trends and donut chart with sleep stages.
  5. **Admin Portal (`src/health_app/dashboard/templates/admin_dashboard.html`)**:
     - Transformed into "Aarogya Admin":
       - Sidebar navigation for Paper Fetching (`#fetching`), Paper Approval (`#approval`), Active Embeddings (`#embeddings`), and Active Users (`#users`).
       - Top stat tiles: Total Papers, Downloaded PDFs, Verified Claims, Total & Verified Embeddings.
       - Paper Fetching: 5-tier document resolver, Hunter search input, candidate checkboxes, 5-stage streaming console with progress bar, log terminal, and downloaded PDFs table.
       - Paper Approval: Ingested research papers registry and verified scientific relationships audit table.
       - Active Embeddings: Category breakdown (Smoking, Alcohol, Age bracket, Chronic risks, Lifestyle) and rules registry.
       - Active Users: Registered patient directory, baseline calibration days, and sync health.
  6. **Prescriptions Hub (`src/health_app/dashboard/templates/prescriptions.html`)**:
     - Upgraded with Aarogya AI palette, drag-and-drop upload zone, clinical verification review modal with checkboxes/edit controls, and active medical history cards.
  7. **Patient Onboarding (`src/health_app/dashboard/templates/onboarding.html`)**:
     - Styled with Aarogya AI card surfaces, sage accents, clean form inputs, and step progress indicators.
- **Verification Results**:
  - Full pytest test suite: **97 / 97 tests passing (100% pass rate)**.
  - Template rendering validation: all 7 templates compile and render without errors.
  - Complete column and data integrity maintained with zero regressions.

### Session: 2026-11-03 ('Ask Clinical AI' Interactive Advisory Section & Embedding Research Citation)
- **User Request**:
  Add an **"Ask AI" section** to the dashboard where patients can enter what they are feeling (symptoms, fatigue, stress) or any question about health improvement. The assistant must personalize outcomes based on their live vitals (heart rate, sleep, steps) and past medical/lifestyle history (active medications, diagnosed conditions, past prescriptions), and **always quote the research paper embeddings, primary authors, publication years, and DOIs**.
- **Architectural Implementation**:
  1. **Clinical Ask AI Advisor Module (`src/health_app/dashboard/ask_ai.py`)**:
     - Created `ClinicalAskAiAdvisor` engine.
     - Assembles multi-modal biometric context: acute resting HR + statistical baseline deviations ($\mu \pm 1.5\sigma$, $z$-score), nocturnal sleep duration + deficit, today's movement cadence, diagnosed conditions, active medications, and past prescription records (prescribing doctor, clinic, date).
     - Queries ChromaDB vector store for top semantic matches in `verified_relationships` (passed-only causal rules) and `research_papers` (full-text scientific chunks).
     - Formulates prompt demanding strict evidence quotation: primary author names, publication year, paper title, and verbatim evidence quotes.
     - Invokes Gemini API (`gemini-3.5-flash` with model fallback cascade).
     - Implemented resilient deterministic fallback engine when offline or when API is unreachable.
  2. **API Endpoint (`src/health_app/dashboard/app.py`)**:
     - Added `POST /api/ai/ask` endpoint accepting `{"query": str}`.
     - Resolves session user, live Google Fit telemetry, 15-day rolling baseline, persistent profile, and ChromaDB vector store.
     - Returns validated JSON with direct assessment, biomarker correlation, scientific mechanisms with author quotes, 3-step actionable improvement plan, physician escalation thresholds, and cited papers.
  3. **Interactive Dashboard UI (`src/health_app/dashboard/templates/dashboard.html`)**:
     - Added glassmorphic **"Ask Clinical AI & Research Intelligence"** section prominently above the Clinical Health Feed.
     - Added quick preset query chips for common inquiries (afternoon fatigue, elevated HR, meal timing, medication interactions).
     - Built client-side consultation workflow with loading spinner and rich result rendering:
       - Direct assessment banner.
       - Biomarker & telemetry correlation breakdown.
       - Evidence-grounded mechanism cards featuring verbatim quotes, author attribution, and clickable DOI badges.
       - 3-step improvement protocol.
       - Physician escalation guidance.
       - Cited research papers bar with external DOI links.
     - Added *"Ask Clinical AI"* navigation shortcut in the left sidebar.
- **Verification**:
  - Created 4 unit and integration tests in `tests/test_ask_ai.py`.
  - Full test suite passed: **97/97 tests passing** (100% pass rate).

### Session: 2026-11-03 (Fix Prescription Photo Extraction & Multi-Source Gemini Key Resolution)
- **Problem Resolved**:
  - The user reported: *"when i upload any phto od priscription it just extract nothing FIX IT ... No specific diagnoses detected ... No medicines detected in image"*.
  - **Root Cause Analysis**:
    1. **Key Isolation**: The user had placed their valid `GEMINI_API_KEY` in `Prescription/.env`, but no `.env` file existed in the root project directory `C:\Vikrant\`. Pydantic's `Settings` was only configured for `.env` in the current working directory, leaving `settings.gemini_api_key` as `None`.
    2. **Silent Offline Fallback**: Because `key` evaluated to `False`, `PrescriptionAnalyzer.analyze_image()` routed directly to `_fallback_extraction()`, which returned empty arrays for diseases and medicines.
    3. **Model Deprecation (404)**: When testing candidate models against Google GenAI, `gemini-2.5-flash` returned `404 NOT_FOUND: This model models/gemini-2.5-flash is no longer available to new users`, while `gemini-3.5-flash` and `gemini-3.5-flash-lite` (configured in `Prescription/.env`) were fully active and functional.
- **Fixes Applied**:
  1. **Root `.env` & Multi-Directory Configuration (`src/health_app/config.py`)**:
     - Created root `C:\Vikrant\.env` containing the active `GEMINI_API_KEY` and setting `GEMINI_MODEL=gemini-3.5-flash`.
     - Updated `SettingsConfigDict` in `config.py` to inspect `[".env", "Prescription/.env", "prescription/.env"]`.
     - Updated default `gemini_model` to `"gemini-3.5-flash"`.
  2. **Multi-Tier API Key Resolver & Model Cascade (`src/health_app/prescription/analyzer.py`)**:
     - Implemented `resolve_gemini_api_key()` checking argument &rarr; settings &rarr; environment &rarr; multi-directory `.env` files.
     - Updated candidate models: `gemini-3.5-flash`, `gemini-3.5-flash-lite`, `gemini-3.8-flash`, `gemini-flash-latest`.
     - Configured `types.GenerateContentConfig(temperature=0.1, response_mime_type="application/json")`.
  3. **Verification**:
     - Verified live vision extraction with test image: successfully extracted doctor ("Dr. Sarah Connor, MD"), clinic ("Silicon Health Clinic"), date ("2026-04-12"), diagnoses ("Essential Hypertension", "Dyslipidemia"), and medicines (Atorvastatin 20mg, Amlodipine 5mg).
     - Full test suite passed: **93/93 tests passing** (100% pass rate).

### Session: 2026-11-03 (Prescription Vision Analyzer Integration, Medical History Sync & AI Biometric Advisor Context)
- **User Request**:
  Integrate the prescription analyzer from the `prescription/` subfolder into the user dashboard:
  - Give it a distinct page (`/dashboard/prescriptions`) accessible via the left sidebar and main navigation.
  - When the user uploads a prescription photo, extract doctor name, place/clinic, date, diagnosed diseases/conditions, and medicines with dosages/instructions using Gemini Vision multi-modal extraction.
  - Present an interactive verification screen where the user is asked if every detail is correct, allowing them to **untick** or **edit** fields.
  - Display an explicit **warning alert** when clinical details are modified or unticked.
  - Add confirmed diseases and medicines to the patient's medical history / lifestyle profile (`UserLifestyleProfile`).
  - Provide full context of past prescriptions, diagnoses, prescribing doctors, dates, and clinic locations to the AI (`BiometricAdvisor`) so it can evaluate drug interactions and biometric risk factors.
  - **Strict UI Constraint**: Never show empty fields or "Not Found" placeholders; only show detected fields and medicines.
- **Architectural Implementation**:
  1. **Prescription Models (`src/health_app/prescription/models.py`)**:
     - Created `PrescribedMedicineItem`, `PrescriptionRecord`, and `PrescriptionExtractionResult`.
     - Built `to_compact_dict()` methods on all models that systematically strip `None`, `""`, `"unclear"`, `"none"`, `"n/a"` placeholder values.
  2. **Image Preprocessor (`src/health_app/prescription/preprocessor.py`)**:
     - Implemented `ImagePreprocessor` with OpenCV deskewing via ink contour `minAreaRect` bounding analysis and CLAHE adaptive local contrast enhancement.
  3. **Vision OCR & Dictionary Normalizer (`src/health_app/prescription/analyzer.py`)**:
     - Built `PrescriptionAnalyzer` invoking Google GenAI multi-modal models (`gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-2.0-flash`).
     - Added fuzzy spelling suggestions using Python's standard library `difflib` against `prescription/data/medicines.json` (eliminating unneeded `rapidfuzz` C-dependency).
     - Added deterministic fallback parser when offline or when API key is unconfigured.
  4. **User Profile Persistence (`src/health_app/dashboard/user_profile.py`)**:
     - Extended `UserLifestyleProfile` with `prescriptions: List[PrescriptionRecord]`, `diagnosed_conditions: List[str]`, and `active_medications: List[PrescribedMedicineItem]`.
     - Added `add_prescription()` with automatic deduplication of diagnoses and active medications, and `delete_prescription()` with profile re-synchronization.
  5. **AI Biometric Advisor Dynamic Context Injection (`src/health_app/dashboard/biometric_advisor.py`)**:
     - Implemented `_build_user_metadata()` injecting `diagnosed_conditions`, `active_medications`, and `past_prescriptions` into `context_payload["user_metadata"]`.
     - Injected past prescriptions, doctors, dates, and clinics directly into Gemini's clinical synthesis prompt for pharmacodynamic risk assessment.
     - Added context-aware rationale in the deterministic fallback synthesizing potential causes for pre-existing diagnoses and active medication timing.
  6. **FastAPI Endpoints (`src/health_app/dashboard/app.py`)**:
     - `GET /dashboard/prescriptions`: Renders dedicated prescription interface.
     - `POST /api/prescriptions/analyze`: Uploads image, deskews, runs Gemini Vision, and returns strictly populated fields.
     - `POST /api/prescriptions/save`: Validates confirmed payload, saves to `UserLifestyleProfile` on disk.
     - `DELETE /api/prescriptions/{rx_id}`: Deletes prescription and updates profile.
     - `GET /api/prescriptions/list`: Returns user's active prescriptions and medications.
  7. **User Interface (`src/health_app/dashboard/templates/prescriptions.html`, `dashboard.html`, `base.html`)**:
     - Built modern glassmorphic dark-themed template for `/dashboard/prescriptions`.
     - Added dropzone with instant image preview, progress state, and interactive review form.
     - Added explicit clinical advisory warning alert upon edit or untick.
     - Omitted all empty or unclear fields (no "Not Found" boxes!).
     - Added left sidebar card in `dashboard.html` with real-time saved count badge.
     - Added top navbar link in `base.html` for logged-in users.
- **Verification**:
  - Created 7 new unit and integration tests in `tests/test_prescription_analyzer.py`.
  - Full regression test suite passed: **93/93 tests passing** (100% pass rate).

### Session: 2026-11-03 (Calibrate Verification Scoring, Systematic Review Detection, Realistic RoB Framework & NLI Overlap Fix)
- **Problem Resolved**:
  - The user observed that during paper ingestion in the Admin PDF Hunter (e.g. *Sun G et al. (2026)* and *Dehesh M et al. (2026)*), **all** extracted clinical claims were being gated as **`EXCLUDED`** with low composite scores ($0.0, 3.2, 8.6, 18.2 / 100$), even for gold-standard evidence like meta-analyses of 148 RCTs, 257,000-subject cohort syntheses, and the PURE study ($130,843$ participants):
    *"why all are excluded EXCLUDED ... Cross-Sectional Observational Study, RoB: SERIOUS / CRITICAL, 3.2 / 100, 18.2 / 100 ..."*.
  - Identified 5 root causes:
    1. Truncation at 2,500 characters in `classify_study_design` caused reviews and meta-analyses to be misclassified as `Cross-Sectional Observational Study` (weight $0.50$).
    2. Non-RCTs were all routed into patient-level `ROBINS-I` checks, penalizing reviews $30 - 45$ points for lack of individual multivariable regression tables and narrow objective measurement regexes.
    3. Severe logarithmic penalty multiplier $\lambda = 18.0$ subtracted $60+$ points from base scores of $\sim 65$, making it mathematically impossible for any observational study to score $\ge 50$.
    4. NLI verifier treated low conceptual overlap ($< 30\%$) as a hard `CONTRADICTION`, triggering Hard Gate A and zeroing out scores to $0 / 100$.
    5. Fallback relationship extractor matched institutional boilerplate (`Centers for Disease Control`) and PRISMA search strings (`strategy was rerun: yielded 4182 results`).
- **Full-Text Study Design Classifier (`src/health_app/verification/article_checks.py`)**:
  - Extended classification text window from 2,500 characters to **15,000 characters** (covering title, abstract, keywords, and methodology sections).
  - Expanded `META_ANALYSIS` and `PROSPECTIVE_COHORT` indicator dictionaries with terms like `cochrane`, `scopus`, `web of science`, `prisma`, `pure study`, `mesa study`, `framingham`, `cardia study`.
- **Dedicated AMSTAR 2 / ROBIS Framework for Reviews & Expanded Endpoints (`src/health_app/verification/article_checks.py`)**:
  - Implemented `AMSTAR 2 / ROBIS` evaluation for `StudyDesignType.META_ANALYSIS`: assesses literature search across databases, study selection protocols, risk of bias of included studies, and heterogeneity ($I^2$, forest plots). Well-conducted systematic reviews receive low risk of bias (0-5 penalty points).
  - In `ROBINS-I`, expanded confounding control indicators (`covariates`, `hazard ratio`, `adjusted odds ratio`, `marginal structural`) and objective cardiovascular/metabolic measurement instrumentation (`blood pressure`, `sphygmomanometer`, `cuff`, `heart rate`, `bpm`, `pulse`, `accelerometer`, `actigraph`, `step count`, `coronary artery calcium`, `cac`, `ccta`, `ultrasound`, `echocardiog`, `lipid`, `cholesterol`, `hdl`, `ldl`, `glucose`, `hba1c`, `biomarkers`, `vo2`).
- **Calibrated Logarithmic Penalty Multiplier (`src/health_app/verification/scoring_engine.py` & `terminal_reporter.py`)**:
  - Tuned `LAMBDA_PENALTY` from $18.0 \rightarrow 8.5$. High-quality observational studies, clinical trials, and meta-analyses with minor or moderate bias now land in `PROVISIONALLY_SUPPORTED` ($70 - 84$) or `ACCEPTED` ($85 - 100$), while preserving strict safety gates for true contradictions, null crossing, and critical flaws.
- **NLI Semantics Fix (`src/health_app/verification/relationship_checks.py`)**:
  - Low conceptual overlap ($< 30\%$) now returns `NLIStatus.NEUTRAL` (score $0.35$), reserving `CONTRADICTION` strictly for directional inversion or explicit negation.
- **Fallback Extractor Noise Rejection (`src/health_app/relationships/extractor.py`)**:
  - Added negative filters for institutional titles (`Centers for Disease Control`, `World Health Organization`, `Department of`, `University of`) and review search strings (`strategy was rerun`, `overlapping searches`, `yielded X results`).
- **Resilient Vector Store Embeddings Fallback (`src/health_app/vectordb/store.py`)**:
  - Wrapped `add_documents` and `query` with automatic fallback to `MockEmbeddingProvider` upon Ollama outage or 404, preventing server crashes during embedding storage.
- **Automated Test Suite Expansion (`tests/test_verification.py`)**:
  - Added `test_classify_study_design_meta_analysis_beyond_2500_chars`.
  - Added `test_assess_risk_of_bias_systematic_review_low_penalty`.
  - Added `test_nli_low_overlap_is_neutral_not_contradiction`.
  - Added `test_composite_scoring_high_quality_meta_analysis_accepted`.
  - Added `test_extractor_noise_filtering`.
  - Total test suite status: **86 passed, 0 failed (100% pass rate across all workspace tests)**.

---

### Session: 2026-11-03 (Fix VerificationReport Relationship Attribute Binding & Defensive Claim Extraction)
- **Problem Resolved**:
  - Investigated and resolved:
    `Pipeline verification error on data\research_papers\...: 'VerificationReport' object has no attribute 'relationship'`
  - Diagnosed that [`VerificationReport`](file:///C:/Vikrant/src/health_app/verification/models.py) previously omitted a direct `.relationship` reference and citation metadata (storing only `claim_summary: str`), while the non-streaming handler in [`src/health_app/dashboard/app.py`](file:///C:/Vikrant/src/health_app/dashboard/app.py) accessed `vr.relationship.subject`, `vr.relationship.relation`, `vr.relationship.object`, and `vr.relationship.evidence_quote`.
  - Also identified and resolved `AttributeError: 'NoneType' object has no attribute 'concept_pair'` in `VectorStore.add_verified_relationships` when single-study claims without GRADE synthesis were passed.
- **Model & Scoring Engine Binding (`src/health_app/verification/models.py` & `scoring_engine.py`)**:
  - Bound `relationship: Optional[HealthRelationship] = None` directly onto `VerificationReport`.
  - Added citation metadata fields (`evidence_quote`, `paper_title`, `authors`, `publish_year`, `doi`) to `VerificationReport`.
  - Added fallback properties for `.subject`, `.relation`, and `.object` that parse `claim_summary` (`"A -> increases -> B"`) if `relationship` is ever omitted.
  - Updated `CompositeScoringEngine.evaluate()` to attach the source `HealthRelationship` and its metadata directly to the generated `VerificationReport`.
- **API & Store Defensive Hardening (`src/health_app/dashboard/app.py` & `src/health_app/vectordb/store.py`)**:
  - In `app.py`, defensively resolved `subject`, `relation`, `object`, and `evidence_quote` from `vr` via direct attribute check, falling back to `claim_summary` parsing.
  - In `store.py` (`add_verified_relationships`), guarded `rep.grade_synthesis` against `None`, falling back to `f"claim_{idx}"` if GRADE synthesis is absent.
- **Automated Test Suite Expansion (`tests/test_pdf_hunter_and_clinical_feed.py`)**:
  - Added `test_verification_report_relationship_binding`: verifies relationship binding on `VerificationReport`, metadata attachment, and fallback properties.
  - Added `test_hunter_ingest_with_mocked_verified_reports_non_streaming`: verifies non-streaming ingest processes verified reports without `AttributeError` and yields structured results.
  - Total test suite status: **81 passed, 0 failed (100% pass rate across all workspace tests)**.

---

### Session: 2026-11-03 (Real-Time Ingestion Streaming, Interactive 5-Step Stepper & Monospace Activity Terminal in Admin PDF Hunter)
- **Problem Resolved**:
  - The user observed that during multi-paper ingestion in the Admin PDF Hunter, the frontend UI appeared stuck on a static spinner without conveying real-time phase updates:
    *"it dosent show progress its stuck here ... show every progress like downloading uploading chunking etc on frontend too"*.
  - Resolved the lack of live progress visibility by transforming the entire backend ingestion pipeline into an NDJSON streaming event architecture and outfitting the admin dashboard with an interactive 5-step progress stepper and live monospace terminal console.
- **Real-Time Streaming Downloader (`src/health_app/fetcher/downloader.py`)**:
  - Implemented `download_stream()`: streams chunks of data from upstream repositories, yielding granular real-time progress events:
    - `download_start`: Endpoint URL and mirror tier.
    - `download_progress`: Real-time downloaded KB vs total KB and percentage.
    - `download_verified`: File presence, byte size, and strict `%PDF-` magic header confirmation.
    - `download_fallback`: Diagnostic notice if a mirror fails and fallback to alternative mirror or `curl` occurs.
    - `download_result`: Final destination path and verification status.
  - Re-routed standard `download()` to seamlessly consume `download_stream()`, maintaining 100% backward compatibility for terminal runners and automated tests.
- **Granular Pipeline Streaming Engine (`src/health_app/relationships/pipeline.py`)**:
  - Implemented `process_text_stream()` and `process_paper_stream()`:
    - Yields `load_start` and `load_complete` with character counts.
    - Yields `chunking_start` and `chunking_complete` with total chunk count.
    - Yields `extract_chunk_start` and `extract_chunk_complete` per text chunk with extracted claim count.
    - Yields `audit_article_start` and `audit_article_complete` (Study Design & RoB 2 / ROBINS-I assessments).
    - Yields `claim_verified` after each individual claim completes NLI, statistical checks, GRADE synthesis, and composite scoring.
    - Resolved attribute access on `rel` (`rel.subject`, `rel.relation`, `rel.object`, `rel.evidence_quote`) preventing any verification `AttributeError`.
  - Re-routed synchronous `process_text()` and `process_paper_file()` to consume the streaming generators.
- **FastAPI NDJSON Streaming Endpoint (`src/health_app/dashboard/app.py`)**:
  - Upgraded `POST /api/admin/hunter/ingest`: detects streaming requests (`stream: true` or `Accept: application/x-ndjson`) and returns a Starlette `StreamingResponse` with media type `application/x-ndjson`.
  - Emits real-time event messages for each stage:
    - `paper_start` / `paper_complete`
    - `download_start` / `download_progress` / `download_verified`
    - `load_start` / `chunking_complete`
    - `extract_chunk_complete` (AI relationship extraction per chunk)
    - `claim_verified` (individual claim card data with scores, study design, RoB, NLI, and DOI)
    - `vector_db_index` (live indexing into ChromaDB collection `verified_relationships`)
    - `stats_update` (live updated total embeddings count)
    - `ingest_complete` (final summary of papers, chunks, claims, and verified entries)
  - Synchronous non-streaming requests continue to receive standard single JSON responses for backward compatibility.
- **Admin Dashboard UI Overhaul (`src/health_app/dashboard/templates/admin_dashboard.html`)**:
  - **Interactive 5-Phase Stepper**:
    - Visual breadcrumb bar showing: `1. Download` &rarr; `2. Chunk` &rarr; `3. AI Extraction` &rarr; `4. Clinical Audit` &rarr; `5. Vector DB`.
    - Active phase pulses with blue background; completed phases turn emerald with a checkmark badge (`✓`).
  - **Dynamic Progress Bar & Activity Label**:
    - Smooth animated progress bar (`#hunterProgressBar`) updating from 0% to 100%.
    - Real-time activity descriptor (`#hunterCurrentActivity`) e.g. *"Downloading PMC13595362: 540 KB / 1040 KB (52%)"*, *"Extracting causal relationships from Chunk 3/8..."*, *"Clinical verification of claim #4/12..."*.
  - **Live Monospace Terminal Activity Log (`#hunterConsoleLog`)**:
    - Dark terminal window (`bg-slate-950 font-mono`) with styled header, status indicator, clear log button, and auto-scrolling terminal feed.
    - Color-coded log tags: `[DOWNLOAD]` (cyan), `[CHUNKING]` (purple), `[AI_EXTRACT]` (amber), `[CLINICAL_AUDIT]` (indigo), `[VECTOR_DB]` (emerald), `[COMPLETE]` (emerald bold), and `[ERROR]` (rose).
  - **Live Claim Card Ingestion**:
    - Discovered verified claims dynamically render into the UI table and audit cards *as they are verified in real time*, eliminating the wait for full batch completion.
  - **Streaming Client Architecture**:
    - Upgraded `ingestSelectedHunterPapers()` using `fetch()` with `response.body.getReader()` and `TextDecoder` to parse incoming NDJSON lines on the fly.
- **Automated Test Suite Expansion (`tests/test_pdf_hunter_and_clinical_feed.py`)**:
  - Added `test_hunter_ingest_endpoint_streaming`: verifies streaming NDJSON output, proper sequence of events (`paper_start`, `chunking_start`, `claim_verified`, `vector_db_index`, `stats_update`, `ingest_complete`).
  - Added `test_downloader_stream_yields_events`: verifies `download_stream` yields `download_start`, `download_progress`, and `download_result`.
  - Total test suite status: **79 passed, 0 failed (100% pass rate across all workspace tests)**.

---

### Session: 2026-11-03 (Fix Pipeline PaperExtractionReport Verified Reports Attribute & Strict PDF Magic Header Validation)
- **Problem Resolved**:
  - Investigated and resolved:
    `Pipeline verification error on data\research_papers\...pdf: 'PaperExtractionReport' object has no attribute 'verified_reports'`
  - Diagnosed false-positive 20 KB HTML downloads: NCBI PubMed Central (`pmc.ncbi.nlm.nih.gov/articles/PMC.../pdf/`) was returning an HTML landing page of ~20 KB. `PDFDownloader` previously accepted any file $> 1024$ bytes, failing to inspect magic bytes and masking Europe PMC's real 2–5 MB binary PDF endpoint (`europepmc.org/api/getPdf?pmcid=PMC...`).
- **Pipeline & Model Integrity (`src/health_app/relationships/models.py`, `pipeline.py`, & `app.py`)**:
  - Added `verified_reports: List[Any] = Field(default_factory=list)` to `PaperExtractionReport`.
  - Updated `RelationshipPipeline.process_text()` to pass `verified_reports=verified_reports` into `PaperExtractionReport`.
  - Defensively updated `app.py` line 631 to inspect `getattr(report, "verified_reports", None)`.
- **Strict PDF Magic Byte Validation & URL Mirror Prioritization (`src/health_app/fetcher/downloader.py` & `recovery.py`)**:
  - Implemented `_is_valid_pdf_file()` in `PDFDownloader`: checks file presence, ensures size $\ge 1024$ bytes, verifies presence of `%PDF-` magic header in first 1024 bytes, and explicitly rejects HTML/XML landing pages.
  - Re-ordered PMC mirrors in `_get_url_variants()`: placed `https://europepmc.org/api/getPdf?pmcid={pmcid}` as the primary (Tier 1) mirror before NIH web endpoints.
  - Updated `download()` and `_download_with_curl()` to reject non-PDF payloads, clean up false-positive files, and cascade to remaining mirrors.
  - Updated `recovery.py` to identify pseudo-PDF HTML files and trigger automated re-download.
- **Disk Cleanup & Verification**:
  - Cleaned up 4 invalid ~20 KB HTML files in `data/research_papers/`.
  - Live verified end-to-end download of `PMC12606180` (1978 KB valid `%PDF-1.4`), chunking into 12 chunks, extracting 45 causal claims, and auditing 45 verified reports without errors.
- **Automated Test Suite Expansion (`tests/test_pdf_hunter_and_clinical_feed.py`)**:
  - Added `test_pipeline_returns_verified_reports_attribute`: verifies `PaperExtractionReport.verified_reports` exists and is populated.
  - Added `test_downloader_rejects_html_landing_pages`: verifies HTML error pages are rejected and not saved as verified PDFs.
  - Total test suite status: **77 passed, 0 failed (100% pass rate across all workspace tests)**.

---

### Session: 2026-11-02 (Resilient Multi-Tier Scientific Paper Search Failover & Offline Fallback Engine)
- **Problem Resolved**:
  - Investigated and resolved Europe PMC DNS resolution failure: `HTTPSConnectionPool(host='www.ebi.ac.uk', port=443): Max retries exceeded ... (Caused by NameResolutionError("HTTPSConnection(host='www.ebi.ac.uk', port=443): Failed to resolve 'www.ebi.ac.uk' ([Errno 11001] getaddrinfo failed)"))`.
  - Addressed single-point biomedical repository dependency and lack of graceful offline handling in the Admin PDF Hunter.
- **4-Tier Resilient Research Search Engine (`src/health_app/fetcher/client.py`)**:
  - **Tier 1: Europe PMC (`www.ebi.ac.uk`)**: Hardened with explicit socket/connection exception handlers (`socket.gaierror`, `NameResolutionError`, `ConnectionError`, `Timeout`). Fails over cleanly rather than raising uncaught exceptions.
  - **Tier 2: Crossref Works Engine (`search_crossref`)**: Queries `https://api.crossref.org/works` on AWS CloudFront CDN. Extracts peer-reviewed journal papers, DOIs, authors, publication years, abstracts, and open-access links.
  - **Tier 3: arXiv Preprints Engine (`search_arxiv`)**: Queries `https://export.arxiv.org/api/query` for preprints and quantitative biology manuscripts.
  - **Tier 4: Local Paper Registry Fallback (`search_local_registry`)**: Fully offline fallback that queries indexed research papers from `data/research_papers_index.json`. Computes keyword token overlap on title, abstract, and authors to return matching manuscripts even if internet access or DNS resolution is completely severed.
  - **Automatic Deduplication & Diagnostic Notice (`search_all`)**: Normalized title and ID deduplication across all 4 tiers; records diagnostic notices when remote repositories fail or when offline fallback is engaged.
- **Admin API & UI Diagnostic Banner (`src/health_app/dashboard/app.py` & `templates/admin_dashboard.html`)**:
  - `POST /api/admin/hunter/search`: Attaches diagnostic `notice` string to JSON response when failover occurs.
  - Added `#hunterNoticeBanner` in Admin UI to display informational feedback (e.g. *"Europe PMC DNS was unreachable; candidate papers retrieved via Crossref / arXiv fallback mirrors."*).
  - Added source badges with color coding: Europe PMC (blue), Crossref (emerald), arXiv (amber), and Local Archive (purple).
  - Updated `hunter_ingest` to directly utilize existing local files on disk when ingested from the offline archive.
- **Automated Test Suite Expansion (`tests/test_pdf_hunter_and_clinical_feed.py`)**:
  - Added `test_hunter_search_endpoint_with_fallback_notice`: verifies notice delivery in hunter search response.
  - Added `test_paper_search_client_epmc_dns_failure_fallback`: verifies DNS failure handling on Europe PMC and automated Crossref/arXiv failover.
  - Added `test_paper_search_client_offline_fallback_to_local_registry`: verifies 100% offline fallback to local index.
  - Total test suite status: **75 passed, 0 failed (100% pass rate across all workspace tests)**.

---

### Session: 2026-11-02 (Admin PDF Hunter, Dynamic Embedding-Determined Clinical Inferences, Feed-Style Customer Dashboard & Vital Sidebar Navigation)
- **Admin PDF Hunter Engine (`src/health_app/dashboard/app.py` & `templates/admin_dashboard.html`)**:
  - Implemented interactive in-browser **VITA PDF Hunter**: Admins can enter research topics, ideas, or medical queries (e.g. "nocturnal heart rate elevation nicotine smoking sleep fragmentation" or "intermittent fasting cardiometabolic health").
  - Added endpoint `POST /api/admin/hunter/search`: Queries open-access scientific repositories (Europe PMC and arXiv) via `PaperSearchClient.search_all`, returning candidate paper metadata, open access status, and direct PDF download links.
  - Built candidate paper selection interface: Checkboxes with Select All toggle, author, year, journal, and expandable abstract preview.
  - Added endpoint `POST /api/admin/hunter/ingest`: Sequentially processes selected papers:
    - Safely downloads full-text PDF to `data/research_papers/`.
    - Registers metadata in `PaperRegistry`.
    - Runs `RelationshipPipeline`: chunks manuscript, extracts causal relationships via Gemini AI, and audits them through the 4-phase clinical verification framework (RoB 2 / ROBINS-I, NLI, statistical checks, GRADE synthesis, composite scoring & gating).
    - Automatically updates `data/health_relationships_verified.json`.
    - Indexes passed relationships (`ACCEPTED` and `PROVISIONALLY_SUPPORTED`, score $\ge 70.0$) directly into ChromaDB vector store collection `verified_relationships`.
    - Returns live execution progress, verified claim cards, and updated total ChromaDB embeddings count.
  - Built real-time verification feed in Admin UI displaying newly audited claims with composite scores, study designs, RoB evaluations, and DOI links, while live updating the "ChromaDB Embeddings in DB" counter.
- **Dynamic Embedding-Determined Clinical Inferences & Evidentiary Signing (`src/health_app/dashboard/biometric_advisor.py`)**:
  - Upgraded `BiometricInsight` schema: includes `vital_category`, `headline`, `metric_observation`, `potential_causes`, `potential_risks`, `action_plan`, `consultation_guidance`, `consult_recommended`, and `evidence_signature` (`ClinicalEvidenceSignature`), while preserving full backward compatibility with `.title`, `.category`, `.clinical_finding`, `.doi`, etc.
  - **Dynamic Vector Embedding Clinical Identification**: Eliminated hardcoded conditions. Any multi-metric deviation state (e.g. resting heart rate above baseline + low daily steps, sleep truncation + elevated pulse) generates a dense semantic probe (e.g. *"elevated resting heart rate above baseline with reduced physical activity and low step volume in sedentary [profession] [smoking_status]"*).
  - Queries ChromaDB `verified_relationships` collection with dense embeddings and metadata filtering (`smoking_relevant`, `alcohol_relevant`, `metric_type`).
  - **The retrieved vector embeddings dynamically dictate the indicated disease, condition, and physiological mechanisms** (e.g. cardiometabolic deconditioning, autonomic neuropathy, arterial stiffness).
  - Synthesizes authoritative clinical explanations using Gemini (`gemini-2.5-flash`) or deterministic grounded clinical fallback, producing:
    - **Personal Metric Observation** vs personal 15-day baseline.
    - **Potential Causes & Physiological Mechanisms** (bulleted).
    - **Potential Risks If Unmitigated** (bulleted).
    - **Recommended Action Plan for Today** (numbered steps).
    - **Physician Consultation Guidance** (highlighted box with red flag warning signs).
    - **Signed with Credible Research Evidence** (doctor-style sign-off box with authors, year, study design, composite score, and direct DOI link).
- **Customer Dashboard Redesign: Clinical Feed & Vital Category Sidebar (`src/health_app/dashboard/templates/dashboard.html` & `app.py`)**:
  - Transformed dashboard into an intuitive two-column clinical portal:
    - **Left Sidebar**: Sticky vital category navigation with:
      - `[All Clinical Findings]` (with total report counter pill)
      - `[Heart Rate & Autonomic Tone]` (with mini status pill e.g. `Elevated (+1.8σ)` and short analysis)
      - `[Sleep Architecture & Recovery]` (with mini status pill e.g. `3h 27m` and short analysis)
      - `[Daily Steps & Movement]` (with mini status pill e.g. `11,240 Steps` and short analysis)
      - Jump links to deep telemetry analytics (`#movement-section`, `#sleep-section`).
      - Client-side category filtering (`filterClinicalFeed`) showing cards dynamically.
    - **Right Main Column**:
      - Quick Stats KPI grid (Steps, Heart Rate, Last Night Sleep, Clinical Grounding).
      - **Clinical Advisory Feed Cards**: Displays rich report cards with multi-sensor correlation banners, causes, risks, action plans, physician consultation boxes, and evidence signatures.
      - **Interactive Analytics Deep Dive**: Preserved 180-Day Movement Explorer (7D/30D/90D/180D), Historical Activity Journal, and 7-Day Sleep Duration Trends & Doughnut Chart.
- **Automated Test Suite Expansion (`tests/test_pdf_hunter_and_clinical_feed.py`)**:
  - Added 9 comprehensive unit tests covering: unauthenticated hunter search & ingest 401s, search query handling, sequential paper ingestion, ChromaDB passed-only indexing, total embeddings count reporting, `BiometricInsight` backward compatibility and evidence signatures, dynamic vector embedding cross-metric anomaly detection, sidebar category summary generation, customer dashboard feed rendering, and admin PDF Hunter UI elements.
  - Total test suite status: **72 passed, 0 failed (100% pass rate across all workspace tests)**.

---

### Session: 2026-11-02 (Multi-Modal Personalization Architecture, 15-Day Statistical Baseline Engine & Passed-Only Vector DB Indexing)
- **Strict Passed-Only Vector DB Indexing (`src/health_app/vectordb/store.py` & `src/health_app/relationships/pipeline.py`)**:
  - Implemented dedicated ChromaDB collection `verified_relationships`.
  - Enforced strict evidentiary gating: only relationships with `status in ["ACCEPTED", "PROVISIONALLY_SUPPORTED"]` and `composite_score >= 70.0` are indexed. Low-credibility claims (`EXCLUDED`, `QUARANTINED`, or score $< 70.0$) are strictly rejected.
  - Sanitized rich metadata attributes for ChromaDB compatibility: `source_doi`, `paper_title`, `publish_year`, `subject`, `relation`, `object`, `risk_level`, `gating_status`, `final_score`, `smoking_relevant`, `alcohol_relevant`, `metric_type`.
  - Added `sync_verified_relationships_cache(cache_path)` and CLI integration `--sync-relationships` in `terminal_runner.py`.
  - Automatically indexes verified relationships directly into ChromaDB upon pipeline verification completion.
- **User Lifestyle & Risk Profile Onboarding Engine (`src/health_app/dashboard/user_profile.py`, `app.py`, `templates/onboarding.html`)**:
  - Defined `UserLifestyleProfile` schema: age, profession, smoking status (`never`, `former`, `occasional`, `current_smoker`), alcohol consumption (`none`, `occasional`, `moderate`, `heavy`), chronic risk factors (`hypertension`, `diabetes`, `cardiovascular`, `insomnia`, `asthma`), primary health goal, and baseline status (`calibration_mode` vs `active_calibrated`).
  - Added server-side JSON profile persistence in `data/user_profiles/profile_{hash}.json` keyed by user email.
  - Built comprehensive Tailwind-styled onboarding questionnaire modal `/onboarding`.
  - Updated OAuth callback flow: automatically detects first-time sign-ins and redirects to `/onboarding` to capture lifestyle metrics before accessing the dashboard.
- **15-Day Rolling Statistical Calibration Engine ($\mu \pm 1.5\sigma$ & EWMA Drift) (`src/health_app/dashboard/baseline_engine.py`)**:
  - Tracks individual biological variance over historical wearable telemetry (minimum 15 active days).
  - Calculates personal rolling mean ($\mu$), personal standard deviation ($\sigma$), and operational bandwidth $[\mu - 1.5\sigma, \mu + 1.5\sigma]$ for resting heart rate, sleep duration, and daily step count.
  - Implemented Exponentially Weighted Moving Average (EWMA, $\alpha = 0.12$) to smooth behavioral drift (e.g. night shifts, fitness changes) without false alarms.
  - Two-Tier State Machine:
    - **Calibration Mode** ($< 15$ active days): UI displays progress meter (`Day N of 15 Baseline Building`) with tentative descriptive observations while suppressing premature clinical alerts.
    - **Active Baseline Mode** ($\ge 15$ active days): Distribution locks in; evaluates acute readings via Z-score $Z = \frac{x_{\text{acute}} - \mu}{\sigma}$ to detect anomalies ($|Z| > 1.5\sigma$).
- **Multi-Modal Personalization & Grounded Biometric Advisor (`src/health_app/dashboard/biometric_advisor.py`)**:
  - Implemented `generate_personalized_insights`: retrieves clinical evidence filtered by user risk tags (`smoking_relevant`, `alcohol_relevant`, `metric_type`).
  - Formats strict dynamic context payload (`user_metadata`, `current_deviation`, `retrieved_evidence`) to generate hyper-personalized clinical advice eliminating generic recommendations.
  - Upgraded dashboard UI with Personalized Risk Profile Strip, 15-Day Calibration Meter / Bandwidth Strip, and variance delta badges (`+1.8σ (Elevated)`).
- **Automated Test Suite (`tests/test_personalization_and_baseline.py`)**:
  - Added 6 comprehensive unit tests covering passed-only indexing, profile CRUD, calibration state machine, EWMA drift, context payload formatting, and onboarding routes.
  - Total test suite status: **63 passed, 0 failed (100% pass rate across all workspace tests)**.

---

### Session: 2026-11-02 (Sleep Metrics Discrepancy Fix, 7-Day Sleep Duration Trends & Stage Parsing)
- **Root Cause 1: 38.8 hrs vs 3h 27m Discrepancy Resolved (`src/health_app/dashboard/google_health.py`)**:
  - `_fetch_sleep` was previously accumulating all sleep segments over a 7-day query window into a single total duration variable ($~5.5\text{ hrs/night} \times 7\text{ nights} \approx 38.8\text{ hrs}$), displaying a week's cumulative sleep as if it were a single day's sleep!
  - Replaced the cumulative window query with Google Fit's official Sessions API: `GET https://www.googleapis.com/fitness/v1/users/me/sessions?startTime={iso}&endTime={iso}&activityType=72`.
  - Grouped sleep sessions by calendar date across the last 7 days and isolated the most recent completed sleep session (e.g. 12,420,000 ms = 207 minutes = **3h 27m** / 3.5 hrs), exactly matching the Google Fit mobile app.
- **Root Cause 2: Validated Google Fit Sleep Stage Parsing (`src/health_app/dashboard/google_health.py`)**:
  - Replaced hardcoded percentage multipliers (`* 0.22`, `* 0.25`) with parsed integer codes from Google Fit's `com.google.sleep.segment`:
    - Code `1`: Awake sleep
    - Code `4`: Light sleep
    - Code `5`: Deep sleep
    - Code `6`: REM sleep
    - Codes `2/3`: General / unclassified sleep
  - Sleep duration and stage breakdowns now reflect the user's authentic physiological sleep recording.
- **7-Day Sleep Duration Trends Bar Chart & Last Night Architecture (`src/health_app/dashboard/templates/dashboard.html` & `app.py`)**:
  - Introduced `DailySleepRecord` schema tracking each day's date, day name, total hours, formatted duration (e.g. "3h 27m"), and stage breakdowns.
  - Added dedicated **7-Day Sleep Duration Trends Bar Chart** (`#weeklySleepChart`) plotting each day's actual sleep across the past week with visual color-coding (emerald for $\ge 7.0$h optimal, indigo for sub-optimal/short sleep) and dynamic KPI strip showing 7-Day Total, Nightly Average, and Last Night Session.
  - Positioned the **Last Night's Sleep Architecture Doughnut** (`#sleepChart`) beside the weekly trends, displaying the 4 stages (Deep, REM, Light, Awake) for last night's session.
  - Updated Quick Stats Card to explicitly show `Last Night's Sleep: 3h 27m (3.5 hrs)` rather than ambiguous labels.
- **Automated Test Suite (`tests/test_dashboard.py`)**:
  - Added unit tests for `DailySleepRecord` and `SleepSummary` models with `formatted_duration`, `generate_demo_weekly_sleep` verifying 7 distinct days ending in `3h 27m`, Google Fit `com.google.sleep.segment` stage parsing (intVal 1, 4, 5, 6), and multi-session grouping/isolation.
  - Verified UI elements: `#weeklySleepChart`, `#weeklySleepData`, "7-Day Sleep Duration Trends", "Last Night's Sleep Architecture".
  - Total test suite status: **57 passed, 0 failed (100% pass rate across all workspace tests)**.

---

### Session: 2026-11-02 (OAuth Login Hang Fix, Permission Re-prompting Elimination & Background Ingestion)
- **Root Cause 1: Elimination of Repeated "Arogya AI Wants Permission" Prompt (`src/health_app/dashboard/auth.py`)**:
  - Replaced forced `prompt="consent"` with `prompt="select_account"`.
  - Google now remembers previously granted scopes and skips the consent screen entirely for returning users, allowing clean account selection without re-prompting. Added optional `force_consent=True` toggle for explicit re-authorization.
- **Root Cause 2: Instant OAuth Callback Redirect (<400ms) (`src/health_app/dashboard/app.py`)**:
  - Decoupled 19 heavy synchronous external API calls from the OAuth callback route.
  - `google_callback` now performs only code-token exchange and basic profile fetch before immediately redirecting to `/dashboard` in under 400ms, completely eliminating the browser redirect freeze / hang.
- **Fast Initial Sync & Resilient Scope Handling (`src/health_app/dashboard/google_health.py`)**:
  - Implemented `fetch_quick_health_data`: loads today's steps, resting heart rate, sleep summary, and 7-day movement cadence in ~300-500ms.
  - Handled HTTP 403 Forbidden gracefully in `_fetch_heart_rate` and `_fetch_sleep` (if the user unchecks sleep or heart rate on the consent screen, it logs cleanly and assigns non-blocking default summaries rather than retrying or hanging).
- **Asynchronous 180-Day Background Ingestion (`src/health_app/dashboard/app.py` & `dashboard.html`)**:
  - Added dedicated endpoint `POST /api/health/sync-history` for background backfill of 30-day batches.
  - Added non-blocking status banner in dashboard UI: triggers background fetch if history is missing or incomplete, automatically updating Chart.js and historical log without freezing the browser or user interaction.
- **Automated Test Suite (`tests/test_dashboard.py`)**:
  - Added unit tests for `select_account` prompt generation and `force_consent=True` behavior, fast quick sync `fetch_quick_health_data`, unauthenticated `/api/health/sync-history` protection, and instant OAuth callback redirect verification.
  - Total test suite status: **52 passed, 0 failed (100% pass rate)**.

---

### Session: 2026-11-02 (Step Discrepancy Fix, 180-Day Batched Movement Explorer & Server Disk Cache)
- **Today's Step Discrepancy Fix (`src/health_app/dashboard/google_health.py`)**:
  - Aligned day bucket timestamps to user's local midnight (`00:00:00.000` to `23:59:59.999`) based on detected local timezone (IST, UTC+5:30) rather than UTC `now - 7 days`.
  - Implemented multi-stream step reconciliation: queries both `estimated_steps` and `merge_step_deltas` (and generic fallback), resolving the true maximum (`max(est, merge, gen)`) so steps recorded by smartwatches, fitness bands (e.g. WearOS, Samsung Health, Mi Fitness), and phones are captured accurately (matching the user's expected ~11k steps).
- **180-Day Batched Historical Fetcher (`src/health_app/dashboard/google_health.py`)**:
  - Replaced crash-prone monolithic 180-day queries with resilient 30-day batches (up to 6 batches).
  - Implemented early termination: if an older batch returns 0 steps across all days, querying stops automatically to preserve API quotas and minimize latency.
- **Server-Side Disk Cache Engine (`src/health_app/dashboard/google_health.py` & `src/health_app/dashboard/app.py`)**:
  - Decoupled Starlette session cookies from large history arrays to prevent exceeding browser 4KB cookie limits.
  - Historical records are saved to and loaded from `data/user_cache/user_{hash}.json` with incremental merging by calendar date.
- **Interactive Health App Movement Explorer (`src/health_app/dashboard/templates/dashboard.html`)**:
  - Built Apple Health / Google Fit style interface with interactive timeframe pills: `[ 7D ]`, `[ 30D ]`, `[ 90D ]`, `[ 180D ]`.
  - Dynamic summary KPI strip: computes Daily Average Steps, Total Steps in Period, Goal Met Days (>= 10,000), and Peak Day in real time without page reload.
  - Chart.js Movement Graph: color-codes bars (emerald green for >=10k goal met, electric blue for in-progress), renders dashed goal reference line (10,000) and period average line, with rich hover tooltips.
  - Historical Activity Log ("Show All History"): scrollable journal with date search filter, progress bars, and goal achievement badges.
  - Automatic browser timezone detection: sets persistent cookie `vita_tz_offset` on page load.
- **Automated Test Suite (`tests/test_dashboard.py`)**:
  - Added unit tests for `DailyRecord` model validation, IST timezone offset resolution (-330 -> +05:30), 180-day demo history generation, user disk caching and date merging, multi-stream step resolution (verifying 11,240 is selected over 7,500), and dashboard template rendering.
  - Total test suite status: **49 passed, 0 failed (100% pass rate)**.

---

### Session: 2026-11-02 (Web Health Dashboard & Google Fitness API Integration)
- **Google OAuth 2.0 Flow (`src/health_app/dashboard/auth.py`)**:
  - Auto-discovers existing Google client secret JSON (`client_secret_2_1059027165335-m2h68ikq9uremd83bk07bvmkprmn3ede.apps.googleusercontent.com.json`) from project root.
  - Generates secure OAuth 2.0 authorization URL requesting fitness read scopes (`fitness.activity.read`, `fitness.heart_rate.read`, `fitness.sleep.read`, `userinfo.profile`, `userinfo.email`).
  - Exchanges authorization code for access tokens with strict redirect URI adherence (`http://127.0.0.1:8001/api/auth/google/callback` and `http://localhost:8001/api/auth/google/callback`).
- **Google Fitness API Client (`src/health_app/dashboard/google_health.py`)**:
  - Queries Google Fitness REST aggregation endpoint (`POST https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate`).
  - Pulls 7-day daily step volume (`com.google.step_count.delta`), resting / min / max heart rate (`com.google.heart_rate.bpm`), and nocturnal sleep stages (REM, deep, light sleep via `com.google.sleep.segment`).
  - Provides realistic demo telemetry fallback when a new Google account lacks wearable biometric data.
- **Biometric Advisory Engine (`src/health_app/dashboard/biometric_advisor.py`)**:
  - Grounds personal biometrics directly in verified scientific research claims (`data/health_relationships_verified.json`).
  - Highlights cardiovascular strain warnings (e.g. short sleep combined with elevated resting HR) and protective activity metrics (daily step count vs. all-cause mortality), complete with authors, journals, and DOIs.
- **FastAPI Web Dashboard Application (`src/health_app/dashboard/app.py` & `templates/`)**:
  - Dual sign-in landing page with "Sign in with Google" and "Admin Account" login options.
  - User Dashboard: Displays real-time metrics cards, Chart.js 7-day step bar chart, nocturnal sleep architecture doughnut chart, and grounded scientific health advice.
  - Admin Portal: Provides an overview of indexed papers, downloaded PDFs, embedding models, and audit logs of verified claims with composite confidence scores and gating statuses.
  - Form parsing resilience: Zero-dependency URL-encoded form parser fallback prevents `python-multipart` missing dependency errors.
  - Configured default port to **8001** matching Google Cloud Console authorized redirect URIs.
- **Menu & CLI Integration (`src/health_app/terminal_runner.py` & `src/health_app/menu.py`)**:
  - Added `--dashboard` CLI flag to launch FastAPI server on Port 8001.
  - Added Option `[8] Launch Web Health Dashboard & Google Health Integration (Port 8001)` in `start.cmd` interactive menu.
- **Automated Test Suite (`tests/test_dashboard.py`)**:
  - Added 9 unit tests covering credential discovery, OAuth URL generation, data models, clinical advisor triggers, landing page, redirect endpoints, and admin authentication flows.
  - Total test suite status: **43 passed, 0 failed (100% pass rate)**.

---

### Session: 2026-11-02 (Live Download Progress Bar, Multi-Engine PDF Parsing & Step-by-Step Credibility Logging)
- **Live Terminal Progress Bar & Anti-Hang Downloader (`src/health_app/fetcher/downloader.py`)**:
  - Implemented dynamic streaming progress bar `[Progress] |#####-----| 50.0% (488 KB / 977 KB)` with live byte counters and streaming fallback.
  - Added NIH PubMed Central mirrors (`https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/pdf/` and `https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/`) alongside Europe PMC endpoints.
  - Replaced 45s unbounded timeouts with split `(8.0, 20.0)` connection/read limits and single retry to avoid multi-minute silent socket hangs.
  - Added real-time step output for every endpoint attempt, Cloudflare WAF/403 alerts, and disk verification.
- **Multi-Engine PDF Loader & Full Manuscript Ingestion (`src/health_app/ingestion/loader.py` & `src/health_app/relationships/pipeline.py`)**:
  - Upgraded `DocumentLoader.load_file` to support PyMuPDF (`fitz`), `PyPDF2`, and `pypdf`, resolving missing module errors and unlocking full-text extraction across all pages of scientific PDFs (e.g. 14,800+ characters across 6 pages vs 2-chunk abstracts).
  - Fixed pipeline file loading priority: always prioritizes the full `.pdf` manuscript over the companion `.md` summary file.
- **Mandatory Article Credibility Card & Step-by-Step Progress (`src/health_app/verification/terminal_reporter.py` & `src/health_app/relationships/pipeline.py`)**:
  - Implemented `print_article_credibility_card` displaying Study Design Tier, Evidential Weight, RoB 2 / ROBINS-I domain evaluations, and Methodological Quality Badges (`[HIGH METHODOLOGICAL CREDIBILITY]`, `[SERIOUS RISK OF BIAS]`, etc.).
  - Ensured Phase 1 Credibility Audit always executes and prints for every research paper, even if 0 individual claims matched extraction patterns.
  - Added granular step logging (`[*] [Step 1/6] ... [*] [Step 6/6]`) for every phase of verification.
- **Broadened Fallback Relationship Extractor (`src/health_app/relationships/extractor.py`)**:
  - Added regex patterns covering "suggests that", "observed effect on", "contributes to", "protects against", "exacerbates", "modulates / regulates".
- **Test Suite (`tests/test_paper_fetcher.py` & `tests/test_verification.py`)**:
  - Added unit tests for NIH PMC mirror generation, progress bar rendering, article credibility card printing, and zero-claim article verification.
  - Suite status: **34 passed, 0 failed (100% pass rate)**.

---

### Session: 2026-11-02 (Phase 4 - 4-Phase Clinical Verification & Anti-Hallucination Framework)
- **Phase 1: Article-Level Checks (`src/health_app/verification/article_checks.py`)**:
  - Implemented `classify_study_design(text, title)` supporting 7 evidentiary tiers: Systematic Review / Meta-Analysis (1.00), RCT (0.95), Prospective Cohort (0.80), Case-Control (0.65), Cross-Sectional (0.50), Preclinical (0.35), and Narrative Review (0.25).
  - Implemented `assess_risk_of_bias(text, design)` executing automated RoB 2 domain criteria for clinical trials (Randomization sequence, Blinding, Missing outcome data / ITT) and ROBINS-I criteria for observational studies (Confounding adjustments, Participant selection, Measurement objectivity, Sample size N < 30).
- **Phase 2: Relationship-Level Checks (`src/health_app/verification/relationship_checks.py`)**:
  - Implemented `verify_textual_nli(premise, hypothesis)`: Queries local lightweight Ollama NLI (`llama3.2:1b`) with zero temperature; includes deterministic fallback evaluating negation patterns and directional polarity mismatches.
  - Implemented `validate_statistics(claim_direction, chunk_text, quote)`: Detects HR, OR, RR, and 95% CIs. Automatically checks if the 95% CI crosses the null value of 1.0 (penalizing non-significant claims by 25 pts) and verifies directional consistency with the verbal claim verb (flagging directional conflicts).
- **Phase 3: Group-Level Evidence Synthesis (`src/health_app/verification/evidence_synthesis.py`)**:
  - Implemented `synthesize_group_evidence(relationships)`: Groups extracted relationships by canonical biological concept pairs and assesses collective certainty using adapted GRADE criteria (High consistency across >=3 studies, moderate for 2, penalty for directional conflict).
- **Phase 4: Non-Linear Composite Scoring & Automated Gating (`src/health_app/verification/scoring_engine.py`)**:
  - Calculates normalized base score: $B = 0.25 \cdot S_{\text{NLI}} + 0.25 \cdot S_{\text{Stat}} + 0.30 \cdot S_{\text{Design}} + 0.10 \cdot S_{\text{Comp}} + 0.10 \cdot S_{\text{Cont}}$.
  - Applies logarithmic risk penalty: $\Delta = 18.0 \cdot \ln(1 + P)$ where $P = P_{\text{RoB}} + P_{\text{Stat}} + P_{\text{GRADE}}$.
  - Executes Hard Gates: NLI Contradiction $\implies$ Immediate Hard Rejection (Score = 0, EXCLUDED); Mathematical Direction Mismatch $\implies$ Hard Rejection (Capped < 50, EXCLUDED); Critical Risk of Bias $\implies$ Capped < 50, EXCLUDED.
  - Automated Gating Statuses: **ACCEPTED (85-100)**, **PROVISIONALLY SUPPORTED (70-84)**, **QUARANTINED (50-69)**, **EXCLUDED (< 50)**.
- **Terminal Audit Card Pretty-Printer (`src/health_app/verification/terminal_reporter.py`)**:
  - Prints structured clinical verification audit cards directly to the terminal showing status badges, score breakdown, methodology indicators, RoB domain evaluations, NLI rationale, statistical diagnostics, GRADE synthesis, and passed/failed checklists.
  - Formatted cleanly for Windows codepages without charset errors.
- **Pipeline Integration & Verified Persistence (`src/health_app/relationships/pipeline.py`)**:
  - Enhanced `process_text` to automatically run all 4 phases and print verification audit cards for all extracted claims.
  - Caches verified results to `data/health_relationships_verified.json`.
- **Test Suite (`tests/test_verification.py`)**:
  - Added 16 tests covering study design classification, RoB 2 / ROBINS-I scoring, NLI entailment and contradiction, statistical validation (CI null crossings, directional conflict), GRADE group synthesis, composite scoring, and terminal output.
  - Total test suite status: **31 passed, 0 failed (100% pass rate)**.

---

### Session: 2026-11-02 (Phase 3 - Gemini Relationship Extraction Pipeline)
- **Dependency & Config**:
  - Installed `google-genai` SDK.
  - Added `gemini_api_key` and `gemini_model` (default: `gemini-2.5-flash`) to `src/health_app/config.py` and `.env.example`.
- **Relationship Schema & Models (`src/health_app/relationships/models.py`)**:
  - Implemented `HealthRelationship` capturing `subject`, `relation`, `object`, `condition`, `evidence_quote`, `confidence`, and citation metadata (`authors`, `publish_year`, `doi`, `paper_title`, `chunk_index`).
  - Implemented `ChunkExtractionResult` and `PaperExtractionReport`.
- **Gemini Extractor (`src/health_app/relationships/extractor.py`)**:
  - Implemented `GeminiRelationshipExtractor` sending structured system instructions to `gemini-2.5-flash` with JSON response formatting (`temperature=0.1` for factual grounding).
  - Built fallback rule-based pattern extractor so the app functions seamlessly in offline and testing modes.
- **Terminal Pretty-Printer (`src/health_app/relationships/printer.py`)**:
  - Formatted chunk preview, relationship cards (`[Subject] --> [Relation] --> [Object]`), context, and exact evidence quotes.
- **Pipeline Orchestrator (`src/health_app/relationships/pipeline.py`)**:
  - Implemented `RelationshipPipeline` handling text/PDF chunking, relationship extraction, terminal printing, and persistent caching in `data/health_relationships.json`.
- **Workflow Integrations**:
  - In `src/health_app/fetcher/interactive.py`: Approving a paper (`y`) now automatically triggers relationship extraction and prints chunk-by-chunk findings in the terminal.
  - In `src/health_app/terminal_runner.py`: Added `--extract-relationships` argument.
  - In `src/health_app/menu.py`: Added Option `[7] Extract Health Relationships from Downloaded Papers`.
- **Test Suite (`tests/test_relationships.py`)**:
  - Verified model validation, fallback extraction, chunking pipeline, and cache JSON persistence.
  - Suite status: **15 passed, 0 failed**.

### Session: 2026-11-03 (Gemini Quota Resilience, Multi-Key Failover & Route Optimization)
- **User Request & Issue**:
  User encountered `429 RESOURCE_EXHAUSTED` with `gemini-3.5-flash` ("Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-3.6-flash ... retry in 8h41m") and a `POST /api/sync/trigger 404 Not Found` in server logs, asking: *"do i need new api key? can we use it rn without chnage of api key? if so use it will it affect performance?"*.
- **Investigation & Key Findings**:
  1. Google isolates free-tier quotas per model family: preview model `gemini-3.5-flash` (aliased to `gemini-3.6-flash`) has a strict 20 requests/day cap.
  2. Live empirical API probe revealed that `gemini-flash-lite-latest` and `gemini-3.5-flash-lite` are completely online with unexhausted quota on the user's existing key, generating accurate clinical JSON in 1.36s.
  3. The 404 for `/api/sync/trigger` occurred because the client poller called `/api/sync/trigger`, whereas the backend handler was `/api/health/sync-history`.
- **Architectural Implementation**:
  1. **Config & Defaults (`src/health_app/config.py`, `.env`, `Prescription/.env`)**:
     - Updated default `gemini_model` to `gemini-flash-lite-latest`.
  2. **Model Prioritization & Fallbacks (`src/health_app/dashboard/ask_ai.py`, `src/health_app/prescription/analyzer.py`, `Prescription/src/gemini_client.py`)**:
     - Expanded `FALLBACK_MODELS` to `["gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-3-flash-preview", "gemini-3.5-flash", "gemini-3.6-flash", "gemini-flash-latest"]`.
     - Added `resolve_gemini_api_keys()` supporting comma-separated multi-key failover (`GEMINI_API_KEYS="key1,key2"`).
  3. **Route Aliasing (`src/health_app/dashboard/app.py`, `src/health_app/dashboard/templates/dashboard.html`)**:
     - Added `@app.post("/api/sync/trigger")` alias endpoint invoking `sync_health_history()` logic and returning HTTP 200 with sync status.
     - Updated dashboard poller to handle sync response cleanly without console errors.
- **Verification**:
  - Live Ask AI test with existing key succeeded in 1.4s with zero 429 errors.
  - `/api/sync/trigger` returned `200 OK`.
  - All 11 targeted tests passed in 47.34s.
  - Full test suite passed: **97 / 97 tests passed (100%)** in 325.71s.

### Session: 2026-11-03 (Ask AI Fast Fallback & Complete Clinical Breakdown Rendering)
- **User Request & Issue**:
  User reported query getting stuck at *"Why is my resting heart rate elevated and how does it correlate with my sleep?"* followed by `"No response generated. Peer-Reviewed Literature References: No direct literature citations retrieved for this query"`.
- **Root Cause Analysis**:
  1. **15–30s Ollama Timeout**: In `embeddings.py`, timeout was set to 15s. When `nomic-embed-text` was not loaded, requests hung for 15s on `/api/embed` and another 15s on `/api/embeddings`.
  2. **Key Mismatch in UI**: `ask_clinical_ai_endpoint` returned `{"status": "success", "result": {...}}` with `direct_assessment`, `biomarker_correlation`, `scientific_mechanisms`, `action_plan`, and `cited_papers`. But `dashboard.html` checked `data.answer` and `data.citations`, which were `undefined`, causing fallback to `"No response generated"`.
- **Architectural Implementation**:
  1. **Fast Vector Embedding Timeout & Cooldown Cache (`src/health_app/vectordb/embeddings.py`)**:
     - Reduced timeout from 15s to 3s.
     - Fail fast on timeout/connection error without executing secondary loops.
     - Added `_OLLAMA_FAILED_UNTIL` in-memory cooldown cache (60s). `get_embedding_provider()` instantly yields `MockEmbeddingProvider` during cooldown with 0ms delay.
  2. **Backend API Contract Enrichment (`src/health_app/dashboard/app.py`)**:
     - In `ask_clinical_ai_endpoint`, exposed both `result` and top-level aliases (`answer` and `citations`).
  3. **Comprehensive Clinical Renderer (`src/health_app/dashboard/templates/dashboard.html`)**:
     - Upgraded `renderAskAiOutcome` to parse `data.result || data` and render:
       - Direct Clinical Assessment
       - Personal Biometric & Lifestyle Correlation
       - Biological Mechanisms with Verbatim Evidentiary Quotes
       - 3-Step Clinical Action Plan
       - Red-Flag Physician Escalation Warning
       - Peer-Reviewed Research Citations with Author, Year, Study Design, and Clickable DOI Links.
- **Verification**:
  - Live Ask AI query test returned complete clinical synthesis with 1 peer-reviewed citation (Nguyen et al., 2026, DOI: 10.3746/pnf.2026.104), 1 biological mechanism, and 3 action plan steps.
  - Test suite speedup from 325s to 74.89s (4.3× faster).
  - All 4 tests in `tests/test_ask_ai.py` passed in 12.82s.
  - Full test suite passed: **97 / 97 tests passed (100%)** in 74.89s.

---

## 4. Current Architecture & File Manifest

```
C:\Vikrant\
├── start.cmd                 # Interactive terminal launcher script
├── start.cms                 # Alias launcher script
├── rules.md                  # Mandatory rules (Rule 1 requires progress.md updates)
├── progress.md               # Current living progress log
├── pyproject.toml            # Python packaging & build configuration
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template (includes GEMINI_API_KEY)
├── README.md                 # User guide and terminal command documentation
├── src\
│   └── health_app\
│       ├── __init__.py
│       ├── config.py         # Application settings (dashboard port 8001, secret auto-discovery)
│       ├── menu.py           # Interactive terminal menu (Options 0 to 8)
│       ├── terminal_runner.py# CLI runner (--fetch, --extract-relationships, --dashboard)
│       ├── dashboard\        # Web Health Dashboard & Google Fitness Integration
│       │   ├── __init__.py
│       │   ├── auth.py       # Google OAuth 2.0 flow & credential discovery
│       │   ├── google_health.py # Google Fitness API client (steps, heart rate, sleep)
│       │   ├── baseline_engine.py # 15-day rolling statistical calibration & EWMA drift
│       │   ├── user_profile.py # User lifestyle & risk profile management
│       │   ├── biometric_advisor.py # Scientific paper grounding for biometrics
│       │   ├── app.py        # FastAPI server & route handlers
│       │   └── templates\    # Jinja2 templates (Tailwind CSS & Chart.js)
│       │       ├── base.html
│       │       ├── index.html
│       │       ├── onboarding.html # User lifestyle & risk profile questionnaire
│       │       ├── dashboard.html
│       │       ├── admin_login.html
│       │       └── admin_dashboard.html
│       ├── verification\     # 4-Phase Clinical Verification & Anti-Hallucination Framework
│       │   ├── __init__.py
│       │   ├── models.py     # Verification report and classification schemas
│       │   ├── article_checks.py # Study design (7 tiers) & RoB 2 / ROBINS-I checks
│       │   ├── relationship_checks.py # Laptop Ollama NLI & statistical validation
│       │   ├── evidence_synthesis.py # Adapted GRADE cross-study synthesis
│       │   ├── scoring_engine.py # Non-linear composite scoring & automated gating
│       │   └── terminal_reporter.py # Clinical verification audit card pretty-printer
│       ├── relationships\    # Gemini AI relationship extraction
│       │   ├── __init__.py
│       │   ├── models.py     # HealthRelationship schema
│       │   ├── extractor.py  # Gemini API & fallback extractor
│       │   ├── pipeline.py   # Document chunking & extraction pipeline
│       │   └── printer.py    # Terminal pretty-printer
│       ├── fetcher\          # Research paper search and curation
│       │   ├── __init__.py
│       │   ├── client.py     # Europe PMC & arXiv search client
│       │   ├── downloader.py # PDF downloader with curl fallback
│       │   ├── interactive.py# Terminal curation flow (auto-triggers extraction)
│       │   ├── recovery.py   # Missing PDF repair tool
│       │   └── registry.py   # Persistent index & deduplication manager
│       ├── vectordb\
│       │   ├── __init__.py
│       │   ├── embeddings.py # Ollama & Mock embedding providers
│       │   └── store.py      # ChromaDB collections
│       ├── ingestion\
│       │   ├── __init__.py
│       │   ├── chunker.py    # Document chunker
│       │   └── loader.py     # Markdown/PDF loader
│       └── rag\
│           ├── __init__.py
│           ├── retriever.py  # Semantic retriever
│           └── engine.py     # Grounded advisory synthesizer
├── data\
│   ├── research_papers\      # Scientific papers & downloaded PDFs
│   ├── fssai_regulations\    # FSSAI statutory standards
│   ├── user_profiles\        # Stored user lifestyle and risk profile JSON files
│   ├── user_cache\           # Historical Google Fit cached telemetry by user
│   ├── research_papers_index.json # Registry index of reviewed/downloaded papers
│   ├── health_relationships.json  # Cached extracted clinical relationships
│   └── health_relationships_verified.json # Verified audit reports with scores and gating
└── tests\
    ├── test_pdf_hunter_and_clinical_feed.py # PDF Hunter search/ingest, clinical feed & sidebar tests
    ├── test_personalization_and_baseline.py # Vector DB filtering, 15D baseline & onboarding tests
    ├── test_dashboard.py     # Dashboard, OAuth, Google Fit, and Advisor tests
    ├── test_verification.py  # 4-Phase verification & anti-hallucination tests
    ├── test_relationships.py # Gemini & fallback extraction pipeline tests
    ├── test_paper_fetcher.py # Deduplication & downloader tests
    ├── test_rules_and_progress.py
    ├── test_vector_store.py
    └── test_ingestion_and_rag.py
```

---

## 5. How to Run

```powershell
# 1. Launch interactive menu (select Option 8 to run the Web Health Dashboard):
start.cmd

# 2. Or launch the Web Health Dashboard directly on Port 8001:
python -m health_app.terminal_runner --dashboard

# 3. Access web dashboard in your browser:
#    User Landing & Google Login:  http://localhost:8001/
#    Admin Control Portal:         http://localhost:8001/admin/login (Password: admin123)

# 4. Search and approve new papers (automatically prints relationships upon download):
#    Option A: In terminal via interactive menu Option 6 or CLI:
python -m health_app.terminal_runner --fetch
#    Option B: In-browser via Admin Control Portal PDF Hunter:
#    Navigate to http://localhost:8001/admin/dashboard and search/hunt papers with one click!

# 5. Extract and audit clinical relationships from downloaded papers:
python -m health_app.terminal_runner --extract-relationships

# 6. Run full automated test suite (72 unit tests):
python -m pytest tests/ -v
```

---

## 6. Immediate Next Steps (For Future AI / Developer)
1. **Google Cloud Console User Verification**: Ensure the user has added their email to the "Test users" list under Google Cloud Console > OAuth consent screen so Google allows live authentication.
2. **Google Fitness API Enabled**: Verify Google Fitness API is enabled in Google Cloud Console > APIs & Services > Library.
3. **Live Wearable Testing**: Authenticate with a personal Google account that has Google Fit / Wear OS activity to verify live biometric synchronization.
