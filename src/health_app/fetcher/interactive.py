import sys
import textwrap
from typing import List

from health_app.fetcher.registry import PaperRegistry
from health_app.fetcher.client import PaperSearchClient, CandidatePaper
from health_app.fetcher.downloader import PDFDownloader
from health_app.relationships.pipeline import RelationshipPipeline

def format_abstract(text: str, width: int = 76) -> str:
    """Format and word-wrap abstract for clean terminal presentation."""
    if not text or text.strip() == "No abstract provided in database.":
        return "  [No abstract provided in source database]"

    wrapped_lines = []
    display_text = text[:1200] + ("..." if len(text) > 1200 else "")
    for line in textwrap.wrap(display_text, width=width):
        wrapped_lines.append(f"  {line}")
    return "\n".join(wrapped_lines)


def run_interactive_fetcher() -> None:
    """Run interactive terminal research paper fetcher and reviewer with resilient download handling."""
    registry = PaperRegistry()
    client = PaperSearchClient()
    downloader = PDFDownloader()

    counts = registry.get_counts()
    print("\n" + "=" * 76)
    print("        EVIDENCE-BASED HEALTH & NUTRITION RESEARCH PAPER FETCHER")
    print("=" * 76)
    print(f"[*] Persistent Index Status: {counts['kept']} kept | {counts['discarded']} discarded | {counts['total']} total")
    print("-" * 76)

    # 1. Ask for research topic / idea
    try:
        topic = input("\nEnter research topic or idea: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n[Exiting research paper fetcher]")
        return

    if not topic:
        print("[!] No topic entered. Returning to menu.")
        return

    # 2. Ask for number of papers to pull
    try:
        count_input = input("How many candidate papers to search? (default: 5): ").strip()
        num_papers = int(count_input) if count_input.isdigit() and int(count_input) > 0 else 5
    except (KeyboardInterrupt, EOFError):
        print("\n[Exiting]")
        return

    print(f"\n[+] Searching open-access scientific repositories for: '{topic}'...")
    candidates = client.search_all(query=topic, limit=num_papers * 2)

    if not candidates:
        print("[-] No papers found for this topic. Try broader search keywords.")
        return

    # 3. Deduplication filter against persistent registry
    unseen_candidates: List[CandidatePaper] = []
    skipped_count = 0

    for paper in candidates:
        if registry.is_indexed(
            paper_id=paper.paper_id,
            title=paper.title,
            doi=paper.doi,
            pmcid=paper.pmcid
        ):
            skipped_count += 1
        else:
            unseen_candidates.append(paper)

    if skipped_count > 0:
        print(f"[*] Skipped {skipped_count} paper(s) already recorded in your persistent index.")

    if not unseen_candidates:
        print("[*] All matching papers for this query are already indexed (kept or discarded).")
        print("    Try a different search query or more specific health keywords.")
        return

    review_list = unseen_candidates[:num_papers]
    print(f"[+] Found {len(review_list)} new candidate paper(s) for your review:\n")

    kept_this_session = 0
    failed_this_session = 0
    discarded_this_session = 0

    # 4. Interactive review loop
    for idx, paper in enumerate(review_list, 1):
        print("=" * 76)
        print(f" CANDIDATE [{idx} of {len(review_list)}]")
        print("=" * 76)
        print(f" TITLE:   {paper.title}")
        print(f" AUTHORS: {paper.authors}")
        print(f" YEAR:    {paper.year}  |  JOURNAL: {paper.journal}  |  SOURCE: {paper.source}")
        if paper.doi:
            print(f" DOI:     {paper.doi}")
        if paper.pdf_url:
            print(f" PDF URL: {paper.pdf_url}")
        print("-" * 76)
        print(" BRIEF SUMMARY / ABSTRACT:")
        print(format_abstract(paper.abstract))
        print("-" * 76)

        while True:
            try:
                choice = input("\nKeep this paper and download PDF? [y=Yes / n=Discard / s=Skip / q=Quit]: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                choice = "q"

            if choice in ["y", "yes"]:
                print(f"[+] Downloading PDF for: '{paper.title[:50]}...'")
                success, saved_path, msg = downloader.download(
                    pdf_url=paper.pdf_url,
                    title=paper.title,
                    authors=paper.authors,
                    year=paper.year,
                    doi=paper.doi,
                    abstract=paper.abstract
                )
                
                # Check actual download success
                if success and saved_path and saved_path.exists():
                    registry.register(
                        paper_id=paper.paper_id,
                        title=paper.title,
                        status="kept",
                        authors=paper.authors,
                        year=paper.year,
                        journal=paper.journal,
                        doi=paper.doi,
                        pmcid=paper.pmcid,
                        abstract=paper.abstract,
                        pdf_url=paper.pdf_url,
                        pdf_path=str(saved_path),
                    )
                    kept_this_session += 1
                    print(f"[SUCCESS] {msg}")
                    print(f"          Saved to: {saved_path}")

                    # Extract and print health relationships chunk-by-chunk to terminal
                    try:
                        pipeline = RelationshipPipeline()
                        pipeline.process_paper_file(saved_path, print_to_terminal=True)
                    except Exception as e:
                        print(f"[!] Relationship extraction note: {e}")

                    break
                else:
                    print(f"\n[WARNING] Download could not be completed: {msg}")
                    # Interactive retry prompt (accepts r, retry, y, yes)
                    retry_choice = input("Would you like to retry the download now? [r/y=Retry / s=Skip for now / d=Discard]: ").strip().lower()
                    if retry_choice in ["r", "retry", "y", "yes"]:
                        print(f"[+] Retrying download with alternate mirrors and direct API...")
                        success, saved_path, msg = downloader.download(
                            pdf_url=paper.pdf_url,
                            title=paper.title,
                            authors=paper.authors,
                            year=paper.year,
                            doi=paper.doi,
                            abstract=paper.abstract,
                            polite_delay=1.5
                        )
                        if success and saved_path and saved_path.exists():
                            registry.register(
                                paper_id=paper.paper_id,
                                title=paper.title,
                                status="kept",
                                authors=paper.authors,
                                year=paper.year,
                                journal=paper.journal,
                                doi=paper.doi,
                                pmcid=paper.pmcid,
                                abstract=paper.abstract,
                                pdf_url=paper.pdf_url,
                                pdf_path=str(saved_path),
                            )
                            kept_this_session += 1
                            print(f"[SUCCESS] {msg}")
                            print(f"          Saved to: {saved_path}")

                            # Extract and print health relationships chunk-by-chunk to terminal
                            try:
                                pipeline = RelationshipPipeline()
                                pipeline.process_paper_file(saved_path, print_to_terminal=True)
                            except Exception as e:
                                print(f"[!] Relationship extraction note: {e}")

                            break

                    if retry_choice in ["d", "discard"]:
                        registry.register(
                            paper_id=paper.paper_id,
                            title=paper.title,
                            status="discarded",
                            authors=paper.authors,
                            year=paper.year,
                            journal=paper.journal,
                            doi=paper.doi,
                            pmcid=paper.pmcid,
                            abstract=paper.abstract,
                            pdf_url=paper.pdf_url,
                        )
                        discarded_this_session += 1
                        print("[MARKED DISCARDED] Saved to index as discarded.")
                        break
                    else:
                        # Log as download_failed so it doesn't falsely show as kept and can be recovered later
                        registry.register(
                            paper_id=paper.paper_id,
                            title=paper.title,
                            status="download_failed",
                            authors=paper.authors,
                            year=paper.year,
                            journal=paper.journal,
                            doi=paper.doi,
                            pmcid=paper.pmcid,
                            abstract=paper.abstract,
                            pdf_url=paper.pdf_url,
                            pdf_path=None
                        )
                        failed_this_session += 1
                        print("[LOGGED FAILED] Saved in index as download_failed. You can run recovery anytime.")
                        break

            elif choice in ["n", "no"]:
                registry.register(
                    paper_id=paper.paper_id,
                    title=paper.title,
                    status="discarded",
                    authors=paper.authors,
                    year=paper.year,
                    journal=paper.journal,
                    doi=paper.doi,
                    pmcid=paper.pmcid,
                    abstract=paper.abstract,
                    pdf_url=paper.pdf_url,
                )
                discarded_this_session += 1
                print("[MARKED DISCARDED] Added to index as discarded (won't appear in future searches).")
                break

            elif choice in ["s", "skip"]:
                print("[SKIPPED] Left unindexed (can appear in future searches).")
                break

            elif choice in ["q", "quit"]:
                print("\n[!] Quitting research paper review...")
                break

            else:
                print("Invalid input. Please enter 'y', 'n', 's', or 'q'.")

        if choice in ["q", "quit"]:
            break

    # Summary
    updated_counts = registry.get_counts()
    print("\n" + "=" * 76)
    print("SESSION SUMMARY:")
    print(f"  - Successfully Kept & Downloaded: {kept_this_session}")
    print(f"  - Failed Downloads:               {failed_this_session}")
    print(f"  - Newly Discarded:                {discarded_this_session}")
    print(f"  - Total Kept in Registry:         {updated_counts['kept']}")
    print(f"  - Total in Registry Index:        {updated_counts['total']}")
    if failed_this_session > 0:
        print("\n  [TIP] You have failed downloads. Run Option [6] in start.cmd or:")
        print("        python -m health_app.terminal_runner --retry-downloads")
    print("=" * 76 + "\n")


if __name__ == "__main__":
    run_interactive_fetcher()
