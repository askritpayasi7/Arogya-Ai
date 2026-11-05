import json
from pathlib import Path
import pytest

from health_app.relationships.models import (
    HealthRelationship,
    ChunkExtractionResult,
    PaperExtractionReport,
)
from health_app.relationships.extractor import GeminiRelationshipExtractor
from health_app.relationships.pipeline import RelationshipPipeline

def test_relationship_model_validation():
    rel = HealthRelationship(
        subject="Elevated resting heart rate with fragmented sleep",
        relation="increases risk of",
        object="cardiac autonomic dysfunction",
        condition="in adult clinical cohort",
        evidence_quote="Patients with fragmented sleep demonstrated significantly elevated nocturnal heart rates and autonomic severity.",
        confidence="High",
        paper_title="Sleep-Autonomic Study",
        authors="Dr. Jin et al.",
        publish_year="2026",
        doi="10.1002/sample.123",
        chunk_index=1
    )
    assert rel.subject.startswith("Elevated")
    assert rel.relation == "increases risk of"
    assert rel.authors == "Dr. Jin et al."
    assert rel.chunk_index == 1


def test_fallback_relationship_extractor():
    extractor = GeminiRelationshipExtractor(api_key=None)
    assert not extractor.is_live

    sample_chunk = (
        "Polysomnography results demonstrated that higher apnea-hypopnea index increases the risk of "
        "orthostatic blood pressure drops. Furthermore, reduced slow-wave sleep was associated with "
        "elevated composite autonomic severity scores."
    )

    relationships = extractor.extract_from_chunk(
        chunk_text=sample_chunk,
        title="Sleep & Cardiac Study",
        authors="Researcher X",
        year="2025",
        doi="10.1000/182",
        chunk_index=0
    )

    assert len(relationships) >= 1
    first_rel = relationships[0]
    assert first_rel.paper_title == "Sleep & Cardiac Study"
    assert first_rel.publish_year == "2025"
    assert "apnea-hypopnea" in first_rel.subject.lower() or "slow-wave" in first_rel.subject.lower()


def test_relationship_pipeline(tmp_path, monkeypatch):
    cache_file = tmp_path / "relationships_cache.json"
    from health_app.relationships import pipeline
    monkeypatch.setattr(pipeline, "DEFAULT_RELATIONSHIPS_CACHE", cache_file)

    pipe = RelationshipPipeline(extractor=GeminiRelationshipExtractor(api_key=None), chunk_size=150, chunk_overlap=30)

    sample_text = (
        "## Abstract\n"
        "Clinical trials confirmed that consumption of industrial trans-fats increases risk of coronary heart disease events by 23%.\n\n"
        "## Physiological Mechanisms\n"
        "Elevated low-density lipoprotein cholesterol leads to vascular endothelial impairment and arterial occlusion."
    )

    report = pipe.process_text(
        text=sample_text,
        title="Cardiovascular Lipid Trial",
        authors="Mozaffarian et al.",
        year="2021",
        doi="10.1056/NEJMra054035",
        paper_id="nejm_transfat",
        print_to_terminal=False
    )

    assert report.total_chunks >= 2
    assert report.total_relationships >= 1
    assert report.title == "Cardiovascular Lipid Trial"
    assert report.authors == "Mozaffarian et al."

    # Verify cache JSON creation
    assert cache_file.exists()
    with open(cache_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) >= 1
    assert data[0]["paper_title"] == "Cardiovascular Lipid Trial"
