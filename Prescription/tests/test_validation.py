from src.models import MedicineItem, PrescriptionExtraction
from src.validation import validate_extraction, validate_unit


def test_unit_format_validation():
    assert validate_unit("500 mg")
    assert validate_unit("40mg")
    assert not validate_unit("unclear")
    assert not validate_unit("plenty")


def test_fuzzy_suggestion_is_not_auto_applied():
    extraction = PrescriptionExtraction(
        overall_confidence="medium",
        medicines=[
            MedicineItem(
                medicine_name_original="Amoxcilin",
                strength_original="500 mg",
                dosage_original="1 cap",
                frequency_original="TDS",
                duration_original="5 days",
                route_original="PO",
                special_instructions_original="after food",
            )
        ],
    )
    report = validate_extraction(extraction)
    assert report.requires_human_review is True
    suggestions = report.medicines[0].suggestions
    assert suggestions
    assert suggestions[0].auto_applied is False
    assert suggestions[0].original == "Amoxcilin"
    assert "Amoxicillin" in suggestions[0].suggestion


def test_missing_and_unclear_fields_are_flagged():
    extraction = PrescriptionExtraction(
        overall_confidence="low",
        medicines=[
            MedicineItem(
                medicine_name_original="unclear",
                strength_original="unclear",
                dosage_original="unclear",
                frequency_original="unclear",
                duration_original="unclear",
                route_original="unclear",
                unclear_fields=["medicine_name_original", "strength_original"],
            )
        ],
    )
    report = validate_extraction(extraction)
    assert report.missing_count >= 5
    assert report.unclear_count >= 2
    assert any(issue.level == "critical" for issue in report.issues)
