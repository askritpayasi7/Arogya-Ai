import sys
import subprocess
from pathlib import Path

from health_app.fetcher.interactive import run_interactive_fetcher
from health_app.fetcher.registry import PaperRegistry
from health_app.fetcher.recovery import repair_missing_pdfs
from health_app.relationships.pipeline import RelationshipPipeline

def display_menu() -> None:
    registry = PaperRegistry()
    counts = registry.get_counts()

    print("\n" + "=" * 70)
    print("      RESEARCH-BACKED HEALTH APP & FSSAI VECTOR DATABASE")
    print("=" * 70)
    print(f" Registry Status: {counts['kept']} papers kept | {counts['discarded']} discarded | {counts['total']} total indexed")
    print("-" * 70)
    print("  [1] Search & Fetch Research Papers (PDF Downloader & Reviewer)")
    print("  [2] View Kept Research Papers in Index")
    print("  [3] Ingest Documents into Vector Database (ChromaDB)")
    print("  [4] Run Grounded Health & FSSAI Query")
    print("  [5] Check Ollama Embedding Service Status")
    print("  [6] Retry / Download Missing PDFs (Repair Tool)")
    print("  [7] Extract Health Relationships from Downloaded Papers (AI Pipeline)")
    print("  [8] Launch Web Health Dashboard & Google Health Integration (Port 8001)")
    print("  [0] Exit")
    print("=" * 70)


def view_kept_papers() -> None:
    registry = PaperRegistry()
    kept = registry.list_kept_papers()

    print("\n" + "=" * 70)
    print(f"KEPT RESEARCH PAPERS ({len(kept)} total)")
    print("=" * 70)
    if not kept:
        print("  No papers have been kept yet. Use Option 1 to search and download papers.")
    else:
        for idx, paper in enumerate(kept, 1):
            status_indicator = "[ON DISK]" if paper.pdf_path and Path(paper.pdf_path).exists() else "[MISSING PDF]"
            print(f"\n[{idx}] {status_indicator} {paper.title}")
            print(f"    Authors: {paper.authors} ({paper.year})")
            print(f"    Journal: {paper.journal} | DOI: {paper.doi or 'N/A'}")
            print(f"    PDF Path: {paper.pdf_path or 'Not downloaded (run Option 6 to retry)'}")
    print("-" * 70)
    input("\nPress Enter to return to menu...")


def run_ingest() -> None:
    print("\n[+] Triggering document ingestion...")
    from health_app.terminal_runner import ingest_data, VectorStore, MockEmbeddingProvider
    choice = input("Use live Ollama embeddings or fast mock embeddings? [o=Ollama / m=Mock (default)]: ").strip().lower()
    if choice in ["o", "ollama"]:
        store = VectorStore()
    else:
        store = VectorStore(embedding_provider=MockEmbeddingProvider())
    ingest_data(store)
    input("\nPress Enter to return to menu...")


def run_query_prompt() -> None:
    from health_app.terminal_runner import run_query, VectorStore, HealthRetriever, HealthAdvisoryEngine, MockEmbeddingProvider
    query_text = input("\nEnter health or safety query: ").strip()
    if not query_text:
        return
    choice = input("Use live Ollama or fast mock embeddings? [o=Ollama / m=Mock (default)]: ").strip().lower()
    if choice in ["o", "ollama"]:
        store = VectorStore()
    else:
        store = VectorStore(embedding_provider=MockEmbeddingProvider())
    retriever = HealthRetriever(store)
    engine = HealthAdvisoryEngine(retriever)
    run_query(engine, query_text)
    input("\nPress Enter to return to menu...")


def check_ollama_status() -> None:
    from health_app.vectordb.embeddings import OllamaEmbeddingProvider
    from health_app.terminal_runner import check_ollama
    provider = OllamaEmbeddingProvider()
    check_ollama(provider)
    input("\nPress Enter to return to menu...")


def run_repair_tool() -> None:
    repair_missing_pdfs()
    input("\nPress Enter to return to menu...")


def run_relationship_extraction() -> None:
    print("\n[+] Starting AI Health Relationship Extraction...")
    pipeline = RelationshipPipeline()
    reports = pipeline.process_all_downloaded_papers(print_to_terminal=True)
    total_extracted = sum(r.total_relationships for r in reports)
    print(f"\n[COMPLETED] Extracted {total_extracted} total relationship(s) across {len(reports)} paper(s).")
    input("\nPress Enter to return to menu...")


def main_menu() -> None:
    while True:
        display_menu()
        try:
            choice = input("\nEnter your choice [0-8]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Goodbye!")
            break

        if choice == "1":
            run_interactive_fetcher()
            input("\nPress Enter to return to menu...")
        elif choice == "2":
            view_kept_papers()
        elif choice == "3":
            run_ingest()
        elif choice == "4":
            run_query_prompt()
        elif choice == "5":
            check_ollama_status()
        elif choice == "6":
            run_repair_tool()
        elif choice == "7":
            run_relationship_extraction()
        elif choice == "8":
            import uvicorn
            from health_app.dashboard.app import app
            from health_app.config import settings
            print(f"\n[+] Starting Web Health Dashboard on http://{settings.dashboard_host}:{settings.dashboard_port}...")
            print("    Press Ctrl+C to stop the dashboard server and return to menu.")
            try:
                uvicorn.run(app, host=settings.dashboard_host, port=settings.dashboard_port)
            except KeyboardInterrupt:
                print("\n[+] Dashboard server stopped.")
            input("\nPress Enter to return to menu...")
        elif choice == "0":
            print("\nExiting. Goodbye!")
            break
        else:
            print("[!] Invalid option. Please select 0 to 8.")


if __name__ == "__main__":
    main_menu()
