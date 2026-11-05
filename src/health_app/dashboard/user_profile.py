import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from health_app.prescription.models import PrescribedMedicineItem, PrescriptionRecord

logger = logging.getLogger(__name__)

USER_PROFILES_DIR = Path("./data/user_profiles")


class UserLifestyleProfile(BaseModel):
    """Personal medical and lifestyle risk profile tied to patient email record."""
    email: str
    age: int = Field(default=28, ge=18, le=120)
    profession: str = "Software Engineer (Desk Job)"
    smoking_status: str = "non_smoker"  # current_smoker, former_smoker, non_smoker
    alcohol_consumption: str = "none"   # none, occasional, moderate, heavy
    chronic_risk_factors: List[str] = Field(default_factory=list)
    primary_health_goal: str = "Cardiovascular & Sleep Health"
    baseline_status: str = "calibration_mode"  # calibration_mode, active_calibrated
    onboarding_completed: bool = False

    # Prescription & Clinical History
    prescriptions: List[PrescriptionRecord] = Field(default_factory=list)
    diagnosed_conditions: List[str] = Field(default_factory=list)
    active_medications: List[PrescribedMedicineItem] = Field(default_factory=list)

    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def get_age_bracket(self) -> str:
        """Categorize age for sub-population literature filters."""
        if self.age < 30:
            return "young_adult"
        elif self.age < 60:
            return "middle_aged"
        return "older_adult"

    def is_current_smoker(self) -> bool:
        return self.smoking_status == "current_smoker"

    def is_regular_drinker(self) -> bool:
        return self.alcohol_consumption in ["moderate", "heavy"]

    def add_prescription(self, record: PrescriptionRecord) -> None:
        """Add prescription record, merging diseases into diagnosed_conditions and medicines into active_medications."""
        self.prescriptions = [p for p in self.prescriptions if p.id != record.id]
        self.prescriptions.append(record)

        # Merge diagnosed diseases
        existing_cond_lower = {c.lower() for c in self.diagnosed_conditions}
        for cond in record.diagnosed_diseases:
            if cond and cond.strip() and cond.strip().lower() not in existing_cond_lower:
                self.diagnosed_conditions.append(cond.strip())
                existing_cond_lower.add(cond.strip().lower())
                if cond.strip() not in self.chronic_risk_factors:
                    self.chronic_risk_factors.append(cond.strip())

        # Merge medicines into active_medications
        existing_meds = {m.name.lower(): m for m in self.active_medications}
        for med in record.medicines:
            if med.included and med.name.strip():
                existing_meds[med.name.lower()] = med
        self.active_medications = list(existing_meds.values())

    def delete_prescription(self, rx_id: str) -> bool:
        """Remove a prescription record and re-evaluate active medications/conditions."""
        initial_len = len(self.prescriptions)
        self.prescriptions = [p for p in self.prescriptions if p.id != rx_id]
        if len(self.prescriptions) < initial_len:
            active_meds = {}
            conditions = set()
            for rx in self.prescriptions:
                for d in rx.diagnosed_diseases:
                    if d.strip():
                        conditions.add(d.strip())
                for med in rx.medicines:
                    if med.included and med.name.strip():
                        active_meds[med.name.lower()] = med
            self.active_medications = list(active_meds.values())
            return True
        return False


def _get_profile_path(email: str) -> Path:
    normalized = email.lower().strip()
    h = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return USER_PROFILES_DIR / f"profile_{h}.json"


def load_user_profile(email: str) -> Optional[UserLifestyleProfile]:
    """Load persistent lifestyle medical profile for the given email."""
    if not email:
        return None
    path = _get_profile_path(email)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return UserLifestyleProfile(**data)
    except Exception as e:
        logger.warning(f"Error loading user profile from {path}: {e}")
        return None


def save_user_profile(email: str, profile: UserLifestyleProfile) -> None:
    """Save persistent lifestyle medical profile to data/user_profiles/."""
    if not email:
        return
    USER_PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    path = _get_profile_path(email)
    try:
        profile.updated_at = datetime.now(timezone.utc).isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile.model_dump(), f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Failed to save user profile to {path}: {e}")


def get_default_demo_profile() -> UserLifestyleProfile:
    """Realistic demo profile matching user's specification."""
    return UserLifestyleProfile(
        email="patient@example.com",
        age=28,
        profession="Software Engineer (Sedentary Desk Job)",
        smoking_status="current_smoker",
        alcohol_consumption="moderate",
        chronic_risk_factors=["Sedentary Desk Hours", "High Workload"],
        primary_health_goal="Nocturnal Recovery & Heart Rate Optimization",
        baseline_status="active_calibrated",
        onboarding_completed=True
    )
