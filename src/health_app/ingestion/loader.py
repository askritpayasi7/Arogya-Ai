import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class IngestedDocument(BaseModel):
    """Normalized representation of a parsed document before chunking."""
    doc_id: str
    title: str
    doc_type: str  # 'research_paper' or 'fssai_regulation'
    file_path: str
    raw_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentLoader:
    """Loads and parses research papers and FSSAI statutory standards."""

    @staticmethod
    def load_file(file_path: Path, doc_type: str) -> Optional[IngestedDocument]:
        """Load a single file (Markdown, TXT, or PDF) and return an IngestedDocument."""
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return None

        suffix = file_path.suffix.lower()
        content = ""

        if suffix in [".md", ".txt"]:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        elif suffix == ".pdf":
            # Multi-engine PDF extractor: PyMuPDF (fitz) -> PyPDF2 -> pypdf
            extracted = False
            # 1. Try PyMuPDF (fitz) - high-fidelity full-text engine
            try:
                import fitz
                doc = fitz.open(str(file_path))
                pages = [page.get_text() or "" for page in doc]
                content = "\n\n".join(pages)
                extracted = bool(content.strip())
            except Exception:
                extracted = False

            # 2. Try PyPDF2
            if not extracted:
                try:
                    import PyPDF2
                    reader = PyPDF2.PdfReader(str(file_path))
                    pages = [page.extract_text() or "" for page in reader.pages]
                    content = "\n\n".join(pages)
                    extracted = bool(content.strip())
                except Exception:
                    extracted = False

            # 3. Try pypdf
            if not extracted:
                try:
                    import pypdf
                    reader = pypdf.PdfReader(str(file_path))
                    pages = [page.extract_text() or "" for page in reader.pages]
                    content = "\n\n".join(pages)
                    extracted = bool(content.strip())
                except Exception as e:
                    logger.error(f"Error reading PDF {file_path}: {e}")
                    return None
        else:
            logger.warning(f"Unsupported file format: {file_path}")
            return None

        if not content.strip():
            logger.warning(f"Empty document: {file_path}")
            return None

        # Parse basic metadata from frontmatter or content headers
        doc_id = re.sub(r'[^a-zA-Z0-9_-]', '_', file_path.stem)
        title = file_path.stem.replace("_", " ").title()

        # Look for markdown title # Title
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()

        metadata: Dict[str, Any] = {
            "title": title,
            "filename": file_path.name,
            "doc_type": doc_type,
            "path": str(file_path),
        }

        # Extract specific research or FSSAI fields if present in header
        doi_match = re.search(r'(?:DOI|doi):\s*([^\s\n]+)', content)
        if doi_match:
            metadata["doi"] = doi_match.group(1).strip()

        authors_match = re.search(r'(?:Authors?|Author):\s*([^\n]+)', content)
        if authors_match:
            metadata["authors"] = authors_match.group(1).strip()

        year_match = re.search(r'(?:Year|Date):\s*([^\n]+)', content)
        if year_match:
            metadata["year"] = year_match.group(1).strip()

        regulation_match = re.search(r'(?:FSSAI Regulation|Notification No|Standard):\s*([^\n]+)', content)
        if regulation_match:
            metadata["regulation_number"] = regulation_match.group(1).strip()

        return IngestedDocument(
            doc_id=doc_id,
            title=title,
            doc_type=doc_type,
            file_path=str(file_path),
            raw_text=content,
            metadata=metadata
        )

    @classmethod
    def load_directory(cls, directory_path: Path, doc_type: str) -> List[IngestedDocument]:
        """Load all compatible files from a directory."""
        if not directory_path.exists():
            logger.warning(f"Directory does not exist: {directory_path}")
            return []

        docs: List[IngestedDocument] = []
        for file_path in directory_path.glob("**/*"):
            if file_path.is_file() and file_path.suffix.lower() in [".md", ".txt", ".pdf"]:
                doc = cls.load_file(file_path, doc_type)
                if doc:
                    docs.append(doc)
        return docs
