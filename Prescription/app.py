from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from PIL import Image

from src.export import to_json_bytes, to_pdf_bytes
from src.gemini_client import (
    DEFAULT_MODEL,
    FALLBACK_MODELS,
    GeminiConfigError,
    GeminiExtractionError,
    extract_prescription,
    get_api_key,
    get_model_name,
)
from src.models import PrescriptionExtraction, ValidationReport
from src.preprocessing import bgr_to_pil, preprocess_prescription
from src.validation import validate_extraction

load_dotenv()

ROOT = Path(__file__).resolve().parent
CSS_PATH = ROOT / "assets" / "styles.css"

st.set_page_config(
    page_title="RxScribe | Prescription Transcription Assistant",
    page_icon="🩺",
    layout="wide",
)

if CSS_PATH.exists():
    st.markdown(f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def init_state() -> None:
    defaults = {
        "extraction": None,
        "report": None,
        "preprocess": None,
        "uploaded_name": None,
        "error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_header() -> None:
    st.markdown(
        """
        <div class="hero">
          <h1>RxScribe — Handwritten Prescription Reader</h1>
          <p>Upload a prescription photo. The app enhances the image, transcribes visible handwriting
          with Gemini, and flags uncertain fields for human review. It does not diagnose or prescribe.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="safety-banner">
          <strong>Human verification required.</strong>
          Uncertain medicine names, dosages, and frequencies are never treated as confirmed.
          Do not dispense, administer, or change treatment from this output.
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar() -> dict:
    st.sidebar.header("Settings")
    api_key = os.getenv("GEMINI_API_KEY", "")
    if api_key:
        st.sidebar.success("Gemini API key loaded from environment.")
    else:
        st.sidebar.warning("No GEMINI_API_KEY found in .env")
        api_key = st.sidebar.text_input(
            "Paste Gemini API key for this session",
            type="password",
            help="The key stays in this browser session only. Prefer a .env file.",
        )

    current_env_model = get_model_name()
    model_options = FALLBACK_MODELS.copy()
    if current_env_model not in model_options:
        model_options.insert(0, current_env_model)

    default_index = model_options.index(current_env_model) if current_env_model in model_options else 0
    selected_model = st.sidebar.selectbox(
        "Gemini Model",
        options=model_options,
        index=default_index,
        help="Recommended: gemini-3.5-flash for balanced quality and speed, or gemini-3.5-flash-lite for ultra-fast latency.",
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "Tips for better photos: even lighting, no flash glare, fill the frame, "
        "avoid heavy shadows, keep the paper flat."
    )
    return {"api_key": api_key.strip(), "model": selected_model}


def run_pipeline(image: Image.Image, api_key: str, model_name: str | None = None) -> None:
    st.session_state.error = None
    processed = preprocess_prescription(image)
    st.session_state.preprocess = processed
    model_image = bgr_to_pil(processed.model_input)
    extraction = extract_prescription(model_image, api_key=api_key or None, model_name=model_name)
    report = validate_extraction(extraction)
    st.session_state.extraction = extraction
    st.session_state.report = report


def show_previews() -> None:
    processed = st.session_state.preprocess
    if processed is None:
        st.info("Upload a prescription image to see original and processed previews.")
        return

    st.subheader("Image preprocessing")
    st.caption(
        f"Detected skew: {processed.skew_angle:.2f}°. "
        "Deskewed full-color image is sent to Gemini to preserve ink nuances and stamps. "
        "Adaptive thresholding is a preview aid for human inspection."
    )
    col1, col2, col3, col4 = st.columns(4)
    col1.image(bgr_to_pil(processed.original_bgr), caption="Original")
    col2.image(processed.grayscale, caption="Grayscale")
    col3.image(bgr_to_pil(processed.model_input), caption="Deskewed (model input)")
    col4.image(processed.thresholded, caption="Adaptive threshold (preview)")


def show_issues(report: ValidationReport) -> None:
    st.subheader("Uncertainty warnings")
    for issue in report.issues:
        if issue.level == "critical":
            st.error(issue.message)
        elif issue.level == "warning":
            st.warning(issue.message)
        else:
            st.info(issue.message)


def medicines_table(extraction: PrescriptionExtraction) -> pd.DataFrame:
    rows = []
    for index, item in enumerate(extraction.medicines, start=1):
        rows.append(
            {
                "item": index,
                "medicine_original": item.medicine_name_original,
                "medicine_suggestion": item.medicine_name_suggestion or "",
                "strength": item.strength_original,
                "dosage": item.dosage_original,
                "frequency": item.frequency_original,
                "duration": item.duration_original,
                "route": item.route_original,
                "instructions": item.special_instructions_original,
                "unclear_fields": ", ".join(item.unclear_fields),
                "confirmed": False,
            }
        )
    return pd.DataFrame(rows)


def show_results() -> None:
    extraction: PrescriptionExtraction | None = st.session_state.extraction
    report: ValidationReport | None = st.session_state.report
    if extraction is None or report is None:
        return

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Medicines found", len(extraction.medicines))
    m2.metric("Unclear fields", report.unclear_count)
    m3.metric("Missing fields", report.missing_count)
    m4.metric("Spelling suggestions", report.suggestion_count)

    show_issues(report)

    left, right = st.columns((1.2, 1))
    with left:
        st.subheader("AI extraction results")
        st.write(
            {
                "patient_name_original": extraction.patient_name_original,
                "prescriber_name_original": extraction.prescriber_name_original,
                "date_original": extraction.date_original,
                "overall_confidence": extraction.overall_confidence,
                "model_uncertainty_notes": extraction.model_uncertainty_notes,
            }
        )
        st.markdown("**Literal transcription**")
        st.text_area(
            "Raw visible text",
            extraction.raw_transcription or "unclear",
            height=140,
            label_visibility="collapsed",
        )
    with right:
        st.subheader("Suggestions for review")
        st.caption("Suggestions are never auto-applied to medicine names or doses.")
        any_suggestion = False
        for index, validated in enumerate(report.medicines, start=1):
            for suggestion in validated.suggestions:
                any_suggestion = True
                st.write(
                    f"Item {index} · {suggestion.field}: `{suggestion.original}` → "
                    f"`{suggestion.suggestion}` ({suggestion.similarity:.0f}% similar)"
                )
        if not any_suggestion:
            st.write("No dictionary suggestions.")

    st.subheader("Medicine information — human correction")
    st.caption(
        "Edit the original transcription if you can read the prescription more accurately. "
        "Tick Confirmed only for fields you have personally verified against the image."
    )
    edited = st.data_editor(
        medicines_table(extraction),
        use_container_width=True,
        hide_index=True,
        column_config={
            "confirmed": st.column_config.CheckboxColumn(
                "Confirmed by reviewer",
                help="Leave unchecked unless you verified this row against the original prescription.",
            )
        },
    )

    reviewer_notes = st.text_area("Reviewer notes", placeholder="Describe anything still uncertain.")
    verified = st.checkbox(
        "I am a qualified reviewer and I verified this transcription against the original prescription."
    )
    if not verified:
        st.warning("Downloads are labeled unverified until you complete the confirmation above.")

    json_bytes = to_json_bytes(
        extraction,
        report,
        verified,
        reviewer_notes,
        corrections=edited.to_dict(orient="records"),
    )
    pdf_bytes = to_pdf_bytes(
        extraction,
        report,
        verified,
        reviewer_notes,
        corrections=edited.to_dict(orient="records"),
    )
    d1, d2 = st.columns(2)
    d1.download_button(
        "Download JSON",
        data=json_bytes,
        file_name="prescription_transcription.json",
        mime="application/json",
    )
    d2.download_button(
        "Download PDF",
        data=pdf_bytes,
        file_name="prescription_transcription.pdf",
        mime="application/pdf",
    )


def main() -> None:
    init_state()
    render_header()
    settings = sidebar()

    uploaded = st.file_uploader(
        "Upload or photograph a prescription",
        type=["png", "jpg", "jpeg", "webp", "tif", "tiff"],
        accept_multiple_files=False,
    )

    if uploaded is not None:
        # Detect new image upload and reset stale state
        if st.session_state.uploaded_name != uploaded.name:
            st.session_state.uploaded_name = uploaded.name
            st.session_state.preprocess = None
            st.session_state.extraction = None
            st.session_state.report = None
            st.session_state.error = None

        image = Image.open(uploaded)
        process = st.button("Process prescription", type="primary")
        if process:
            if not settings["api_key"] and not get_api_key():
                st.session_state.error = (
                    "Add GEMINI_API_KEY to a .env file, or paste a key in the sidebar."
                )
            else:
                model_used = settings.get("model") or get_model_name()
                with st.spinner(f"Enhancing image and reading handwriting with {model_used}…"):
                    try:
                        run_pipeline(image, settings["api_key"], model_name=model_used)
                    except (GeminiConfigError, GeminiExtractionError, ValueError, OSError) as exc:
                        st.session_state.error = str(exc)
                        st.session_state.extraction = None
                        st.session_state.report = None

        if st.session_state.preprocess is None:
            preview = preprocess_prescription(image)
            st.session_state.preprocess = preview

    if st.session_state.error:
        st.error(st.session_state.error)
        st.info("Tip: If you encounter high traffic (503) or latency, try selecting 'gemini-3.5-flash-lite' from the sidebar settings.")

    show_previews()
    show_results()


if __name__ == "__main__":
    main()
