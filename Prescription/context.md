# Project Context: RxScribe (Handwritten Prescription Reader)

## 1. Project Overview
RxScribe is a local Python web application built with Streamlit and Google Gemini Vision. It assists human reviewers (clinicians, pharmacists, or administrative reviewers) in transcribing handwritten and printed medical prescriptions into structured, verifiable digital data.

### Core Philosophy
- **Transcription Assistant, Not a Doctor**: Never invents medicines, doses, frequencies, or directions.
- **Human Verification Required**: Uncertain fields remain flagged as `"unclear"`. Spelling suggestions are never auto-applied to prescription items.
- **Auditable Output**: Generates human-verified JSON and PDF reports noting all discrepancies, confidence levels, and reviewer confirmations.

---

## 2. Tech Stack & Dependencies
- **Language**: Python 3.10+ (tested on Python 3.12)
- **Frontend / Dashboard**: Streamlit (`streamlit>=1.32.0`)
- **Image Processing**: OpenCV (`opencv-python-headless>=4.9.0`), Pillow (`Pillow>=10.2.0`), NumPy (`numpy>=1.26.0`)
- **Multimodal AI**: Google GenAI SDK (`google-genai>=1.0.0`)
- **Fuzzy Matching / Dictionary**: RapidFuzz (`rapidfuzz>=3.6.0`)
- **Data Validation & Schemas**: Pydantic (`pydantic>=2.6.0`)
- **Exporting**: ReportLab (`reportlab>=4.1.0`)
- **Testing**: Pytest (`pytest>=8.0.0`)

---

## 3. Architecture & Codebase Map

```
prescription-reader/
├── start.cmd                # One-click Windows launcher (opens app in default browser)
├── app.py                   # Streamlit web UI, session state, UI rendering
├── context.md               # Project context and agent operating guidelines (this file)
├── agent_rules.md           # Core agent rules and coding constraints
├── requirements.txt         # Dependencies
├── pytest.ini               # Test configuration
├── .env / .env.example      # Environment variables (GEMINI_API_KEY, GEMINI_MODEL)
├── assets/
│   └── styles.css           # Custom styling for Streamlit UI
├── data/
│   ├── medicines.json       # Reference medical dictionary (names, routes, frequencies)
│   └── sample_prescription.png # Test prescription image
├── src/
│   ├── __init__.py
│   ├── gemini_client.py     # Gemini Vision API client, prompt, model fallbacks, JSON parsing
│   ├── preprocessing.py     # OpenCV deskewing, CLAHE, adaptive thresholding previews
│   ├── models.py            # Pydantic schemas (MedicineItem, PrescriptionExtraction, etc.)
│   ├── validation.py        # RapidFuzz fuzzy checks against medicines.json & unit validation
│   └── export.py            # JSON and PDF export generation
└── tests/
    ├── test_export.py       # PDF and JSON export generation tests
    ├── test_gemini_parse.py # JSON extraction & response parsing tests
    ├── test_preprocessing.py# Skew detection, CLAHE, and image transform tests
    └── test_validation.py   # Dictionary lookup, unit check, and issue flagging tests
```

---

## 4. Processing Pipeline
1. **Upload & Preprocessing** (`src/preprocessing.py`):
   - Computes grayscale, CLAHE (Contrast Limited Adaptive Histogram Equalization), and skew angle.
   - Generates deskewed image and adaptive threshold binary image for human inspection.
   - Retains color deskewed image for multimodal LLM vision to preserve pen ink shades (blue, black) and stamps.
2. **Gemini Extraction** (`src/gemini_client.py`):
   - Invokes Google Gemini Vision (`gemini-3.5-flash` by default, with automatic fallback to `gemini-3.5-flash-lite`, `gemini-3.8-flash`, etc.).
   - Uses strict JSON schema enforcement via `response_mime_type="application/json"`.
   - Populates `PrescriptionExtraction` schema.
3. **Medical Validation** (`src/validation.py`):
   - Compares medicine names against `data/medicines.json` using `rapidfuzz.process.extract`.
   - Validates dosage units and standard routes/frequencies.
   - Highlights unclear fields without overriding transcribed text.
4. **Human Review & Export** (`app.py`, `src/export.py`):
   - Interactive `st.data_editor` for reviewer correction.
   - Review confirmation checkbox required for "verified" status.
   - One-click export to structured JSON and formatted PDF.

---

## 5. Gemini Models Reference
- **Active Primary Model**: `gemini-3.5-flash` (balanced speed, multimodal accuracy, and low latency).
- **Lightweight Alternative**: `gemini-3.5-flash-lite` (ultra-fast transcription fallback).
- **Advanced Alternatives**: `gemini-3.8-flash`, `gemini-flash-latest`.
- **Deprecated / Incompatible Models**: `gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-1.5-flash` (return 404/API version errors).

---

## 6. How to Run
- **Windows One-Click**: Double-click `start.cmd` in the project root. It validates the environment, creates `.env` if missing, starts the Streamlit server, and launches the dashboard in your default browser.
- **Manual Launch**:
  ```powershell
  .\.venv\Scripts\streamlit run app.py
  ```

---

## 7. Operating Rules for Agents
For detailed rules, see [`agent_rules.md`](file:///C:/Users/LENOVO/Desktop/ai/prescription-reader/agent_rules.md).
- **Rule 1**: Maintain this `context.md` file whenever changes to architecture, dependencies, or workflows are made.
