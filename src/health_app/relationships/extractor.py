import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from health_app.config import settings
from health_app.relationships.models import HealthRelationship

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = (
    "You are an expert biomedical and clinical relationship extraction system for an evidence-grounded health app. "
    "Your mission is to extract verifiable, scientific cause-and-effect or correlational relationships established in the text. "
    "Rules:\n"
    "1. Strict Grounding: Only extract relationships directly stated or measured in the text. Do NOT hallucinate or extrapolate.\n"
    "2. Schema: Each relationship must specify subject (biomarker/exposure/behavior), relation (directional verb/effect), "
    "object (clinical outcome/physiological marker), optional condition (population/context), exact evidence_quote, and confidence.\n"
    "3. Format: Return ONLY valid JSON adhering to the specified schema."
)

EXTRACTION_PROMPT_TEMPLATE = """Research Paper: {title}
Authors: {authors} ({year})

Text Chunk to Analyze:
\"\"\"{chunk_text}\"\"\"

Extract all verifiable health/physiological relationships from this chunk as a JSON object with a "relationships" array:
{{
  "relationships": [
    {{
      "subject": "e.g. Lower stage N3 sleep combined with elevated apnea-hypopnea index",
      "relation": "e.g. indicates increased risk of / positively correlates with / impairs",
      "object": "e.g. cardiac autonomic dysfunction and orthostatic blood pressure drops",
      "condition": "e.g. in patients with alpha-synucleinopathies / general adult cohort",
      "evidence_quote": "exact sentence or phrase from the chunk",
      "confidence": "High"
    }}
  ]
}}
If no explicit relationships or findings are established in this chunk, return {{"relationships": []}}.
"""

_DEFAULT_KEY = object()

class GeminiRelationshipExtractor:
    """Extracts factual clinical and health relationships from text chunks using Gemini API."""

    def __init__(self, api_key: Any = _DEFAULT_KEY, model: Optional[str] = None):
        if api_key is _DEFAULT_KEY:
            self.api_key = settings.gemini_api_key or os.environ.get("GEMINI_API_KEY")
        else:
            self.api_key = api_key
        self.model = model or settings.gemini_model
        self._client = None

        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")

    @property
    def is_live(self) -> bool:
        """Check if live Gemini API is configured."""
        return self._client is not None

    def extract_from_chunk(
        self,
        chunk_text: str,
        title: str,
        authors: str,
        year: str,
        doi: Optional[str] = None,
        chunk_index: int = 0
    ) -> List[HealthRelationship]:
        """Extract relationships from a chunk of scientific text."""
        if not chunk_text or len(chunk_text.strip()) < 40:
            return []

        if self.is_live:
            return self._extract_with_gemini(chunk_text, title, authors, year, doi, chunk_index)
        else:
            return self._extract_with_fallback(chunk_text, title, authors, year, doi, chunk_index)

    def _extract_with_gemini(
        self,
        chunk_text: str,
        title: str,
        authors: str,
        year: str,
        doi: Optional[str],
        chunk_index: int
    ) -> List[HealthRelationship]:
        """Call Gemini API with structured prompt."""
        prompt = EXTRACTION_PROMPT_TEMPLATE.format(
            title=title,
            authors=authors,
            year=year,
            chunk_text=chunk_text
        )

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    "system_instruction": SYSTEM_INSTRUCTION,
                    "response_mime_type": "application/json",
                    "temperature": 0.1,  # Low temperature for deterministic, factual extraction
                }
            )

            text_output = response.text
            data = json.loads(text_output)
            raw_relationships = data.get("relationships", [])

            results: List[HealthRelationship] = []
            for item in raw_relationships:
                rel = HealthRelationship(
                    subject=item.get("subject", "Unspecified entity"),
                    relation=item.get("relation", "correlates with"),
                    object=item.get("object", "Unspecified outcome"),
                    condition=item.get("condition"),
                    evidence_quote=item.get("evidence_quote", chunk_text[:120]),
                    confidence=item.get("confidence", "High"),
                    paper_title=title,
                    authors=authors,
                    publish_year=year,
                    doi=doi,
                    chunk_index=chunk_index
                )
                results.append(rel)

            return results

        except Exception as e:
            logger.warning(f"Gemini API extraction failed ({e}), using fallback parser.")
            return self._extract_with_fallback(chunk_text, title, authors, year, doi, chunk_index)

    def _extract_with_fallback(
        self,
        chunk_text: str,
        title: str,
        authors: str,
        year: str,
        doi: Optional[str],
        chunk_index: int
    ) -> List[HealthRelationship]:
        """Rule-based relationship extraction fallback for offline / mock / testing modes."""
        results: List[HealthRelationship] = []
        sentences = re.split(r'(?<=[.!?])\s+', chunk_text.strip())

        relation_patterns = [
            (r'(.+?)\s+(?:increases?|elevates?|raises?)\s+(?:the\s+)?risk\s+of\s+(.+)', 'increases risk of'),
            (r'(.+?)\s+(?:is|are|was|were)\s+associated\s+with\s+(.+)', 'is associated with'),
            (r'(.+?)\s+(?:correlates?|correlated)\s+with\s+(.+)', 'correlates with'),
            (r'(.+?)\s+(?:demonstrated|showed|revealed)\s+(.+)', 'demonstrated effect on'),
            (r'(.+?)\s+(?:reduces?|decreases?|lowers?|mitigates?)\s+(.+)', 'reduces / mitigates'),
            (r'(.+?)\s+(?:impairs?|disrupts?|disturbs?)\s+(.+)', 'impairs / disrupts'),
            (r'(.+?)\s+(?:leads?\s+to|causes?|results?\s+in)\s+(.+)', 'leads to / causes'),
            (r'(.+?)\s+(?:suggests?|indicated?|implied?)\s+that\s+(.+)', 'indicates'),
            (r'(.+?)\s+(?:found\s+that|observed\s+that)\s+(.+)', 'observed effect on'),
            (r'(.+?)\s+(?:plays?\s+a\s+role\s+in|contributes?\s+to)\s+(.+)', 'contributes to'),
            (r'(.+?)\s+(?:protects?\s+against|prevents?)\s+(.+)', 'protects against'),
            (r'(.+?)\s+(?:worsens?|aggravates?|exacerbates?)\s+(.+)', 'exacerbates'),
            (r'(.+?)\s+(?:regulates?|modulates?|controls?)\s+(.+)', 'modulates / regulates'),
        ]

        noise_patterns = [
            r'\bcenters for disease control\b',
            r'\bworld health organization\b',
            r'\bdepartment of\b',
            r'\buniversity of\b',
            r'\bsearch strings?\b',
            r'\brecords were exported\b',
            r'\bmain-search\b',
            r'\bscopus search\b',
            r'\bpubmed search\b',
            r'\bcochrane library\b',
            r'\bstrategy was rerun\b',
            r'\boverlapping searches\b',
            r'\byielded \d+ results\b',
        ]

        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) < 30:
                continue

            if any(re.search(pat, s_clean, re.IGNORECASE) for pat in noise_patterns):
                continue

            for pattern, rel_verb in relation_patterns:
                match = re.search(pattern, s_clean, re.IGNORECASE)
                if match:
                    subject = match.group(1).strip()
                    obj = match.group(2).strip().rstrip(".")
                    # Clean leading conjunctions/headers
                    subject = re.sub(r'^(?:Moreover|Furthermore|In addition|However|Results|Conclusions)[:,\s]+', '', subject, flags=re.IGNORECASE)
                    if len(subject) > 5 and len(obj) > 5 and len(subject) < 140 and len(obj) < 140:
                        # Require at least two meaningful words in both subject and object to avoid institutional titles
                        if len(re.findall(r'[a-zA-Z]{3,}', subject)) < 2 or len(re.findall(r'[a-zA-Z]{3,}', obj)) < 2:
                            continue

                        results.append(
                            HealthRelationship(
                                subject=subject,
                                relation=rel_verb,
                                object=obj,
                                condition="Observed in study findings",
                                evidence_quote=s_clean,
                                confidence="High (Rule-based Fallback)",
                                paper_title=title,
                                authors=authors,
                                publish_year=year,
                                doi=doi,
                                chunk_index=chunk_index
                            )
                        )
                        break  # Match at most one relationship per sentence

        return results
