import re
from typing import Dict, List, Tuple
from health_app.verification.models import (
    StudyDesignClassification,
    StudyDesignType,
    RiskOfBiasAssessment,
    RiskOfBiasLevel,
)

DESIGN_PATTERNS = [
    (
        StudyDesignType.META_ANALYSIS,
        1.00,
        [
            r'\bmeta-analy', r'\bsystematic review\b', r'\bpooled analysis\b',
            r'\bprisma\b', r'\bcochrane\b', r'\bsearch strategy\b',
            r'\bliterature search\b', r'\bdatabase search\b', r'\bscopus\b', r'\bweb of science\b'
        ]
    ),
    (
        StudyDesignType.RCT,
        0.95,
        [
            r'\brandomized controlled trial\b', r'\brandomised trial\b', r'\brandomized\b',
            r'\brandomised\b', r'\bdouble-blind\b', r'\bplacebo-controlled\b', r'\bclinical trial\b'
        ]
    ),
    (
        StudyDesignType.PROSPECTIVE_COHORT,
        0.80,
        [
            r'\bprospective cohort\b', r'\blongitudinal study\b', r'\bfollow-up cohort\b',
            r'\bprospective study\b', r'\bpure study\b', r'\bframingham\b', r'\bmesa study\b',
            r'\bcardia study\b', r'\bcohort study\b'
        ]
    ),
    (
        StudyDesignType.CASE_CONTROL,
        0.65,
        [r'\bcase-control\b', r'\bmatched controls?\b']
    ),
    (
        StudyDesignType.CROSS_SECTIONAL,
        0.50,
        [r'\bcross-sectional\b', r'\bobservational cohort\b', r'\bretrospective cohort\b', r'\bcorrelates of\b', r'\bprevalence study\b']
    ),
    (
        StudyDesignType.PRECLINICAL,
        0.35,
        [r'\bin vitro\b', r'\bmurine\b', r'\bmice\b', r'\brat model\b', r'\banimal models?\b', r'\bfetal sheep\b', r'\bcell culture\b']
    ),
    (
        StudyDesignType.NARRATIVE_REVIEW,
        0.40,
        [r'\bnarrative review\b', r'\bcomprehensive review\b', r'\bmini-review\b', r'\bexpert review\b', r'\bliterature review\b', r'\bscoping review\b']
    ),
]


def classify_study_design(text: str, title: str = "") -> StudyDesignClassification:
    """Classifies research paper methodology into a structured design category."""
    combined = (title + "\n" + text[:15000]).lower()

    for design_type, weight, patterns in DESIGN_PATTERNS:
        matched_indicators = []
        for pattern in patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                matched_indicators.append(pattern.replace(r'\b', ''))
        
        if matched_indicators:
            return StudyDesignClassification(
                design_type=design_type,
                weight=weight,
                indicators_found=matched_indicators
            )

    # Default fallback: Observational study
    return StudyDesignClassification(
        design_type=StudyDesignType.CROSS_SECTIONAL,
        weight=0.50,
        indicators_found=["default_observational_fallback"]
    )


def assess_risk_of_bias(text: str, design: StudyDesignClassification) -> RiskOfBiasAssessment:
    """Evaluates methodological risk of bias using automated RoB 2, AMSTAR 2 / ROBIS, or ROBINS-I criteria."""
    content = text.lower()
    flags: List[str] = []
    domain_evals: Dict[str, str] = {}
    penalty = 0.0

    if design.design_type == StudyDesignType.META_ANALYSIS:
        framework = "AMSTAR 2 / ROBIS"
        # Domain 1: Multi-database literature search
        if re.search(r'pubmed|embase|cochrane|scopus|web of science|medline|cinahl|google scholar', content):
            domain_evals["Literature Search"] = "Low Risk (Comprehensive multi-database search stated)"
        else:
            domain_evals["Literature Search"] = "Some Concerns (Search databases not fully specified)"
            penalty += 3.0

        # Domain 2: Study Selection and Screening
        if re.search(r'prisma|flow diagram|selection criteria|two independent|screened|eligibility|inclusion criteria', content):
            domain_evals["Study Selection"] = "Low Risk (Explicit eligibility and screening protocol)"
        else:
            domain_evals["Study Selection"] = "Some Concerns (Selection protocol not detailed)"
            penalty += 2.0

        # Domain 3: Quality Assessment of Included Studies
        if re.search(r'risk of bias|rob 2|robins|cochrane tool|newcastle|pedro|jadad|quality assessment|grade|methodological quality', content):
            domain_evals["Study Quality"] = "Low Risk (Formal risk of bias assessment of included studies documented)"
        else:
            domain_evals["Study Quality"] = "Some Concerns (Quality assessment of included studies not stated)"
            penalty += 3.0

        # Domain 4: Synthesis & Heterogeneity
        if re.search(r'heterogeneity|i2|random-effects|fixed-effect|forest plot|funnel plot|meta-regression|narrative synthesis|pooled estimate', content):
            domain_evals["Synthesis"] = "Low Risk (Statistical pooling and/or heterogeneity evaluated)"
        else:
            domain_evals["Synthesis"] = "Some Concerns (Synthesis methods not detailed)"
            penalty += 2.0

    elif design.design_type == StudyDesignType.RCT:
        framework = "RoB 2"
        # RoB 2 Domain 1: Randomization
        if re.search(r'random allocation|computer-generated|random sequence|random permuted|conceal', content):
            domain_evals["Randomization"] = "Low Risk (Concealed allocation or algorithmic randomization stated)"
        else:
            domain_evals["Randomization"] = "Some Concerns (Specific allocation concealment method not detailed)"
            flags.append("Allocation concealment unclear")
            penalty += 5.0

        # RoB 2 Domain 2: Blinding
        if re.search(r'double-blind|blinded assessor|sham|placebo', content):
            domain_evals["Blinding"] = "Low Risk (Blinding of participants and/or assessors noted)"
        else:
            domain_evals["Blinding"] = "Some Concerns (Open-label or blinding not specified)"
            flags.append("Lack of blinding specified")
            penalty += 5.0

        # RoB 2 Domain 3: Missing Outcome Data / Attrition
        if re.search(r'intention-to-treat|itt analysis|drop-out rate|attrition', content):
            domain_evals["Missing Data"] = "Low Risk (ITT analysis or attrition documented)"
        else:
            domain_evals["Missing Data"] = "Some Concerns (Handling of missing participants not detailed)"
            flags.append("Attrition handling not detailed")
            penalty += 4.0

    else:
        framework = "ROBINS-I"
        # ROBINS-I Domain 1: Confounding
        if re.search(r'adjusted for|multivariable|multivariate|regression|propensity score|controlled for|covariates?|confounders?|stratified by|hazard ratio|adjusted odds ratio|marginal structural', content):
            domain_evals["Confounding"] = "Low/Moderate Risk (Multivariable adjustments documented)"
        else:
            domain_evals["Confounding"] = "Serious Risk (Unadjusted confounding factors)"
            flags.append("Uncontrolled confounding in observational design")
            penalty += 20.0

        # ROBINS-I Domain 2: Selection of participants
        if re.search(r'consecutive patients|population-based|random sampling|representative cohort|community-based cohort|registry-based', content):
            domain_evals["Selection"] = "Low Risk (Systematic participant selection)"
        else:
            domain_evals["Selection"] = "Moderate Risk (Potential selection bias or convenience cohort)"
            flags.append("Convenience or non-random cohort selection")
            penalty += 6.0

        # ROBINS-I Domain 3: Measurement of outcomes
        if re.search(r'polysomnography|electrocardiog|laboratory assay|spectrometry|clinical record|blood pressure|sphygmomanometer|cuff|heart rate|bpm|pulse|accelerometer|actigraph|pedometer|step count|coronary artery calcium|cac|ccta|ultrasound|echocardiog|ct scan|lipid|cholesterol|hdl|ldl|glucose|hba1c|biomarker|apelin|crf|cardiorespiratory fitness|vo2', content):
            domain_evals["Measurement"] = "Low Risk (Objective physiological or clinical biomarker instrumentation)"
        elif re.search(r'self-reported|questionnaire|survey|recall', content):
            domain_evals["Measurement"] = "Moderate/Serious Risk (Subjective self-reported outcome measures)"
            flags.append("Subjective recall / self-report instrument")
            penalty += 10.0
        else:
            domain_evals["Measurement"] = "Moderate Risk (Measurement standard not fully detailed)"
            penalty += 4.0

    # Small sample penalty flag (for clinical cohorts/trials)
    small_n = re.search(r'\b(sample size of|n\s*=\s*)\s*([0-9]+)\b', content)
    if small_n and int(small_n.group(2)) < 30 and design.design_type not in [StudyDesignType.META_ANALYSIS, StudyDesignType.NARRATIVE_REVIEW]:
        flags.append(f"Small sample size (N={small_n.group(2)} < 30)")
        penalty += 15.0

    # Determine overall Risk of Bias Level
    if penalty >= 35.0:
        level = RiskOfBiasLevel.CRITICAL
    elif penalty >= 20.0:
        level = RiskOfBiasLevel.SERIOUS
    elif penalty >= 8.0:
        level = RiskOfBiasLevel.MODERATE
    else:
        level = RiskOfBiasLevel.LOW

    return RiskOfBiasAssessment(
        framework=framework,
        level=level,
        penalty_points=penalty,
        domain_evaluations=domain_evals,
        flags=flags
    )
