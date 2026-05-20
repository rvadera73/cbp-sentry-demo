"""
Entity resolution routes — FastAPI endpoints for entity resolution.

Endpoints:
- POST /load — Load entities from manifest
- GET /why/{entity_a}/{entity_b} — Get why-explanation
- GET /graph/{entity_id} — Get subgraph for entity
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any

from models.schemas import (
    ERLoadRequest, ERLoadResponse, WhyExplanation, EntityGraphPayload
)
from .service import EntityResolutionService
from .senzing_client import SenzingClient
from .graph_builder import (
    get_graph_nodes, get_graph_edges, get_subgraph, find_shortest_path
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize service (will be dependency-injected in production)
_senzing_client = None
_er_service = None
_entities_cache = None


def init_service(senzing_client: Optional[SenzingClient] = None):
    """Initialize entity resolution service."""
    global _senzing_client, _er_service
    _senzing_client = senzing_client
    _er_service = EntityResolutionService(senzing_client=_senzing_client)


@router.post("/load")
async def load_entities(request: ERLoadRequest) -> ERLoadResponse:
    """
    Load entities from manifest into Senzing and resolve against CORD data.

    Args:
        request: ERLoadRequest with manifest_id

    Returns:
        ERLoadResponse with entities_loaded, resolutions, relationships
    """
    try:
        # Fetch manifest from database
        from core.shipments_db import get_shipment_by_manifest_id
        manifest_data = get_shipment_by_manifest_id(request.manifest_id)

        if not manifest_data:
            raise HTTPException(status_code=404, detail=f"Manifest not found: {request.manifest_id}")

        # Load manifest entities into Senzing
        from .loader import load_manifest_entities
        record_ids = load_manifest_entities(manifest_data, senzing_client=_senzing_client)

        # Search Senzing for matches against CORD data
        resolutions = []
        if _senzing_client:
            # Search for shipper matches in CORD
            shipper_matches = _search_entity_matches(
                f"{manifest_data.get('shipper_name', '')}",
                entity_type="SHIPPER",
                country=manifest_data.get('shipper_country')
            )

            # Search for consignee matches
            consignee_matches = _search_entity_matches(
                f"{manifest_data.get('consignee_name', '')}",
                entity_type="CONSIGNEE",
                country=manifest_data.get('consignee_country')
            )

            resolutions = shipper_matches + consignee_matches

        # Detect relationships from matches
        relationships = _detect_cord_relationships(resolutions)

        summary = {
            "manifest_id": request.manifest_id,
            "entities_matched": len(resolutions),
            "relationships_detected": len(relationships),
            "cord_data_used": True
        }

        return ERLoadResponse(
            entities_loaded=len(record_ids),
            resolutions=resolutions,
            relationships=relationships,
            summary=summary
        )

    except Exception as e:
        logger.error(f"Entity loading failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/why/{entity_a}/{entity_b}")
async def get_why_explanation(
    entity_a: str,
    entity_b: str
) -> WhyExplanation:
    """
    Get why-explanation for why two entities are connected.

    Args:
        entity_a: First entity ID
        entity_b: Second entity ID

    Returns:
        WhyExplanation with explanation and evidence
    """
    try:
        entities = _get_mock_entities()

        explanation = _er_service.get_why_explanation(
            entity_a,
            entity_b,
            entities
        )

        return WhyExplanation(
            why_key=explanation.get("why_key", ""),
            entity_a=explanation.get("entity_a", ""),
            entity_b=explanation.get("entity_b", ""),
            confidence=explanation.get("confidence", 0.0),
            explanation=explanation.get("explanation", ""),
            evidence=explanation.get("evidence", [])
        )

    except Exception as e:
        logger.error(f"Why explanation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/{entity_id}")
async def get_entity_graph(
    entity_id: str,
    hops: int = Query(2, ge=1, le=3)
) -> EntityGraphPayload:
    """
    Get subgraph for entity and related entities.

    Args:
        entity_id: Center entity ID
        hops: Number of relationship hops (1-3)

    Returns:
        EntityGraphPayload with nodes and edges
    """
    try:
        entities = _get_mock_entities()

        # Build full graph
        from .service import _detect_relationships
        relationships = _detect_relationships(entities, [])

        from .graph_builder import build_entity_graph
        full_graph = build_entity_graph([], relationships)

        # Get subgraph around entity_id
        subgraph = get_subgraph(full_graph, entity_id, hops=hops)

        return EntityGraphPayload(
            nodes=get_graph_nodes(subgraph),
            edges=get_graph_edges(subgraph),
            metadata={
                "center_entity": entity_id,
                "hops": hops,
                "total_nodes": subgraph.number_of_nodes(),
                "total_edges": subgraph.number_of_edges()
            }
        )

    except Exception as e:
        logger.error(f"Graph query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_mock_entities() -> Dict[str, Dict[str, Any]]:
    """Get mock entities for testing."""
    return {
        "shipper_vn": {
            "id": "ENT-VN-001",
            "name": "Greenfield Industrial Trading Co., Ltd.",
            "country": "VN",
            "jurisdiction": "VN",
            "type": "TRADING_COMPANY",
            "senzing_record_id": "rec_vn_001",
            "senzing_confidence": 0.95,
            "risk_score": 45,
            "metadata": {}
        },
        "parent_cn": {
            "id": "ENT-CN-001",
            "name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
            "country": "CN",
            "jurisdiction": "CN",
            "type": "MANUFACTURER",
            "senzing_record_id": "rec_cn_001",
            "senzing_confidence": 0.98,
            "risk_score": 68,
            "metadata": {}
        }
    }
