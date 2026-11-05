import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

import chromadb
from chromadb.config import Settings as ChromaSettings

from health_app.config import settings
from health_app.vectordb.embeddings import BaseEmbeddingProvider, get_embedding_provider, MockEmbeddingProvider

logger = logging.getLogger(__name__)

# Constants for collection names
COLLECTION_RESEARCH = "research_papers"
COLLECTION_FSSAI = "fssai_standards"
COLLECTION_VERIFIED_RELATIONSHIPS = "verified_relationships"

DEFAULT_VERIFIED_CACHE = Path("./data/health_relationships_verified.json")

class SearchResultItem(BaseModel):
    """Represents a single retrieved chunk with its metadata and similarity score."""
    chunk_id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    distance: float
    collection_name: str


class VectorStore:
    """ChromaDB vector store manager for research papers and FSSAI standards."""

    def __init__(
        self,
        persist_dir: Optional[Path] = None,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
        in_memory: bool = False,
        collection_prefix: str = "",
    ):
        self.persist_dir = persist_dir or settings.chroma_persist_dir
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.in_memory = in_memory
        self.collection_prefix = collection_prefix

        if self.in_memory:
            self.client = chromadb.EphemeralClient()
        else:
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False)
            )

        res_name = f"{collection_prefix}_{COLLECTION_RESEARCH}" if collection_prefix else COLLECTION_RESEARCH
        fssai_name = f"{collection_prefix}_{COLLECTION_FSSAI}" if collection_prefix else COLLECTION_FSSAI
        verified_name = f"{collection_prefix}_{COLLECTION_VERIFIED_RELATIONSHIPS}" if collection_prefix else COLLECTION_VERIFIED_RELATIONSHIPS

        # Initialize collections
        self.research_collection = self.client.get_or_create_collection(
            name=res_name,
            metadata={"description": "Peer-reviewed scientific research papers and dietary trials"}
        )
        self.fssai_collection = self.client.get_or_create_collection(
            name=fssai_name,
            metadata={"description": "Statutory FSSAI regulations, additive limits, and guidelines"}
        )
        self.verified_collection = self.client.get_or_create_collection(
            name=verified_name,
            metadata={"description": "Clinically verified cause-and-effect health relationships (ACCEPTED & PROVISIONALLY_SUPPORTED)"}
        )

    def clear(self) -> None:
        """Clear all documents from all collections."""
        try:
            res_name = self.research_collection.name
            fssai_name = self.fssai_collection.name
            ver_name = self.verified_collection.name
            self.client.delete_collection(res_name)
            self.client.delete_collection(fssai_name)
            self.client.delete_collection(ver_name)
            self.research_collection = self.client.get_or_create_collection(name=res_name)
            self.fssai_collection = self.client.get_or_create_collection(name=fssai_name)
            self.verified_collection = self.client.get_or_create_collection(name=ver_name)
        except Exception as e:
            logger.debug(f"Error resetting collections: {e}")

    def add_documents(
        self,
        collection_name: str,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """Add documents and their computed embeddings to the specified collection."""
        if not documents:
            return 0

        if collection_name == COLLECTION_RESEARCH:
            target_collection = self.research_collection
        elif collection_name == COLLECTION_FSSAI:
            target_collection = self.fssai_collection
        else:
            target_collection = self.verified_collection

        try:
            embeddings = self.embedding_provider.embed_documents(documents)
        except Exception as e:
            logger.warning(f"Embedding provider ({type(self.embedding_provider).__name__}) failed ({e}). Falling back to deterministic MockEmbeddingProvider.")
            self.embedding_provider = MockEmbeddingProvider()
            embeddings = self.embedding_provider.embed_documents(documents)

        # ChromaDB requires all metadata values to be str, int, float, or bool
        sanitized_metadatas = []
        if metadatas:
            for m in metadatas:
                sanitized = {
                    k: (str(v) if not isinstance(v, (str, int, float, bool)) else v)
                    for k, v in m.items()
                }
                sanitized_metadatas.append(sanitized)
        else:
            sanitized_metadatas = [{} for _ in documents]

        target_collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=sanitized_metadatas
        )
        return len(documents)

    def query(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 4,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResultItem]:
        """Perform semantic similarity query against a collection with optional metadata filters."""
        if collection_name == COLLECTION_RESEARCH:
            target_collection = self.research_collection
        elif collection_name == COLLECTION_FSSAI:
            target_collection = self.fssai_collection
        else:
            target_collection = self.verified_collection

        if target_collection.count() == 0:
            return []

        try:
            query_embedding = self.embedding_provider.embed_query(query_text)
        except Exception as e:
            logger.warning(f"Embedding provider query failed ({e}). Falling back to MockEmbeddingProvider.")
            self.embedding_provider = MockEmbeddingProvider()
            query_embedding = self.embedding_provider.embed_query(query_text)
        query_kwargs: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": min(n_results, target_collection.count())
        }
        if where:
            query_kwargs["where"] = where

        results = target_collection.query(**query_kwargs)

        items: List[SearchResultItem] = []
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0] if results.get("distances") else [0.0] * len(ids)

        for i in range(len(ids)):
            items.append(
                SearchResultItem(
                    chunk_id=ids[i],
                    content=docs[i],
                    metadata=metas[i] if i < len(metas) else {},
                    distance=float(dists[i]) if i < len(dists) else 0.0,
                    collection_name=collection_name
                )
            )

        return items

    def add_verified_relationships(self, reports: List[Any]) -> int:
        """Strictly index ONLY passed clinical relationships into the vector database.
        Claims gated as EXCLUDED or QUARANTINED are strictly rejected.
        """
        if not reports:
            return 0

        passed_ids: List[str] = []
        passed_docs: List[str] = []
        passed_metas: List[Dict[str, Any]] = []

        for idx, rep in enumerate(reports):
            # Extract attributes from dict or Pydantic VerificationReport
            if isinstance(rep, dict):
                status = rep.get("gating_status", "")
                final_score = float(rep.get("final_score", 0.0))
                claim_summary = rep.get("claim_summary", "")
                study_design = rep.get("study_design", {}).get("design_type", "Unknown") if isinstance(rep.get("study_design"), dict) else "Unknown"
                grade_info = rep.get("grade_synthesis", {}) if isinstance(rep.get("grade_synthesis"), dict) else {}
                concept_pair = grade_info.get("concept_pair", f"claim_{idx}")
                evidence = rep.get("evidence_quote", "")
                paper_title = rep.get("paper_title", "")
                authors = rep.get("authors", "")
                publish_year = rep.get("publish_year", "")
                doi = rep.get("doi", "")
            else:
                status = rep.gating_status.value if hasattr(rep.gating_status, "value") else str(rep.gating_status)
                final_score = float(rep.final_score)
                claim_summary = rep.claim_summary
                study_design = rep.study_design.design_type.value if hasattr(rep.study_design.design_type, "value") else str(rep.study_design.design_type)
                grade_syn = getattr(rep, "grade_synthesis", None)
                concept_pair = grade_syn.concept_pair if (grade_syn and hasattr(grade_syn, "concept_pair")) else f"claim_{idx}"
                evidence = getattr(rep, "evidence_quote", "")
                paper_title = getattr(rep, "paper_title", "")
                authors = getattr(rep, "authors", "")
                publish_year = getattr(rep, "publish_year", "")
                doi = getattr(rep, "doi", "") or ""

            # STRICT GATING: Keep ONLY passed relationships (ACCEPTED or PROVISIONALLY_SUPPORTED) with score >= 70.0
            if status not in ["ACCEPTED", "PROVISIONALLY_SUPPORTED"] or final_score < 70.0:
                continue

            clean_text = f"Clinical Causal Rule: {claim_summary}."
            if evidence:
                clean_text += f" Evidence: {evidence}"

            text_lower = (claim_summary + " " + evidence).lower()
            is_smoker_relevant = any(w in text_lower for w in ["smok", "nicotine", "tobacco", "cigarette"])
            is_alcohol_relevant = any(w in text_lower for w in ["alcohol", "ethanol", "drink", "wine", "beer", "liquor"])

            if any(w in text_lower for w in ["heart", "pulse", "bpm", "cardio", "tachycardia", "autonomic", "sympathetic"]):
                metric_type = "heart_rate"
            elif any(w in text_lower for w in ["sleep", "rem", "nocturnal", "polysomnography", "slow-wave", "insomnia"]):
                metric_type = "sleep"
            elif any(w in text_lower for w in ["step", "walk", "exercise", "physical activity", "cadence", "sedentary"]):
                metric_type = "step_volume"
            else:
                metric_type = "metabolic_general"

            risk_level = "warning" if any(w in text_lower for w in ["elevat", "risk", "hazard", "impair", "hypertension", "dysfunction"]) else "protective"

            rel_id = f"rel_{idx}_{concept_pair[:32]}"
            passed_ids.append(rel_id)
            passed_docs.append(clean_text)
            passed_metas.append({
                "rule_id": rel_id,
                "claim_summary": claim_summary,
                "gating_status": status,
                "final_score": final_score,
                "study_design": study_design,
                "metric_type": metric_type,
                "smoking_relevant": is_smoker_relevant,
                "alcohol_relevant": is_alcohol_relevant,
                "risk_level": risk_level,
                "paper_title": paper_title,
                "authors": authors,
                "publish_year": str(publish_year),
                "doi": str(doi)
            })

        if not passed_ids:
            return 0

        return self.add_documents(
            collection_name=COLLECTION_VERIFIED_RELATIONSHIPS,
            ids=passed_ids,
            documents=passed_docs,
            metadatas=passed_metas
        )

    def query_verified_relationships(
        self,
        query_text: str,
        n_results: int = 4,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResultItem]:
        """Query passed clinical causal relationships with sub-population metadata filters."""
        return self.query(
            collection_name=COLLECTION_VERIFIED_RELATIONSHIPS,
            query_text=query_text,
            n_results=n_results,
            where=where
        )

    def sync_verified_relationships_cache(self, cache_path: Optional[Path] = None) -> int:
        """Scan data/health_relationships_verified.json and index all passed rules into vector DB."""
        target_path = cache_path or DEFAULT_VERIFIED_CACHE
        if not target_path.exists():
            return 0

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return self.add_verified_relationships(data)
        except Exception as e:
            logger.warning(f"Error syncing verified relationships to vector store: {e}")
        return 0

    def query_all(self, query_text: str, n_results_per_collection: int = 3) -> Dict[str, List[SearchResultItem]]:
        """Query both research papers and FSSAI standards."""
        return {
            COLLECTION_RESEARCH: self.query(COLLECTION_RESEARCH, query_text, n_results=n_results_per_collection),
            COLLECTION_FSSAI: self.query(COLLECTION_FSSAI, query_text, n_results=n_results_per_collection),
        }

    def count(self) -> Dict[str, int]:
        """Return counts of items in each collection."""
        return {
            COLLECTION_RESEARCH: self.research_collection.count(),
            COLLECTION_FSSAI: self.fssai_collection.count(),
            COLLECTION_VERIFIED_RELATIONSHIPS: self.verified_collection.count(),
        }
