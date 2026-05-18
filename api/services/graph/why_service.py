"""
Why-Connected Service — Explain relationships between entities
"""
from typing import Dict, List, Any
from models.schemas import WhyConnectedResponse


# Hardcoded explanation data for testing
EXPLANATIONS = {
    ("entity_vn_1", "entity_cn_1"): {
        "relationship_chain": [
            {
                "entity": "entity_vn_1",
                "label": "Greenfield Industrial Trading Co., Ltd.",
                "type": "TRADING_COMPANY"
            },
            {
                "relationship": "OWNED_BY",
                "confidence": 0.89
            },
            {
                "entity": "entity_cn_1",
                "label": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
                "type": "MANUFACTURER"
            }
        ],
        "explanation": "This Vietnamese entity (Greenfield Industrial Trading Co., Ltd.) is linked to Guangdong Greenfield (CN manufacturer) via direct ownership. The transliterated name match ('Greenfield' in both) and shared director Nguyen Van Hung suggest common beneficial ownership.",
        "evidence": [
            {
                "type": "NAME_TRANSLITERATION",
                "description": "Both entities share 'Greenfield' in translated names",
                "confidence": 0.91
            },
            {
                "type": "SHARED_DIRECTOR",
                "description": "Director Nguyen Van Hung appears in both corporate records",
                "confidence": 0.92
            },
            {
                "type": "OWNERSHIP_CHAIN",
                "description": "VN trading company owns/controls CN manufacturer",
                "confidence": 0.89
            },
            {
                "type": "PRIOR_FILINGS",
                "description": "18 prior CN filings from related entities",
                "confidence": 0.88
            }
        ],
        "confidence": 0.90
    },
    ("entity_vn_1", "entity_vn_2"): {
        "relationship_chain": [
            {
                "entity": "entity_vn_1",
                "label": "Greenfield Industrial Trading Co., Ltd.",
                "type": "TRADING_COMPANY"
            },
            {
                "relationship": "SHARES_DIRECTOR",
                "confidence": 0.91
            },
            {
                "entity": "entity_vn_2",
                "label": "Greenfield Logistics Vietnam Co., Ltd.",
                "type": "LOGISTICS"
            }
        ],
        "explanation": "Both Vietnamese entities are linked through shared director Nguyen Van Hung. The network structure suggests coordinated control of export and logistics operations.",
        "evidence": [
            {
                "type": "SHARED_DIRECTOR",
                "description": "Director Nguyen Van Hung in both companies",
                "confidence": 0.92
            },
            {
                "type": "RELATED_NAMES",
                "description": "Both use 'Greenfield' prefix",
                "confidence": 0.85
            },
            {
                "type": "SECTOR_ALIGNMENT",
                "description": "Trading (import/export) + Logistics suggests supply chain integration",
                "confidence": 0.88
            }
        ],
        "confidence": 0.88
    }
}


async def get_why_connected(
    entity_a: str,
    entity_b: str,
    entity_names: Dict[str, str] = None
) -> WhyConnectedResponse:
    """
    Explain why two entities are connected.

    Queries Neo4j for shortest path, extracts relationship chain,
    calls Senzing why-explanation API, and formats response.

    Args:
        entity_a: First entity ID
        entity_b: Second entity ID
        entity_names: Optional dict of entity_id -> label for display

    Returns:
        WhyConnectedResponse with relationship_chain, explanation, evidence, confidence
    """
    # TODO: Implement actual Neo4j shortest path query + Senzing API call
    # For now, return hardcoded explanations

    key = (entity_a, entity_b)
    reverse_key = (entity_b, entity_a)

    if key in EXPLANATIONS:
        data = EXPLANATIONS[key]
    elif reverse_key in EXPLANATIONS:
        data = EXPLANATIONS[reverse_key]
    else:
        # Generic explanation for unmapped pairs
        data = {
            "relationship_chain": [
                {
                    "entity": entity_a,
                    "label": entity_names.get(entity_a, entity_a) if entity_names else entity_a,
                    "type": "ENTITY"
                },
                {
                    "relationship": "RELATED_TO",
                    "confidence": 0.5
                },
                {
                    "entity": entity_b,
                    "label": entity_names.get(entity_b, entity_b) if entity_names else entity_b,
                    "type": "ENTITY"
                }
            ],
            "explanation": f"Entities {entity_a} and {entity_b} are connected through the supply chain network.",
            "evidence": [],
            "confidence": 0.5
        }

    return WhyConnectedResponse(
        entity_a=entity_a,
        entity_b=entity_b,
        relationship_chain=data.get("relationship_chain", []),
        explanation=data.get("explanation", ""),
        evidence=data.get("evidence", []),
        confidence=data.get("confidence", 0.5)
    )


async def search_entities(query: str) -> List[Dict[str, Any]]:
    """
    Search for entities by name or ID.

    Args:
        query: Search query string

    Returns:
        List of matching entities with id, label, type, confidence
    """
    # TODO: Implement actual Neo4j full-text search
    # For now, mock search against fixture

    from services.graph.query_service import GREENFIELD_GRAPH_FIXTURE

    results = []
    query_lower = query.lower()

    for node in GREENFIELD_GRAPH_FIXTURE["nodes"]:
        label_lower = node["label"].lower()
        id_lower = node["id"].lower()

        if query_lower in label_lower or query_lower in id_lower:
            results.append({
                "id": node["id"],
                "label": node["label"],
                "type": node["type"],
                "jurisdiction": node["jurisdiction"],
                "confidence": 0.95 if query_lower in label_lower else 0.80
            })

    return sorted(results, key=lambda x: x["confidence"], reverse=True)
