from src.gemini_client import _candidate_models, _extract_json


def test_extract_json_from_fenced_text():
    payload = _extract_json(
        """```json
        {"patient_name_original": "unclear", "medicines": []}
        ```"""
    )
    assert payload["patient_name_original"] == "unclear"


def test_extract_json_from_noisy_text():
    payload = _extract_json('Here you go:\n{"overall_confidence": "low"}')
    assert payload["overall_confidence"] == "low"


def test_candidate_models_prefers_specified_and_deduplicates():
    candidates = _candidate_models(preferred="gemini-3.5-flash-lite")
    assert candidates[0] == "gemini-3.5-flash-lite"
    assert len(candidates) == len(set(candidates))
    assert "gemini-3.5-flash" in candidates
