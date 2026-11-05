from src.export import to_json_bytes, to_pdf_bytes
from src.models import MedicineItem, PrescriptionExtraction
from src.validation import validate_extraction


def _sample() -> tuple[PrescriptionExtraction, object]:
    extraction = PrescriptionExtraction(
        patient_name_original="Test User",
        prescriber_name_original="Dr. Sharma",
        date_original="unclear",
        raw_transcription="Amoxicillin 500 mg 1 cap TDS",
        overall_confidence="medium",
        medicines=[
            MedicineItem(
                medicine_name_original="Amoxicillin",
                strength_original="500 mg",
                dosage_original="1 cap",
                frequency_original="TDS",
                duration_original="5 days",
                route_original="PO",
            )
        ],
    )
    return extraction, validate_extraction(extraction)


def test_json_and_pdf_export_include_disclaimer():
    extraction, report = _sample()
    json_bytes = to_json_bytes(extraction, report, verified=False, reviewer_notes="")
    pdf_bytes = to_pdf_bytes(extraction, report, verified=False, reviewer_notes="check dose")
    assert b"transcription" in json_bytes.lower()
    assert b"verified_by_human" in json_bytes
    assert pdf_bytes.startswith(b"%PDF")
    assert b"SAFETY NOTICE" in pdf_bytes or len(pdf_bytes) > 500
