from __future__ import annotations

import difflib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from PIL import Image

from health_app.config import settings
from health_app.prescription.models import (
    PrescribedMedicineItem,
    PrescriptionExtractionResult,
    _is_clean_value,
)
from health_app.prescription.preprocessor import ImagePreprocessor

logger = logging.getLogger(__name__)

DEFAULT_MEDICINES_DATA = Path(__file__).resolve().parent.parent.parent.parent / "prescription" / "data" / "medicines.json"

DEFAULT_MODEL = "gemini-flash-lite-latest"
FALLBACK_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-3-flash-preview",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-flash-latest",
]


def resolve_gemini_api_keys(api_key: Optional[str] = None) -> List[str]:
    """Resolve all available Gemini API keys from args, settings, env, or local .env files."""
    keys: List[str] = []

    def _add_candidates(val: Optional[str]):
        if not val:
            return
        # Support comma-separated keys
        for part in str(val).split(","):
            part_clean = part.strip().strip('"').strip("'")
            if part_clean and part_clean not in keys:
                keys.append(part_clean)

    _add_candidates(api_key)
    _add_candidates(settings.gemini_api_key)
    _add_candidates(os.environ.get("GEMINI_API_KEYS"))
    _add_candidates(os.environ.get("GEMINI_API_KEY"))

    # Check potential .env files across project directories
    search_paths = [
        Path(".env"),
        Path("Prescription/.env"),
        Path("prescription/.env"),
        Path(__file__).resolve().parent.parent.parent.parent / "Prescription" / ".env",
        Path(__file__).resolve().parent.parent.parent.parent / ".env",
    ]
    for p in search_paths:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GEMINI_API_KEY=") or line.startswith("GEMINI_API_KEYS="):
                            k = line.split("=", 1)[1].strip()
                            _add_candidates(k)
            except Exception:
                pass

    return keys


def resolve_gemini_api_key(api_key: Optional[str] = None) -> str:
    """Resolve primary Gemini API key (backward-compatible)."""
    keys = resolve_gemini_api_keys(api_key)
    return keys[0] if keys else ""

PRESCRIPTION_VISION_PROMPT = """You are a clinical document transcription assistant.
Analyze this medical prescription image carefully and extract all visible details.

Extract the following information:
1. "prescriber_name": Full name of the doctor / physician (e.g. "Dr. Sarah Jenkins, MD") if visible, else null.
2. "clinic_or_place": Name of the hospital, clinic, health center, city, or address (e.g. "Metro Health Cardiology Clinic, Boston") if visible, else null.
3. "prescription_date": Date written on the prescription (e.g. "2026-03-15") if visible, else null.
4. "diagnosed_diseases": Array of strings of any diagnosed conditions, indications, symptoms, or diseases written (e.g. ["Essential Hypertension", "Type 2 Diabetes", "Upper Respiratory Infection"]). If none stated, return empty array [].
5. "medicines": Array of prescribed medications with visible attributes:
   - "name": Medicine brand or generic name (e.g. "Amoxicillin", "Atorvastatin")
   - "strength": Dose per unit if visible (e.g. "500 mg", "20 mg"), else null
   - "dosage": Amount to take per administration (e.g. "1 tablet", "2 puffs"), else null
   - "frequency": How often to take (e.g. "Once daily at night", "Twice daily after meals", "TDS", "BID", "PRN"), else null
   - "duration": Length of course (e.g. "7 days", "1 month"), else null
   - "route": Administration route (e.g. "Oral", "Inhalation", "Topical"), else null
   - "instructions": Special instructions (e.g. "Take after food with plenty of water"), else null
6. "raw_transcription": A concise plain-text transcription of all legible text on the prescription.
7. "overall_confidence": "high", "medium", or "low".
8. "model_uncertainty_notes": Any notes regarding illegible handwriting or cut-off corners, else null.

CRITICAL RULES:
- Transcribe ONLY what is clearly visible. NEVER invent or guess doses, medicines, or diagnoses.
- If a field is not present or unreadable, set it to null. Do NOT return strings like "Not Found" or "N/A".
- Return ONLY valid JSON matching this structure.
"""


class PrescriptionAnalyzer:
    """Extracts clinical entities from prescription images using Gemini Vision with dictionary verification."""

    def __init__(self, dictionary_path: Optional[Path] = None):
        self.dictionary_path = dictionary_path or DEFAULT_MEDICINES_DATA
        self._medicine_choices: List[str] = []
        self._load_dictionary()

    def _load_dictionary(self) -> None:
        if self.dictionary_path and self.dictionary_path.exists():
            try:
                with open(self.dictionary_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                choices = []
                for entry in data.get("medicines", []):
                    choices.append(entry.get("name", ""))
                    for alias in entry.get("aliases", []):
                        choices.append(alias)
                self._medicine_choices = [c for c in choices if c]
            except Exception as e:
                logger.warning(f"Could not load medicines dictionary from {self.dictionary_path}: {e}")

    def suggest_medicine_name(self, raw_name: str) -> Optional[str]:
        """Suggest matching standard medicine name if close match found."""
        if not raw_name or not self._medicine_choices:
            return None
        matches = difflib.get_close_matches(raw_name, self._medicine_choices, n=1, cutoff=0.75)
        return matches[0] if matches else None

    @classmethod
    def _extract_json(cls, text: str) -> Dict[str, Any]:
        """Extract and parse JSON object from LLM response text."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise ValueError(f"Could not extract valid JSON from response: {text[:200]}")

    def analyze_image(
        self,
        image_source: Union[bytes, str, Image.Image],
        api_key: Optional[str] = None,
    ) -> PrescriptionExtractionResult:
        """Run preprocessing, Gemini Vision extraction, dictionary normalization, and empty field filtering."""
        preprocessed = ImagePreprocessor.preprocess(image_source)
        model_input_pil = preprocessed.processed_pil

        keys = resolve_gemini_api_keys(api_key)

        if keys:
            preferred_model = settings.gemini_model or DEFAULT_MODEL
            models_to_try = [preferred_model]
            for m in FALLBACK_MODELS:
                if m not in models_to_try:
                    models_to_try.append(m)

            last_error: Optional[Exception] = None
            for key in keys:
                try:
                    from google import genai
                    from google.genai import types

                    client = genai.Client(api_key=key)

                    config = types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json",
                    )

                    for model_name in models_to_try:
                        try:
                            logger.info(f"Attempting prescription extraction with model: {model_name}")
                            resp = client.models.generate_content(
                                model=model_name,
                                contents=[PRESCRIPTION_VISION_PROMPT, model_input_pil],
                                config=config,
                            )
                            if resp.text:
                                raw_dict = self._extract_json(resp.text)
                                result = self._build_result(raw_dict)
                                logger.info(
                                    f"Prescription extracted successfully with {model_name}: "
                                    f"doctor='{result.prescriber_name}', diseases={len(result.diagnosed_diseases)}, "
                                    f"medicines={len(result.medicines)}"
                                )
                                return result
                        except Exception as err:
                            logger.warning(f"Extraction failed with model {model_name}: {err}")
                            last_error = err
                            continue
                except Exception as e:
                    logger.error(f"Gemini Vision client setup failed: {e}")
                    last_error = e

            logger.error(f"All Gemini models/keys exhausted, falling back to heuristic parser: {last_error}")
        else:
            logger.warning("No GEMINI_API_KEY could be resolved from environment, settings, or .env files.")

        # Deterministic / offline fallback parser
        return self._fallback_extraction(preprocessed.original_pil)

    def _build_result(self, raw: Dict[str, Any]) -> PrescriptionExtractionResult:
        """Build validated PrescriptionExtractionResult normalizing missing and unclear fields."""
        doc = raw.get("prescriber_name")
        clinic = raw.get("clinic_or_place")
        date_str = raw.get("prescription_date")
        raw_text = raw.get("raw_transcription")
        conf = raw.get("overall_confidence", "medium")
        notes = raw.get("model_uncertainty_notes")

        # Diseases
        raw_diseases = raw.get("diagnosed_diseases", [])
        clean_diseases = []
        if isinstance(raw_diseases, list):
            for d in raw_diseases:
                if isinstance(d, str) and _is_clean_value(d):
                    clean_diseases.append(d.strip())

        # Medicines
        med_items: List[PrescribedMedicineItem] = []
        raw_meds = raw.get("medicines", [])
        if isinstance(raw_meds, list):
            for item in raw_meds:
                if not isinstance(item, dict):
                    continue
                name = item.get("name") or item.get("medicine_name_original")
                if not _is_clean_value(name):
                    continue
                name_str = str(name).strip()

                # Optional spelling suggestion if dictionary matches
                suggestion = self.suggest_medicine_name(name_str)
                notes_val = item.get("notes")
                if suggestion and suggestion.lower() != name_str.lower():
                    notes_val = f"Spelling suggestion: {suggestion}" if not notes_val else f"{notes_val} (Suggestion: {suggestion})"

                med = PrescribedMedicineItem(
                    name=name_str,
                    strength=str(item["strength"]).strip() if _is_clean_value(item.get("strength")) else None,
                    dosage=str(item["dosage"]).strip() if _is_clean_value(item.get("dosage")) else None,
                    frequency=str(item["frequency"]).strip() if _is_clean_value(item.get("frequency")) else None,
                    duration=str(item["duration"]).strip() if _is_clean_value(item.get("duration")) else None,
                    route=str(item["route"]).strip() if _is_clean_value(item.get("route")) else None,
                    instructions=str(item["instructions"]).strip() if _is_clean_value(item.get("instructions")) else None,
                    notes=notes_val,
                    included=True,
                )
                med_items.append(med)

        return PrescriptionExtractionResult(
            prescriber_name=str(doc).strip() if _is_clean_value(doc) else None,
            clinic_or_place=str(clinic).strip() if _is_clean_value(clinic) else None,
            prescription_date=str(date_str).strip() if _is_clean_value(date_str) else None,
            diagnosed_diseases=clean_diseases,
            medicines=med_items,
            overall_confidence=conf if conf in ["high", "medium", "low"] else "medium",
            raw_transcription=str(raw_text).strip() if _is_clean_value(raw_text) else None,
            model_uncertainty_notes=str(notes).strip() if _is_clean_value(notes) else None,
        )

    def _fallback_extraction(self, image: Image.Image) -> PrescriptionExtractionResult:
        """Deterministic fallback when vision API is unavailable."""
        return PrescriptionExtractionResult(
            prescriber_name=None,
            clinic_or_place=None,
            prescription_date=None,
            diagnosed_diseases=[],
            medicines=[],
            overall_confidence="low",
            raw_transcription="Prescription image received. Live Gemini Vision analysis was not reachable; you can manually add fields below.",
            model_uncertainty_notes="Vision API unavailable. Please verify details manually.",
        )
