import pytest
from health_app.vectordb.embeddings import MockEmbeddingProvider
from health_app.vectordb.store import (
    VectorStore,
    COLLECTION_RESEARCH,
    COLLECTION_FSSAI,
)

@pytest.fixture
def memory_store():
    provider = MockEmbeddingProvider(dimension=64)
    store = VectorStore(embedding_provider=provider, in_memory=True, collection_prefix="test_vs")
    store.clear()
    return store


def test_mock_embeddings():
    provider = MockEmbeddingProvider(dimension=64)
    is_ready, msg = provider.check_connection()
    assert is_ready
    vector = provider.embed_query("trans fat health risk")
    assert len(vector) == 64
    docs_vectors = provider.embed_documents(["doc 1", "doc 2"])
    assert len(docs_vectors) == 2
    assert len(docs_vectors[0]) == 64


def test_vector_store_add_and_query(memory_store):
    # Add research paper
    research_ids = ["res_1", "res_2"]
    research_docs = [
        "Trans fats increase LDL cholesterol and cardiovascular disease incidence.",
        "Clinical trials show dietary fiber mitigates glucose spikes."
    ]
    research_meta = [
        {"title": "Cardio Study", "doi": "10.1000/182"},
        {"title": "Fiber Trial", "doi": "10.1000/183"}
    ]

    added = memory_store.add_documents(
        collection_name=COLLECTION_RESEARCH,
        ids=research_ids,
        documents=research_docs,
        metadatas=research_meta
    )
    assert added == 2

    # Add FSSAI regulation
    fssai_ids = ["fssai_1"]
    fssai_docs = ["FSSAI mandates trans fat limits of less than 2% by weight in all edible oils."]
    fssai_meta = [{"title": "FSSAI Notification 2020", "regulation_number": "Sec 2.3.15"}]

    added_fssai = memory_store.add_documents(
        collection_name=COLLECTION_FSSAI,
        ids=fssai_ids,
        documents=fssai_docs,
        metadatas=fssai_meta
    )
    assert added_fssai == 1

    # Verify counts
    counts = memory_store.count()
    assert counts[COLLECTION_RESEARCH] == 2
    assert counts[COLLECTION_FSSAI] == 1

    # Query research
    results = memory_store.query(
        collection_name=COLLECTION_RESEARCH,
        query_text="cholesterol cardiovascular risk",
        n_results=1
    )
    assert len(results) == 1
    assert "LDL cholesterol" in results[0].content
    assert results[0].metadata["title"] == "Cardio Study"

    # Query all
    multi_results = memory_store.query_all("trans fat regulations and health effects")
    assert len(multi_results[COLLECTION_RESEARCH]) >= 1
    assert len(multi_results[COLLECTION_FSSAI]) >= 1
