import logging
from pathlib import Path
from typing import Dict, List

from health_app.fetcher.registry import PaperRegistry, PaperRecord
from health_app.fetcher.downloader import PDFDownloader

logger = logging.getLogger(__name__)

def repair_missing_pdfs(index_path: Path | None = None, target_dir: Path | None = None) -> Dict[str, int]:
    """
    Scans the research papers registry for records marked as kept or failed
    where the PDF file is missing or was never downloaded, and attempts recovery.
    """
    registry = PaperRegistry(index_path=index_path)
    downloader = PDFDownloader(target_dir=target_dir)

    missing_records: List[PaperRecord] = []

    for record in registry.records.values():
        if record.status in ["kept", "download_failed"]:
            # Check if PDF path is missing or file does not exist
            is_missing = False
            if not record.pdf_path:
                is_missing = True
            else:
                p = Path(record.pdf_path)
                if not p.exists() or not downloader._is_valid_pdf_file(p):
                    is_missing = True

            if is_missing and record.pdf_url:
                missing_records.append(record)

    print("\n" + "=" * 76)
    print("           RESEARCH PAPER PDF RECOVERY & REPAIR TOOL")
    print("=" * 76)

    if not missing_records:
        print("[+] All kept papers in the registry have verified PDFs on disk!")
        print("    No recovery needed.")
        print("=" * 76 + "\n")
        return {"recovered": 0, "failed": 0, "total_missing": 0}

    print(f"[!] Found {len(missing_records)} paper(s) with missing or failed PDF downloads.")
    print("    Attempting re-download with retries and alternate mirrors...\n")

    recovered_count = 0
    failed_count = 0

    for idx, record in enumerate(missing_records, 1):
        print(f"[{idx}/{len(missing_records)}] '{record.title[:60]}...'")
        print(f"      URL: {record.pdf_url}")

        success, saved_path, msg = downloader.download(
            pdf_url=record.pdf_url,
            title=record.title,
            authors=record.authors,
            year=record.year,
            doi=record.doi,
            abstract=record.abstract,
            polite_delay=1.5  # Polite delay to prevent connection resets
        )

        if success and saved_path and saved_path.exists():
            registry.register(
                paper_id=record.paper_id,
                title=record.title,
                status="kept",
                authors=record.authors,
                year=record.year,
                journal=record.journal,
                doi=record.doi,
                pmcid=record.pmcid,
                abstract=record.abstract,
                pdf_url=record.pdf_url,
                pdf_path=str(saved_path),
            )
            recovered_count += 1
            print(f"      [SUCCESS] {msg}")
            print(f"      Saved to: {saved_path}\n")
        else:
            registry.register(
                paper_id=record.paper_id,
                title=record.title,
                status="download_failed",
                authors=record.authors,
                year=record.year,
                journal=record.journal,
                doi=record.doi,
                pmcid=record.pmcid,
                abstract=record.abstract,
                pdf_url=record.pdf_url,
                pdf_path=None
            )
            failed_count += 1
            print(f"      [FAILED] {msg}\n")

    print("=" * 76)
    print(f"RECOVERY SUMMARY: {recovered_count} recovered | {failed_count} still failing")
    print("=" * 76 + "\n")

    return {"recovered": recovered_count, "failed": failed_count, "total_missing": len(missing_records)}


if __name__ == "__main__":
    repair_missing_pdfs()
