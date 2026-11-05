import argparse
import sys
from pathlib import Path

from health_app.config import settings
from health_app.vectordb.embeddings import (
    OllamaEmbeddingProvider,
    MockEmbeddingProvider,
)
from health_app.vectordb.store import (
    VectorStore,
    COLLECTION_RESEARCH,
    COLLECTION_FSSAI,
    COLLECTION_VERIFIED_RELATIONSHIPS,
)
from health_app.ingestion.loader import DocumentLoader
from health_app.ingestion.chunker import TextChunker
from health_app.rag.retriever import HealthRetriever
from health_app.rag.engine import HealthAdvisoryEngine
from health_app.fetcher.interactive import run_interactive_fetcher
from health_app.fetcher.recovery import repair_missing_pdfs
from health_app.relationships.pipeline import RelationshipPipeline

def check_ollama(provider: OllamaEmbeddingProvider) -> None:
    """Check Ollama service connection and model readiness."""
    print(f"\n[+] Checking Ollama service at: {provider.base_url}")
    print(f"[+] Target embedding model: {provider.model}")
    is_ready, message = provider.check_connection()
    if is_ready:
        print(f"[SUCCESS] {message}\n")
    else:
        print(f"[WARNING] {message}\n")


def ingest_data(vector_store: VectorStore) -> None:
    """Ingest research papers and FSSAI standards into ChromaDB."""
    print("\n[+] Starting Document Ingestion Pipeline...")
    chunker = TextChunker(target_chunk_size=400, overlap_size=80)

    # 1. Ingest Research Papers
    research_dir = settings.research_papers_dir
    print(f"[*] Scanning research papers in: {research_dir}")
    research_docs = DocumentLoader.load_directory(research_dir, doc_type="research_paper")
    total_research_chunks = 0

    for doc in research_docs:
        chunks = chunker.chunk_text(doc.raw_text, base_id=doc.doc_id, base_metadata=doc.metadata)
        if chunks:
            ids = [c.chunk_id for c in chunks]
            texts = [c.text for c in chunks]
            metas = [c.metadata for c in chunks]
            vector_store.add_documents(COLLECTION_RESEARCH, ids=ids, documents=texts, metadatas=metas)
            total_research_chunks += len(chunks)
            print(f"  -> Indexed paper: '{doc.title}' ({len(chunks)} chunks)")

    # 2. Ingest FSSAI Regulations
    fssai_dir = settings.fssai_regulations_dir
    print(f"[*] Scanning FSSAI regulations in: {fssai_dir}")
    fssai_docs = DocumentLoader.load_directory(fssai_dir, doc_type="fssai_regulation")
    total_fssai_chunks = 0

    for doc in fssai_docs:
        chunks = chunker.chunk_text(doc.raw_text, base_id=doc.doc_id, base_metadata=doc.metadata)
        if chunks:
            ids = [c.chunk_id for c in chunks]
            texts = [c.text for c in chunks]
            metas = [c.metadata for c in chunks]
            vector_store.add_documents(COLLECTION_FSSAI, ids=ids, documents=texts, metadatas=metas)
            total_fssai_chunks += len(chunks)
            print(f"  -> Indexed FSSAI standard: '{doc.title}' ({len(chunks)} chunks)")

    # 3. Ingest verified passed clinical relationships into ChromaDB
    synced_rules = vector_store.sync_verified_relationships_cache()
    if synced_rules > 0:
        print(f"[*] Indexed {synced_rules} passed clinical relationships into vector DB.")

    counts = vector_store.count()
    print("\n[SUCCESS] Ingestion complete!")
    print(f"  - Total research chunks in DB: {counts.get(COLLECTION_RESEARCH, 0)}")
    print(f"  - Total FSSAI chunks in DB:    {counts.get(COLLECTION_FSSAI, 0)}")
    print(f"  - Passed clinical rules in DB: {counts.get(COLLECTION_VERIFIED_RELATIONSHIPS, 0)}\n")


def run_query(engine: HealthAdvisoryEngine, query_text: str) -> None:
    """Run a grounded query and print formatted advisory response."""
    print(f"\n========================================================")
    print(f"HEALTH & FSSAI ADVISORY QUERY: '{query_text}'")
    print(f"========================================================\n")

    response = engine.evaluate_query(query_text)

    print(f"SUMMARY:\n{response.summary}\n")

    if response.scientific_findings:
        print("PEER-REVIEWED SCIENTIFIC RESEARCH FINDINGS:")
        for idx, finding in enumerate(response.scientific_findings, 1):
            print(f"  {idx}. {finding}\n")

    if response.fssai_standards:
        print("STATUTORY FSSAI SAFETY STANDARDS & REGULATIONS:")
        for idx, standard in enumerate(response.fssai_standards, 1):
            print(f"  {idx}. {standard}\n")

    if response.citations:
        print("VERIFIABLE CITATIONS:")
        for idx, cite in enumerate(response.citations, 1):
            print(f"  [{idx}] Type: {cite.source_type} | Title: {cite.title} | {cite.identifier}")
            print(f"      Section: {cite.section}")
            print(f"      Excerpt: {cite.excerpt}\n")

    print(f"DISCLAIMER:\n{response.disclaimer}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evidence-Based Health App & FSSAI Vector Database Runner"
    )
    parser.add_argument("--check-ollama", action="store_true", help="Check Ollama server and model connection")
    parser.add_argument("--ingest", action="store_true", help="Ingest research papers and FSSAI standards")
    parser.add_argument("--query", type=str, help="Run an evidence-backed health query")
    parser.add_argument("--fetch", action="store_true", help="Launch interactive research paper search and downloader")
    parser.add_argument("--retry-downloads", action="store_true", help="Scan index and re-download any missing or failed PDFs")
    parser.add_argument("--extract-relationships", action="store_true", help="Extract and print clinical relationships from downloaded papers")
    parser.add_argument("--sync-relationships", action="store_true", help="Sync passed clinical relationships from cache into ChromaDB")
    parser.add_argument("--dashboard", action="store_true", help="Launch web health dashboard with Google Health on Port 8001")
    parser.add_argument("--mock", action="store_true", help="Use deterministic mock embeddings (for testing/offline)")

    args = parser.parse_args()

    # Embedding provider setup
    if args.mock:
        embedding_provider = MockEmbeddingProvider()
        print("[INFO] Operating in Mock Embedding Mode.")
    else:
        embedding_provider = OllamaEmbeddingProvider()

    if args.check_ollama:
        if isinstance(embedding_provider, OllamaEmbeddingProvider):
            check_ollama(embedding_provider)
        else:
            print("[INFO] Mock embedding provider is active; Ollama check skipped.")
        return

    if args.fetch:
        run_interactive_fetcher()
        return

    if args.retry_downloads:
        repair_missing_pdfs()
        return

    if args.extract_relationships:
        pipeline = RelationshipPipeline()
        pipeline.process_all_downloaded_papers(print_to_terminal=True)
        return

    if args.sync_relationships:
        vs = VectorStore(embedding_provider=embedding_provider)
        count = vs.sync_verified_relationships_cache()
        print(f"\n[SUCCESS] Indexed {count} passed clinical relationship(s) into ChromaDB collection '{COLLECTION_VERIFIED_RELATIONSHIPS}'.\n")
        return

    if args.dashboard:
        import uvicorn
        from health_app.dashboard.app import app
        print("\n" + "=" * 76)
        print(" LAUNCHING VITA WEB HEALTH DASHBOARD & GOOGLE HEALTH INTEGRATION")
        print("=" * 76)
        print(f" Dashboard URL:    http://{settings.dashboard_host}:{settings.dashboard_port}")
        print(f" Google Auth URI:  http://{settings.dashboard_host}:{settings.dashboard_port}/api/auth/google/login")
        print(f" Admin Portal:     http://{settings.dashboard_host}:{settings.dashboard_port}/admin/login")
        print(f" Client Secret:    {settings.find_client_secret_file() or 'Not found'}")
        print("=" * 76 + "\n")
        uvicorn.run(app, host=settings.dashboard_host, port=settings.dashboard_port)
        return

    vector_store = VectorStore(embedding_provider=embedding_provider)
    retriever = HealthRetriever(vector_store)
    engine = HealthAdvisoryEngine(retriever)

    if args.ingest:
        ingest_data(vector_store)

    if args.query:
        run_query(engine, args.query)

    if not args.check_ollama and not args.ingest and not args.query and not args.fetch and not args.retry_downloads and not args.extract_relationships:
        parser.print_help()


if __name__ == "__main__":
    main()
