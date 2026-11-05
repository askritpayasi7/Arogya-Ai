import pytest
from pathlib import Path
from starlette.testclient import TestClient

from health_app.dashboard.app import app
from health_app.vectordb.store import (
    VectorStore,
    COLLECTION_VERIFIED_RELATIONSHIPS,
    SearchResultItem,
)
from health_app.vectordb.embeddings import MockEmbeddingProvider
from health_app.dashboard.user_profile import (
    UserLifestyleProfile,
    load_user_profile,
    save_user_profile,
    get_default_demo_profile,
)
from health_app.dashboard.baseline_engine import (
    StatisticalBaselineEngine,
    UserBaselineReport,
    MetricBaseline,
)
from health_app.dashboard.biometric_advisor import BiometricAdvisor, BiometricInsight
from health_app.dashboard.google_health import (
    UserHealthData,
    HeartRateSummary,
    SleepSummary,
    DailyRecord,
    DailySteps,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_vector_store_strict_passed_only_indexing():
    """Verify that ONLY passed relationships (ACCEPTED or PROVISIONALLY_SUPPORTED >= 70.0) are indexed in ChromaDB."""
    vs = VectorStore(embedding_provider=MockEmbeddingProvider(), in_memory=True, collection_prefix="test_strict")
    vs.clear()

    mock_reports = [
        # Passed 1: ACCEPTED
        {
            "claim_summary": "Combined short sleep duration and nicotine use -> elevates -> nocturnal heart rate and sympathetic tone",
            "evidence_quote": "Combined short sleep duration and nicotine use significantly amplify sympathetic nervous system activation and nocturnal heart rate elevation.",
            "gating_status": "ACCEPTED",
            "final_score": 85.0,
            "paper_title": "Sleep-Autonomic Interactions & Stimulant Synergies",
            "authors": "Mackenbach et al.",
            "publish_year": "2024",
            "doi": "10.1002/mdc3.70817",
            "study_design": {"design_type": "Prospective Cohort"},
            "grade_synthesis": {"concept_pair": "nicotine_sleep__to__heart_rate"}
        },
        # Passed 2: PROVISIONALLY_SUPPORTED
        {
            "claim_summary": "Slow-wave nocturnal sleep -> reduces -> morning arterial stiffness",
            "evidence_quote": "Clinical polysomnography establishes that adequate slow-wave sleep stabilizes myocardial metabolic demand.",
            "gating_status": "PROVISIONALLY_SUPPORTED",
            "final_score": 74.0,
            "paper_title": "Fetal and Adult Sleep Physiology",
            "authors": "Tang et al.",
            "publish_year": "2025",
            "doi": "10.1093/sleep/zsag003",
            "study_design": {"design_type": "Cross-Sectional Observational Study"},
            "grade_synthesis": {"concept_pair": "sleep__to__arterial_stiffness"}
        },
        # FAILED 1: EXCLUDED (must be strictly blocked!)
        {
            "claim_summary": "Low-quality observational claim -> has no effect on -> outcomes",
            "evidence_quote": "Uncontrolled observational survey.",
            "gating_status": "EXCLUDED",
            "final_score": 35.0,
            "paper_title": "Unverified Blog Claim",
            "study_design": {"design_type": "Narrative"},
            "grade_synthesis": {"concept_pair": "unverified__to__none"}
        },
        # FAILED 2: QUARANTINED (must be strictly blocked!)
        {
            "claim_summary": "Borderline claim -> conflicts with -> established clinical literature",
            "evidence_quote": "Conflicting observations.",
            "gating_status": "QUARANTINED",
            "final_score": 52.0,
            "paper_title": "Conflicting Trial",
            "study_design": {"design_type": "Cross-Sectional"},
            "grade_synthesis": {"concept_pair": "conflicting__to__outcomes"}
        }
    ]

    added_count = vs.add_verified_relationships(mock_reports)
    # Exactly 2 passed reports must be added; the 2 excluded/quarantined reports must be rejected
    assert added_count == 2
    assert vs.verified_collection.count() == 2

    # Query with metadata filter for smoking
    results = vs.query_verified_relationships("nicotine heart rate", n_results=2, where={"smoking_relevant": True})
    assert len(results) >= 1
    assert "nicotine" in results[0].content.lower()
    assert results[0].metadata["smoking_relevant"] is True
    assert results[0].metadata["gating_status"] == "ACCEPTED"


def test_user_lifestyle_profile_crud(tmp_path, monkeypatch):
    """Test user profile model validation, age bracket resolution, and serialization."""
    from health_app.dashboard import user_profile

    monkeypatch.setattr(user_profile, "USER_PROFILES_DIR", tmp_path)

    profile = UserLifestyleProfile(
        email="smoker_test@example.com",
        age=28,
        profession="Software Engineer",
        smoking_status="current_smoker",
        alcohol_consumption="moderate",
        chronic_risk_factors=["Sedentary Desk Time"],
        primary_health_goal="Cardiovascular Stability",
        onboarding_completed=True
    )

    assert profile.get_age_bracket() == "young_adult"
    assert profile.is_current_smoker() is True
    assert profile.is_regular_drinker() is True

    # Test save and reload
    save_user_profile("smoker_test@example.com", profile)
    loaded = load_user_profile("smoker_test@example.com")

    assert loaded is not None
    assert loaded.email == "smoker_test@example.com"
    assert loaded.age == 28
    assert loaded.smoking_status == "current_smoker"
    assert loaded.onboarding_completed is True


def test_15_day_calibration_mode_state_machine():
    """Verify that fewer than 15 active days triggers Calibration Mode with clinical alarm suppression."""
    history = [
        DailyRecord(date=f"2026-10-0{i}", formatted_date=f"Oct 0{i}", day_name="Mon", steps=7500, heart_rate_bpm=68, sleep_hours=6.8)
        for i in range(1, 8)  # Exactly 7 active days
    ]

    report = StatisticalBaselineEngine.evaluate_user_telemetry(
        email="calib_user@example.com",
        history_records=history,
        acute_heart_rate=80.0,
        acute_sleep_hours=4.0,
        acute_steps=5000
    )

    assert report.state == "calibration_mode"
    assert report.calibration_day == 7
    assert report.calibration_target == 15
    assert report.calibration_percentage == 46  # round(7/15 * 100)
    assert report.suppress_clinical_alarms is True

    # Verify that BiometricAdvisor acknowledges calibration mode and suppresses harsh diagnostic alarms
    profile = UserLifestyleProfile(email="calib_user@example.com", onboarding_completed=True)
    health_data = UserHealthData(
        user_name="Calib User",
        user_email="calib_user@example.com",
        today_steps=5000,
        heart_rate=HeartRateSummary(resting_bpm=80),
        sleep=SleepSummary(total_hours=4.0)
    )

    insights = BiometricAdvisor.generate_personalized_insights(health_data, profile, report)
    calib_insight = next(i for i in insights if "Calibration" in i.category)
    assert calib_insight.status_level == "caution"
    assert "CALIBRATING" in calib_insight.verification_badge


def test_active_calibrated_baseline_and_ewma_drift():
    """Verify that 15+ active days locks in personalized baseline (μ ± 1.5σ) and computes EWMA drift."""
    # 20 days with historical resting heart rate averaging ~64 bpm (60 - 68 bpm)
    history = [
        DailyRecord(
            date=f"2026-10-{i:02d}",
            formatted_date=f"Oct {i:02d}",
            day_name="Wed",
            steps=9500,
            heart_rate_bpm=62 if i % 2 == 0 else 66,
            sleep_hours=7.2
        )
        for i in range(1, 21)  # 20 active days
    ]

    # Acute reading: resting heart rate spikes to 78 bpm (+14 bpm above personal 64 bpm norm)
    report = StatisticalBaselineEngine.evaluate_user_telemetry(
        email="calibrated@example.com",
        history_records=history,
        acute_heart_rate=78.0,
        acute_sleep_hours=3.5,
        acute_steps=11240
    )

    assert report.state == "active_calibrated"
    assert report.calibration_percentage == 100
    assert report.suppress_clinical_alarms is False

    hr_base = report.heart_rate
    assert hr_base is not None
    assert hr_base.rolling_mean == 64.0
    assert hr_base.lower_bound < 64.0 < hr_base.upper_bound
    # 78 bpm is well above upper bound (64 + 1.5 * 2.0 = 67.0)
    assert hr_base.acute_value == 78.0
    assert hr_base.is_anomaly is True
    assert hr_base.variance_delta_z > 1.5
    assert "Elevated" in hr_base.deviation_label


def test_dynamic_context_payload_and_multi_modal_personalization():
    """Verify metadata-filtered retrieval and dynamic context payload formatting matching clinical spec."""
    vs = VectorStore(embedding_provider=MockEmbeddingProvider(), in_memory=True, collection_prefix="test_mm")
    vs.clear()

    # Index passed clinical rule
    vs.add_verified_relationships([
        {
            "claim_summary": "Combined short sleep duration and nicotine use -> significantly amplify -> sympathetic nervous system activation and nocturnal heart rate elevation",
            "evidence_quote": "Combined short sleep duration and nicotine use significantly amplify sympathetic nervous system activation and nocturnal heart rate elevation.",
            "gating_status": "ACCEPTED",
            "final_score": 88.5,
            "paper_title": "Ambulatory Sleep-Autonomic Interactions in Daily Smokers",
            "authors": "Mackenbach et al.",
            "publish_year": "2024",
            "doi": "10.1002/mdc3.70817",
            "study_design": {"design_type": "Prospective Cohort"},
            "grade_synthesis": {"concept_pair": "nicotine_sleep__to__heart_rate"}
        }
    ])

    user_profile = UserLifestyleProfile(
        email="smoker_patient@example.com",
        age=28,
        profession="Software Engineer",
        smoking_status="current_smoker",
        alcohol_consumption="moderate",
        chronic_risk_factors=["Desk Work"],
        onboarding_completed=True
    )

    history = [
        DailyRecord(date=f"2026-10-{i:02d}", formatted_date=f"Oct {i:02d}", day_name="Mon", steps=8000, heart_rate_bpm=64, sleep_hours=7.2)
        for i in range(1, 18)  # 17 days
    ]

    report = StatisticalBaselineEngine.evaluate_user_telemetry(
        email=user_profile.email,
        history_records=history,
        acute_heart_rate=78.0,
        acute_sleep_hours=3.5,
        acute_steps=11240
    )

    health_data = UserHealthData(
        user_name="John Smoker",
        user_email=user_profile.email,
        today_steps=11240,
        heart_rate=HeartRateSummary(resting_bpm=78, latest_bpm=78),
        sleep=SleepSummary(total_hours=3.5)
    )

    insights = BiometricAdvisor.generate_personalized_insights(
        health_data=health_data,
        user_profile=user_profile,
        baseline_report=report,
        vector_store=vs
    )

    hr_insight = next(i for i in insights if "Cardiovascular" in i.category and i.status_level == "warning")
    assert hr_insight is not None
    # Verifies hyper-personalized, non-generic explanation referencing smoker profile
    assert "current smoker" in hr_insight.clinical_finding.lower()
    assert "personal mean of 64.0 bpm" in hr_insight.clinical_finding
    assert "nicotine" in hr_insight.clinical_finding.lower()

    # Verify context payload structure
    payload = hr_insight.context_payload
    assert payload is not None
    assert payload["user_metadata"]["smoking_status"] == "current_smoker"
    assert payload["user_metadata"]["baseline_status"] == "active_calibrated"
    assert payload["current_deviation"]["metric"] == "resting_heart_rate"
    assert len(payload["retrieved_evidence"]) > 0


def test_onboarding_page_and_submission_routes(client):
    """Test GET /onboarding form view and POST /api/user/onboarding form submission."""
    # 1. GET /onboarding
    res_get = client.get("/onboarding")
    assert res_get.status_code == 200
    assert "Personalized Medical Profile Setup" in res_get.text
    assert "smoking_status" in res_get.text
    assert "alcohol_consumption" in res_get.text

    # 2. POST /api/user/onboarding
    form_data = {
        "email": "form_test@example.com",
        "age": "32",
        "profession": "Clinical Data Scientist",
        "smoking_status": "former_smoker",
        "alcohol_consumption": "occasional",
        "chronic_risk_factors": ["Sedentary Workday"],
        "primary_health_goal": "Autonomic Stress Modulation"
    }
    res_post = client.post("/api/user/onboarding", data=form_data, follow_redirects=False)
    assert res_post.status_code == 303
    assert res_post.headers["location"] == "/dashboard"

    # Verify saved profile
    saved = load_user_profile("form_test@example.com")
    assert saved is not None
    assert saved.age == 32
    assert saved.profession == "Clinical Data Scientist"
    assert saved.smoking_status == "former_smoker"
    assert saved.onboarding_completed is True
