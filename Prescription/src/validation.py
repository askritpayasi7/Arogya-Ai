from __future__ import annotations

import json
import re
from pathlib import Path

from rapidfuzz import fuzz, process

from src.models import (
    FieldSuggestion,
    MedicineItem,
    PrescriptionExtraction,
    ValidatedMedicine,
    ValidationIssue,
    ValidationReport,
)

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "medicines.json"

UNCLEAR_VALUES = {"", "unclear", "illegible", "unknown", "n/a", "na", "none", "null"}

REQUIRED_FIELDS = [
    "medicine_name_original",
    "strength_original",
    "dosage_original",
    "frequency_original",
    "duration_original",
    "route_original",
]

UNIT_PATTERN = re.compile(
    r"^\s*(\d+(\.\d+)?\s*)?(mg|mcg|µg|ug|g|ml|mL|%|iu|IU|units?|meq|mEq|mmol|"
    r"tablet(s)?|tab(s)?|cap(s)?|capsule(s)?|drop(s)?|puff(s)?|tsp|tbsp|"
    r"unit(s)?)\b",
    re.IGNORECASE,
)

STRENGTH_HINT = re.compile(
    r"\d+(\.\d+)?\s*(mg|mcg|µg|ug|g|ml|%|iu|units?)",
    re.IGNORECASE,
)


def _is_unclear(value: str | None) -> bool:
    if value is None:
        return True
    return value.strip().lower() in UNCLEAR_VALUES


def load_dictionary(path: Path | None = None) -> dict:
    dictionary_path = path or DATA_PATH
    with dictionary_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _name_choices(dictionary: dict) -> list[str]:
    choices: list[str] = []
    for entry in dictionary.get("medicines", []):
        choices.append(entry["name"])
        choices.extend(entry.get("aliases", []))
    return choices


def suggest_term(query: str, choices: list[str], limit: int = 3) -> list[tuple[str, float]]:
    if _is_unclear(query):
        return []
    matches = process.extract(query, choices, scorer=fuzz.WRatio, limit=limit)
    return [(name, float(score)) for name, score, _ in matches if score >= 70]


def validate_unit(value: str) -> bool:
    if _is_unclear(value):
        return False
    return bool(UNIT_PATTERN.search(value) or STRENGTH_HINT.search(value))


def validate_extraction(
    extraction: PrescriptionExtraction,
    dictionary: dict | None = None,
) -> ValidationReport:
    dictionary = dictionary or load_dictionary()
    medicine_choices = _name_choices(dictionary)
    route_choices = dictionary.get("routes", [])
    frequency_choices = dictionary.get("frequencies", [])

    report = ValidationReport(requires_human_review=True)
    global_issues: list[ValidationIssue] = [
        ValidationIssue(
            level="critical",
            message=(
                "This tool is a transcription assistant only. A qualified clinician "
                "or pharmacist must verify every field before anyone uses the result."
            ),
        )
    ]

    if not extraction.medicines:
        global_issues.append(
            ValidationIssue(
                level="warning",
                message="No medicines were extracted. The image may be unreadable.",
            )
        )

    if extraction.overall_confidence.lower() != "high":
        global_issues.append(
            ValidationIssue(
                level="warning",
                message=f"Model confidence is '{extraction.overall_confidence}', not confirmed.",
            )
        )

    for index, item in enumerate(extraction.medicines):
        validated = _validate_medicine(
            item,
            index,
            medicine_choices,
            route_choices,
            frequency_choices,
        )
        report.medicines.append(validated)
        report.missing_count += len(validated.missing_fields)
        report.unclear_count += len(item.unclear_fields)
        report.suggestion_count += len(validated.suggestions)
        report.issues.extend(validated.issues)

    report.issues = global_issues + report.issues
    return report


def _validate_medicine(
    item: MedicineItem,
    index: int,
    medicine_choices: list[str],
    route_choices: list[str],
    frequency_choices: list[str],
) -> ValidatedMedicine:
    issues: list[ValidationIssue] = []
    suggestions: list[FieldSuggestion] = []
    missing: list[str] = []

    for field in REQUIRED_FIELDS:
        value = getattr(item, field)
        if _is_unclear(value):
            missing.append(field)
            issues.append(
                ValidationIssue(
                    level="warning",
                    message=f"Missing or unclear: {field.replace('_original', '').replace('_', ' ')}",
                    field=field,
                    medicine_index=index,
                )
            )

    name_matches = suggest_term(item.medicine_name_original, medicine_choices)
    if name_matches:
        best_name, best_score = name_matches[0]
        if best_name.lower() != item.medicine_name_original.lower():
            suggestions.append(
                FieldSuggestion(
                    field="medicine_name",
                    original=item.medicine_name_original,
                    suggestion=best_name,
                    similarity=best_score,
                    auto_applied=False,
                )
            )
            issues.append(
                ValidationIssue(
                    level="info",
                    message=(
                        f"Possible medicine name match: '{best_name}' "
                        f"({best_score:.0f}% similar). Not applied automatically."
                    ),
                    field="medicine_name_original",
                    medicine_index=index,
                )
            )

    if not _is_unclear(item.route_original):
        route_matches = suggest_term(item.route_original, route_choices)
        if route_matches and route_matches[0][0].lower() != item.route_original.lower():
            suggestions.append(
                FieldSuggestion(
                    field="route",
                    original=item.route_original,
                    suggestion=route_matches[0][0],
                    similarity=route_matches[0][1],
                    auto_applied=False,
                )
            )

    if not _is_unclear(item.frequency_original):
        freq_matches = suggest_term(item.frequency_original, frequency_choices)
        if freq_matches and freq_matches[0][0].lower() != item.frequency_original.lower():
            suggestions.append(
                FieldSuggestion(
                    field="frequency",
                    original=item.frequency_original,
                    suggestion=freq_matches[0][0],
                    similarity=freq_matches[0][1],
                    auto_applied=False,
                )
            )

    unit_ok = True
    if not _is_unclear(item.strength_original):
        unit_ok = validate_unit(item.strength_original)
        if not unit_ok:
            issues.append(
                ValidationIssue(
                    level="warning",
                    message=f"Strength '{item.strength_original}' does not look like a standard unit.",
                    field="strength_original",
                    medicine_index=index,
                )
            )

    if item.unclear_fields:
        issues.append(
            ValidationIssue(
                level="warning",
                message="Model marked fields as unclear: " + ", ".join(item.unclear_fields),
                medicine_index=index,
            )
        )

    return ValidatedMedicine(
        item=item,
        suggestions=suggestions,
        issues=issues,
        missing_fields=missing,
        unit_ok=unit_ok,
    )
