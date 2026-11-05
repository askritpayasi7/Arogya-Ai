"""Research paper fetcher, index registry, and downloader module."""

from health_app.fetcher.registry import PaperRegistry, PaperRecord
from health_app.fetcher.client import PaperSearchClient, CandidatePaper
from health_app.fetcher.downloader import PDFDownloader
from health_app.fetcher.interactive import run_interactive_fetcher
from health_app.fetcher.recovery import repair_missing_pdfs

__all__ = [
    "PaperRegistry",
    "PaperRecord",
    "PaperSearchClient",
    "CandidatePaper",
    "PDFDownloader",
    "run_interactive_fetcher",
    "repair_missing_pdfs",
]
