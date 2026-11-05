import textwrap
from typing import List
from health_app.relationships.models import ChunkExtractionResult, HealthRelationship

def print_chunk_relationships(result: ChunkExtractionResult, title: str, authors: str, year: str, total_chunks: int) -> None:
    """Pretty-print extracted relationships for a specific chunk to the terminal."""
    print("\n" + "=" * 76)
    print(f" HEALTH RELATIONSHIPS: CHUNK [{result.chunk_index + 1} of {total_chunks}]")
    print("=" * 76)
    print(f" Paper:   {title}")
    print(f" Authors: {authors} ({year})")
    print("-" * 76)

    # Print chunk preview (first 180 chars)
    preview = result.chunk_text.strip().replace("\n", " ")
    if len(preview) > 180:
        preview = preview[:180] + "..."
    print(f" [CHUNK PREVIEW]:\n  \"{preview}\"")
    print("-" * 76)

    if not result.relationships:
        print("  [No direct health/clinical relationships detected in this chunk]")
    else:
        for idx, rel in enumerate(result.relationships, 1):
            print(f"  * RELATIONSHIP #{idx}:")
            print(f"    - [Subject]    : {rel.subject}")
            print(f"    - [Relation]   : --> {rel.relation} -->")
            print(f"    - [Object]     : {rel.object}")
            if rel.condition:
                print(f"    - [Context]    : {rel.condition}")
            
            wrapped_quote = "\n      ".join(textwrap.wrap(f'"{rel.evidence_quote}"', width=68))
            print(f"    - [Evidence]   : {wrapped_quote}")
            print(f"    - [Confidence] : {rel.confidence}")
            print()

    print("=" * 76)
