from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MedicineItem(BaseModel):
    medicine_name_original: str = Field(
        default="unclear",
        description="Exact transcription of the medicine name as seen on the prescription.",
    )
    medicine_name_suggestion: str | None = Field(
        default=None,
        description="Optional spelling suggestion. Never treat this as confirmed.",
    )
    strength_original: str = "unclear"
    dosage_original: str = "unclear"
    frequency_original: str = "unclear"
    duration_original: str = "unclear"
    route_original: str = "unclear"
    special_instructions_original: str = "unclear"
    unclear_fields: list[str] = Field(default_factory=list)
    notes: str = ""


class PrescriptionExtraction(BaseModel):
    patient_name_original: str = "unclear"
    prescriber_name_original: str = "unclear"
    date_original: str = "unclear"
    raw_transcription: str = ""
    medicines: list[MedicineItem] = Field(default_factory=list)
    overall_confidence: str = Field(
        default="low",
        description="Model self-assessment only: high, medium, or low. Not a clinical guarantee.",
    )
    model_uncertainty_notes: str = ""
    extraction_errors: list[str] = Field(default_factory=list)


class FieldSuggestion(BaseModel):
    field: str
    original: str
    suggestion: str
    similarity: float
    auto_applied: bool = False


class ValidationIssue(BaseModel):
    level: str
    message: str
    field: str | None = None
    medicine_index: int | None = None


class ValidatedMedicine(BaseModel):
    item: MedicineItem
    suggestions: list[FieldSuggestion] = Field(default_factory=list)
    issues: list[ValidationIssue] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    unit_ok: bool = True


class ValidationReport(BaseModel):
    medicines: list[ValidatedMedicine] = Field(default_factory=list)
    issues: list[ValidationIssue] = Field(default_factory=list)
    missing_count: int = 0
    unclear_count: int = 0
    suggestion_count: int = 0
    requires_human_review: bool = True

    def to_serializable(self) -> dict[str, Any]:
        return self.model_dump()
