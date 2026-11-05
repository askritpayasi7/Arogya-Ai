"""Clinical Verification & Anti-Hallucination Framework.

4-Phase verification pipeline auditing extracted health relationships:
- Phase 1: Article-Level Checks (Study Design Classification & RoB 2 / ROBINS-I)
- Phase 2: Relationship-Level Checks (Textual NLI & Statistical Validation)
- Phase 3: Group-Level Evidence Synthesis (Adapted GRADE)
- Phase 4: Non-linear Composite Scoring & Automated Gating
"""

from health_app.verification.models import (
    GatingStatus,
    GRADEEvidenceSynthesis,
    NLIVerificationResult,
    NLIStatus,
    RiskOfBiasAssessment,
    RiskOfBiasLevel,
    StatisticalValidationResult,
    StudyDesignClassification,
    StudyDesignType,
    VerificationReport,
)
from health_app.verification.article_checks import (
    classify_study_design,
    assess_risk_of_bias,
)
from health_app.verification.relationship_checks import (
    verify_textual_nli,
    validate_statistics,
)
from health_app.verification.evidence_synthesis import (
    synthesize_group_evidence,
    get_synthesis_for_relationship,
    extract_concept_key,
)
from health_app.verification.scoring_engine import (
    CompositeScoringEngine,
)
from health_app.verification.terminal_reporter import (
    print_verification_report,
    print_article_credibility_card,
)

__all__ = [
    "GatingStatus",
    "GRADEEvidenceSynthesis",
    "NLIVerificationResult",
    "NLIStatus",
    "RiskOfBiasAssessment",
    "RiskOfBiasLevel",
    "StatisticalValidationResult",
    "StudyDesignClassification",
    "StudyDesignType",
    "VerificationReport",
    "classify_study_design",
    "assess_risk_of_bias",
    "verify_textual_nli",
    "validate_statistics",
    "synthesize_group_evidence",
    "get_synthesis_for_relationship",
    "extract_concept_key",
    "CompositeScoringEngine",
    "print_verification_report",
    "print_article_credibility_card",
]
