import logging
import re
import socket
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET
from pydantic import BaseModel
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class CandidatePaper(BaseModel):
    """Candidate research paper retrieved from open scientific repositories."""
    paper_id: str
    title: str
    authors: str = "Unknown"
    year: str = "Unknown"
    journal: str = "Unknown"
    doi: Optional[str] = None
    pmcid: Optional[str] = None
    abstract: str = ""
    pdf_url: Optional[str] = None
    source: str = "Europe PMC"


class PaperSearchClient:
    """Resilient client for retrieving open-access research papers from Europe PMC, Crossref, arXiv, and local registry."""

    def __init__(self, timeout: int = 25):
        self.timeout = timeout
        self.session = self._create_resilient_session()
        self.last_notice: Optional[str] = None
        self._last_epmc_error: Optional[str] = None

    def _create_resilient_session(self) -> requests.Session:
        """Create a requests session with retries for transient DNS/connection drops."""
        session = requests.Session()
        retries = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update({
            "User-Agent": "ResearchHealthApp/0.1.0 (Nutrition & Health Research Tool; mailto:contact@local.app)"
        })
        return session

    @staticmethod
    def _norm_title(title: str) -> str:
        """Normalize paper title for deduplication."""
        return re.sub(r'[^a-zA-Z0-9]', '', title.lower().strip())

    def search_europe_pmc(self, query: str, limit: int = 5) -> List[CandidatePaper]:
        """Search Europe PMC for open-access biomedical and health research papers."""
        self._last_epmc_error = None
        clean_query = re.sub(r'[^a-zA-Z0-9\s-]', ' ', query).strip()
        encoded_query = f"{clean_query} AND (OPEN_ACCESS:y OR hasPDF:y)"
        url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        params = {
            "query": encoded_query,
            "format": "json",
            "resultType": "core",
            "pageSize": min(limit * 2, 25),
        }

        papers: List[CandidatePaper] = []
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("resultList", {}).get("result", [])

            for item in results:
                title = item.get("title", "").strip().rstrip(".")
                if not title:
                    continue

                pmcid = item.get("pmcid")
                doi = item.get("doi")
                pmid = item.get("pmid")
                paper_id = pmcid or doi or (f"pmid_{pmid}" if pmid else f"epmc_{item.get('id', '')}")

                authors = item.get("authorString", "Unknown")
                year = str(item.get("pubYear") or item.get("firstPublicationDate", "Unknown")[:4])
                journal = item.get("journalTitle") or item.get("bookOrReportDetails", {}).get("publisher", "Biomedical Journal")

                abstract = item.get("abstractText", "")
                abstract = re.sub(r'<[^>]+>', ' ', abstract).strip()
                abstract = re.sub(r'\s+', ' ', abstract)

                pdf_url = None
                # Check for direct PDF links in fullTextUrlList
                full_text_list = item.get("fullTextUrlList", {}).get("fullTextUrl", [])
                for ft in full_text_list:
                    url_val = ft.get("url", "")
                    if ft.get("documentStyle") == "pdf" and url_val:
                        if pmcid and "europepmc.org" in url_val:
                            pdf_url = f"https://europepmc.org/api/getPdf?pmcid={pmcid}"
                        else:
                            pdf_url = url_val
                        break

                if not pdf_url and pmcid:
                    pdf_url = f"https://europepmc.org/api/getPdf?pmcid={pmcid}"

                papers.append(
                    CandidatePaper(
                        paper_id=str(paper_id),
                        title=title,
                        authors=authors,
                        year=year,
                        journal=journal,
                        doi=doi,
                        pmcid=pmcid,
                        abstract=abstract or "No abstract provided in database.",
                        pdf_url=pdf_url,
                        source="Europe PMC"
                    )
                )
                if len(papers) >= limit:
                    break

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, socket.gaierror) as net_err:
            self._last_epmc_error = f"DNS/Network unreachable ({type(net_err).__name__})"
            logger.warning(f"Europe PMC network/DNS unreachable: {net_err}")
            self.session = self._create_resilient_session()
        except Exception as e:
            self._last_epmc_error = str(e)
            logger.warning(f"Europe PMC search encountered transient issue: {e}")
            self.session = self._create_resilient_session()

        return papers

    def search_crossref(self, query: str, limit: int = 5) -> List[CandidatePaper]:
        """Search Crossref Works API for biomedical and clinical research literature."""
        clean_query = re.sub(r'[^a-zA-Z0-9\s-]', ' ', query).strip()
        url = "https://api.crossref.org/works"
        params = {
            "query": clean_query,
            "rows": min(limit * 2, 25),
            "select": "DOI,title,author,published,issued,abstract,container-title,link,URL",
        }
        papers: List[CandidatePaper] = []
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("message", {}).get("items", [])

            for item in items:
                titles = item.get("title", [])
                title = titles[0].strip().rstrip(".") if titles else ""
                if not title:
                    continue

                doi = item.get("DOI")
                paper_id = f"crossref_{doi.replace('/', '_')}" if doi else f"crossref_{abs(hash(title))}"

                # Author extraction
                author_names = []
                for a in item.get("author", []):
                    if "family" in a:
                        given = a.get("given", "")
                        author_names.append(f"{given} {a['family']}".strip())
                    elif "name" in a:
                        author_names.append(a["name"])
                authors = ", ".join(author_names[:4]) or "Unknown"

                # Year extraction
                year_part = (
                    item.get("published", {}).get("date-parts", [[None]])[0][0]
                    or item.get("issued", {}).get("date-parts", [[None]])[0][0]
                )
                year = str(year_part) if year_part else "Unknown"

                # Journal
                containers = item.get("container-title", [])
                journal = containers[0] if (containers and containers[0]) else "Biomedical Literature"

                # Abstract
                raw_abstract = item.get("abstract", "")
                abstract = re.sub(r'<[^>]+>', ' ', raw_abstract).strip()
                abstract = re.sub(r'\s+', ' ', abstract)

                # PDF / Full text link
                pdf_url = None
                links = item.get("link", [])
                for l in links:
                    url_val = l.get("URL", "")
                    content_type = l.get("content-type", "")
                    if "pdf" in content_type.lower() or url_val.endswith(".pdf"):
                        pdf_url = url_val
                        break
                if not pdf_url and doi:
                    pdf_url = f"https://doi.org/{doi}"

                papers.append(
                    CandidatePaper(
                        paper_id=str(paper_id),
                        title=title,
                        authors=authors,
                        year=year,
                        journal=journal,
                        doi=doi,
                        abstract=abstract or "Peer-reviewed literature cataloged via Crossref DOI registry.",
                        pdf_url=pdf_url,
                        source="Crossref"
                    )
                )
                if len(papers) >= limit:
                    break

        except Exception as e:
            logger.warning(f"Crossref search encountered transient issue: {e}")

        return papers

    def search_arxiv(self, query: str, limit: int = 5) -> List[CandidatePaper]:
        """Search arXiv API for quantitative biology and health preprints."""
        url = "https://export.arxiv.org/api/query"
        clean_query = re.sub(r'[^a-zA-Z0-9\s]', ' ', query).strip()
        params = {
            "search_query": f"all:{clean_query}",
            "start": 0,
            "max_results": limit,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        papers: List[CandidatePaper] = []
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()

            root = ET.fromstring(resp.text)
            ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

            for entry in root.findall("atom:entry", ns):
                title_elem = entry.find("atom:title", ns)
                title = title_elem.text.strip().replace("\n", " ") if title_elem is not None and title_elem.text else ""
                if not title:
                    continue

                id_elem = entry.find("atom:id", ns)
                raw_id = id_elem.text.strip() if id_elem is not None and id_elem.text else ""
                arxiv_id = raw_id.split("/abs/")[-1]

                author_elems = entry.findall("atom:author/atom:name", ns)
                authors = ", ".join([a.text.strip() for a in author_elems if a.text]) or "Unknown"

                published_elem = entry.find("atom:published", ns)
                year = published_elem.text[:4] if published_elem is not None and published_elem.text else "Unknown"

                summary_elem = entry.find("atom:summary", ns)
                abstract = summary_elem.text.strip().replace("\n", " ") if summary_elem is not None and summary_elem.text else ""
                abstract = re.sub(r'\s+', ' ', abstract)

                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else None
                doi_elem = entry.find("arxiv:doi", ns)
                doi = doi_elem.text.strip() if doi_elem is not None and doi_elem.text else None

                papers.append(
                    CandidatePaper(
                        paper_id=f"arxiv_{arxiv_id}",
                        title=title,
                        authors=authors,
                        year=year,
                        journal="arXiv.org",
                        doi=doi,
                        abstract=abstract or "No abstract available.",
                        pdf_url=pdf_url,
                        source="arXiv"
                    )
                )

        except Exception as e:
            logger.warning(f"arXiv search encountered transient issue: {e}")

        return papers

    def search_local_registry(self, query: str, limit: int = 5) -> List[CandidatePaper]:
        """Search local indexed research paper archive as offline fallback."""
        papers: List[CandidatePaper] = []
        try:
            from health_app.fetcher.registry import PaperRegistry
            registry = PaperRegistry()
            if not registry.records:
                return papers

            q_tokens = [tok for tok in re.findall(r'[a-zA-Z0-9]+', query.lower()) if len(tok) >= 3]
            scored_candidates = []

            for rec in registry.records.values():
                title_lower = rec.title.lower()
                abstract_lower = (rec.abstract or "").lower()
                author_lower = (rec.authors or "").lower()

                score = 0
                for tok in q_tokens:
                    if tok in title_lower:
                        score += 3
                    if tok in abstract_lower:
                        score += 1
                    if tok in author_lower:
                        score += 1

                scored_candidates.append((score, rec))

            # Sort by score descending; if no tokens matched, keep natural recency order
            scored_candidates.sort(key=lambda x: x[0], reverse=True)

            for score, rec in scored_candidates:
                papers.append(
                    CandidatePaper(
                        paper_id=rec.paper_id,
                        title=rec.title,
                        authors=rec.authors,
                        year=rec.year,
                        journal=rec.journal or "Local Research Archive",
                        doi=rec.doi,
                        pmcid=rec.pmcid,
                        abstract=rec.abstract or "Full manuscript indexed in local repository.",
                        pdf_url=rec.pdf_path or rec.pdf_url,
                        source="Local Archive (Offline)"
                    )
                )
                if len(papers) >= limit:
                    break

        except Exception as e:
            logger.warning(f"Local repository search fallback issue: {e}")

        return papers

    def search_all(self, query: str, limit: int = 5) -> List[CandidatePaper]:
        """Hierarchical multi-tier research search with automatic failover across 4 tiers:
        Tier 1: Europe PMC (Primary biomedical)
        Tier 2: Crossref (Broad peer-reviewed literature)
        Tier 3: arXiv (Preprints & bio-AI)
        Tier 4: Local Paper Registry (100% offline failover)
        """
        papers: List[CandidatePaper] = []
        notices: List[str] = []
        self.last_notice = None

        # Tier 1: Europe PMC
        try:
            epmc_papers = self.search_europe_pmc(query, limit=limit)
            papers.extend(epmc_papers)
        except Exception as e:
            self._last_epmc_error = str(e)
            logger.warning(f"Europe PMC uncaught exception: {e}")

        if self._last_epmc_error:
            notices.append("Europe PMC DNS/network issue")

        # Tier 2: Crossref Works API if more candidates needed
        if len(papers) < limit:
            remaining = limit - len(papers)
            try:
                crossref_papers = self.search_crossref(query, limit=remaining)
                existing_ids = {p.paper_id for p in papers}
                existing_titles = {self._norm_title(p.title) for p in papers}
                for cp in crossref_papers:
                    norm = self._norm_title(cp.title)
                    if cp.paper_id not in existing_ids and norm not in existing_titles:
                        papers.append(cp)
                        existing_ids.add(cp.paper_id)
                        existing_titles.add(norm)
            except Exception as e:
                logger.warning(f"Crossref search exception: {e}")

        # Tier 3: arXiv Preprints if still needed
        if len(papers) < limit:
            remaining = limit - len(papers)
            try:
                arxiv_papers = self.search_arxiv(query, limit=remaining)
                existing_ids = {p.paper_id for p in papers}
                existing_titles = {self._norm_title(p.title) for p in papers}
                for ap in arxiv_papers:
                    norm = self._norm_title(ap.title)
                    if ap.paper_id not in existing_ids and norm not in existing_titles:
                        papers.append(ap)
                        existing_ids.add(ap.paper_id)
                        existing_titles.add(norm)
            except Exception as e:
                logger.warning(f"arXiv search exception: {e}")

        # Tier 4: Local Archive Fallback if 0 papers found or network offline
        if not papers:
            try:
                local_papers = self.search_local_registry(query, limit=limit)
                papers.extend(local_papers)
                if local_papers:
                    notices.append("local_archive")
            except Exception as e:
                logger.warning(f"Local registry search exception: {e}")

        # Build user-friendly diagnostic notice
        if "local_archive" in notices:
            self.last_notice = "Remote repositories were unreachable; candidate papers loaded from local offline archive."
        elif "Europe PMC DNS/network issue" in notices:
            self.last_notice = "Europe PMC DNS was unreachable; candidate papers retrieved via Crossref / arXiv fallback mirrors."

        return papers[:limit]

