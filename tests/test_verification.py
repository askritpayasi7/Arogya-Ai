import io
import pytest
from health_app.relationships.models import HealthRelationship
from health_app.verification import (
    CompositeScoringEngine,
    GatingStatus,
    GRADEEvidenceSynthesis,
    NLIVerificationResult,
    NLIStatus,
    RiskOfBiasAssessment,
    RiskOfBiasLevel,
    StatisticalValidationResult,
    StudyDesignClassification,
    StudyDesignType,
    assess_risk_of_bias,
    classify_study_design,
    get_synthesis_for_relationship,
    print_verification_report,
    print_article_credibility_card,
    synthesize_group_evidence,
    validate_statistics,
    verify_textual_nli,
)


# ============================================================================
# PHASE 1 TESTS: Article-Level Checks
# ============================================================================

def test_classify_study_design_rct():
    text = (
        "Methods: This was a double-blind, randomized, placebo-controlled trial "
        "evaluating the effect of daily 8,000 steps on sleep latency. Participants "
        "were allocated via random sequence generation to parallel control groups."
    )
    result = classify_study_design(text)
    assert result.design_type == StudyDesignType.RCT
    assert result.weight == 0.95
    assert any("randomized" in ind.lower() for ind in result.indicators_found)


def test_classify_study_design_meta_analysis():
    text = (
        "Background: We conducted a systematic review and meta-analysis adhering to "
        "the PRISMA statement. Pooled odds ratios and forest plots were calculated across "
        "24 eligible studies to evaluate obstructive sleep apnea and cardiac outcomes."
    )
    result = classify_study_design(text)
    assert result.design_type == StudyDesignType.META_ANALYSIS
    assert result.weight == 1.0


def test_classify_study_design_cohort():
    text = (
        "Methods: In this prospective cohort study, a longitudinal cohort of 4,200 "
        "participants was followed over a 10-year follow-up period to assess baseline "
        "sleep fragmentation and incident coronary heart disease."
    )
    result = classify_study_design(text)
    assert result.design_type == StudyDesignType.PROSPECTIVE_COHORT
    assert result.weight == 0.80


def test_risk_of_bias_rob2_low():
    design = StudyDesignClassification(design_type=StudyDesignType.RCT, weight=1.0)
    text = (
        "Patients were allocated via computerized random sequence generation with allocation "
        "concealment. Double-blind protocols were maintained. Complete follow-up was achieved "
        "with an intention-to-treat analysis and pre-registered protocol."
    )
    rob = assess_risk_of_bias(text, design)
    assert rob.framework == "RoB 2"
    assert rob.level == RiskOfBiasLevel.LOW
    assert rob.penalty_points == 0.0


def test_risk_of_bias_robins_i_serious():
    design = StudyDesignClassification(design_type=StudyDesignType.PROSPECTIVE_COHORT, weight=0.85)
    text = (
        "This study had unadjusted confounding factors, non-randomized self-selected participants, "
        "and lost 45% of patients to follow-up (high attrition and missing data)."
    )
    rob = assess_risk_of_bias(text, design)
    assert rob.framework == "ROBINS-I"
    assert rob.level in [RiskOfBiasLevel.SERIOUS, RiskOfBiasLevel.CRITICAL]
    assert rob.penalty_points >= 20.0


# ============================================================================
# PHASE 2 TESTS: Relationship-Level Checks
# ============================================================================

def test_nli_verification_entailment():
    premise = "High intake of trans fats increases low-density lipoprotein cholesterol and elevates cardiovascular risk."
    hypothesis = "Trans fat consumption increases risk of cardiovascular disease."
    result = verify_textual_nli(premise, hypothesis)
    assert result.status == NLIStatus.ENTAILMENT
    assert result.score == 1.0


def test_nli_verification_contradiction():
    premise = "Moderate physical activity decreases resting heart rate and reduces cardiovascular disease mortality."
    hypothesis = "Moderate physical activity increases cardiovascular disease mortality."
    result = verify_textual_nli(premise, hypothesis)
    assert result.status == NLIStatus.CONTRADICTION
    assert result.score == 0.0


def test_statistical_validation_significant():
    claim_dir = "indicates increased risk of"
    chunk_text = (
        "Multivariate Cox regression demonstrated that fragmented sleep was significantly associated "
        "with myocardial infarction (HR = 1.48; 95% CI: 1.18 to 1.85, p < 0.01)."
    )
    quote = "HR = 1.48; 95% CI: 1.18 to 1.85, p < 0.01"
    stat = validate_statistics(claim_dir, chunk_text, quote)
    assert stat.has_statistics is True
    assert stat.null_crossing is False
    assert stat.directional_consistent is True
    assert stat.penalty_points == 0.0


def test_statistical_validation_null_crossing():
    claim_dir = "increases risk of"
    chunk_text = "Analysis showed a non-significant trend (OR = 1.15; 95% CI: 0.92 to 1.44, p = 0.21)."
    quote = "OR = 1.15; 95% CI: 0.92 to 1.44"
    stat = validate_statistics(claim_dir, chunk_text, quote)
    assert stat.has_statistics is True
    assert stat.null_crossing is True
    assert stat.penalty_points >= 25.0


def test_statistical_validation_directional_mismatch():
    claim_dir = "increases risk of"
    chunk_text = "Patients in the intervention arm experienced lower cardiac events (RR = 0.62; 95% CI: 0.45 to 0.85)."
    quote = "RR = 0.62; 95% CI: 0.45 to 0.85"
    stat = validate_statistics(claim_dir, chunk_text, quote)
    assert stat.has_statistics is True
    assert stat.directional_consistent is False
    assert stat.penalty_points >= 35.0


# ============================================================================
# PHASE 3 TESTS: GRADE Cross-Study Evidence Synthesis
# ============================================================================

def test_grade_evidence_synthesis_multi_study():
    rel1 = HealthRelationship(
        subject="daily physical steps",
        relation="reduces risk of",
        object="cardiovascular disease",
        evidence_quote="Walking 8000 steps reduced cardiac mortality.",
        paper_title="Study A (Lancet)",
        doi="10.1016/sample1"
    )
    rel2 = HealthRelationship(
        subject="daily physical steps",
        relation="lowers incidence of",
        object="cardiovascular disease",
        evidence_quote="Higher daily step volume lowers cardiovascular events.",
        paper_title="Study B (JAMA)",
        doi="10.1001/sample2"
    )
    rel3 = HealthRelationship(
        subject="daily physical steps",
        relation="mitigates risk of",
        object="cardiovascular disease",
        evidence_quote="Long-term pedometer data shows mitigation of heart disease.",
        paper_title="Study C (BMJ)",
        doi="10.1136/sample3"
    )

    synthesis_map = synthesize_group_evidence([rel1, rel2, rel3])
    synthesis = get_synthesis_for_relationship(rel1, synthesis_map)
    assert synthesis.studies_count == 3
    assert synthesis.consistency_level == "HIGH"
    assert synthesis.penalty_points == 0.0


def test_grade_evidence_synthesis_directional_conflict():
    rel1 = HealthRelationship(
        subject="dietary sodium intake",
        relation="increases risk of",
        object="hypertension",
        evidence_quote="Excessive sodium intake significantly increases hypertension risk.",
        paper_title="Cohort Study 1",
    )
    rel2 = HealthRelationship(
        subject="dietary sodium intake",
        relation="decreases risk of",
        object="hypertension",
        evidence_quote="Low salt diet unexpectedly reduced vascular tone.",
        paper_title="Trial Study 2",
    )

    synthesis_map = synthesize_group_evidence([rel1, rel2])
    synthesis = get_synthesis_for_relationship(rel1, synthesis_map)
    assert synthesis.consistency_level == "INCONSISTENT"
    assert synthesis.penalty_points >= 20.0


# ============================================================================
# PHASE 4 TESTS: Composite Scoring & Automated Gating
# ============================================================================

def test_composite_scoring_accepted():
    rel = HealthRelationship(
        subject="aerobic physical exercise",
        relation="reduces resting heart rate and",
        object="cardiovascular mortality risk",
        condition="in healthy adults",
        evidence_quote="Aerobic physical exercise reduces resting heart rate and cardiovascular mortality risk significantly (p < 0.001).",
        confidence="High",
        paper_title="Physical Activity and Cardiac Health Trial",
        doi="10.1001/jama.2024.12345"
    )
    design = StudyDesignClassification(design_type=StudyDesignType.RCT, weight=1.0)
    rob = RiskOfBiasAssessment(framework="RoB 2", level=RiskOfBiasLevel.LOW, penalty_points=0.0)
    nli = NLIVerificationResult(status=NLIStatus.ENTAILMENT, score=1.0, model_used="NLI", explanation="Entails")
    stat = StatisticalValidationResult(has_statistics=True, score=1.0, penalty_points=0.0, null_crossing=False, directional_consistent=True)

    report = CompositeScoringEngine.evaluate(rel, design, rob, nli, stat)
    assert report.final_score >= 85.0
    assert report.gating_status == GatingStatus.ACCEPTED
    assert len(report.passed_checks) >= 4


def test_composite_scoring_hard_gate_contradiction():
    rel = HealthRelationship(
        subject="dietary sugar",
        relation="prevents development of",
        object="type 2 diabetes",
        evidence_quote="Sugar consumption is a well-established driver of type 2 diabetes.",
        paper_title="Nutritional Review",
        doi="10.1016/sample"
    )
    design = StudyDesignClassification(design_type=StudyDesignType.META_ANALYSIS, weight=1.0)
    rob = RiskOfBiasAssessment(framework="RoB 2", level=RiskOfBiasLevel.LOW, penalty_points=0.0)
    nli = NLIVerificationResult(status=NLIStatus.CONTRADICTION, score=0.0, model_used="NLI", explanation="Contradicts")
    stat = StatisticalValidationResult(has_statistics=False)

    report = CompositeScoringEngine.evaluate(rel, design, rob, nli, stat)
    assert report.final_score == 0.0
    assert report.gating_status == GatingStatus.EXCLUDED
    assert "Hard Gate Rejection" in report.action_reason


def test_composite_scoring_hard_gate_math_mismatch():
    rel = HealthRelationship(
        subject="sleep deprivation",
        relation="reduces incidence of",
        object="coronary heart disease",
        evidence_quote="Sleep deprivation was associated with higher cardiac events (HR = 1.65; 95% CI: 1.25 to 2.10).",
        paper_title="Sleep Cohort Study",
        doi="10.1093/sleep/sample"
    )
    design = StudyDesignClassification(design_type=StudyDesignType.PROSPECTIVE_COHORT, weight=0.85)
    rob = RiskOfBiasAssessment(framework="ROBINS-I", level=RiskOfBiasLevel.LOW, penalty_points=0.0)
    nli = NLIVerificationResult(status=NLIStatus.ENTAILMENT, score=1.0, model_used="NLI", explanation="Entails")
    stat = StatisticalValidationResult(
        has_statistics=True,
        null_crossing=False,
        directional_consistent=False,  # Conflict: claim says reduces, HR = 1.65 indicates elevation
        penalty_points=35.0
    )

    report = CompositeScoringEngine.evaluate(rel, design, rob, nli, stat)
    assert report.gating_status == GatingStatus.EXCLUDED
    assert report.final_score < 50.0
    assert "Hard Gate Rejection" in report.action_reason


def test_terminal_reporter_output():
    rel = HealthRelationship(
        subject="omega-3 fatty acids",
        relation="reduces systemic levels of",
        object="c-reactive protein",
        evidence_quote="Omega-3 supplementation reduced serum CRP levels by 22% compared to placebo.",
        paper_title="Cardiovascular Biomarker Trial",
        doi="10.1056/nejm.sample"
    )
    design = StudyDesignClassification(design_type=StudyDesignType.RCT, weight=1.0)
    rob = RiskOfBiasAssessment(framework="RoB 2", level=RiskOfBiasLevel.LOW, penalty_points=0.0)
    nli = NLIVerificationResult(status=NLIStatus.ENTAILMENT, score=1.0, model_used="NLI", explanation="Entails")
    stat = StatisticalValidationResult(has_statistics=False)

    report = CompositeScoringEngine.evaluate(rel, design, rob, nli, stat)
    
    buf = io.StringIO()
    print_verification_report(report, stream=buf, use_color=False)
    output = buf.getvalue()

    assert "[ACCEPTED]" in output
    assert "CLINICAL VERIFICATION AUDIT" in output
    assert "PHASE 1: ARTICLE-LEVEL" in output
    assert "PHASE 2: CLAIM-LEVEL" in output
    assert "ACTION & RATIONALE" in output


def test_print_article_credibility_card():
    design = StudyDesignClassification(
        design_type=StudyDesignType.RCT,
        weight=0.95,
        indicators_found=["randomized", "double-blind"]
    )
    rob = RiskOfBiasAssessment(
        framework="RoB 2",
        level=RiskOfBiasLevel.LOW,
        penalty_points=0.0,
        domain_evaluations={"Randomization": "Low Risk", "Blinding": "Low Risk"}
    )
    buf = io.StringIO()
    print_article_credibility_card(
        study_design=design,
        risk_of_bias=rob,
        title="Sample RCT on Sleep and Cardiac Recovery",
        authors="Dr. Smith et al.",
        year="2024",
        stream=buf,
        use_color=False
    )
    output = buf.getvalue()

    assert "ARTICLE METHODOLOGICAL CREDIBILITY AUDIT" in output
    assert "[HIGH METHODOLOGICAL CREDIBILITY]" in output
    assert "Randomized Controlled Trial (RCT)" in output
    assert "Low Risk" in output


def test_pipeline_zero_claims_still_verifies_article(capsys):
    from health_app.relationships.pipeline import RelationshipPipeline
    pipeline = RelationshipPipeline()

    # Text discussing method with no extractable causal relationships
    text = (
        "Background: A randomized controlled trial evaluating hospital equipment maintenance schedules. "
        "Double-blind allocation was utilized with parallel arms. Routine telemetry was monitored."
    )
    report = pipeline.process_text(
        text=text,
        title="Equipment Trial",
        authors="Tech Authors",
        year="2024",
        print_to_terminal=True
    )
    captured = capsys.readouterr()

    # Even with 0 relationships, article-level credibility audit must be executed and logged
    assert "ARTICLE METHODOLOGICAL CREDIBILITY AUDIT" in captured.out
    assert "Randomized Controlled Trial (RCT)" in captured.out
    assert report.total_relationships == 0


def test_classify_study_design_meta_analysis_beyond_2500_chars():
    """Verify study design classifier inspects beyond 2,500 characters and captures meta-analysis."""
    # Prefix text with 3,000 characters of journal header / author affiliation text
    header_padding = "Journal of Clinical Medicine. Open Access. Affiliations: Department of Cardiology. " * 40
    assert len(header_padding) > 2800

    full_text = header_padding + (
        " Methods: We conducted a systematic review and meta-analysis of cohort studies adhering to the PRISMA statement. "
        "Comprehensive database search was performed across PubMed, Scopus, and the Cochrane Library."
    )
    result = classify_study_design(full_text, title="Physical Activity and Cardiovascular Disease")
    assert result.design_type == StudyDesignType.META_ANALYSIS
    assert result.weight == 1.0


def test_assess_risk_of_bias_systematic_review_low_penalty():
    """Verify systematic reviews are evaluated under AMSTAR 2 / ROBIS with low penalty."""
    design = StudyDesignClassification(design_type=StudyDesignType.META_ANALYSIS, weight=1.0)
    text = (
        "Methods: A systematic review was conducted across PubMed, Embase, and Cochrane Library. "
        "Two independent reviewers screened studies according to PRISMA flow diagram and selection criteria. "
        "Risk of bias of included studies was formally assessed using the Cochrane tool. "
        "Statistical heterogeneity was assessed using the I2 statistic and random-effects forest plot models."
    )
    rob = assess_risk_of_bias(text, design)
    assert rob.framework == "AMSTAR 2 / ROBIS"
    assert rob.level == RiskOfBiasLevel.LOW
    assert rob.penalty_points == 0.0


def test_nli_low_overlap_is_neutral_not_contradiction():
    """Verify partial or low concept overlap yields NEUTRAL rather than false CONTRADICTION."""
    premise = "High cardiorespiratory fitness correlates with extended healthy longevity in epidemiological datasets."
    hypothesis = "Cardiorespiratory fitness modulates cellular senescence biomarkers."
    result = verify_textual_nli(premise, hypothesis)
    assert result.status == NLIStatus.NEUTRAL
    assert result.score > 0.0


def test_composite_scoring_high_quality_meta_analysis_accepted():
    """Verify high-quality claims from meta-analyses achieve ACCEPTED or PROVISIONALLY_SUPPORTED."""
    rel = HealthRelationship(
        subject="Muscle-strengthening activity",
        relation="is associated with",
        object="a 17% lower risk of cardiovascular disease",
        condition="in general adult populations",
        evidence_quote="A 2022 meta-analysis of seven cohorts involving 257,888 participants found that muscle-strengthening activity was associated with a 17% lower risk of CVD (RR 0.83, 95% CI 0.73-0.93).",
        paper_title="Physical Activity & CVD Prevention Meta-Analysis",
        authors="Dehesh M, et al.",
        publish_year="2026",
        doi="10.3390/jcdd13100479"
    )
    design = StudyDesignClassification(design_type=StudyDesignType.META_ANALYSIS, weight=1.0)
    rob = RiskOfBiasAssessment(framework="AMSTAR 2 / ROBIS", level=RiskOfBiasLevel.LOW, penalty_points=0.0)
    nli = verify_textual_nli(rel.to_claim_sentence(), rel.evidence_quote)
    stat = validate_statistics(rel.relation, rel.evidence_quote, rel.evidence_quote)

    report = CompositeScoringEngine.evaluate(rel, design, rob, nli, stat)
    assert report.final_score >= 70.0
    assert report.gating_status in [GatingStatus.ACCEPTED, GatingStatus.PROVISIONALLY_SUPPORTED]


def test_extractor_noise_filtering():
    """Verify fallback extractor rejects institutional titles and PRISMA search strings."""
    from health_app.relationships.extractor import GeminiRelationshipExtractor
    extractor = GeminiRelationshipExtractor(api_key=None)

    noisy_chunk = (
        "Centers for Disease Control and Prevention. "
        "To make the Scopus search transparent and visible, the strategy was rerun on 20 July 2026: the S1-S5 main-search strings yielded 4182 results in total across overlapping searches. "
        "Habitual brisk walking significantly reduces resting arterial blood pressure and improves vascular endothelial function in adults with prehypertension."
    )

    results = extractor.extract_from_chunk(
        chunk_text=noisy_chunk,
        title="Physical Activity Review",
        authors="Cardio Team",
        year="2026",
        doi="10.1016/sample",
        chunk_index=0
    )

    # Must reject "Centers for Disease Control" and Scopus search count strings
    assert not any("Centers for Disease" in r.subject for r in results)
    assert not any("main-search" in r.subject or "yielded" in r.relation for r in results)
    # Must capture genuine clinical finding
    assert any("walking" in r.subject.lower() and "blood pressure" in r.object.lower() for r in results)


