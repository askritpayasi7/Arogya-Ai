import json
import pytest
from starlette.testclient import TestClient

from health_app.config import settings
from health_app.dashboard.app import app
from health_app.dashboard.user_profile import UserLifestyleProfile
from health_app.dashboard.baseline_engine import (
    StatisticalBaselineEngine,
    UserBaselineReport,
    MetricBaseline,
)
from health_app.dashboard.google_health import (
    UserHealthData,
    DailySteps,
    DailyRecord,
    HeartRateSummary,
    SleepSummary,
    DailySleepRecord,
    resolve_user_timezone,
    generate_demo_history,
    generate_demo_weekly_sleep,
)
from health_app.dashboard.biometric_advisor import (
    BiometricAdvisor,
    BiometricInsight,
    ClinicalEvidenceSignature,
    CategoryVitalSummary,
)
from health_app.fetcher.client import CandidatePaper
from health_app.vectordb.store import VectorStore, COLLECTION_VERIFIED_RELATIONSHIPS


@pytest.fixture
def client():
    return TestClient(app)


def test_hunter_search_endpoint_unauthorized(client):
    """Attempting hunter search without admin session must return 401."""
    resp = client.post("/api/admin/hunter/search", json={"query": "circadian rhythm"})
    assert resp.status_code == 401


def test_hunter_search_endpoint_success(client, monkeypatch):
    """Admin hunter search returns candidate papers from mock search client."""
    def mock_search_all(self, query, limit=6):
        return [
            CandidatePaper(
                paper_id="pmc_12345",
                title="Circadian Sleep Architecture and Autonomic Regulation",
                authors="Smith J, Doe A",
                year="2024",
                journal="Journal of Sleep Medicine",
                doi="10.1016/j.sleep.2024.01.001",
                abstract="Investigation into slow wave sleep and cardiac vagal tone.",
                pdf_url="https://europepmc.org/articles/PMC12345/pdf",
                source="Europe PMC"
            )
        ]

    from health_app.fetcher.client import PaperSearchClient
    monkeypatch.setattr(PaperSearchClient, "search_all", mock_search_all)

    # Set admin session cookie
    client.post("/admin/login", data={"password": settings.admin_password})
    resp = client.post("/api/admin/hunter/search", json={"query": "circadian rhythm", "limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["total_found"] == 1
    assert data["candidates"][0]["title"] == "Circadian Sleep Architecture and Autonomic Regulation"
    assert data["candidates"][0]["pdf_url"] is not None


def test_hunter_ingest_endpoint_unauthorized(client):
    """Attempting hunter ingest without admin session must return 401."""
    resp = client.post("/api/admin/hunter/ingest", json={"selected_papers": []})
    assert resp.status_code == 401


def test_hunter_ingest_endpoint_success(client, tmp_path, monkeypatch):
    """Admin hunter ingest sequentially processes papers, extracts claims, and updates embeddings."""
    from health_app.fetcher.downloader import PDFDownloader
    from health_app.fetcher.registry import PaperRegistry

    monkeypatch.setattr(settings, "research_papers_dir", tmp_path / "papers")
    monkeypatch.setattr(settings, "chroma_persist_dir", tmp_path / "vdb")

    sample_paper = {
        "paper_id": "test_pmc_999",
        "title": "Combined Physical Inactivity and Nocturnal Tachycardia in Sedentary Cohorts",
        "authors": "Mackenbach H, Johnson P",
        "year": "2024",
        "journal": "Circulation",
        "doi": "10.1161/CIRC.2024.999",
        "abstract": "Sedentary adults exhibiting resting pulse above personal mean displayed impaired vagal reactivation and cardiovascular strain.",
        "pdf_url": ""  # triggers markdown summary path
    }

    # Authenticate as admin
    client.post("/admin/login", data={"password": settings.admin_password})
    resp = client.post("/api/admin/hunter/ingest", json={"selected_papers": [sample_paper]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["processed_papers_count"] == 1
    assert "total_embeddings_in_db" in data
    assert isinstance(data["total_embeddings_in_db"], int)


def test_biometric_insight_model_backward_compatibility_and_signing():
    """Verify BiometricInsight synchronizes headline, title, category, and evidence signatures."""
    sig = ClinicalEvidenceSignature(
        paper_title="Sleep Physiology & Heart Rate Variability",
        authors="Alexander S, et al.",
        publish_year="2025",
        doi="10.1093/sleep/zsag001",
        study_design="RCT",
        composite_score=91.5,
        gating_status="ACCEPTED",
        signature_badge="[ACCEPTED - GRADE VERIFIED]"
    )

    insight = BiometricInsight(
        vital_category="cardiovascular",
        category_title="Cardiovascular & Autonomic Strain",
        headline="Acute Resting Pulse Elevation Compounded by Sedentary Duration",
        metric_observation="Resting heart rate is 78 bpm (+1.8σ) while daily steps are 3,420 (-1.5σ).",
        potential_causes=["Delayed vagal reactivation", "Sympathetic overdrive"],
        potential_risks=["Arterial stiffening", "Nocturnal non-dipping blood pressure"],
        action_plan=["Walk briskly for 20 minutes", "Practice paced respiration"],
        consultation_guidance="RECOMMENDED: Consult physician if resting pulse remains >75 bpm for 48h.",
        consult_recommended=True,
        evidence_signature=sig
    )

    # Check backward-compatible properties
    assert insight.title == "Acute Resting Pulse Elevation Compounded by Sedentary Duration"
    assert insight.category == "Cardiovascular & Autonomic Strain"
    assert insight.paper_title == "Sleep Physiology & Heart Rate Variability"
    assert insight.authors == "Alexander S, et al."
    assert insight.publish_year == "2025"
    assert insight.doi == "10.1093/sleep/zsag001"
    assert insight.verification_badge == "[ACCEPTED - GRADE VERIFIED]"
    assert insight.consult_recommended is True
    assert len(insight.potential_causes) == 2
    assert len(insight.potential_risks) == 2
    assert len(insight.action_plan) == 2


def test_dynamic_vector_embedding_determined_cross_metric_anomaly(tmp_path, monkeypatch):
    """Verify that cross-metric deviations (HR above baseline + low steps) generate a multi-sensor advisory report."""
    monkeypatch.setattr(settings, "chroma_persist_dir", tmp_path / "vdb")

    profile = UserLifestyleProfile(
        email="smoker_patient@example.com",
        age=29,
        profession="Software Engineer",
        smoking_status="current_smoker",
        alcohol_consumption="moderate",
        chronic_risk_factors=["hypertension"],
        baseline_status="active_calibrated",
        onboarding_completed=True
    )

    tz = resolve_user_timezone(-330)
    health_data = UserHealthData(
        user_name="John Doe",
        user_email="smoker_patient@example.com",
        today_steps=3200,  # low steps (<5000)
        heart_rate=HeartRateSummary(resting_bpm=79, latest_bpm=81),  # acute high HR
        sleep=SleepSummary(total_hours=5.5, formatted_duration="5h 30m"),
        is_live_data=True
    )

    # 15+ days history establishing calibrated mean: HR mean = 63 bpm, Steps mean = 10,200
    history = generate_demo_history(tz, days=20)
    baseline_report = StatisticalBaselineEngine.evaluate_user_telemetry(
        email=profile.email,
        history_records=history,
        acute_heart_rate=79.0,  # significantly above rolling mean of ~63
        acute_sleep_hours=5.5,
        acute_steps=3200        # significantly below rolling mean of ~10k
    )

    assert baseline_report.state == "active_calibrated"
    assert baseline_report.heart_rate.is_anomaly is True
    assert baseline_report.heart_rate.status_category == "elevated"

    vs = VectorStore()
    insights = BiometricAdvisor.generate_personalized_insights(
        health_data=health_data,
        user_profile=profile,
        baseline_report=baseline_report,
        vector_store=vs
    )

    assert len(insights) >= 1
    cross_card = next((i for i in insights if i.cross_metric_flag), None)
    assert cross_card is not None, "Expected cross-metric correlation card when HR is elevated and steps are low"
    assert cross_card.vital_category == "cardiovascular"
    assert cross_card.status_level == "warning"
    assert len(cross_card.potential_causes) > 0
    assert len(cross_card.potential_risks) > 0
    assert len(cross_card.action_plan) > 0
    assert cross_card.consult_recommended is True
    assert "RECOMMENDED" in cross_card.consultation_guidance
    assert cross_card.evidence_signature is not None
    assert cross_card.evidence_signature.doi is not None


def test_category_vital_summaries_generation():
    """Verify generation of sidebar category summaries with short analyses."""
    tz = resolve_user_timezone(-330)
    profile = UserLifestyleProfile(
        email="patient@example.com",
        age=32,
        profession="Architect",
        smoking_status="never",
        alcohol_consumption="none",
        baseline_status="active_calibrated"
    )
    health_data = UserHealthData(
        user_name="Jane Doe",
        user_email="patient@example.com",
        today_steps=11500,
        heart_rate=HeartRateSummary(resting_bpm=62),
        sleep=SleepSummary(total_hours=7.5, formatted_duration="7h 30m"),
        is_live_data=True
    )
    history = generate_demo_history(tz, days=20)
    baseline_report = StatisticalBaselineEngine.evaluate_user_telemetry(
        email=profile.email,
        history_records=history,
        acute_heart_rate=62.0,
        acute_sleep_hours=7.5,
        acute_steps=11500
    )

    summaries = BiometricAdvisor.generate_category_summaries(
        health_data=health_data,
        user_profile=profile,
        baseline_report=baseline_report
    )

    assert "cardiovascular" in summaries
    assert "sleep" in summaries
    assert "movement" in summaries
    assert summaries["cardiovascular"].title == "Cardiovascular & Autonomic Tone"
    assert len(summaries["cardiovascular"].short_analysis) > 15
    assert summaries["movement"].status_tone == "emerald"


def test_dashboard_renders_clinical_feed_and_sidebar(client):
    """Verify dashboard renders clinical feed, vital sidebar navigation, and signatures."""
    resp = client.get("/dashboard?demo=true")
    assert resp.status_code == 200
    text = resp.text

    # Sidebar navigation elements
    assert "Vitals & Clinical Feeds" in text
    assert "btn-vital-all" in text
    assert "btn-vital-cardiovascular" in text
    assert "btn-vital-sleep" in text
    assert "btn-vital-movement" in text

    # Feed structure elements
    assert "Clinical Advisory Feed" in text
    assert "clinical-feed-card" in text
    assert "Personal Metric Observation" in text
    assert "Signed with Credible Research Evidence" in text
    assert "DOI:" in text

    # Existing analytics charts preserved
    assert "historicalStepsChart" in text
    assert "historyLogList" in text
    assert "weeklySleepChart" in text
    assert "sleepChart" in text


def test_admin_dashboard_renders_pdf_hunter(client):
    """Verify admin dashboard displays PDF Hunter interface and ChromaDB embeddings counter."""
    client.post("/admin/login", data={"password": settings.admin_password})
    resp = client.get("/admin/dashboard")
    assert resp.status_code == 200
    text = resp.text

    assert "VITA Research Paper Hunter & Clinical Embedder" in text
    assert "hunterQuery" in text
    assert "btnHunterSearch" in text
    assert "stat-total-embeddings" in text
    assert "Candidate Papers Discovered" in text
    assert "Hunt & Ingest Selected Papers" in text
    assert "hunterNoticeBanner" in text


def test_hunter_search_endpoint_with_fallback_notice(client, monkeypatch):
    """Admin hunter search returns notice when Europe PMC DNS resolution drops."""
    from health_app.fetcher.client import PaperSearchClient

    def mock_search_all(self, query, limit=6):
        self.last_notice = "Europe PMC DNS was unreachable; candidate papers retrieved via Crossref / arXiv fallback mirrors."
        return [
            CandidatePaper(
                paper_id="crossref_10.1016_sleep",
                title="Crossref Biomedical Sleep Trial",
                authors="Miller R",
                year="2025",
                journal="Sleep Health",
                doi="10.1016/j.sleh.2025.01.002",
                abstract="Controlled trial on autonomic vagal tone.",
                pdf_url="https://doi.org/10.1016/j.sleh.2025.01.002",
                source="Crossref"
            )
        ]

    monkeypatch.setattr(PaperSearchClient, "search_all", mock_search_all)
    client.post("/admin/login", data={"password": settings.admin_password})
    resp = client.post("/api/admin/hunter/search", json={"query": "autonomic vagal tone", "limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["total_found"] == 1
    assert data["candidates"][0]["source"] == "Crossref"
    assert "Europe PMC DNS was unreachable" in data["notice"]


def test_paper_search_client_epmc_dns_failure_fallback():
    """Verify PaperSearchClient catches Europe PMC DNS errors and fails over to Crossref/arXiv."""
    import requests
    from health_app.fetcher.client import PaperSearchClient

    client = PaperSearchClient(timeout=5)

    # Force search_europe_pmc to trigger a DNS resolution error
    def mock_search_epmc(query, limit=5):
        client._last_epmc_error = "DNS/Network unreachable (ConnectionError)"
        return []

    client.search_europe_pmc = mock_search_epmc

    # Mock Crossref to return a candidate paper
    def mock_search_crossref(query, limit=5):
        return [
            CandidatePaper(
                paper_id="crossref_123",
                title="Crossref Cardiometabolic Study",
                authors="Watson K",
                year="2024",
                source="Crossref"
            )
        ]

    client.search_crossref = mock_search_crossref

    papers = client.search_all("cardiometabolic heart rate", limit=3)
    assert len(papers) == 3
    assert any(p.source == "Crossref" for p in papers)
    assert any(p.source == "arXiv" for p in papers)
    assert client.last_notice is not None
    assert "Europe PMC DNS was unreachable" in client.last_notice


def test_paper_search_client_offline_fallback_to_local_registry(tmp_path, monkeypatch):
    """Verify complete offline mode falls back to local research papers registry."""
    from health_app.fetcher.client import PaperSearchClient
    from health_app.fetcher.registry import PaperRegistry, PaperRecord

    # Create temporary local registry with a known paper
    test_index_path = tmp_path / "test_research_index.json"
    registry = PaperRegistry(index_path=test_index_path)
    registry.register(
        paper_id="local_paper_001",
        title="Local Nocturnal Heart Rate and Autonomic Dysregulation Cohort",
        status="kept",
        authors="Offline Scientist",
        year="2024",
        journal="Journal of Local Medicine",
        abstract="Extensive observational analysis of nocturnal pulse and recovery."
    )

    client = PaperSearchClient(timeout=5)

    # Simulate all remote network calls failing
    def fail_remote(query, limit=5):
        return []

    client.search_europe_pmc = fail_remote
    client.search_crossref = fail_remote
    client.search_arxiv = fail_remote

    # Point local registry to test index
    monkeypatch.setattr("health_app.fetcher.registry.DEFAULT_INDEX_PATH", test_index_path)

    papers = client.search_all("nocturnal heart rate", limit=3)
    assert len(papers) >= 1
    assert any("Local Archive" in p.source for p in papers)
    assert client.last_notice is not None
    assert "local offline archive" in client.last_notice


def test_pipeline_returns_verified_reports_attribute(tmp_path, monkeypatch):
    """Verify PaperExtractionReport contains verified_reports and avoids AttributeError."""
    from health_app.relationships.pipeline import RelationshipPipeline

    monkeypatch.setattr(settings, "chroma_persist_dir", tmp_path / "vdb")

    pipeline = RelationshipPipeline()
    sample_text = (
        "In this randomized controlled trial of 150 adults, elevated nocturnal heart rate "
        "significantly increases cardiovascular strain with an odds ratio of 2.1 (95% CI: 1.4-3.2). "
        "Conclusion: nocturnal pulse reflects autonomic impairment."
    )

    report = pipeline.process_text(
        text=sample_text,
        title="Nocturnal Heart Rate and Autonomic Impairment",
        authors="Clinician A, Researcher B",
        year="2025",
        paper_id="test_paper_attr_001",
        print_to_terminal=False,
        verify_relationships=True
    )

    assert hasattr(report, "verified_reports")
    assert isinstance(report.verified_reports, list)
    if report.total_relationships > 0:
        assert len(report.verified_reports) > 0
        vr = report.verified_reports[0]
        assert hasattr(vr, "final_score")
        assert hasattr(vr, "gating_status")


def test_downloader_rejects_html_landing_pages(tmp_path, monkeypatch):
    """Verify PDFDownloader rejects HTTP 200 HTML pages and does not verify them as PDFs."""
    from health_app.fetcher.downloader import PDFDownloader

    downloader = PDFDownloader(target_dir=tmp_path / "papers")

    # Mock response returning an HTML landing page
    class MockHtmlResponse:
        status_code = 200
        headers = {"content-type": "text/html; charset=utf-8"}
        def iter_content(self, chunk_size=8192):
            yield b"<!doctype html><html lang='en'><head><title>NCBI Landing</title></head><body>Redirecting...</body></html>"

    monkeypatch.setattr(downloader.session, "get", lambda *args, **kwargs: MockHtmlResponse())
    monkeypatch.setattr(downloader, "_download_with_curl", lambda *args, **kwargs: False)

    test_file = tmp_path / "fake.pdf"
    with open(test_file, "wb") as f:
        f.write(b"<!doctype html><html><body>Error</body></html>")

    # _is_valid_pdf_file must return False for HTML content
    assert downloader._is_valid_pdf_file(test_file) is False

    # download() must reject the HTML response across mirrors
    success, saved_path, msg = downloader.download(
        pdf_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC12606180/pdf/",
        title="Asthma Control in Children",
        polite_delay=0.0
    )
    assert success is False
    assert saved_path is None


def test_hunter_ingest_endpoint_streaming(client, tmp_path, monkeypatch):
    """Admin hunter ingest streaming yields newline-delimited JSON events."""
    monkeypatch.setattr(settings, "research_papers_dir", tmp_path / "papers")
    monkeypatch.setattr(settings, "chroma_persist_dir", tmp_path / "vdb")

    sample_paper = {
        "paper_id": "stream_test_001",
        "title": "Intermittent Fasting and Autonomic Vagal Modulation",
        "authors": "Johnson D",
        "year": "2025",
        "journal": "Clinical Nutrition",
        "doi": "10.1016/j.nut.2025.001",
        "abstract": "Time-restricted feeding improved nocturnal pulse variance.",
        "pdf_url": ""
    }

    client.post("/admin/login", data={"password": settings.admin_password})
    resp = client.post(
        "/api/admin/hunter/ingest",
        json={"selected_papers": [sample_paper], "stream": True},
        headers={"Accept": "application/x-ndjson"}
    )
    assert resp.status_code == 200
    lines = [line.strip() for line in resp.text.strip().split("\n") if line.strip()]
    assert len(lines) >= 3

    events = [json.loads(line) for line in lines]
    event_types = [e.get("type") for e in events]
    assert "ingest_start" in event_types
    assert "paper_start" in event_types
    assert "complete" in event_types

    complete_evt = [e for e in events if e.get("type") == "complete"][0]
    assert complete_evt["status"] == "success"
    assert complete_evt["processed_papers_count"] == 1


def test_downloader_stream_yields_events(tmp_path, monkeypatch):
    """Verify PDFDownloader.download_stream yields progress events."""
    from health_app.fetcher.downloader import PDFDownloader

    downloader = PDFDownloader(target_dir=tmp_path / "papers")

    class MockStreamResponse:
        status_code = 200
        headers = {"content-length": "2048"}
        def iter_content(self, chunk_size=8192):
            yield b"%PDF-1.4\n" + (b"x" * 2038)

    monkeypatch.setattr(downloader.session, "get", lambda *args, **kwargs: MockStreamResponse())

    events = list(downloader.download_stream(
        pdf_url="https://europepmc.org/articles/PMC9999999",
        title="Stream Test Paper",
        polite_delay=0.0
    ))

    types = [e.get("type") for e in events]
    assert "download_start" in types
    assert "download_progress" in types
    assert "download_verified" in types
    assert "download_result" in types


def test_verification_report_relationship_binding():
    """Verify VerificationReport binds relationship and provides fallback properties."""
    from health_app.relationships.models import HealthRelationship
    from health_app.verification import (
        CompositeScoringEngine,
        classify_study_design,
        assess_risk_of_bias,
        verify_textual_nli,
        validate_statistics,
        VerificationReport,
        GatingStatus,
    )

    rel = HealthRelationship(
        subject="Elevated nocturnal heart rate",
        relation="positively correlates with",
        object="cardiac autonomic neuropathy",
        condition="in diabetic patients",
        evidence_quote="Elevated nocturnal heart rate positively correlates with cardiac autonomic neuropathy in diabetic patients.",
        paper_title="Autonomic Neuropathy & Sleep Heart Rate",
        authors="Dr. Test, Dr. Sample",
        publish_year="2025",
        doi="10.1001/test.2025.1"
    )

    design = classify_study_design("Prospective cohort study of 500 patients", "Methods")
    rob = assess_risk_of_bias("No deviations from intended interventions were observed.", design)
    nli = verify_textual_nli(rel.to_claim_sentence(), rel.evidence_quote)
    stat = validate_statistics(rel.relation, rel.evidence_quote, rel.evidence_quote)

    report = CompositeScoringEngine.evaluate(
        relationship=rel,
        study_design=design,
        risk_of_bias=rob,
        nli_result=nli,
        statistical_check=stat
    )

    # 1. Verify relationship is bound
    assert report.relationship is not None
    assert report.relationship.subject == "Elevated nocturnal heart rate"
    assert report.relationship.relation == "positively correlates with"
    assert report.relationship.object == "cardiac autonomic neuropathy"
    assert report.evidence_quote == rel.evidence_quote
    assert report.paper_title == rel.paper_title
    assert report.doi == rel.doi

    # 2. Verify convenience properties
    assert report.subject == "Elevated nocturnal heart rate"
    assert report.relation == "positively correlates with"
    assert report.object == "cardiac autonomic neuropathy"

    # 3. Test fallback when relationship is None
    fallback_report = VerificationReport(
        claim_summary="High sugar intake -> increases risk of -> type 2 diabetes",
        study_design=design,
        risk_of_bias=rob,
        nli_result=nli,
        statistical_check=stat,
        base_score=80.0,
        penalty_points=5.0,
        final_score=75.0,
        gating_status=GatingStatus.PROVISIONALLY_SUPPORTED,
        action_reason="Supported"
    )
    assert fallback_report.subject == "High sugar intake"
    assert fallback_report.relation == "increases risk of"
    assert fallback_report.object == "type 2 diabetes"


def test_hunter_ingest_with_mocked_verified_reports_non_streaming(client, tmp_path, monkeypatch):
    """Verify non-streaming hunter ingest processes verified_reports with zero AttributeError."""
    from health_app.relationships.models import HealthRelationship, PaperExtractionReport
    from health_app.verification import (
        CompositeScoringEngine,
        classify_study_design,
        assess_risk_of_bias,
        verify_textual_nli,
        validate_statistics,
    )

    monkeypatch.setattr(settings, "research_papers_dir", tmp_path / "papers")
    monkeypatch.setattr(settings, "chroma_persist_dir", tmp_path / "vdb")

    rel = HealthRelationship(
        subject="Air purifier usage",
        relation="significantly reduces",
        object="cardiovascular inflammatory markers",
        condition="in urban adults",
        evidence_quote="Air purifier usage significantly reduces cardiovascular inflammatory markers in urban adults.",
        paper_title="Health Benefits of Air Purification",
        authors="Xue T, et al.",
        publish_year="2026",
        doi="10.1016/j.envres.2026.100"
    )

    design = classify_study_design("Systematic review and meta-analysis", "Methods")
    rob = assess_risk_of_bias("Low risk of bias across all domains.", design)
    nli = verify_textual_nli(rel.to_claim_sentence(), rel.evidence_quote)
    stat = validate_statistics(rel.relation, rel.evidence_quote, rel.evidence_quote)

    ver_rep = CompositeScoringEngine.evaluate(rel, design, rob, nli, stat)

    extraction_report = PaperExtractionReport(
        paper_id="paper_mock_001",
        title="Health Benefits of Air Purification",
        authors="Xue T, et al.",
        publish_year="2026",
        doi="10.1016/j.envres.2026.100",
        total_chunks=1,
        total_relationships=1,
        chunk_results=[],
        verified_reports=[ver_rep]
    )

    # Mock pipeline.process_paper_file to return extraction_report
    from health_app.relationships.pipeline import RelationshipPipeline
    monkeypatch.setattr(RelationshipPipeline, "process_paper_file", lambda self, *args, **kwargs: extraction_report)

    sample_paper = {
        "paper_id": "paper_mock_001",
        "title": "Health Benefits of Air Purification",
        "authors": "Xue T, et al.",
        "year": "2026",
        "journal": "Environmental Research",
        "doi": "10.1016/j.envres.2026.100",
        "abstract": "Air purifier usage significantly reduces cardiovascular inflammatory markers.",
        "pdf_url": ""
    }

    # Authenticate as admin
    client.post("/admin/login", data={"password": settings.admin_password})

    # Non-streaming request (no stream=True)
    resp = client.post("/api/admin/hunter/ingest", json={"selected_papers": [sample_paper], "stream": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["new_relationships_verified"] == 1
    assert len(data["results"]) == 1
    result_claim = data["results"][0]
    assert result_claim["subject"] == "Air purifier usage"
    assert result_claim["relation"] == "significantly reduces"
    assert result_claim["object"] == "cardiovascular inflammatory markers"
    assert result_claim["paper_title"] == "Health Benefits of Air Purification"




