import logging
from typing import Dict, List
from pydantic import BaseModel, Field

from health_app.vectordb.store import (
    VectorStore,
    SearchResultItem,
    COLLECTION_RESEARCH,
    COLLECTION_FSSAI,
)

logger = logging.getLogger(__name__)

class EvidenceSet(BaseModel):
    """Container for retrieved evidence chunks from both research and regulatory sources."""
    query: str
    research_evidence: List[SearchResultItem] = Field(default_factory=list)
    fssai_evidence: List[SearchResultItem] = Field(default_factory=list)

    @property
    def total_evidence_count(self) -> int:
        return len(self.research_evidence) + len(self.fssai_evidence)


class HealthRetriever:
    """Orchestrates semantic retrieval across scientific and FSSAI vector collections."""

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    def retrieve(self, query: str, top_k_per_source: int = 3) -> EvidenceSet:
        """Retrieve evidence chunks for a health/safety query from both collections."""
        results = self.vector_store.query_all(
            query_text=query,
            n_results_per_collection=top_k_per_source
        )

        return EvidenceSet(
            query=query,
            research_evidence=results.get(COLLECTION_RESEARCH, []),
            fssai_evidence=results.get(COLLECTION_FSSAI, []),
        )
