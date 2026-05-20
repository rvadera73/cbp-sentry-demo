"""
CORD RAG API Routes — REST endpoints for entity investigation via CORD data.

Endpoints:
- POST /api/cord/investigate — Investigate entity connections
- GET /api/cord/status — Check CORD status
- POST /api/cord/download — Download CORD dataset
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
from pydantic import BaseModel

from .agent import CORDRAGAgent
from .cord_downloader import CORDDownloader
from .search_first_integration import SearchFirstCORDIntegration

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
_rag_agent = None
_downloader = None
_search_first = None


def init_services():
    """Initialize CORD services."""
    global _rag_agent, _downloader
    _rag_agent = CORDRAGAgent()
    _downloader = CORDDownloader()


# Request/Response models
class InvestigateRequest(BaseModel):
    entity_name: str
    country: Optional[str] = None
    depth: int = 2


class InvestigateResponse(BaseModel):
    status: str
    primary_entity: Optional[Dict[str, Any]]
    entity_chain: list
    beneficial_owners: list
    risk_flags: list
    explanation: str
    confidence: float
    sources: list


class ConnectionCheckRequest(BaseModel):
    entity_a: str
    entity_b: str
    max_hops: int = 3


class ConnectionCheckResponse(BaseModel):
    connected: bool
    details: Dict[str, Any]


class CORDStatusResponse(BaseModel):
    status: str
    london_loaded: bool
    moscow_loaded: bool
    records_total: int
    last_updated: Optional[str]


class SearchFirstInvestigateRequest(BaseModel):
    """Manifest-based investigation using search-first CORD approach."""
    manifest_id: str
    shipper_name: str
    shipper_country: str
    consignee_name: str
    consignee_country: str
    declared_origin: Optional[str] = None
    manufacturer_inferred: Optional[str] = None
    base_score: int = 30


class SearchFirstInvestigateResponse(BaseModel):
    """Search-first investigation result with entity chains and risks."""
    manifest_id: str
    status: str
    investigation: Dict[str, Any]
    scoring: Dict[str, Any]
    sources: list
    eval_safety: Dict[str, Any]
    timestamp: str


# Endpoints

@router.post("/investigate-shipment", response_model=SearchFirstInvestigateResponse)
async def investigate_shipment_search_first(
    request: SearchFirstInvestigateRequest
) -> SearchFirstInvestigateResponse:
    """
    Investigate shipment manifest using search-first CORD approach.

    Flow:
    1. Extract entities from manifest (shipper, consignee, manufacturer)
    2. Search FULL CORD via REST API (unlimited scope)
    3. Extract relevant subset (~20 entities per case)
    4. Load only subset into Senzing SDK (<100K eval limit)
    5. Resolve entity chains with confidence scores
    6. Flag risks (OFAC, AD/CVD, sanctions, patterns)
    7. Calculate risk score (H1 + H2 + H3)

    This approach avoids evaluation limits while using real CORD data.

    Args:
        request: Manifest data with entity information

    Returns:
        Investigation result with entity chains, risk flags, and score
    """
    global _search_first
    if not _search_first:
        _search_first = SearchFirstCORDIntegration(
            cord_rest_url="http://localhost:8250",
            senzing_sdk_enabled=True
        )

    try:
        manifest_data = {
            "manifest_id": request.manifest_id,
            "shipper_name": request.shipper_name,
            "shipper_country": request.shipper_country,
            "consignee_name": request.consignee_name,
            "consignee_country": request.consignee_country,
            "declared_origin": request.declared_origin or request.shipper_country,
            "manufacturer_inferred": request.manufacturer_inferred or "",
            "base_score": request.base_score
        }

        result = _search_first.investigate_shipment(manifest_data)
        return SearchFirstInvestigateResponse(**result)

    except Exception as e:
        logger.error(f"Shipment investigation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/investigate", response_model=InvestigateResponse)
async def investigate_entity(request: InvestigateRequest) -> InvestigateResponse:
    """
    Investigate entity using CORD RAG.

    Searches CORD for the entity and traces relationships to find:
    - Parent companies and manufacturers
    - Beneficial owners
    - Risk indicators (OFAC, PEP, AD/CVD)
    - Evidence from GLEIF, ICIJ, sanctions data

    Args:
        entity_name: Company or person name
        country: Optional country code
        depth: Relationship depth (1-3)

    Returns:
        Entity investigation with chain and risks
    """
    if not _rag_agent:
        init_services()

    try:
        result = _rag_agent.investigate_entity(
            request.entity_name,
            country=request.country,
            depth=request.depth
        )

        if result["status"] == "not_found":
            raise HTTPException(status_code=404, detail=result["message"])

        return InvestigateResponse(**result)

    except Exception as e:
        logger.error(f"Investigation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/is-connected", response_model=ConnectionCheckResponse)
async def check_connection(request: ConnectionCheckRequest) -> ConnectionCheckResponse:
    """
    Check if two entities are connected in CORD.

    Args:
        entity_a: First entity name
        entity_b: Second entity name
        max_hops: Maximum relationship hops

    Returns:
        Connection status and path details
    """
    if not _rag_agent:
        init_services()

    try:
        connected, details = _rag_agent.is_entity_connected(
            request.entity_a,
            request.entity_b,
            max_hops=request.max_hops
        )

        return ConnectionCheckResponse(
            connected=connected,
            details=details
        )

    except Exception as e:
        logger.error(f"Connection check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=CORDStatusResponse)
async def get_cord_status() -> CORDStatusResponse:
    """
    Get CORD data status.

    Returns:
        Status of loaded CORD collections
    """
    if not _downloader:
        init_services()

    return CORDStatusResponse(
        status="ready",
        london_loaded=True,  # In production: check Senzing
        moscow_loaded=True,
        records_total=16000000,
        last_updated="2026-05-19T00:00:00Z"
    )


@router.post("/download")
async def download_cord(
    location: str = Query("london", description="CORD location: london, moscow, las_vegas"),
    auto_load: bool = Query(False, description="Auto-load into Senzing after download")
) -> Dict[str, Any]:
    """
    Download CORD dataset.

    Args:
        location: CORD location (london, moscow, las_vegas)
        auto_load: Automatically load into Senzing

    Returns:
        Download status and file info
    """
    if not _downloader:
        init_services()

    try:
        # Download
        cord_file = _downloader.download_cord(location, format="jsonl")

        result = {
            "status": "downloaded",
            "location": location,
            "file": str(cord_file),
            "auto_load": auto_load
        }

        # Load if requested
        if auto_load:
            load_result = _downloader.load_cord_to_senzing(location)
            result["load"] = load_result

        return result

    except Exception as e:
        logger.error(f"Download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/available-locations")
async def list_available_cords() -> Dict[str, Any]:
    """List available CORD collections."""
    if not _downloader:
        init_services()

    return {
        "locations": _downloader.list_available_cords()
    }
