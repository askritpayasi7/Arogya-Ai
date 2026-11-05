import math
import sys
import textwrap
from typing import TextIO, Optional
from health_app.verification.models import (
    GatingStatus,
    RiskOfBiasAssessment,
    RiskOfBiasLevel,
    StudyDesignClassification,
    VerificationReport,
)

# ANSI color codes for terminal highlights
ANSI_GREEN = "\033[92m"
ANSI_CYAN = "\033[96m"
ANSI_YELLOW = "\033[93m"
ANSI_RED = "\033[91m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[2m"
ANSI_RESET = "\033[0m"


def _format_status_badge(status: GatingStatus, use_color: bool = True) -> str:
    color_map = {
        GatingStatus.ACCEPTED: ANSI_GREEN,
        GatingStatus.PROVISIONALLY_SUPPORTED: ANSI_CYAN,
        GatingStatus.QUARANTINED: ANSI_YELLOW,
        GatingStatus.EXCLUDED: ANSI_RED,
    }
    label_map = {
        GatingStatus.ACCEPTED: "[ACCEPTED]",
        GatingStatus.PROVISIONALLY_SUPPORTED: "[PROVISIONALLY SUPPORTED]",
        GatingStatus.QUARANTINED: "[QUARANTINED]",
        GatingStatus.EXCLUDED: "[EXCLUDED]",
    }
    badge = label_map.get(status, f"[{status.value}]")
    if use_color:
        color = color_map.get(status, "")
        return f"{ANSI_BOLD}{color}{badge}{ANSI_RESET}"
    return badge


def print_article_credibility_card(
    study_design: StudyDesignClassification,
    risk_of_bias: RiskOfBiasAssessment,
    title: str,
    authors: str = "Unknown",
    year: str = "Unknown",
    stream: Optional[TextIO] = None,
    use_color: bool = True
) -> None:
    """Print an exhaustive Article-Level Methodological Credibility & Bias Audit Card."""
    out = stream if stream is not None else sys.stdout

    # Determine overall status badge
    if risk_of_bias.level == RiskOfBiasLevel.LOW and study_design.weight >= 0.80:
        badge_text = "[HIGH METHODOLOGICAL CREDIBILITY]"
        color = ANSI_GREEN
    elif risk_of_bias.level in [RiskOfBiasLevel.LOW, RiskOfBiasLevel.MODERATE] and study_design.weight >= 0.50:
        badge_text = "[MODERATE CREDIBILITY / OBSERVATIONAL]"
        color = ANSI_CYAN
    elif risk_of_bias.level == RiskOfBiasLevel.SERIOUS:
        badge_text = "[SERIOUS RISK OF BIAS]"
        color = ANSI_YELLOW
    else:
        badge_text = "[CRITICAL RISK OF BIAS / LOW EVIDENTIAL WEIGHT]"
        color = ANSI_RED

    badge = f"{ANSI_BOLD}{color}{badge_text}{ANSI_RESET}" if use_color else badge_text

    print("\n" + "=" * 78, file=out)
    print(f" ARTICLE METHODOLOGICAL CREDIBILITY AUDIT: {badge}", file=out)
    print("=" * 78, file=out)
    print(f" Paper:       {title}", file=out)
    print(f" Authors:     {authors} ({year})", file=out)
    print("-" * 78, file=out)
    print(f" [PHASE 1: STUDY DESIGN & METHODOLOGICAL HIERARCHY]", file=out)
    print(f"  * Design Tier  : {study_design.design_type.value}", file=out)
    print(f"  * Weight Score : {study_design.weight:.2f} / 1.00", file=out)
    if study_design.indicators_found:
        print(f"  * Indicators   : {', '.join(study_design.indicators_found[:6])}", file=out)
    print("-" * 78, file=out)
    print(f" [PHASE 1: RISK OF BIAS ASSESSMENT ({risk_of_bias.framework})]", file=out)
    print(f"  * Overall RoB  : {risk_of_bias.level.value} (Bias Penalty: {risk_of_bias.penalty_points} pts)", file=out)
    if risk_of_bias.domain_evaluations:
        for domain, verdict in risk_of_bias.domain_evaluations.items():
            print(f"    - {domain}: {verdict}", file=out)
    if risk_of_bias.flags:
        for flag in risk_of_bias.flags:
            print(f"    ! Bias Flag  : {flag}", file=out)
    else:
        print(f"    + Bias Flags : None identified (Adheres to methodological standards)", file=out)
    print("=" * 78 + "\n", file=out)


def print_verification_report(
    report: VerificationReport,
    stream: Optional[TextIO] = None,
    use_color: bool = True
) -> None:
    """Print an exhaustive, professional clinical verification audit card to terminal."""
    out = stream if stream is not None else sys.stdout
    badge = _format_status_badge(report.gating_status, use_color=use_color)
    
    # Calculate log penalty delta for display
    from health_app.verification.scoring_engine import LAMBDA_PENALTY
    log_delta = round(LAMBDA_PENALTY * math.log(1.0 + report.penalty_points), 1) if report.penalty_points > 0 else 0.0

    print("=" * 78, file=out)
    print(f" CLINICAL VERIFICATION AUDIT: {badge}  (Final Score: {report.final_score}/100)", file=out)
    print("=" * 78, file=out)
    print(f" Claim:       {report.claim_summary}", file=out)
    print(f" Scoring:     Base: {report.base_score} | Penalty Pts: {report.penalty_points} (Delta: -{log_delta}) | Final: {report.final_score}", file=out)
    print(f" Gating:      {report.gating_status.value}", file=out)
    print("-" * 78, file=out)

    # Phase 1: Study Design & RoB
    print(f" [PHASE 1: ARTICLE-LEVEL METHODOLOGY & BIAS]", file=out)
    print(f"  * Study Design : {report.study_design.design_type.value} (Evidential Weight: {report.study_design.weight:.2f})", file=out)
    if report.study_design.indicators_found:
        print(f"    Indicators   : {', '.join(report.study_design.indicators_found[:5])}", file=out)
    print(f"  * Risk of Bias : {report.risk_of_bias.level.value} (Framework: {report.risk_of_bias.framework}, Bias Penalty: {report.risk_of_bias.penalty_points} pts)", file=out)
    if report.risk_of_bias.domain_evaluations:
        for domain, verdict in report.risk_of_bias.domain_evaluations.items():
            print(f"    - {domain}: {verdict}", file=out)
    if report.risk_of_bias.flags:
        for flag in report.risk_of_bias.flags:
            print(f"    ! Bias Flag  : {flag}", file=out)
    print("-" * 78, file=out)

    # Phase 2: Claim-Level Verification
    print(f" [PHASE 2: CLAIM-LEVEL NLI & STATISTICAL AUDIT]", file=out)
    print(f"  * Textual NLI  : {report.nli_result.status.value} (Score: {report.nli_result.score:.2f} | Engine: {report.nli_result.model_used})", file=out)
    wrapped_nli_exp = "\n    ".join(textwrap.wrap(report.nli_result.explanation, width=72))
    print(f"    Rationale    : {wrapped_nli_exp}", file=out)
    
    stat = report.statistical_check
    stat_status = "PASS" if (not stat.null_crossing and stat.directional_consistent) else "FLAGGED"
    print(f"  * Statistics   : {stat_status} (Score: {stat.score:.2f} | Penalty: {stat.penalty_points} pts)", file=out)
    if stat.metrics_found:
        print(f"    Metrics      : {', '.join(stat.metrics_found)}", file=out)
    print(f"    Null Crossing: {'YES (Non-Significant)' if stat.null_crossing else 'NO (Statistically Significant)'}", file=out)
    print(f"    Direction    : {'CONSISTENT' if stat.directional_consistent else 'INCONSISTENT / CONTRADICTS ESTIMATE'}", file=out)
    wrapped_stat_diag = "\n    ".join(textwrap.wrap(stat.diagnostics, width=72))
    print(f"    Diagnostics  : {wrapped_stat_diag}", file=out)
    print("-" * 78, file=out)

    # Phase 3: GRADE Group Synthesis
    if report.grade_synthesis:
        print(f" [PHASE 3: GRADE CROSS-STUDY EVIDENCE SYNTHESIS]", file=out)
        print(f"  * Concept Pair : {report.grade_synthesis.concept_pair}", file=out)
        print(f"  * Consistency  : {report.grade_synthesis.consistency_level} (Studies: {report.grade_synthesis.studies_count})", file=out)
        print(f"  * Synthesis    : {report.grade_synthesis.rationale}", file=out)
        print("-" * 78, file=out)

    # Phase 4: Gating Decision & Audit Rationale
    print(f" [PHASE 4: AUDIT DECISION & CHECKS]", file=out)
    print(f"  [+] Passed Checks ({len(report.passed_checks)}):", file=out)
    if report.passed_checks:
        for chk in report.passed_checks:
            print(f"      + {chk}", file=out)
    else:
        print(f"      (None)", file=out)

    print(f"  [-] Failed Checks / Warnings ({len(report.failed_checks)}):", file=out)
    if report.failed_checks:
        for chk in report.failed_checks:
            print(f"      - {chk}", file=out)
    else:
        print(f"      (None - clean clinical audit)", file=out)

    print(f"\n  [*] ACTION & RATIONALE:", file=out)
    wrapped_action = "\n      ".join(textwrap.wrap(report.action_reason, width=70))
    print(f"      {wrapped_action}", file=out)
    print("=" * 78 + "\n", file=out)
