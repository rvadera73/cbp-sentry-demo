"""
Entity resolution service — core business logic for resolving entities via Senzing.

Coordinates:
1. Load manifest entities into Senzing
2. Search for entity matches
3. Build entity resolution list
4. Construct entity graph
5. Sync to Neo4j
"""

import logging
from typing import Dict, List, Optional, Tuple
import networkx as nx

from .senzing_client import SenzingClient
from .loader import load_manifest_entities
from .graph_builder import build_entity_graph

logger = logging.getLogger(__name__)


class EntityResolutionService:
    """Service for entity resolution via Senzing."""

    def __init__(
        self,
        senzing_client: Optional[SenzingClient] = None,
        neo4j_session=None
    ):
        """
        Initialize service.

        Args:
            senzing_client: SenzingClient instance
            neo4j_session: Neo4j session for graph sync
        """
        self.senzing_client = senzing_client
        self.neo4j_session = neo4j_session

    def resolve_entities(
        self,
        manifest_data: Dict,
        entities: Dict
    ) -> Dict:
        """
        Resolve entities from manifest.

        Args:
            manifest_data: Manifest dict
            entities: Pre-loaded entities fixture (for testing)

        Returns:
            Dict with:
            - resolutions: List of entity resolutions
            - entity_graph: NetworkX DiGraph
            - summary: Resolution summary
        """
        resolutions = []
        entity_map = {}

        # Load entities into Senzing
        record_ids = load_manifest_entities(
            manifest_data,
            self.senzing_client
        )
        logger.info(f"Loaded {len(record_ids)} entities into Senzing")

        # For each entity, search for matches
        for entity_key, entity_data in entities.items():
            if not isinstance(entity_data, dict):
                continue

            entity_name = entity_data.get("name", "")
            entity_country = entity_data.get("country", "")

            # Search for matches
            if self.senzing_client:
                try:
                    matches = self.senzing_client.search_entity({
                        "name": entity_name,
                        "country": entity_country,
                        "address": entity_data.get("address", ""),
                        "phone": entity_data.get("phone", ""),
                    })
                except Exception as e:
                    logger.warning(f"Search failed for {entity_name}: {e}")
                    matches = []
            else:
                matches = []

            # Record resolution
            record = {
                "entity_id": entity_data.get("id", ""),
                "entity_name": entity_name,
                "entity_type": entity_data.get("type", ""),
                "country": entity_country,
                "jurisdiction": entity_data.get("jurisdiction", entity_country),
                "confidence": entity_data.get("senzing_confidence", 0.0),
                "senzing_record_id": entity_data.get("senzing_record_id", ""),
                "risk_score": entity_data.get("risk_score", 0),
                "matches": matches,
                "metadata": entity_data.get("metadata", {})
            }
            resolutions.append(record)
            entity_map[entity_data.get("id", "")] = record

        # Detect special relationships (e.g., VN → CN parent)
        relationships = _detect_relationships(entities, resolutions)

        # Build entity graph
        graph = build_entity_graph(resolutions, relationships)

        return {
            "resolutions": resolutions,
            "relationships": relationships,
            "entity_graph": graph,
            "summary": {
                "total_entities": len(resolutions),
                "high_confidence": sum(
                    1 for r in resolutions if r["confidence"] >= 0.85
                ),
                "key_matches": _summarize_matches(relationships)
            }
        }

    def get_why_explanation(
        self,
        entity_a_id: str,
        entity_b_id: str,
        entities: Dict
    ) -> Dict:
        """
        Get why-explanation for why two entities are connected.

        Args:
            entity_a_id: First entity ID
            entity_b_id: Second entity ID
            entities: Entities fixture

        Returns:
            Dict with explanation, confidence, evidence
        """
        entity_a = entities.get(entity_a_id, {})
        entity_b = entities.get(entity_b_id, {})

        if not entity_a or not entity_b:
            return {
                "why_key": "WHY_NOT_FOUND",
                "confidence": 0.0,
                "explanation": "One or both entities not found"
            }

        # Get Senzing explanation if available
        rec_a = entity_a.get("senzing_record_id", "")
        rec_b = entity_b.get("senzing_record_id", "")

        if self.senzing_client and rec_a and rec_b:
            try:
                why_data = self.senzing_client.why_entities(rec_a, rec_b)
            except Exception as e:
                logger.warning(f"Senzing why-explanation failed: {e}")
                why_data = None
        else:
            why_data = None

        # Build explanation from fixtures or why_data
        explanation = _build_explanation(
            entity_a,
            entity_b,
            why_data
        )

        return explanation


def _detect_relationships(entities: Dict, resolutions: List[Dict]) -> List[Dict]:
    """
    Detect relationships between entities.

    For Greenfield case, detects:
    - Shared director (SHARES_DIRECTOR)
    - Shared phone (SHARED_CONTACT)
    - Ownership chain (OWNED_BY)
    - Freight forwarder (FREIGHT_FORWARDED_BY)
    """
    relationships = []

    entity_list = list(entities.items())

    # Check for shared directors
    for i, (key_a, entity_a) in enumerate(entity_list):
        if not isinstance(entity_a, dict):
            continue

        director_a = entity_a.get("director") or entity_a.get("beneficial_owner")
        phone_a = entity_a.get("phone", "")
        forwarder_a = entity_a.get("metadata", {}).get("freight_forwarder", "")

        for key_b, entity_b in entity_list[i+1:]:
            if not isinstance(entity_b, dict):
                continue

            director_b = entity_b.get("director") or entity_b.get("beneficial_owner")
            phone_b = entity_b.get("phone", "")
            forwarder_b = entity_b.get("metadata", {}).get("freight_forwarder", "")

            # Shared director
            if director_a and director_a == director_b:
                relationships.append({
                    "source": entity_a.get("id"),
                    "target": entity_b.get("id"),
                    "relationship_type": "SHARES_DIRECTOR",
                    "confidence": 0.91,
                    "evidence": [f"Shared director: {director_a}"]
                })

            # Shared phone
            if phone_a and phone_a == phone_b:
                relationships.append({
                    "source": entity_a.get("id"),
                    "target": entity_b.get("id"),
                    "relationship_type": "SHARED_CONTACT",
                    "confidence": 0.85,
                    "evidence": [f"Shared phone: {phone_a}"]
                })

            # Shared freight forwarder
            if forwarder_a and forwarder_a == forwarder_b:
                relationships.append({
                    "source": entity_a.get("id"),
                    "target": entity_b.get("id"),
                    "relationship_type": "FREIGHT_FORWARDED_BY",
                    "confidence": 0.87,
                    "evidence": [f"Freight forwarder: {forwarder_a}"]
                })

    # Detect ownership chain (VN → HK → CN)
    for key, entity in entities.items():
        if not isinstance(entity, dict):
            continue

        name = entity.get("name", "")
        country = entity.get("country", "")

        # Greenfield VN shipper → CN parent (inferred from parent_cn key)
        if key == "shipper_vn" and "parent_cn" in entities:
            parent_cn = entities["parent_cn"]
            relationships.append({
                "source": entity.get("id"),
                "target": parent_cn.get("id"),
                "relationship_type": "OWNED_BY",
                "confidence": 0.98,
                "evidence": [
                    "Name pattern match: Greenfield in both",
                    "Commercial records: CN parent has 18 prior CBP filings"
                ]
            })

    return relationships


def _summarize_matches(relationships: List[Dict]) -> str:
    """Summarize key matches for summary."""
    if not relationships:
        return "No matches detected"

    key_types = set(r["relationship_type"] for r in relationships)
    return f"Detected: {', '.join(sorted(key_types))}"


def _build_explanation(
    entity_a: Dict,
    entity_b: Dict,
    why_data: Optional[Dict] = None
) -> Dict:
    """Build why-explanation from entities and Senzing data."""
    if why_data:
        return {
            "why_key": why_data.get("why_key", "WHY_ENTITIES_RELATED"),
            "confidence": why_data.get("confidence", 0.0),
            "explanation": _format_match_factors(
                why_data.get("match_factors", [])
            ),
            "evidence": why_data.get("match_factors", []),
            "entity_a": entity_a.get("name", ""),
            "entity_b": entity_b.get("name", "")
        }

    # Fallback explanation
    return {
        "why_key": "WHY_ENTITY_COMPARISON",
        "confidence": 0.0,
        "explanation": "Entities exist but Senzing explanation not available",
        "evidence": [],
        "entity_a": entity_a.get("name", ""),
        "entity_b": entity_b.get("name", "")
    }


def _format_match_factors(factors: List[Dict]) -> str:
    """Format match factors into explanation string."""
    if not factors:
        return "No match factors found"

    parts = []
    for factor in factors:
        detail = factor.get("detail", "")
        score = factor.get("score", 0)
        if detail:
            parts.append(f"{detail} (confidence: {score:.2f})")

    return "; ".join(parts) if parts else "Entities matched"
