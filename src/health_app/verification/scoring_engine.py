import math
from typing import List, Optional
from health_app.relationships.models import HealthRelationship
from health_app.verification.models import (
    GatingStatus,
    NLIStatus,
    NLIVerificationResult,
    RiskOfBiasAssessment,
    RiskOfBiasLevel,
    StatisticalValidationResult,
    StudyDesignClassification,
    GRADEEvidenceSynthesis,
    VerificationReport,
)

LAMBDA_PENALTY = 8.5

class CompositeScoringEngine:
    """Calculates non-linear composite score and executes automated gating rules."""

    @staticmethod
    def evaluate(
        relationship: HealthRelationship,
        study_design: StudyDesignClassification,
        risk_of_bias: RiskOfBiasAssessment,
        nli_result: NLIVerificationResult,
        statistical_check: StatisticalValidationResult,
        grade_synthesis: Optional[GRADEEvidenceSynthesis] = None,
    ) -> VerificationReport:
        passed_checks: List[str] = []
        failed_checks: List[str] = []

        # 1. Component Sub-scores (0 to 100)
        # NLI (25%)
        s_nli = nli_result.score * 100.0
        if nli_result.status == NLIStatus.ENTAILMENT:
            passed_checks.append("NLI Entailment: Quote logically supports claim")
        elif nli_result.status == NLIStatus.NEUTRAL:
            failed_checks.append("NLI Neutral: Premise lacks direct decisive support")
        else:
            failed_checks.append("NLI Contradiction: Claim contradicts source text")

        # Statistics (25%)
        s_stat = statistical_check.score * 100.0
        if statistical_check.has_statistics:
            if not statistical_check.null_crossing and statistical_check.directional_consistent:
                passed_checks.append("Statistical Validation: Estimates are statistically significant and directionally aligned")
            if statistical_check.null_crossing:
                failed_checks.append("Statistical Null Crossing: 95% CI crosses 1.0 (non-significant)")
            if not statistical_check.directional_consistent:
                failed_checks.append("Directional Inconsistency: Mathematical metric contradicts verbal claim")
        else:
            passed_checks.append("Statistical Check: Qualitative observation accepted at baseline")

        # Study Quality (30%)
        s_design = study_design.weight * 100.0
        if study_design.weight >= 0.80:
            passed_checks.append(f"High-quality study design: {study_design.design_type.value}")
        else:
            failed_checks.append(f"Lower-tier methodology: {study_design.design_type.value} (Weight: {study_design.weight})")

        # Completeness (10%)
        has_doi = bool(relationship.doi)
        has_cond = bool(relationship.condition)
        has_quote = len(relationship.evidence_quote) >= 40
        s_completeness = (40.0 if has_doi else 15.0) + (30.0 if has_cond else 15.0) + (30.0 if has_quote else 10.0)
        if has_doi and has_quote:
            passed_checks.append("Citation Completeness: Verifiable DOI and source excerpt attached")
        else:
            failed_checks.append("Citation Completeness: Incomplete DOI or short evidence quote")

        # Context (10%)
        has_clear_sub = len(relationship.subject) >= 8
        has_clear_obj = len(relationship.object) >= 8
        s_context = 100.0 if (has_clear_sub and has_clear_obj) else 60.0
        if has_clear_sub and has_clear_obj:
            passed_checks.append("Context Clarity: Subject and clinical outcome are explicitly defined")

        # Normalized Base Score B
        base_score = (
            0.25 * s_nli +
            0.25 * s_stat +
            0.30 * s_design +
            0.10 * s_completeness +
            0.10 * s_context
        )

        # 2. Total Penalty Points P
        total_p = (
            risk_of_bias.penalty_points +
            statistical_check.penalty_points +
            (grade_synthesis.penalty_points if grade_synthesis else 0.0)
        )

        if risk_of_bias.level == RiskOfBiasLevel.LOW:
            passed_checks.append(f"Risk of Bias ({risk_of_bias.framework}): Low risk of bias")
        else:
            failed_checks.append(f"Risk of Bias ({risk_of_bias.framework}): {risk_of_bias.level.value} ({', '.join(risk_of_bias.flags) or 'Methodological concerns'})")

        # Logarithmic Risk Penalty: lambda * ln(1 + P)
        log_penalty = LAMBDA_PENALTY * math.log(1.0 + total_p)
        raw_final_score = max(0.0, base_score - log_penalty)

        # 3. Hard Gating Rules
        # Hard Gate A: NLI Contradiction -> Immediate Excluded (Score = 0)
        if nli_result.status == NLIStatus.CONTRADICTION:
            final_score = 0.0
            gating_status = GatingStatus.EXCLUDED
            action_reason = "Hard Gate Rejection: Claim explicitly contradicts source quote."
        # Hard Gate B: Directional Inconsistency with Math -> Hard Rejection (< 50)
        elif not statistical_check.directional_consistent:
            final_score = min(raw_final_score, 45.0)
            gating_status = GatingStatus.EXCLUDED
            action_reason = "Hard Gate Rejection: Verbal claim direction contradicts mathematical effect estimate."
        # Hard Gate C: Critical Risk of Bias -> Capped below 50
        elif risk_of_bias.level == RiskOfBiasLevel.CRITICAL:
            final_score = min(raw_final_score, 49.0)
            gating_status = GatingStatus.EXCLUDED
            action_reason = "Hard Gate Rejection: Severe methodological flaws (Critical Risk of Bias)."
        else:
            final_score = round(raw_final_score, 1)
            # Threshold Gating
            if final_score >= 85.0:
                gating_status = GatingStatus.ACCEPTED
                action_reason = "Strong automated support; high study quality with robust textual and statistical backing."
            elif final_score >= 70.0:
                gating_status = GatingStatus.PROVISIONALLY_SUPPORTED
                action_reason = "Accepted with caution tag; minor bias or observational design limits."
            elif final_score >= 50.0:
                gating_status = GatingStatus.QUARANTINED
                action_reason = "Quarantined for manual review due to significant methodological limits or neutral NLI."
            else:
                gating_status = GatingStatus.EXCLUDED
                action_reason = "Excluded: Score fell below evidentiary safety threshold (< 50.0)."

        claim_summary = f"{relationship.subject} -> {relationship.relation} -> {relationship.object}"

        return VerificationReport(
            relationship=relationship,
            evidence_quote=getattr(relationship, "evidence_quote", ""),
            paper_title=getattr(relationship, "paper_title", ""),
            authors=getattr(relationship, "authors", ""),
            publish_year=getattr(relationship, "publish_year", ""),
            doi=getattr(relationship, "doi", None),
            claim_summary=claim_summary,
            study_design=study_design,
            risk_of_bias=risk_of_bias,
            nli_result=nli_result,
            statistical_check=statistical_check,
            grade_synthesis=grade_synthesis,
            base_score=round(base_score, 1),
            penalty_points=round(total_p, 1),
            final_score=round(final_score, 1),
            gating_status=gating_status,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            action_reason=action_reason
        )
