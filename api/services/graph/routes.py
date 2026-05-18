"""
Graph Service Router — Entity graph queries and why-connected explanations
"""
from fastapi import APIRouter, HTTPException, Query
from models.schemas import EntityGraphPayload, WhyConnectedResponse
from services.graph.query_service import get_shipment_graph, get_entity_subgraph
from services.graph.why_service import get_why_connected, search_entities

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/shipment/{shipment_id}", response_model=EntityGraphPayload)
async def get_shipment_entity_graph(shipment_id: str) -> EntityGraphPayload:
    """
    Get full entity graph for a shipment.

    Returns nodes, edges, and metadata for entity exploration.
    """
    try:
        graph = await get_shipment_graph(shipment_id)
        return graph
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load graph: {str(e)}")


@router.get("/entity/{entity_id}", response_model=EntityGraphPayload)
async def get_entity_graph(entity_id: str, hops: int = Query(2, ge=1, le=3)) -> EntityGraphPayload:
    """
    Get subgraph centered on a single entity.

    Args:
        entity_id: Entity to center on
        hops: Relationship distance (1-3, default 2)

    Returns:
        Subgraph with related entities
    """
    try:
        graph = await get_entity_subgraph(entity_id, hop_limit=hops)
        return graph
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load entity graph: {str(e)}")


@router.get("/why/{entity_a}/{entity_b}", response_model=WhyConnectedResponse)
async def get_why_connected_endpoint(entity_a: str, entity_b: str) -> WhyConnectedResponse:
    """
    Explain why two entities are connected.

    Returns relationship chain, evidence, and Senzing explanation.
    """
    try:
        response = await get_why_connected(entity_a, entity_b)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch explanation: {str(e)}")


@router.get("/search")
async def search_entities_endpoint(q: str = Query(..., min_length=1)) -> list:
    """
    Search for entities by name or ID.

    Args:
        q: Search query string

    Returns:
        List of matching entities
    """
    try:
        results = await search_entities(q)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
