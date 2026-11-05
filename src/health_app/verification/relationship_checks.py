import logging
import re
from typing import List, Optional, Tuple
import requests

from health_app.config import settings
from health_app.verification.models import (
    NLIVerificationResult,
    NLIStatus,
    StatisticalValidationResult,
)

logger = logging.getLogger(__name__)

def verify_textual_nli(premise: str, hypothesis: str) -> NLIVerificationResult:
    """
    Verifies relationship claim against exact source quote using lightweight Ollama NLI
    or local deterministic NLI fallback.
    """
    ollama_url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"
    model = settings.ollama_nli_model

    prompt = (
        f"Task: Natural Language Inference (NLI)\n"
        f"Premise: \"{premise}\"\n"
        f"Hypothesis: \"{hypothesis}\"\n\n"
        f"Does the Premise entail, contradict, or remain neutral toward the Hypothesis?\n"
        f"Answer ONLY with one word: ENTAILMENT, CONTRADICTION, or NEUTRAL."
    )

    # 1. Try lightweight Ollama NLI model
    try:
        resp = requests.post(
            ollama_url,
            json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.0}},
            timeout=8
        )
        if resp.status_code == 200:
            text = resp.json().get("response", "").upper().strip()
            if "CONTRADICTION" in text:
                return NLIVerificationResult(
                    status=NLIStatus.CONTRADICTION,
                    score=0.0,
                    model_used=f"Ollama ({model})",
                    explanation="Ollama NLI classified relationship claim as contradicting the source text."
                )
            elif "ENTAILMENT" in text:
                return NLIVerificationResult(
                    status=NLIStatus.ENTAILMENT,
                    score=1.0,
                    model_used=f"Ollama ({model})",
                    explanation="Ollama NLI confirmed source sentence entails the claim."
                )
            elif "NEUTRAL" in text:
                return NLIVerificationResult(
                    status=NLIStatus.NEUTRAL,
                    score=0.4,
                    model_used=f"Ollama ({model})",
                    explanation="Ollama NLI found insufficient or neutral support in the direct premise."
                )
    except Exception:
        # Fallback to local rule-based verifier if Ollama is not running
        pass

    # 2. Local Deterministic NLI Verifier (Zero-dependency fallback)
    return _local_rule_based_nli(premise, hypothesis)


def _local_rule_based_nli(premise: str, hypothesis: str) -> NLIVerificationResult:
    """Deterministic lexical & directional NLI verifier."""
    p_lower = premise.lower()
    h_lower = hypothesis.lower()

    # Contradiction detection: Negation polarity mismatches
    negation_patterns = [r'\bno\s+significant\b', r'\bnot\s+associated\b', r'\bfailed\s+to\b', r'\bno\s+evidence\b', r'\bwas\s+not\b']
    has_negation_in_premise = any(re.search(pat, p_lower) for pat in negation_patterns)

    claim_asserts_effect = any(v in h_lower for v in ["increases", "elevates", "causes", "correlates", "associated with", "impairs"])

    if has_negation_in_premise and claim_asserts_effect:
        return NLIVerificationResult(
            status=NLIStatus.CONTRADICTION,
            score=0.0,
            model_used="Local Rule-based NLI",
            explanation="Premise explicitly notes lack of significance/association, contradicting positive claim."
        )

    # Directional polarity contradiction check (e.g. premise says decreases/reduces, hypothesis says increases/elevates)
    premise_positive = any(w in p_lower for w in ["increase", "elevat", "worsen", "harm", "impair", "cause"])
    premise_negative = any(w in p_lower for w in ["decrease", "reduc", "lowers", "mitigat", "prevent", "protect"])

    hypothesis_positive = any(w in h_lower for w in ["increase", "elevat", "worsen", "harm", "impair", "cause"])
    hypothesis_negative = any(w in h_lower for w in ["decrease", "reduc", "lowers", "mitigat", "prevent", "protect"])

    if (premise_positive and not premise_negative and hypothesis_negative and not hypothesis_positive) or \
       (premise_negative and not premise_positive and hypothesis_positive and not hypothesis_negative):
        return NLIVerificationResult(
            status=NLIStatus.CONTRADICTION,
            score=0.0,
            model_used="Local Rule-based NLI",
            explanation="Directional contradiction: Premise asserts reduction/protection while claim asserts increase/elevation (or vice-versa)."
        )

    # Word overlap / coverage
    h_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', h_lower))
    p_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', p_lower))

    if not h_words:
        return NLIVerificationResult(status=NLIStatus.NEUTRAL, score=0.4, model_used="Local Rule-based NLI", explanation="Empty claim hypothesis.")

    overlap = len(h_words.intersection(p_words)) / len(h_words)

    if overlap >= 0.55:
        return NLIVerificationResult(
            status=NLIStatus.ENTAILMENT,
            score=1.0,
            model_used="Local Rule-based NLI",
            explanation=f"High conceptual overlap ({int(overlap*100)}%) with premise."
        )
    elif overlap >= 0.30:
        return NLIVerificationResult(
            status=NLIStatus.NEUTRAL,
            score=0.4,
            model_used="Local Rule-based NLI",
            explanation=f"Partial overlap ({int(overlap*100)}%); insufficient direct grounding."
        )
    else:
        return NLIVerificationResult(
            status=NLIStatus.NEUTRAL,
            score=0.35,
            model_used="Local Rule-based NLI",
            explanation=f"Low concept grounding ({int(overlap*100)}%) in source quote."
        )


def validate_statistics(claim_direction: str, chunk_text: str, quote: str) -> StatisticalValidationResult:
    """
    Validates statistical metrics: checks CI null crossings (1.0 for ratios)
    and directional consistency with claim verb.
    """
    text_to_scan = quote + "\n" + chunk_text
    metrics_found: List[str] = []
    penalty = 0.0
    null_crossing = False
    direction_consistent = True

    # 1. Search for ratio metrics (HR, OR, RR) with optional 95% CI
    # Example: HR = 1.34 (95% CI: 1.12 to 1.60), OR 0.78 [0.65-0.92], OR = 1.15; 95% CI: 0.92 to 1.44
    ratio_matches = re.finditer(
        r'\b(HR|OR|RR|hazard ratio|odds ratio|relative risk)\s*[:=]?\s*([0-9]+\.?[0-9]*)'
        r'(?:[;,]?\s*[\(\[]?\s*(?:95%\s*CI\s*[:=]?)?\s*([0-9]+\.?[0-9]*)\s*(?:-|–|,|\bto\b)\s*([0-9]+\.?[0-9]*)[\)\]]?)?',
        text_to_scan,
        re.IGNORECASE
    )

    seen_ratio_keys = set()
    for m in ratio_matches:
        metric_name = m.group(1).upper()
        estimate = float(m.group(2))
        ci_low = float(m.group(3)) if m.group(3) else None
        ci_high = float(m.group(4)) if m.group(4) else None

        ratio_key = (metric_name, estimate, ci_low, ci_high)
        if ratio_key in seen_ratio_keys:
            continue
        seen_ratio_keys.add(ratio_key)

        metric_str = f"{metric_name} = {estimate}"
        if ci_low is not None and ci_high is not None:
            metric_str += f" (95% CI: [{ci_low}, {ci_high}])"

            # Check Null Crossing: For ratios, does CI cross 1.0?
            if ci_low <= 1.0 <= ci_high:
                null_crossing = True
                penalty += 25.0
                metric_str += " [NULL CROSSING: Non-significant]"
            else:
                metric_str += " [STATISTICALLY SIGNIFICANT]"

        metrics_found.append(metric_str)

        # Check Directional Consistency
        claim_dir_lower = claim_direction.lower()
        asserts_increase = any(w in claim_dir_lower for w in ["increase", "elevate", "risk of", "worsen", "higher"])
        asserts_decrease = any(w in claim_dir_lower for w in ["decrease", "reduce", "lower", "protect", "mitigate"])

        if asserts_increase and estimate < 1.0:
            direction_consistent = False
            penalty += 35.0
            metrics_found.append(f"DIRECTIONAL CONFLICT: Claim asserts increase but {metric_name} = {estimate} (< 1.0) indicates protective effect!")
        elif asserts_decrease and estimate > 1.0:
            direction_consistent = False
            penalty += 35.0
            metrics_found.append(f"DIRECTIONAL CONFLICT: Claim asserts decrease but {metric_name} = {estimate} (> 1.0) indicates elevated risk!")

    # 2. Check P-values
    p_matches = re.findall(r'\bp\s*([<>=])\s*(0?\.[0-9]+)\b', text_to_scan, re.IGNORECASE)
    for op, p_val in p_matches:
        val = float(p_val)
        if op == '<' and val <= 0.05:
            metrics_found.append(f"p < {p_val} (Statistically Significant)")
        elif op == '>' and val >= 0.05:
            metrics_found.append(f"p > {p_val} (Non-Significant)")
            penalty += 15.0

    # 3. Correlation values (r or rho)
    r_matches = re.findall(r'\b(?:r|rho|Spearman\'?s?\s+rho)\s*[:=]\s*([-0-9.]+)\b', text_to_scan, re.IGNORECASE)
    for r_val in r_matches:
        metrics_found.append(f"Correlation coefficient r = {r_val}")

    if not metrics_found:
        return StatisticalValidationResult(
            has_statistics=False,
            metrics_found=[],
            score=0.70,  # Neutral baseline when no numerical stats are cited
            penalty_points=0.0,
            diagnostics="No statistical metric expressions detected in chunk."
        )

    stat_score = max(0.0, 1.0 - (penalty / 50.0))
    diagnostics = "; ".join(metrics_found)

    return StatisticalValidationResult(
        has_statistics=True,
        metrics_found=metrics_found,
        null_crossing=null_crossing,
        directional_consistent=direction_consistent,
        score=stat_score,
        penalty_points=penalty,
        diagnostics=diagnostics
    )
