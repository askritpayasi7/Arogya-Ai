import logging
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from health_app.config import settings

logger = logging.getLogger(__name__)

BROWSER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

class PDFDownloader:
    """Safely downloads scientific research paper PDFs with retries, mirror fallbacks, and Windows-safe path handling."""

    def __init__(self, target_dir: Optional[Path] = None, timeout: Tuple[float, float] = (8.0, 20.0)):
        self.target_dir = target_dir or settings.research_papers_dir
        self.target_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        
        # Configure resilient session with fast connection timeouts and full browser headers
        self.session = requests.Session()
        retries = Retry(
            total=1,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,application/pdf,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        })

    def _render_progress_bar(self, downloaded: int, total: Optional[int]) -> None:
        """Render live download progress bar in the terminal."""
        dl_kb = downloaded / 1024
        if total and total > 0:
            tot_kb = total / 1024
            pct = min(100.0, (downloaded / total) * 100.0)
            bar_len = 25
            filled = int(bar_len * (pct / 100.0))
            bar = "#" * filled + "-" * (bar_len - filled)
            print(f"\r  [Progress] |{bar}| {pct:5.1f}% ({dl_kb:.0f} KB / {tot_kb:.0f} KB)", end="", flush=True)
        else:
            print(f"\r  [Progress] Downloaded: {dl_kb:.0f} KB (Streaming)...", end="", flush=True)

    def _sanitize_filename(self, text: str) -> str:
        """Sanitize text to create safe Windows filenames."""
        clean = re.sub(r'[<>:"/\\|?*]', '_', text)
        clean = re.sub(r'\s+', '_', clean).strip(" ._")
        return clean[:110]

    def _is_valid_pdf_file(self, file_path: Path) -> bool:
        """Check that file exists, is >= 1024 bytes, and contains valid %PDF- magic header."""
        if not file_path or not file_path.exists():
            return False
        try:
            if file_path.stat().st_size < 1024:
                return False
            with open(file_path, "rb") as f:
                header = f.read(1024)
                # Reject HTML landing pages or XML error docs
                if b"<html" in header.lower() or b"<!doctype html" in header.lower():
                    return False
                if b"%PDF-" in header:
                    return True
        except Exception as e:
            logger.debug(f"Error validating PDF header for {file_path}: {e}")
        return False

    def _get_url_variants(self, url: str) -> List[str]:
        """Generate alternative direct API endpoints or mirror URLs if available."""
        urls = []

        # PubMed Central transformations: prioritize Europe PMC direct binary API
        pmc_match = re.search(r'PMC\d+', url, re.IGNORECASE)
        if pmc_match:
            pmcid = pmc_match.group(0).upper()
            # Europe PMC direct API is the gold standard for clean binary PDFs
            urls.append(f"https://europepmc.org/api/getPdf?pmcid={pmcid}")
            # NIH PubMed Central direct mirrors as secondaries
            urls.append(f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/pdf/")
            urls.append(f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/")

        # For arXiv: try standard and export mirror
        if "arxiv.org/pdf/" in url:
            if "export.arxiv.org" not in url:
                urls.append(url.replace("https://arxiv.org/pdf/", "https://export.arxiv.org/pdf/"))
            else:
                urls.append(url.replace("https://export.arxiv.org/pdf/", "https://arxiv.org/pdf/"))

        # Add original URL if not already in list
        if url not in urls:
            urls.append(url)

        return urls

    def _download_with_curl(self, url: str, target_file: Path) -> bool:
        """Fallback downloader using Windows built-in curl.exe to bypass TLS fingerprint blocks."""
        curl_path = shutil.which("curl.exe") or shutil.which("curl")
        if not curl_path:
            return False

        try:
            print(f"  [*] Invoking native curl.exe fallback to bypass TLS blocks...", flush=True)
            cmd = [
                curl_path,
                "-L",
                "-s",
                "-A", BROWSER_USER_AGENT,
                "-H", "Accept: application/pdf,text/html,*/*",
                "--max-time", "20",
                "-o", str(target_file),
                url
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=25)
            if result.returncode == 0 and self._is_valid_pdf_file(target_file):
                file_kb = target_file.stat().st_size // 1024
                print(f"  [+] curl.exe successfully retrieved PDF ({file_kb} KB)", flush=True)
                return True
        except Exception as e:
            logger.debug(f"curl.exe fallback exception: {e}")

        if target_file.exists():
            target_file.unlink(missing_ok=True)
        return False

    def download_stream(
        self,
        pdf_url: str,
        title: str,
        authors: str = "Unknown",
        year: str = "Unknown",
        doi: Optional[str] = None,
        abstract: str = "",
        polite_delay: float = 1.0,
    ) -> Iterator[Dict[str, Any]]:
        """
        Download PDF from URL, yielding real-time progress events.
        Yields: download_start, download_progress, download_verified, download_result.
        """
        if not pdf_url:
            yield {
                "type": "download_result",
                "success": False,
                "saved_path": None,
                "message": "No PDF download URL available for this paper."
            }
            return

        if polite_delay > 0:
            time.sleep(polite_delay)

        # Generate readable filename
        first_author = authors.split(",")[0].split()[0] if authors else "Author"
        safe_author = self._sanitize_filename(first_author)
        safe_title = self._sanitize_filename(title)
        safe_year = self._sanitize_filename(year)
        base_name = f"{safe_year}_{safe_author}_{safe_title}"
        pdf_path = self.target_dir / f"{base_name}.pdf"
        md_path = self.target_dir / f"{base_name}.md"

        urls_to_try = self._get_url_variants(pdf_url)
        last_error = "Unknown error"
        total_endpoints = len(urls_to_try)

        for idx, url in enumerate(urls_to_try, 1):
            yield {
                "type": "download_start",
                "step": idx,
                "total_steps": total_endpoints,
                "url": url,
                "title": title,
                "message": f"Contacting endpoint [{idx}/{total_endpoints}]: {url[:65]}..."
            }
            print(f"  [Step {idx}/{total_endpoints}] Contacting endpoint: {url[:72]}...", flush=True)

            try:
                resp = self.session.get(url, stream=True, timeout=self.timeout, allow_redirects=True)
                
                # If HTTP 403 or non-200, try curl fallback for this URL
                if resp.status_code != 200:
                    last_error = f"HTTP Error {resp.status_code} from {url}"
                    yield {
                        "type": "download_progress",
                        "status": "warning",
                        "status_code": resp.status_code,
                        "message": f"Server responded with HTTP {resp.status_code}. Invoking native curl fallback..."
                    }

                    if self._download_with_curl(url, pdf_path):
                        self._write_summary_md(md_path, title, authors, year, doi, url, abstract)
                        file_size = pdf_path.stat().st_size
                        yield {
                            "type": "download_verified",
                            "saved_path": str(pdf_path),
                            "size_kb": file_size // 1024,
                            "method": "curl",
                            "message": f"Verified PDF on disk via curl fallback ({file_size // 1024} KB)."
                        }
                        yield {
                            "type": "download_result",
                            "success": True,
                            "saved_path": pdf_path,
                            "message": f"Saved PDF ({file_size // 1024} KB) and summary markdown."
                        }
                        return
                    continue

                # Stream content to disk with live progress updates
                headers = getattr(resp, "headers", None) or {}
                content_len = headers.get("content-length")
                total_bytes = int(content_len) if content_len and str(content_len).isdigit() else None
                downloaded_bytes = 0
                last_yielded_kb = 0

                with open(pdf_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=16384):
                        if chunk:
                            f.write(chunk)
                            downloaded_bytes += len(chunk)
                            dl_kb = downloaded_bytes / 1024
                            self._render_progress_bar(downloaded_bytes, total_bytes)

                            # Yield progress event roughly every ~64KB or when total reached or on initial chunk
                            if (dl_kb - last_yielded_kb >= 64) or (total_bytes and downloaded_bytes >= total_bytes) or last_yielded_kb == 0:
                                pct = min(100.0, (downloaded_bytes / total_bytes) * 100.0) if total_bytes else 0.0
                                tot_kb = (total_bytes / 1024) if total_bytes else 0.0
                                last_yielded_kb = dl_kb
                                yield {
                                    "type": "download_progress",
                                    "downloaded_kb": round(dl_kb, 1),
                                    "total_kb": round(tot_kb, 1),
                                    "pct": round(pct, 1),
                                    "message": f"Downloading PDF: {pct:.1f}% ({dl_kb:.0f} KB / {tot_kb:.0f} KB)" if total_bytes else f"Downloading PDF: {dl_kb:.0f} KB (Streaming)..."
                                }

                print("", flush=True)  # Newline after progress bar

                # Validate downloaded file size and %PDF- binary header
                if not pdf_path.exists():
                    last_error = "File was not written to disk."
                    continue

                if not self._is_valid_pdf_file(pdf_path):
                    raw_size = pdf_path.stat().st_size if pdf_path.exists() else 0
                    pdf_path.unlink(missing_ok=True)
                    yield {
                        "type": "download_progress",
                        "status": "warning",
                        "message": f"Received non-PDF / HTML payload ({raw_size} bytes). Trying curl fallback..."
                    }
                    if self._download_with_curl(url, pdf_path) and self._is_valid_pdf_file(pdf_path):
                        self._write_summary_md(md_path, title, authors, year, doi, url, abstract)
                        file_size = pdf_path.stat().st_size
                        yield {
                            "type": "download_verified",
                            "saved_path": str(pdf_path),
                            "size_kb": file_size // 1024,
                            "method": "curl",
                            "message": f"Verified PDF on disk ({file_size // 1024} KB)."
                        }
                        yield {
                            "type": "download_result",
                            "success": True,
                            "saved_path": pdf_path,
                            "message": f"Saved PDF ({file_size // 1024} KB) and summary markdown."
                        }
                        return

                    last_error = f"Downloaded content from {url} is not a valid PDF binary ({raw_size} bytes)."
                    continue

                # Write companion markdown summary
                self._write_summary_md(md_path, title, authors, year, doi, url, abstract)
                file_size = pdf_path.stat().st_size
                print(f"  [+] PDF verified on disk ({file_size // 1024} KB).", flush=True)
                yield {
                    "type": "download_verified",
                    "saved_path": str(pdf_path),
                    "size_kb": file_size // 1024,
                    "method": "stream",
                    "message": f"Verified %PDF- binary on disk ({file_size // 1024} KB)."
                }
                yield {
                    "type": "download_result",
                    "success": True,
                    "saved_path": pdf_path,
                    "message": f"Saved PDF ({file_size // 1024} KB) and summary markdown."
                }
                return

            except Exception as e:
                last_error = str(e)
                print(f"\n  [!] Connection note: {e}", flush=True)
                if pdf_path.exists():
                    pdf_path.unlink(missing_ok=True)
                yield {
                    "type": "download_progress",
                    "status": "warning",
                    "message": f"Connection note: {e}. Trying curl fallback..."
                }
                if self._download_with_curl(url, pdf_path) and self._is_valid_pdf_file(pdf_path):
                    self._write_summary_md(md_path, title, authors, year, doi, url, abstract)
                    file_size = pdf_path.stat().st_size
                    print(f"  [+] PDF verified on disk ({file_size // 1024} KB).", flush=True)
                    yield {
                        "type": "download_verified",
                        "saved_path": str(pdf_path),
                        "size_kb": file_size // 1024,
                        "method": "curl",
                        "message": f"Verified PDF on disk ({file_size // 1024} KB)."
                    }
                    yield {
                        "type": "download_result",
                        "success": True,
                        "saved_path": pdf_path,
                        "message": f"Saved PDF ({file_size // 1024} KB) and summary markdown."
                    }
                    return

                time.sleep(0.5)

        yield {
            "type": "download_result",
            "success": False,
            "saved_path": None,
            "message": f"Download failed across all mirrors: {last_error}"
        }

    def download(
        self,
        pdf_url: str,
        title: str,
        authors: str = "Unknown",
        year: str = "Unknown",
        doi: Optional[str] = None,
        abstract: str = "",
        polite_delay: float = 1.0,
    ) -> Tuple[bool, Optional[Path], str]:
        """
        Download PDF from URL and save to target directory.
        Tries direct APIs, mirrors, and native curl fallback if needed.
        Also creates a companion summary markdown file.
        Returns (success, saved_path, message).
        """
        for event in self.download_stream(
            pdf_url=pdf_url,
            title=title,
            authors=authors,
            year=year,
            doi=doi,
            abstract=abstract,
            polite_delay=polite_delay,
        ):
            if event.get("type") == "download_result":
                return event["success"], event["saved_path"], event["message"]
        return False, None, "Download failed"

    def _write_summary_md(self, md_path: Path, title: str, authors: str, year: str, doi: Optional[str], url: str, abstract: str) -> None:
        """Create companion markdown summary file."""
        md_content = (
            f"# {title}\n"
            f"Authors: {authors}\n"
            f"Year: {year}\n"
            f"DOI: {doi or 'N/A'}\n"
            f"Source URL: {url}\n\n"
            f"## Abstract\n{abstract}\n"
        )
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
