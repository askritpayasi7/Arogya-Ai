import pytest
from starlette.testclient import TestClient

from health_app.dashboard.app import app
from health_app.dashboard.ask_ai import ClinicalAskAiAdvisor
from health_app.dashboard.google_health import UserHealthData, HeartRateSummary, SleepSummary
from health_app.dashboard.user_profile import UserLifestyleProfile
from health_app.prescription.models import PrescribedMedicineItem, PrescriptionRecord
from health_app.vectordb.store import VectorStore
from health_app.vectordb.embeddings import MockEmbeddingProvider


def test_ask_ai_empty_query():
    result = ClinicalAskAiAdvisor.consult("")
    assert "direct_assessment" in result
    assert "Please enter a health question" in result["direct_assessment"]


def test_ask_ai_deterministic_fallback():
    profile = UserLifestyleProfile(
        email="test_ask_ai@example.com",
        age=32,
        profession="Software Engineer",
        smoking_status="non_smoker",
        diagnosed_conditions=["Prediabetes"],
        active_medications=[PrescribedMedicineItem(name="Metformin", strength="500 mg")],
        prescriptions=[
            PrescriptionRecord(
                prescriber_name="Dr. Alan Vance",
                clinic_or_place="Austin Health",
                prescription_date="2026-03-01",
                diagnosed_diseases=["Prediabetes"],
                medicines=[PrescribedMedicineItem(name="Metformin", strength="500 mg")],
            )
        ],
    )

    retrieved = [
        {
            "title": "Role of Nutrition and Behavioral Timing in Metabolic Stability",
            "authors": "Nguyen HT, Phan PD, et al.",
            "year": "2026",
            "doi": "10.3746/pnf.2026.104",
            "quote": "Dietary interventions and structured behavioral rhythms demonstrate significant improvements in glycemic variability and parasympathetic autonomic regulation.",
            "claim": "Structured behavioral and nutritional timing supports parasympathetic recovery."
        }
    ]

    res = ClinicalAskAiAdvisor._deterministic_fallback(
        query="Feeling sudden energy crash and fatigue after lunch",
        heart_rate_str="74 bpm (Optimal)",
        sleep_str="6.8 hrs",
        steps_str="4,200 steps",
        user_profile=profile,
        retrieved_items=retrieved,
    )

    assert "direct_assessment" in res
    assert "Nguyen HT" in res["direct_assessment"]
    assert "Metformin" in res["direct_assessment"]
    assert "biomarker_correlation" in res
    assert "Software Engineer" in res["biomarker_correlation"]
    assert len(res["scientific_mechanisms"]) >= 1

    mech = res["scientific_mechanisms"][0]
    assert "evidence_quote" in mech
    assert "Dietary interventions" in mech["evidence_quote"]
    assert mech["authors"] == "Nguyen HT, Phan PD, et al."
    assert mech["doi"] == "10.3746/pnf.2026.104"

    assert len(res["action_plan"]) == 3
    assert "physician_escalation" in res
    assert len(res["cited_papers"]) >= 1
    assert res["cited_papers"][0]["authors"] == "Nguyen HT, Phan PD, et al."


def test_ask_ai_evidence_retrieval_and_formatting():
    vs = VectorStore(embedding_provider=MockEmbeddingProvider(), in_memory=True, collection_prefix="test_ask")
    vs.clear()

    vs.add_verified_relationships([
        {
            "claim_summary": "Postprandial light movement -> improves -> glycemic excursion and autonomic balance",
            "evidence_quote": "A 10-minute post-meal walk attenuated glucose peaks by 22% and enhanced parasympathetic reactivation.",
            "gating_status": "ACCEPTED",
            "final_score": 90.0,
            "paper_title": "Postprandial Walking and Cardiometabolic Dynamics",
            "authors": "Reynolds AN, Mann J, et al.",
            "publish_year": "2025",
            "doi": "10.1007/s00125-025-05820-2",
            "study_design": {"design_type": "RCT"},
            "grade_synthesis": {"concept_pair": "walking__to__glucose"}
        }
    ])

    profile = UserLifestyleProfile(email="eval_user@example.com")
    items = ClinicalAskAiAdvisor._retrieve_evidence("postprandial walking glucose", vs, profile)
    assert len(items) >= 1
    top = items[0]
    assert "Reynolds AN" in top["authors"]
    assert "10.1007/s00125-025-05820-2" in top["doi"]
    assert "evidence_quote" in top or "quote" in top


def test_ask_ai_api_endpoint():
    client = TestClient(app)

    # 1. Empty query should return 400
    bad_resp = client.post("/api/ai/ask", json={"query": ""})
    assert bad_resp.status_code == 400

    # 2. Valid clinical query
    resp = client.post(
        "/api/ai/ask",
        json={"query": "I am feeling fatigued in the afternoon with elevated resting pulse. What does literature recommend?"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "result" in data
    res = data["result"]
    assert "direct_assessment" in res
    assert "biomarker_correlation" in res
    assert "scientific_mechanisms" in res
    assert len(res["scientific_mechanisms"]) >= 1

    # Check that scientific mechanisms contain author quotes and DOI
    for mech in res["scientific_mechanisms"]:
        assert "evidence_quote" in mech
        assert "authors" in mech
        assert "doi" in mech

    assert "action_plan" in res
    assert len(res["action_plan"]) >= 1
    assert "cited_papers" in res
    assert len(res["cited_papers"]) >= 1
