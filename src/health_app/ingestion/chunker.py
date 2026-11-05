import re
from typing import Any, Dict, List
from pydantic import BaseModel, Field

class DocumentChunk(BaseModel):
    """A semantic chunk of text with associated citation metadata."""
    chunk_id: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TextChunker:
    """Splits documents into overlapping chunks while preserving paragraph and sentence boundaries."""

    def __init__(self, target_chunk_size: int = 500, overlap_size: int = 100):
        self.target_chunk_size = target_chunk_size
        self.overlap_size = overlap_size

    def chunk_text(
        self,
        text: str,
        base_id: str,
        base_metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """Split text into chunks with context metadata attached."""
        cleaned_text = text.strip()
        if not cleaned_text:
            return []

        # Split on markdown headers or double newlines (paragraphs)
        paragraphs = re.split(r'\n{2,}', cleaned_text)
        chunks: List[DocumentChunk] = []

        current_segment = ""
        current_section = base_metadata.get("title", "General")
        chunk_index = 0

        for para in paragraphs:
            para_clean = para.strip()
            if not para_clean:
                continue

            # Check if this paragraph is a section header (e.g. ## Header)
            header_match = re.match(r'^(#{1,6})\s+(.+)$', para_clean)
            if header_match:
                current_section = header_match.group(2).strip()

            # If adding this paragraph exceeds target size and current_segment is non-empty, flush it
            if len(current_segment) + len(para_clean) > self.target_chunk_size and current_segment:
                chunk_meta = dict(base_metadata)
                chunk_meta["section"] = current_section
                chunk_meta["chunk_index"] = chunk_index
                
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{base_id}_chunk_{chunk_index}",
                        text=current_segment.strip(),
                        metadata=chunk_meta
                    )
                )
                chunk_index += 1

                # Keep overlap from tail of current_segment
                words = current_segment.split()
                overlap_words = words[-max(1, self.overlap_size // 6):] if len(words) > 10 else []
                current_segment = (" ".join(overlap_words) + " " + para_clean).strip()
            else:
                if current_segment:
                    current_segment += "\n\n" + para_clean
                else:
                    current_segment = para_clean

        # Flush final remaining segment
        if current_segment.strip():
            chunk_meta = dict(base_metadata)
            chunk_meta["section"] = current_section
            chunk_meta["chunk_index"] = chunk_index
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{base_id}_chunk_{chunk_index}",
                    text=current_segment.strip(),
                    metadata=chunk_meta
                )
            )

        return chunks
