import datetime
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DEFAULT_INDEX_PATH = Path("./data/research_papers_index.json")

class PaperRecord(BaseModel):
    """Metadata record for an indexed research paper."""
    paper_id: str
    title: str
    authors: str = "Unknown"
    year: str = "Unknown"
    journal: str = "Unknown"
    doi: Optional[str] = None
    pmcid: Optional[str] = None
    abstract: str = ""
    pdf_url: Optional[str] = None
    status: str  # "kept" or "discarded"
    pdf_path: Optional[str] = None
    recorded_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())


class PaperRegistry:
    """Persistent registry for deduplicating and indexing research papers."""

    def __init__(self, index_path: Optional[Path] = None):
        self.index_path = index_path or DEFAULT_INDEX_PATH
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.records: Dict[str, PaperRecord] = {}
        self._title_lookup: Dict[str, str] = {}  # normalized_title -> paper_id
        self._load()

    def _normalize_title(self, title: str) -> str:
        """Normalize title string for robust duplicate detection."""
        return re.sub(r'[^a-zA-Z0-9]', '', title.lower().strip())

    def _load(self) -> None:
        """Load records from index JSON file."""
        if not self.index_path.exists():
            self.records = {}
            self._title_lookup = {}
            return

        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.records = {}
            self._title_lookup = {}
            for item in data.get("papers", []):
                record = PaperRecord(**item)
                self.records[record.paper_id] = record
                self._title_lookup[self._normalize_title(record.title)] = record.paper_id
        except Exception as e:
            logger.error(f"Error loading registry index {self.index_path}: {e}")
            self.records = {}
            self._title_lookup = {}

    def _save(self) -> None:
        """Save records to index JSON file atomically."""
        temp_path = self.index_path.with_suffix(".tmp")
        data = {
            "updated_at": datetime.datetime.now().isoformat(),
            "total_count": len(self.records),
            "papers": [record.model_dump() for record in self.records.values()]
        }
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_path.replace(self.index_path)

    def is_indexed(self, paper_id: Optional[str] = None, title: Optional[str] = None, doi: Optional[str] = None, pmcid: Optional[str] = None) -> bool:
        """Check if paper is already indexed by ID, DOI, PMCID, or normalized title."""
        if paper_id and paper_id in self.records:
            return True

        if doi:
            clean_doi = doi.lower().strip()
            for rec in self.records.values():
                if rec.doi and rec.doi.lower().strip() == clean_doi:
                    return True

        if pmcid:
            clean_pmc = pmcid.upper().strip()
            for rec in self.records.values():
                if rec.pmcid and rec.pmcid.upper().strip() == clean_pmc:
                    return True

        if title:
            norm_title = self._normalize_title(title)
            if norm_title in self._title_lookup:
                return True

        return False

    def register(
        self,
        paper_id: str,
        title: str,
        status: str,
        authors: str = "Unknown",
        year: str = "Unknown",
        journal: str = "Unknown",
        doi: Optional[str] = None,
        pmcid: Optional[str] = None,
        abstract: str = "",
        pdf_url: Optional[str] = None,
        pdf_path: Optional[str] = None,
    ) -> PaperRecord:
        """Register or update a paper record and persist to disk."""
        record = PaperRecord(
            paper_id=paper_id,
            title=title,
            authors=authors,
            year=year,
            journal=journal,
            doi=doi,
            pmcid=pmcid,
            abstract=abstract,
            pdf_url=pdf_url,
            status=status,
            pdf_path=pdf_path,
        )
        self.records[paper_id] = record
        self._title_lookup[self._normalize_title(title)] = paper_id
        self._save()
        return record

    def get_counts(self) -> Dict[str, int]:
        """Return counts of kept and discarded papers."""
        kept = sum(1 for r in self.records.values() if r.status == "kept")
        discarded = sum(1 for r in self.records.values() if r.status == "discarded")
        return {"kept": kept, "discarded": discarded, "total": len(self.records)}

    def list_kept_papers(self) -> List[PaperRecord]:
        """Return list of all kept/downloaded papers."""
        return [r for r in self.records.values() if r.status == "kept"]
