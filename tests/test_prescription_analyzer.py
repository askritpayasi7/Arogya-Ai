import io
import pytest
from PIL import Image, ImageDraw
from starlette.testclient import TestClient

from health_app.dashboard.app import app
from health_app.dashboard.biometric_advisor import BiometricAdvisor
from health_app.dashboard.user_profile import (
    UserLifestyleProfile,
    save_user_profile,
    load_user_profile,
)
from health_app.prescription.analyzer import PrescriptionAnalyzer
from health_app.prescription.models import (
    PrescribedMedicineItem,
    PrescriptionExtractionResult,
    PrescriptionRecord,
    _is_clean_value,
)
from health_app.prescription.preprocessor import ImagePreprocessor


def create_sample_prescription_image() -> bytes:
    """Generate a clean synthetic test prescription image."""
    img = Image.new("RGB", (600, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((30, 30), "Dr. Sarah Jenkins, MD - Cardiology Clinic", fill=(0, 0, 0))
    draw.text((30, 60), "Date: 2026-04-10", fill=(0, 0, 0))
    draw.text((30, 90), "Rx: Atorvastatin 20mg - 1 tab at bedtime", fill=(0, 0, 0))
    draw.text((30, 120), "Diagnosis: Hyperlipidemia", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_clean_value_filter():
    assert _is_clean_value("Amoxicillin") is True
    assert _is_clean_value("") is False
    assert _is_clean_value("   ") is False
    assert _is_clean_value("unclear") is False
    assert _is_clean_value("N/A") is False
    assert _is_clean_value("null") is False
    assert _is_clean_value(None) is False


def test_models_omit_empty_fields():
    # Medicine Item with missing duration/route
    med = PrescribedMedicineItem(
        name="Metformin",
        strength="500 mg",
        dosage="1 tablet",
        frequency="Twice daily",
        duration="unclear",  # Should be omitted
        route=None,          # Should be omitted
        instructions="Take with meals",
    )
    compact_med = med.to_compact_dict()
    assert compact_med["name"] == "Metformin"
    assert compact_med["strength"] == "500 mg"
    assert compact_med["dosage"] == "1 tablet"
    assert compact_med["frequency"] == "Twice daily"
    assert compact_med["instructions"] == "Take with meals"
    assert "duration" not in compact_med
    assert "route" not in compact_med

    # Prescription Record with missing clinic
    rx = PrescriptionRecord(
        prescriber_name="Dr. Jenkins",
        clinic_or_place="unclear",  # Should be omitted
        prescription_date="2026-03-20",
        diagnosed_diseases=["Type 2 Diabetes", "n/a"],
        medicines=[med],
    )
    compact_rx = rx.to_compact_dict()
    assert compact_rx["prescriber_name"] == "Dr. Jenkins"
    assert "clinic_or_place" not in compact_rx
    assert compact_rx["prescription_date"] == "2026-03-20"
    assert compact_rx["diagnosed_diseases"] == ["Type 2 Diabetes"]
    assert len(compact_rx["medicines"]) == 1


def test_image_preprocessor():
    raw_bytes = create_sample_prescription_image()
    preprocessed = ImagePreprocessor.preprocess(raw_bytes)
    assert preprocessed.original_pil is not None
    assert preprocessed.processed_pil is not None
    assert preprocessed.width == 600
    assert preprocessed.height == 400
    assert isinstance(preprocessed.skew_angle, float)


def test_analyzer_dictionary_suggestions():
    analyzer = PrescriptionAnalyzer()
    # Test close match lookup for common misspelled drugs
    sug = analyzer.suggest_medicine_name("Paracetmol")
    if sug:
        assert "Paracetamol" in sug or "paracetamol" in sug.lower()


def test_user_profile_prescription_lifecycle():
    test_email = "rx_test_patient@example.com"
    profile = UserLifestyleProfile(
        email=test_email,
        age=35,
        profession="Architect",
    )

    rx = PrescriptionRecord(
        id="rx_test_123",
        prescriber_name="Dr. Elizabeth Reed",
        clinic_or_place="Northwestern Memorial Hospital",
        prescription_date="2026-02-15",
        diagnosed_diseases=["Essential Hypertension", "Mild Tachycardia"],
        medicines=[
            PrescribedMedicineItem(
                name="Amlodipine",
                strength="5 mg",
                dosage="1 tablet",
                frequency="Once daily in morning",
            ),
            PrescribedMedicineItem(
                name="Propranolol",
                strength="10 mg",
                dosage="1 tablet",
                frequency="PRN for palpitations",
            ),
        ],
    )

    profile.add_prescription(rx)
    assert len(profile.prescriptions) == 1
    assert "Essential Hypertension" in profile.diagnosed_conditions
    assert "Mild Tachycardia" in profile.diagnosed_conditions
    assert any(m.name == "Amlodipine" for m in profile.active_medications)

    # Save and reload
    save_user_profile(test_email, profile)
    reloaded = load_user_profile(test_email)
    assert reloaded is not None
    assert len(reloaded.prescriptions) == 1
    assert reloaded.prescriptions[0].prescriber_name == "Dr. Elizabeth Reed"

    # Delete prescription
    deleted = profile.delete_prescription("rx_test_123")
    assert deleted is True
    assert len(profile.prescriptions) == 0
    assert len(profile.active_medications) == 0


def test_biometric_advisor_incorporates_prescriptions():
    profile = UserLifestyleProfile(
        email="advisor_rx_test@example.com",
        age=40,
        profession="Financial Analyst",
        diagnosed_conditions=["Hypertension", "Dyslipidemia"],
        active_medications=[
            PrescribedMedicineItem(name="Atorvastatin", strength="20 mg"),
            PrescribedMedicineItem(name="Metoprolol", strength="25 mg"),
        ],
        prescriptions=[
            PrescriptionRecord(
                prescriber_name="Dr. Robert Vance",
                clinic_or_place="Boston Heart Center",
                prescription_date="2026-01-10",
                diagnosed_diseases=["Hypertension"],
                medicines=[PrescribedMedicineItem(name="Metoprolol", strength="25 mg")],
            )
        ],
    )

    meta = BiometricAdvisor._build_user_metadata(profile)
    assert "diagnosed_conditions" in meta
    assert "Hypertension" in meta["diagnosed_conditions"]
    assert "active_medications" in meta
    assert any(m["name"] == "Metoprolol" for m in meta["active_medications"])
    assert "past_prescriptions" in meta
    assert meta["past_prescriptions"][0]["prescriber_name"] == "Dr. Robert Vance"

    # Test report synthesis fallback includes condition & medication context
    context_payload = {
        "user_metadata": meta,
        "current_deviation": {"metric": "resting_heart_rate", "acute_reading": "82 bpm"},
    }
    evidence = {
        "subject": "Sympathetic autonomic tone",
        "relation": "elevates",
        "object": "resting pulse",
        "evidence_quote": "Elevated sympathetic activation accelerates sinus node firing.",
    }
    report = BiometricAdvisor._synthesize_report_from_evidence(
        context_payload=context_payload,
        retrieved_evidence=evidence,
        user_profile=profile,
        vital_category="cardiovascular",
        default_headline="Elevated Heart Rate",
    )
    assert "potential_causes" in report
    causes_text = " ".join(report["potential_causes"]).lower()
    assert any(term in causes_text for term in ["metoprolol", "blockade", "hypertension", "pre-existing", "medication", "beta"])


def test_prescription_api_endpoints():
    client = TestClient(app)

    # 1. GET /dashboard/prescriptions page
    resp = client.get("/dashboard/prescriptions?demo=true")
    assert resp.status_code == 200
    assert "Prescription Analyzer" in resp.text
    assert "Upload Prescription" in resp.text
    assert "Review Extracted Details" in resp.text

    # 2. POST /api/prescriptions/analyze
    raw_img = create_sample_prescription_image()
    files = {"prescription_image": ("prescription.png", raw_img, "image/png")}
    resp = client.post("/api/prescriptions/analyze", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "data" in data

    # 3. POST /api/prescriptions/save
    save_payload = {
        "prescriber_name": "Dr. Catherine Howard",
        "clinic_or_place": "Cedars-Sinai Medical Center",
        "prescription_date": "2026-05-12",
        "diagnosed_diseases": ["Chronic Bronchitis", "Seasonal Rhinitis"],
        "medicines": [
            {
                "name": "Levocetirizine",
                "strength": "5 mg",
                "dosage": "1 tablet",
                "frequency": "Once daily at night",
                "included": True,
            },
            {
                "name": "ExcludedMed",
                "included": False,  # Should not be added to active meds
            },
        ],
    }
    resp = client.post("/api/prescriptions/save", json=save_payload)
    assert resp.status_code == 200
    save_data = resp.json()
    assert save_data["status"] == "success"
    assert "Chronic Bronchitis" in save_data["diagnosed_conditions"]
    assert any(m["name"] == "Levocetirizine" for m in save_data["active_medications"])
    assert not any(m["name"] == "ExcludedMed" for m in save_data["active_medications"])

    # 4. GET /api/prescriptions/list
    resp = client.get("/api/prescriptions/list")
    assert resp.status_code == 200
    list_data = resp.json()
    assert list_data["status"] == "success"
    assert len(list_data["prescriptions"]) >= 1

    # 5. DELETE /api/prescriptions/{rx_id}
    rx_id = list_data["prescriptions"][0]["id"]
    del_resp = client.delete(f"/api/prescriptions/{rx_id}")
    assert del_resp.status_code == 200
    del_data = del_resp.json()
    assert del_data["status"] == "success"
