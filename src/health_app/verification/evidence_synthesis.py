import re
from typing import Dict, List, Optional
from health_app.relationships.models import HealthRelationship
from health_app.verification.models import GRADEEvidenceSynthesis

def extract_concept_key(rel: HealthRelationship) -> str:
    """Normalize subject and object into a canonical concept pair key."""
    s = re.sub(r'[^a-zA-Z]', '', rel.subject.lower())[:15]
    o = re.sub(r'[^a-zA-Z]', '', rel.object.lower())[:15]
    return f"{s}__to__{o}"


def _is_direction_increase(relation: str) -> bool:
    r = relation.lower()
    if any(neg in r for neg in ["reduc", "decreas", "lower", "mitigat", "prevent", "protect", "inhibit"]):
        return False
    return any(pos in r for pos in ["increas", "elevat", "worsen", "harm", "heighten", "promote", "induc", "cause", "lead to"])


def _is_direction_decrease(relation: str) -> bool:
    r = relation.lower()
    return any(neg in r for neg in ["reduc", "decreas", "lower", "mitigat", "prevent", "protect", "inhibit"])


def synthesize_group_evidence(relationships: List[HealthRelationship]) -> Dict[str, GRADEEvidenceSynthesis]:
    """
    Groups relationships by biological concept pairs and evaluates cross-study
    consistency using adapted GRADE framework principles.
    """
    grouped: Dict[str, List[HealthRelationship]] = {}
    for rel in relationships:
        key = extract_concept_key(rel)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(rel)

    synthesis_map: Dict[str, GRADEEvidenceSynthesis] = {}

    for key, items in grouped.items():
        distinct_papers = {r.paper_title for r in items}
        study_count = len(distinct_papers)

        if study_count <= 1:
            synthesis_map[key] = GRADEEvidenceSynthesis(
                concept_pair=key,
                studies_count=1,
                consistency_level="PRELIMINARY_SINGLE_STUDY",
                penalty_points=0.0,
                rationale="Single study finding; cross-study replication not yet established."
            )
            continue

        # Check directional agreement across multiple studies
        increase_count = sum(1 for r in items if _is_direction_increase(r.relation))
        decrease_count = sum(1 for r in items if _is_direction_decrease(r.relation))

        if increase_count > 0 and decrease_count > 0:
            synthesis_map[key] = GRADEEvidenceSynthesis(
                concept_pair=key,
                studies_count=study_count,
                consistency_level="INCONSISTENT",
                penalty_points=20.0,
                rationale=f"Directional conflict across {study_count} studies ({increase_count} positive vs {decrease_count} negative effects)."
            )
        elif study_count >= 3:
            synthesis_map[key] = GRADEEvidenceSynthesis(
                concept_pair=key,
                studies_count=study_count,
                consistency_level="HIGH",
                penalty_points=0.0,
                rationale=f"High consistency across {study_count} independent research studies."
            )
        else:
            synthesis_map[key] = GRADEEvidenceSynthesis(
                concept_pair=key,
                studies_count=study_count,
                consistency_level="MODERATE",
                penalty_points=0.0,
                rationale=f"Consistent findings across {study_count} research studies."
            )

    return synthesis_map


def get_synthesis_for_relationship(
    rel: HealthRelationship,
    synthesis_map: Optional[Dict[str, GRADEEvidenceSynthesis]] = None,
) -> GRADEEvidenceSynthesis:
    """Retrieve the GRADE evidence synthesis for a specific relationship."""
    key = extract_concept_key(rel)
    if synthesis_map and key in synthesis_map:
        return synthesis_map[key]
    return GRADEEvidenceSynthesis(
        concept_pair=key,
        studies_count=1,
        consistency_level="PRELIMINARY_SINGLE_STUDY",
        penalty_points=0.0,
        rationale="Single study finding; baseline evidence level."
    )

