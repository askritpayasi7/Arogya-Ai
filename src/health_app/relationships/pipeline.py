import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from health_app.config import settings
from health_app.ingestion.chunker import TextChunker
from health_app.ingestion.loader import DocumentLoader
from health_app.relationships.models import (
    ChunkExtractionResult,
    HealthRelationship,
    PaperExtractionReport,
)
from health_app.relationships.extractor import GeminiRelationshipExtractor
from health_app.relationships.printer import print_chunk_relationships
from health_app.verification import (
    classify_study_design,
    assess_risk_of_bias,
    verify_textual_nli,
    validate_statistics,
    synthesize_group_evidence,
    get_synthesis_for_relationship,
    CompositeScoringEngine,
    print_verification_report,
    print_article_credibility_card,
    VerificationReport,
)

logger = logging.getLogger(__name__)

DEFAULT_RELATIONSHIPS_CACHE = Path("./data/health_relationships.json")
DEFAULT_VERIFIED_CACHE = Path("./data/health_relationships_verified.json")

class RelationshipPipeline:
    """Orchestrates document chunking, Gemini relationship extraction, and terminal display."""

    def __init__(
        self,
        extractor: Optional[GeminiRelationshipExtractor] = None,
        chunk_size: int = 450,
        chunk_overlap: int = 70,
    ):
        self.extractor = extractor or GeminiRelationshipExtractor()
        self.chunker = TextChunker(target_chunk_size=chunk_size, overlap_size=chunk_overlap)

    def process_text_stream(
        self,
        text: str,
        title: str,
        authors: str = "Unknown",
        year: str = "Unknown",
        doi: Optional[str] = None,
        paper_id: str = "paper",
        print_to_terminal: bool = True,
        verify_relationships: bool = True,
    ) -> Iterator[Dict[str, Any]]:
        """Process text chunk-by-chunk, yielding real-time progress events."""
        yield {
            "type": "chunking_start",
            "paper_id": paper_id,
            "title": title,
            "message": f"Segmenting manuscript into semantic chunks..."
        }

        chunks = self.chunker.chunk_text(
            text=text,
            base_id=paper_id,
            base_metadata={"title": title, "authors": authors, "year": year, "doi": doi}
        )

        total_chunks = len(chunks)
        chunk_results: List[ChunkExtractionResult] = []
        all_relationships: List[HealthRelationship] = []

        yield {
            "type": "chunking_complete",
            "total_chunks": total_chunks,
            "message": f"Manuscript segmented into {total_chunks} chunk(s)."
        }

        if print_to_terminal:
            status_desc = "Gemini AI" if self.extractor.is_live else "Fallback Pattern Parser (Set GEMINI_API_KEY in .env for live AI)"
            print(f"\n[+] Extracting health relationships from {total_chunks} chunk(s) using {status_desc}...")

        for idx, chunk in enumerate(chunks):
            yield {
                "type": "chunk_extracting",
                "chunk_index": idx + 1,
                "total_chunks": total_chunks,
                "message": f"Chunk {idx+1}/{total_chunks}: extracting causal mechanisms via Gemini AI..."
            }

            relationships = self.extractor.extract_from_chunk(
                chunk_text=chunk.text,
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                chunk_index=idx
            )

            result = ChunkExtractionResult(
                chunk_index=idx,
                chunk_text=chunk.text,
                relationships=relationships
            )
            chunk_results.append(result)
            all_relationships.extend(relationships)

            yield {
                "type": "chunk_extracted",
                "chunk_index": idx + 1,
                "total_chunks": total_chunks,
                "relationships_count": len(relationships),
                "total_relationships_so_far": len(all_relationships),
                "message": f"Chunk {idx+1}/{total_chunks}: extracted {len(relationships)} causal claim(s)."
            }

            if print_to_terminal:
                print_chunk_relationships(
                    result=result,
                    title=title,
                    authors=authors,
                    year=year,
                    total_chunks=total_chunks
                )

        # 4-Phase Clinical Verification & Anti-Hallucination Framework
        verified_reports: List[VerificationReport] = []

        yield {
            "type": "audit_article_start",
            "message": "Step 1/4: Classifying study design and auditing methodological risk of bias..."
        }

        if print_to_terminal:
            print("\n" + "=" * 78)
            print(" [4-PHASE CLINICAL VERIFICATION & ANTI-HALLUCINATION AUDIT]")
            print(" Evaluating methodological credibility and scientific evidence...")
            print("=" * 78, flush=True)
            print("[*] [Step 1/6] Classifying study design and methodological hierarchy...", flush=True)

        study_design = classify_study_design(text, title=title)

        if print_to_terminal:
            print(f"    -> Result: {study_design.design_type.value} (Evidential Weight: {study_design.weight:.2f})", flush=True)
            print(f"[*] [Step 2/6] Auditing methodological risk of bias ({study_design.design_type.value})...", flush=True)

        risk_of_bias = assess_risk_of_bias(text, study_design)

        if print_to_terminal:
            print(f"    -> Framework: {risk_of_bias.framework} | Level: {risk_of_bias.level.value} (Penalty: {risk_of_bias.penalty_points} pts)", flush=True)
            print_article_credibility_card(
                study_design=study_design,
                risk_of_bias=risk_of_bias,
                title=title,
                authors=authors,
                year=year
            )

        yield {
            "type": "article_audit",
            "study_design": study_design.design_type.value,
            "risk_of_bias": risk_of_bias.level.value,
            "weight": study_design.weight,
            "penalty": risk_of_bias.penalty_points,
            "message": f"Article Audit: {study_design.design_type.value} | RoB: {risk_of_bias.level.value}"
        }

        if all_relationships and verify_relationships:
            yield {
                "type": "verification_start",
                "total_claims": len(all_relationships),
                "message": f"Starting claim verification on {len(all_relationships)} extracted claim(s)..."
            }

            synthesis_map = synthesize_group_evidence(all_relationships)
            chunk_text_map = {res.chunk_index: res.chunk_text for res in chunk_results}

            if print_to_terminal:
                print(f"[*] Auditing {len(all_relationships)} extracted relationship claim(s)...", flush=True)

            # Phase 2 & 4: Claim-level NLI, Statistical Checks, Composite Scoring & Gating
            for rel_idx, rel in enumerate(all_relationships, 1):
                premise = rel.evidence_quote
                hypothesis = rel.to_claim_sentence()
                parent_chunk = chunk_text_map.get(rel.chunk_index, text)

                yield {
                    "type": "claim_auditing",
                    "claim_index": rel_idx,
                    "total_claims": len(all_relationships),
                    "subject": rel.subject,
                    "relation": rel.relation,
                    "object": rel.object,
                    "message": f"Auditing claim {rel_idx}/{len(all_relationships)}: {rel.subject} -> {rel.object}..."
                }

                if print_to_terminal:
                    print(f"\n[*] [Step 3/6] Running Textual NLI Verification on claim #{rel_idx}...", flush=True)
                    print(f"    Premise:    \"{premise[:90]}...\"", flush=True)
                    print(f"    Hypothesis: \"{hypothesis[:90]}\"", flush=True)

                # Phase 2: Claim-level checks
                nli_result = verify_textual_nli(premise=premise, hypothesis=hypothesis)

                if print_to_terminal:
                    print(f"    -> NLI Verdict: {nli_result.status.value} (Score: {nli_result.score:.2f} via {nli_result.model_used})", flush=True)
                    print("[*] [Step 4/6] Validating statistical estimates and directional alignment...", flush=True)

                stat_result = validate_statistics(
                    claim_direction=rel.relation,
                    chunk_text=parent_chunk,
                    quote=premise
                )

                if print_to_terminal:
                    stat_status = "PASS" if (not stat_result.null_crossing and stat_result.directional_consistent) else "FLAGGED"
                    print(f"    -> Statistical Check: {stat_status} (Null Crossing: {'YES' if stat_result.null_crossing else 'NO'}, Direction: {'CONSISTENT' if stat_result.directional_consistent else 'CONFLICT'})", flush=True)
                    print("[*] [Step 5/6] Performing cross-study GRADE evidence synthesis...", flush=True)

                # Phase 3: GRADE mapping
                grade_res = get_synthesis_for_relationship(rel, synthesis_map)

                if print_to_terminal:
                    print(f"    -> Synthesis: {grade_res.consistency_level} ({grade_res.rationale})", flush=True)
                    print("[*] [Step 6/6] Computing non-linear composite score & executing automated safety gates...", flush=True)

                # Phase 4: Non-linear composite scoring and automated gating
                ver_report = CompositeScoringEngine.evaluate(
                    relationship=rel,
                    study_design=study_design,
                    risk_of_bias=risk_of_bias,
                    nli_result=nli_result,
                    statistical_check=stat_result,
                    grade_synthesis=grade_res
                )
                verified_reports.append(ver_report)

                gating_val = ver_report.gating_status.value if hasattr(ver_report.gating_status, "value") else str(ver_report.gating_status)
                study_val = ver_report.study_design.design_type.value if ver_report.study_design else "Observational"
                rob_val = ver_report.risk_of_bias.level.value if ver_report.risk_of_bias else "LOW"

                yield {
                    "type": "claim_verified",
                    "claim_index": rel_idx,
                    "total_claims": len(all_relationships),
                    "claim": {
                        "paper_title": title,
                        "authors": authors,
                        "year": year,
                        "doi": doi,
                        "claim_summary": ver_report.claim_summary,
                        "subject": rel.subject,
                        "relation": rel.relation,
                        "object": rel.object,
                        "study_design": study_val,
                        "risk_of_bias": rob_val,
                        "nli_status": ver_report.nli_result.status.value if ver_report.nli_result else "PASS",
                        "composite_score": ver_report.final_score,
                        "gating_status": gating_val,
                        "evidence_quote": rel.evidence_quote
                    },
                    "message": f"Claim #{rel_idx} verified: Score {ver_report.final_score}/100 [{gating_val}]"
                }

                if print_to_terminal:
                    print(f"    -> Base: {ver_report.base_score} | Penalty: {ver_report.penalty_points} | Final Score: {ver_report.final_score}/100 | Gating: {ver_report.gating_status.value}", flush=True)
                    print_verification_report(ver_report)

            self._save_verified_cache(verified_reports)
        elif not all_relationships and print_to_terminal:
            print(f"\n[i] No direct causal/clinical relationships were detected in this document's text.", flush=True)
            print(f"[+] Article-Level Credibility and Study Design was successfully verified above.\n", flush=True)

        report = PaperExtractionReport(
            paper_id=paper_id,
            title=title,
            authors=authors,
            publish_year=year,
            doi=doi,
            total_chunks=total_chunks,
            total_relationships=len(all_relationships),
            chunk_results=chunk_results,
            verified_reports=verified_reports
        )

        self._save_to_cache(all_relationships)
        yield {
            "type": "report_complete",
            "report": report,
            "verified_reports": verified_reports,
            "message": f"Processed paper '{title[:45]}...': {len(verified_reports)} claim(s) audited."
        }

    def process_text(
        self,
        text: str,
        title: str,
        authors: str = "Unknown",
        year: str = "Unknown",
        doi: Optional[str] = None,
        paper_id: str = "paper",
        print_to_terminal: bool = True,
        verify_relationships: bool = True,
    ) -> PaperExtractionReport:
        """Process raw text, extract relationships chunk-by-chunk, verify, and print to terminal."""
        final_report = None
        for event in self.process_text_stream(
            text=text,
            title=title,
            authors=authors,
            year=year,
            doi=doi,
            paper_id=paper_id,
            print_to_terminal=print_to_terminal,
            verify_relationships=verify_relationships,
        ):
            if event.get("type") == "report_complete":
                final_report = event["report"]
        return final_report

    def process_paper_stream(self, file_path: Path, print_to_terminal: bool = False) -> Iterator[Dict[str, Any]]:
        """Load and extract relationships from a PDF or Markdown paper file, yielding progress events."""
        yield {
            "type": "loading_file",
            "file": file_path.name,
            "message": f"Loading manuscript from disk: {file_path.name}..."
        }

        # Prioritize full PDF if available (contains complete manuscript across all pages)
        pdf_candidate = file_path if file_path.suffix.lower() == ".pdf" else file_path.with_suffix(".pdf")
        md_companion = file_path if file_path.suffix.lower() in [".md", ".txt"] else file_path.with_suffix(".md")

        doc = None
        # 1. Try loading full PDF
        if pdf_candidate.exists():
            doc = DocumentLoader.load_file(pdf_candidate, doc_type="research_paper")

        # 2. If PDF missing or returned empty text, fall back to companion markdown
        if (not doc or not doc.raw_text.strip()) and md_companion.exists():
            doc = DocumentLoader.load_file(md_companion, doc_type="research_paper")

        if not doc:
            logger.warning(f"Could not load paper: {file_path}")
            yield {
                "type": "report_complete",
                "report": None,
                "verified_reports": [],
                "message": f"Failed to load manuscript file {file_path.name}"
            }
            return

        title = doc.metadata.get("title", doc.title)
        authors = doc.metadata.get("authors", "Unknown")
        year = doc.metadata.get("year", "Unknown")
        doi = doc.metadata.get("doi")

        # Enrich metadata from companion markdown if available (it has exact structured headers)
        if md_companion.exists():
            md_doc = DocumentLoader.load_file(md_companion, doc_type="research_paper")
            if md_doc and md_doc.metadata:
                if md_doc.metadata.get("title") and ("_" in doc.title or len(doc.title) < 15):
                    title = md_doc.metadata["title"]
                if md_doc.metadata.get("authors") and authors == "Unknown":
                    authors = md_doc.metadata["authors"]
                if md_doc.metadata.get("year") and year == "Unknown":
                    year = md_doc.metadata["year"]
                if md_doc.metadata.get("doi") and not doi:
                    doi = md_doc.metadata["doi"]

        for event in self.process_text_stream(
            text=doc.raw_text,
            title=title,
            authors=authors,
            year=year,
            doi=doi,
            paper_id=doc.doc_id,
            print_to_terminal=print_to_terminal,
            verify_relationships=True
        ):
            yield event

    def process_paper_file(self, file_path: Path, print_to_terminal: bool = True) -> Optional[PaperExtractionReport]:
        """Load and extract relationships from a PDF or Markdown paper file (prioritizes full PDF)."""
        report = None
        for event in self.process_paper_stream(file_path, print_to_terminal=print_to_terminal):
            if event.get("type") == "report_complete":
                report = event["report"]
        return report

    def process_all_downloaded_papers(self, print_to_terminal: bool = True) -> List[PaperExtractionReport]:
        """Process all papers currently stored in data/research_papers/."""
        papers_dir = settings.research_papers_dir
        if not papers_dir.exists():
            print("[-] No research papers directory found.")
            return []

        # Find unique base names (avoid processing both .pdf and .md of the same paper twice)
        seen_stems = set()
        reports: List[PaperExtractionReport] = []

        files = sorted(list(papers_dir.glob("*.pdf")) + list(papers_dir.glob("*.md")))
        for f in files:
            if f.stem in seen_stems:
                continue
            seen_stems.add(f.stem)

            print(f"\n============================================================================")
            print(f" PROCESSING RESEARCH PAPER: {f.name}")
            print(f"============================================================================")
            report = self.process_paper_file(f, print_to_terminal=print_to_terminal)
            if report:
                reports.append(report)

        return reports

    def _save_to_cache(self, relationships: List[HealthRelationship]) -> None:
        """Persist extracted relationships to data/health_relationships.json."""
        if not relationships:
            return

        DEFAULT_RELATIONSHIPS_CACHE.parent.mkdir(parents=True, exist_ok=True)
        existing_items = []

        if DEFAULT_RELATIONSHIPS_CACHE.exists():
            try:
                with open(DEFAULT_RELATIONSHIPS_CACHE, "r", encoding="utf-8") as f:
                    existing_items = json.load(f)
            except Exception:
                existing_items = []

        # Append new unique relationships (deduplicate by subject + relation + object)
        seen_keys = {
            (r.get("subject"), r.get("relation"), r.get("object"))
            for r in existing_items
        }

        for rel in relationships:
            key = (rel.subject, rel.relation, rel.object)
            if key not in seen_keys:
                existing_items.append(rel.model_dump())
                seen_keys.add(key)

        try:
            with open(DEFAULT_RELATIONSHIPS_CACHE, "w", encoding="utf-8") as f:
                json.dump(existing_items, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.debug(f"Failed to cache relationships: {e}")

    def _save_verified_cache(self, reports: List[VerificationReport]) -> None:
        """Persist clinical verification reports to data/health_relationships_verified.json."""
        if not reports:
            return

        DEFAULT_VERIFIED_CACHE.parent.mkdir(parents=True, exist_ok=True)
        existing_items = []

        if DEFAULT_VERIFIED_CACHE.exists():
            try:
                with open(DEFAULT_VERIFIED_CACHE, "r", encoding="utf-8") as f:
                    existing_items = json.load(f)
            except Exception:
                existing_items = []

        seen_claims = {item.get("claim_summary") for item in existing_items}

        for rep in reports:
            if rep.claim_summary not in seen_claims:
                existing_items.append(rep.model_dump())
                seen_claims.add(rep.claim_summary)

        try:
            with open(DEFAULT_VERIFIED_CACHE, "w", encoding="utf-8") as f:
                json.dump(existing_items, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.debug(f"Failed to cache verified relationships: {e}")

        # Sync passed relationships directly to ChromaDB verified_relationships collection
        try:
            from health_app.vectordb.store import VectorStore
            vs = VectorStore()
            vs.add_verified_relationships(reports)
        except Exception as e:
            logger.debug(f"Vector store passed relationship indexing note: {e}")

