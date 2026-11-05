from typing import Any, List, Optional
from pydantic import BaseModel, Field

class HealthRelationship(BaseModel):
    """Structured health/clinical relationship extracted from scientific literature."""
    subject: str = Field(description="Primary entity, biomarker, behavior, or exposure (e.g. 'elevated heart rate with reduced slow-wave sleep')")
    relation: str = Field(description="Interaction, correlation, or directional mechanism (e.g. 'indicates increased risk of', 'positively correlates with', 'mitigates')")
    object: str = Field(description="Health outcome, physiological effect, or clinical condition (e.g. 'cardiac autonomic dysfunction')")
    condition: Optional[str] = Field(default=None, description="Context, population, or boundary conditions (e.g. 'in adult cohort', 'with obstructive sleep apnea')")
    evidence_quote: str = Field(description="Verbatim excerpt from the chunk supporting this relationship")
    confidence: str = Field(default="High", description="Confidence level: High / Moderate / Preliminary")
    
    # Metadata fields
    paper_title: str = Field(description="Title of source research paper")
    authors: str = Field(default="Unknown", description="Authors of research paper")
    publish_year: str = Field(default="Unknown", description="Year / date of publication")
    doi: Optional[str] = Field(default=None, description="DOI identifier")
    chunk_index: int = Field(default=0, description="Index of chunk within document")

    def to_claim_sentence(self) -> str:
        """Construct a declarative hypothesis sentence for NLI verification."""
        base = f"{self.subject} {self.relation} {self.object}"
        if self.condition:
            base += f" under condition: {self.condition}"
        return base



class ChunkExtractionResult(BaseModel):
    """Result of relationship extraction for a single chunk."""
    chunk_index: int
    chunk_text: str
    relationships: List[HealthRelationship] = Field(default_factory=list)


class PaperExtractionReport(BaseModel):
    """Consolidated relationship extraction report for a full research paper."""
    paper_id: str
    title: str
    authors: str
    publish_year: str
    doi: Optional[str] = None
    total_chunks: int
    total_relationships: int
    chunk_results: List[ChunkExtractionResult] = Field(default_factory=list)
    verified_reports: List[Any] = Field(default_factory=list)
