from __future__ import annotations

import json
import os
import re

from google import genai
from google.genai import types
from PIL import Image

from src.models import MedicineItem, PrescriptionExtraction

DEFAULT_MODEL = "gemini-flash-lite-latest"
FALLBACK_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-3-flash-preview",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-flash-latest",
]

EXTRACTION_PROMPT = """You are a medical prescription transcription assistant, not a doctor.

Read the handwritten or printed prescription image carefully.

Rules you MUST follow:
1. Transcribe only what is visible. Never invent a medicine, dose, frequency, duration, or route.
2. If a word or number is unreadable, set that field to "unclear".
3. Keep original_transcription fields as the closest literal reading, including misspellings.
4. You may propose a spelling suggestion in medicine_name_suggestion only when the letters are readable but possibly misspelled. Do not replace the original field.
5. Do not diagnose, prescribe, or complete missing clinical details.
6. Return JSON only, matching this schema:

{
  "patient_name_original": "string or unclear",
  "prescriber_name_original": "string or unclear",
  "date_original": "string or unclear",
  "raw_transcription": "full visible text as faithfully as possible",
  "overall_confidence": "high | medium | low",
  "model_uncertainty_notes": "string",
  "medicines": [
    {
      "medicine_name_original": "string or unclear",
      "medicine_name_suggestion": "string or null",
      "strength_original": "string or unclear",
      "dosage_original": "string or unclear",
      "frequency_original": "string or unclear",
      "duration_original": "string or unclear",
      "route_original": "string or unclear",
      "special_instructions_original": "string or unclear",
      "unclear_fields": ["field names that were hard to read"],
      "notes": "optional"
    }
  ]
}
"""


class GeminiConfigError(RuntimeError):
    pass


class GeminiExtractionError(RuntimeError):
    pass


def get_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "").strip()


def get_model_name() -> str:
    return os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def require_api_key(api_key: str | None = None) -> str:
    key = (api_key or get_api_key()).strip()
    if not key:
        raise GeminiConfigError(
            "GEMINI_API_KEY is missing. Copy .env.example to .env and add your key."
        )
    return key


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise GeminiExtractionError("The model did not return valid JSON.")
        return json.loads(match.group(0))


def _candidate_models(preferred: str | None = None) -> list[str]:
    pref = (preferred or get_model_name()).strip()
    candidates = [pref] if pref else []
    for name in FALLBACK_MODELS:
        if name not in candidates:
            candidates.append(name)
    return candidates


def _generate(image: Image.Image, api_key: str, preferred_model: str | None = None):
    client = genai.Client(api_key=api_key)
    attempted_errors: list[str] = []
    config = types.GenerateContentConfig(
        temperature=0.1,
        response_mime_type="application/json",
    )
    for model_name in _candidate_models(preferred_model):
        try:
            return client.models.generate_content(
                model=model_name,
                contents=[EXTRACTION_PROMPT, image],
                config=config,
            )
        except Exception as exc:  # noqa: BLE001 - try the next available model
            attempted_errors.append(f"{model_name} ({exc})")
            continue
    error_summary = "; ".join(attempted_errors)
    raise GeminiExtractionError(f"Gemini request failed: {error_summary}")


def extract_prescription(
    image: Image.Image,
    api_key: str | None = None,
    model_name: str | None = None,
) -> PrescriptionExtraction:
    key = require_api_key(api_key)
    response = _generate(image, key, preferred_model=model_name)
    text = (getattr(response, "text", None) or "").strip()
    if not text:
        candidates = getattr(response, "candidates", None)
        finish_reason = ""
        if candidates and len(candidates) > 0:
            finish_reason = getattr(candidates[0], "finish_reason", "")
        detail = f" (finish_reason: {finish_reason})" if finish_reason else ""
        raise GeminiExtractionError(f"Gemini returned an empty response{detail}.")

    try:
        payload = _extract_json(text)
        extraction = PrescriptionExtraction.model_validate(payload)
    except Exception as exc:  # noqa: BLE001
        raise GeminiExtractionError(f"Could not parse extraction JSON: {exc}") from exc

    if extraction.overall_confidence not in {"high", "medium", "low"}:
        extraction.overall_confidence = "low"
    if not extraction.medicines:
        extraction.medicines = [MedicineItem()]
        extraction.extraction_errors.append("No medicines found in the model output.")
    return extraction
