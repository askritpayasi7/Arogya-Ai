from pathlib import Path
import pytest

from health_app.ingestion.chunker import TextChunker
from health_app.ingestion.loader import DocumentLoader
from health_app.vectordb.embeddings import MockEmbeddingProvider
from health_app.vectordb.store import (
    VectorStore,
    COLLECTION_RESEARCH,
    COLLECTION_FSSAI,
)
from health_app.rag.retriever import HealthRetriever
from health_app.rag.engine import HealthAdvisoryEngine

REPO_ROOT = Path(__file__).resolve().parent.parent

def test_text_chunker():
    chunker = TextChunker(target_chunk_size=100, overlap_size=20)
    sample_text = (
        "## Section 1\nThis is paragraph one about health impacts.\n\n"
        "## Section 2\nThis is paragraph two detailing cardiovascular metrics and clinical evidence."
    )
    chunks = chunker.chunk_text(
        text=sample_text,
        base_id="paper_1",
        base_metadata={"title": "Trial Paper"}
    )
    assert len(chunks) >= 2
    assert chunks[0].chunk_id.startswith("paper_1_chunk_")
    assert "title" in chunks[0].metadata
    assert chunks[0].metadata["title"] == "Trial Paper"


def test_document_loader_sample_files():
    research_file = REPO_ROOT / "data" / "research_papers" / "sample_trans_fat_cardiovascular_study.md"
    fssai_file = REPO_ROOT / "data" / "fssai_regulations" / "sample_fssai_trans_fat_regulations.md"

    res_doc = DocumentLoader.load_file(research_file, doc_type="research_paper")
    assert res_doc is not None
    assert "Trans-Fatty Acids" in res_doc.title
    assert res_doc.metadata.get("doi") == "10.1056/NEJMra054035"

    fssai_doc = DocumentLoader.load_file(fssai_file, doc_type="fssai_regulation")
    assert fssai_doc is not None
    assert "FSSAI" in fssai_doc.raw_text
    assert "regulation_number" in fssai_doc.metadata or "year" in fssai_doc.metadata


def test_health_advisory_rag_engine():
    # Setup in-memory store with mock embeddings
    provider = MockEmbeddingProvider(dimension=64)
    store = VectorStore(embedding_provider=provider, in_memory=True)

    # Ingest research
    store.add_documents(
        collection_name=COLLECTION_RESEARCH,
        ids=["res_chunk_1"],
        documents=["Clinical trials confirm 2% trans-fat intake raises coronary heart disease by 23%."],
        metadatas=[{"title": "NEJM Study", "doi": "10.1056/sample", "section": "Clinical Endpoints"}]
    )

    # Ingest FSSAI
    store.add_documents(
        collection_name=COLLECTION_FSSAI,
        ids=["fssai_chunk_1"],
        documents=["FSSAI limits trans-fat in edible oils and fats to less than 2% by weight."],
        metadatas=[{"title": "FSSAI Notification", "regulation_number": "Sec 2.3.15", "section": "Statutory Limit"}]
    )

    retriever = HealthRetriever(store)
    engine = HealthAdvisoryEngine(retriever)

    response = engine.evaluate_query("trans fat coronary risks and permissible limits")

    assert response.query == "trans fat coronary risks and permissible limits"
    assert len(response.scientific_findings) >= 1
    assert len(response.fssai_standards) >= 1
    assert len(response.citations) >= 2

    # Check citation provenance
    sources = [c.source_type for c in response.citations]
    assert "research_paper" in sources
    assert "fssai_regulation" in sources
