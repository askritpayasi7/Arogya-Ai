import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from health_app.rag.retriever import HealthRetriever, EvidenceSet
from health_app.vectordb.store import SearchResultItem

logger = logging.getLogger(__name__)

class Citation(BaseModel):
    """Citation metadata for verifiable evidence grounding."""
    source_type: str  # 'research_paper' or 'fssai_regulation'
    title: str
    section: Optional[str] = None
    identifier: Optional[str] = None  # DOI, Notification No, etc.
    excerpt: str


class HealthAdvisoryResponse(BaseModel):
    """Synthesized response strictly grounded in research and FSSAI standards."""
    query: str
    summary: str
    scientific_findings: List[str] = Field(default_factory=list)
    fssai_standards: List[str] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    disclaimer: str = (
        "Disclaimer: This advisory is synthesized from peer-reviewed scientific literature and "
        "official FSSAI statutory standards for informational and compliance purposes. "
        "It does not replace personalized clinical advice from certified medical professionals."
    )


class HealthAdvisoryEngine:
    """Core advisory engine generating evidence-grounded health and safety reports."""

    def __init__(self, retriever: HealthRetriever):
        self.retriever = retriever

    def evaluate_query(self, query: str, top_k: int = 3) -> HealthAdvisoryResponse:
        """Process user query, retrieve relevant evidence, and synthesize grounded response."""
        evidence: EvidenceSet = self.retriever.retrieve(query=query, top_k_per_source=top_k)

        citations: List[Citation] = []
        scientific_findings: List[str] = []
        fssai_standards: List[str] = []

        # Process Research Papers
        for item in evidence.research_evidence:
            meta = item.metadata
            title = meta.get("title", "Scientific Research Paper")
            section = meta.get("section", "General")
            doi = meta.get("doi") or meta.get("year", "N/A")

            finding_text = f"[{title} - {section}]: {item.content.strip()}"
            scientific_findings.append(finding_text)

            citations.append(
                Citation(
                    source_type="research_paper",
                    title=title,
                    section=section,
                    identifier=f"DOI/Year: {doi}",
                    excerpt=item.content[:200].strip() + "..."
                )
            )

        # Process FSSAI Standards
        for item in evidence.fssai_evidence:
            meta = item.metadata
            title = meta.get("title", "FSSAI Regulation")
            section = meta.get("section", "Statutory Rule")
            reg_no = meta.get("regulation_number") or meta.get("year", "FSSAI Standard")

            standard_text = f"[{title} - {section}]: {item.content.strip()}"
            fssai_standards.append(standard_text)

            citations.append(
                Citation(
                    source_type="fssai_regulation",
                    title=title,
                    section=section,
                    identifier=f"Regulation: {reg_no}",
                    excerpt=item.content[:200].strip() + "..."
                )
            )

        if evidence.total_evidence_count == 0:
            summary = (
                f"No indexed research papers or FSSAI statutory standards directly matched the query: '{query}'. "
                "Please ensure relevant documents are ingested into the vector database."
            )
        else:
            summary = (
                f"Evaluation for '{query}' grounded in {len(evidence.research_evidence)} peer-reviewed "
                f"research excerpts and {len(evidence.fssai_evidence)} FSSAI regulatory standards."
            )

        return HealthAdvisoryResponse(
            query=query,
            summary=summary,
            scientific_findings=scientific_findings,
            fssai_standards=fssai_standards,
            citations=citations
        )
