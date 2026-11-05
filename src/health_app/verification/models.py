from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from health_app.relationships.models import HealthRelationship

class StudyDesignType(str, Enum):
    META_ANALYSIS = "Systematic Review / Meta-Analysis"
    RCT = "Randomized Controlled Trial (RCT)"
    PROSPECTIVE_COHORT = "Prospective Cohort Study"
    CASE_CONTROL = "Case-Control Study"
    CROSS_SECTIONAL = "Cross-Sectional Observational Study"
    PRECLINICAL = "Preclinical / In Vitro Study"
    NARRATIVE_REVIEW = "Narrative Review / Case Series"


class RiskOfBiasLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    SERIOUS = "SERIOUS"
    CRITICAL = "CRITICAL"


class NLIStatus(str, Enum):
    ENTAILMENT = "ENTAILMENT"
    CONTRADICTION = "CONTRADICTION"
    NEUTRAL = "NEUTRAL"


class GatingStatus(str, Enum):
    ACCEPTED = "ACCEPTED"                      # 85-100: Strong support
    PROVISIONALLY_SUPPORTED = "PROVISIONALLY_SUPPORTED" # 70-84: Supported with caution
    QUARANTINED = "QUARANTINED"                # 50-69: Held back for review
    EXCLUDED = "EXCLUDED"                      # < 50 or hard gate violation


class StudyDesignClassification(BaseModel):
    """Article-level classification of research methodology."""
    design_type: StudyDesignType
    weight: float = Field(description="Methodological evidential weight (0.25 to 1.0)")
    indicators_found: List[str] = Field(default_factory=list)


class RiskOfBiasAssessment(BaseModel):
    """Article-level automated RoB 2 / ROBINS-I bias assessment."""
    framework: str  # 'RoB 2' or 'ROBINS-I'
    level: RiskOfBiasLevel
    penalty_points: float = 0.0
    domain_evaluations: Dict[str, str] = Field(default_factory=dict)
    flags: List[str] = Field(default_factory=list)


class NLIVerificationResult(BaseModel):
    """Relationship-level Natural Language Inference verification result."""
    status: NLIStatus
    score: float = Field(description="Normalized NLI score (0.0 to 1.0)")
    model_used: str
    explanation: str


class StatisticalValidationResult(BaseModel):
    """Relationship-level mathematical and directional consistency result."""
    has_statistics: bool = False
    metrics_found: List[str] = Field(default_factory=list)
    null_crossing: bool = False
    directional_consistent: bool = True
    score: float = 1.0
    penalty_points: float = 0.0
    diagnostics: str = "No numerical claims detected."


class GRADEEvidenceSynthesis(BaseModel):
    """Group-level evidence synthesis using adapted GRADE criteria."""
    concept_pair: str
    studies_count: int = 1
    consistency_level: str = "MODERATE"
    penalty_points: float = 0.0
    rationale: str = "Single study observation."


class VerificationReport(BaseModel):
    """Consolidated 4-phase verification report for an extracted health relationship."""
    claim_summary: str
    study_design: StudyDesignClassification
    risk_of_bias: RiskOfBiasAssessment
    nli_result: NLIVerificationResult
    statistical_check: StatisticalValidationResult
    grade_synthesis: Optional[GRADEEvidenceSynthesis] = None

    relationship: Optional[HealthRelationship] = None
    evidence_quote: str = ""
    paper_title: str = ""
    authors: str = ""
    publish_year: str = ""
    doi: Optional[str] = None
    
    base_score: float
    penalty_points: float
    final_score: float
    gating_status: GatingStatus
    
    passed_checks: List[str] = Field(default_factory=list)
    failed_checks: List[str] = Field(default_factory=list)
    action_reason: str

    @property
    def subject(self) -> str:
        if self.relationship and getattr(self.relationship, "subject", None):
            return self.relationship.subject
        parts = self.claim_summary.split(" -> ")
        return parts[0] if len(parts) >= 1 else ""

    @property
    def relation(self) -> str:
        if self.relationship and getattr(self.relationship, "relation", None):
            return self.relationship.relation
        parts = self.claim_summary.split(" -> ")
        return parts[1] if len(parts) >= 2 else ""

    @property
    def object(self) -> str:
        if self.relationship and getattr(self.relationship, "object", None):
            return self.relationship.object
        parts = self.claim_summary.split(" -> ")
        return parts[2] if len(parts) >= 3 else ""
