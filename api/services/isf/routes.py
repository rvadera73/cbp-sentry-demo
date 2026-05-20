"""ISF enrichment REST API routes."""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from .models import ISFEnrichmentRequest, ISFEnrichmentResponse, Element9Data
from .isf_service import ISFEnrichmentService
from .vessel_tracker import VesselTrackerClient

router = APIRouter(prefix="/api/isf", tags=["ISF Enrichment"])

# Initialize clients (in production, use dependency injection)
vessel_tracker = VesselTrackerClient()
isf_service = ISFEnrichmentService(vessel_tracker)


@router.post("/enrich-manifest", response_model=ISFEnrichmentResponse)
async def enrich_manifest(request: ISFEnrichmentRequest) -> ISFEnrichmentResponse:
    """
    Enrich manifest with ISF data and Element 9 analysis.

    Fetches real-time vessel data from VesselFinder and analyzes for:
    - Element 9 Country of Origin mismatches (transshipment detection)
    - Dwell time anomalies
    - Port routing consistency
    """
    response = await isf_service.enrich_manifest(request)
    return response


@router.get("/vessel/{imo}")
async def get_vessel_info(imo: str):
    """
    Get vessel information by IMO number.

    Returns:
    - Vessel identification (name, flag, type)
    - Dimensions and capacity
    - Recent port call history
    """
    vessel_info = await vessel_tracker.get_vessel_info(imo)
    if not vessel_info:
        raise HTTPException(
            status_code=404, detail=f"Vessel with IMO {imo} not found"
        )
    return vessel_info


@router.get("/vessel/{imo}/position")
async def get_vessel_position(imo: str):
    """
    Get current position of vessel by IMO.

    Returns:
    - Current latitude/longitude
    - Port/water status
    - Speed and course
    """
    position = await vessel_tracker.get_vessel_position(imo)
    if not position:
        raise HTTPException(
            status_code=404, detail=f"Position data not available for IMO {imo}"
        )
    return position


@router.get("/vessel/{imo}/port-calls")
async def get_port_calls(
    imo: str, limit: int = Query(20, ge=1, le=100)
):
    """
    Get port call history for a vessel.

    Returns list of recent ports with:
    - Arrival/departure dates
    - Dwell time in days
    - Port location coordinates
    """
    port_calls = await vessel_tracker.get_port_calls(imo, limit=limit)
    if not port_calls:
        raise HTTPException(
            status_code=404, detail=f"No port calls found for IMO {imo}"
        )
    return {"imo": imo, "port_calls": port_calls}


@router.get("/element9/{manifest_id}")
async def get_element9_analysis(manifest_id: str) -> Element9Data:
    """
    Get Element 9 analysis for a manifest.

    Element 9: Country of Origin Pre-Arrival field analysis.

    Returns:
    - Declared vs actual country comparison
    - Mismatch risk assessment
    - Transshipment indicators
    - Evidence and data sources
    """
    # This would fetch from cache/database in production
    raise HTTPException(
        status_code=501, detail="Element 9 lookup requires prior enrichment"
    )


@router.get("/dwell-anomaly/{imo}")
async def detect_dwell_anomaly(
    imo: str,
    origin_port: str = Query(..., description="Port code of origin, e.g. CNSHA"),
    baseline_days: int = Query(3, ge=1, le=30),
):
    """
    Detect dwell time anomalies at origin port.

    Compares actual dwell against typical baseline (default 3 days).
    Flag if dwell > 5x baseline (typical transshipment indicator).
    """
    dwell = await vessel_tracker.get_recent_dwell_time(imo, origin_port)
    if dwell is None:
        raise HTTPException(
            status_code=404,
            detail=f"No recent dwell data for {imo} at {origin_port}",
        )

    anomaly_threshold = baseline_days * 5
    is_anomaly = dwell > anomaly_threshold

    return {
        "imo": imo,
        "port": origin_port,
        "dwell_days": dwell,
        "baseline_days": baseline_days,
        "anomaly_threshold": anomaly_threshold,
        "is_anomaly": is_anomaly,
        "anomaly_severity": "HIGH" if is_anomaly else "NORMAL",
    }


@router.get("/health")
async def health_check():
    """Check ISF service and external API health."""
    vessel_health = await vessel_tracker.health_check()
    return {
        "status": "healthy" if vessel_health.get("vesselfinder_available") else "degraded",
        "vessel_tracker": vessel_health,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/vessel/search")
async def search_vessel(vessel_name: Optional[str] = None, imo: Optional[str] = None):
    """
    Search for vessel by name or IMO.

    Returns matching vessel candidates with scores.
    """
    if not vessel_name and not imo:
        raise HTTPException(
            status_code=400,
            detail="Either vessel_name or imo must be provided",
        )

    if imo:
        vessel = await vessel_tracker.get_vessel_info(imo)
        if vessel:
            return {"results": [vessel], "count": 1}

    # Vessel name search not yet implemented
    return {
        "results": [],
        "count": 0,
        "note": "Vessel name search not yet implemented",
    }


@router.get("/api-keys/status")
async def check_api_keys():
    """Check configured API keys for vessel tracking services."""
    return {
        "vesselfinder": "configured" if vessel_tracker.vesselfinder_api_key else "not_configured",
        "aisstream": "configured" if vessel_tracker.aisstream_api_key else "not_configured",
        "cache_entries": len(vessel_tracker.vessel_cache),
    }


@router.post("/cache/clear")
async def clear_cache():
    """Clear vessel data cache."""
    vessel_tracker.clear_cache()
    return {"status": "cache_cleared", "timestamp": datetime.utcnow().isoformat()}
