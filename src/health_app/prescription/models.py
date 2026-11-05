from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

UNCLEAR_STRINGS = {"", "unclear", "none", "null", "n/a", "na", "unknown", "illegible"}


def _is_clean_value(val: Any) -> bool:
    """Check if value is meaningful and not a placeholder."""
    if val is None:
        return False
    if isinstance(val, str):
        return val.strip().lower() not in UNCLEAR_STRINGS
    return True


class PrescribedMedicineItem(BaseModel):
    name: str
    strength: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    route: Optional[str] = None
    instructions: Optional[str] = None
    notes: Optional[str] = None
    included: bool = True

    def to_compact_dict(self) -> Dict[str, Any]:
        """Return dict omitting any null, empty, or unclear placeholder fields."""
        data: Dict[str, Any] = {"name": self.name.strip(), "included": self.included}
        for field in ["strength", "dosage", "frequency", "duration", "route", "instructions", "notes"]:
            val = getattr(self, field, None)
            if _is_clean_value(val):
                data[field] = str(val).strip()
        return data


class PrescriptionRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    prescriber_name: Optional[str] = None
    clinic_or_place: Optional[str] = None
    prescription_date: Optional[str] = None
    diagnosed_diseases: List[str] = Field(default_factory=list)
    medicines: List[PrescribedMedicineItem] = Field(default_factory=list)
    raw_transcription: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_compact_dict(self) -> Dict[str, Any]:
        """Return dict omitting empty or unclear fields so frontend never shows placeholders."""
        res: Dict[str, Any] = {"id": self.id, "created_at": self.created_at}
        if _is_clean_value(self.prescriber_name):
            res["prescriber_name"] = self.prescriber_name.strip()
        if _is_clean_value(self.clinic_or_place):
            res["clinic_or_place"] = self.clinic_or_place.strip()
        if _is_clean_value(self.prescription_date):
            res["prescription_date"] = self.prescription_date.strip()
        
        clean_diseases = [d.strip() for d in self.diagnosed_diseases if _is_clean_value(d)]
        if clean_diseases:
            res["diagnosed_diseases"] = clean_diseases

        clean_meds = [m.to_compact_dict() for m in self.medicines if _is_clean_value(m.name) and m.included]
        if clean_meds:
            res["medicines"] = clean_meds

        if _is_clean_value(self.raw_transcription):
            res["raw_transcription"] = self.raw_transcription.strip()

        return res


class PrescriptionExtractionResult(BaseModel):
    prescriber_name: Optional[str] = None
    clinic_or_place: Optional[str] = None
    prescription_date: Optional[str] = None
    diagnosed_diseases: List[str] = Field(default_factory=list)
    medicines: List[PrescribedMedicineItem] = Field(default_factory=list)
    overall_confidence: str = "medium"
    raw_transcription: Optional[str] = None
    model_uncertainty_notes: Optional[str] = None
    extraction_errors: List[str] = Field(default_factory=list)

    def to_compact_dict(self) -> Dict[str, Any]:
        """Omit all empty fields, guaranteeing software only returns genuinely extracted fields."""
        res: Dict[str, Any] = {
            "overall_confidence": self.overall_confidence,
            "extraction_errors": self.extraction_errors,
        }
        if _is_clean_value(self.prescriber_name):
            res["prescriber_name"] = self.prescriber_name.strip()
        if _is_clean_value(self.clinic_or_place):
            res["clinic_or_place"] = self.clinic_or_place.strip()
        if _is_clean_value(self.prescription_date):
            res["prescription_date"] = self.prescription_date.strip()
        
        clean_diseases = [d.strip() for d in self.diagnosed_diseases if _is_clean_value(d)]
        if clean_diseases:
            res["diagnosed_diseases"] = clean_diseases

        clean_meds = [m.to_compact_dict() for m in self.medicines if _is_clean_value(m.name)]
        if clean_meds:
            res["medicines"] = clean_meds

        if _is_clean_value(self.raw_transcription):
            res["raw_transcription"] = self.raw_transcription.strip()
        if _is_clean_value(self.model_uncertainty_notes):
            res["model_uncertainty_notes"] = self.model_uncertainty_notes.strip()

        return res
