"""
Risk Corridor API endpoints
"""
from fastapi import APIRouter, Query, HTTPException, status
from datetime import datetime
from typing import Optional, List

from .models import (
    RiskCorridorIndexResponse,
    RiskCorridorDetailResponse,
    PortVesselsResponse,
    TimelineResponse,
    FeedbackOverrideResponse,
    FeedbackOverride,
)
from .db import (
    init_risk_corridor_tables,
    get_risk_corridors,
    get_corridor_detail,
    get_vessels_by_port,
    get_corridor_timeline,
    log_feedback_override,
)

router = APIRouter()

# Initialize tables on module load
init_risk_corridor_tables()


@router.get(
    "/api/risk-corridors",
    response_model=RiskCorridorIndexResponse,
    summary="Risk Corridor Index",
    description="Return aggregated view of active risk corridors for supervisor dashboard",
)
async def list_risk_corridors(
    industry_filter: Optional[str] = Query(None, description="Comma-separated HTS codes (e.g., 7604,8541)"),
    time_period: str = Query("7d", description="Time period: 7d, 14d, 30d"),
):
    """
    Get aggregated risk corridors grouped by (HTS Industry Segment, Geographic Route, Supplier Entity).

    Returns:
    - Corridor aggregations with YoY surge calculations
    - Macro volumetric delta flags
    - Risk level classifications
    - Summary statistics
    """
    # Parse time period
    time_days = int(time_period.rstrip("d"))

    # Parse industry filter
    industries = None
    if industry_filter:
        industries = [code.strip() for code in industry_filter.split(",")]

    result = get_risk_corridors(industry_filter=industries, time_period_days=time_days)
    return RiskCorridorIndexResponse(**result)


@router.get(
    "/api/risk-corridors/{corridor_id}",
    response_model=RiskCorridorDetailResponse,
    summary="Risk Corridor Detail",
    description="Deep-dive view for field officers with vessel activity and entity chain",
)
async def get_risk_corridor_detail(
    corridor_id: str,
    include: Optional[str] = Query(
        None,
        description="Comma-separated options: vessel_activity, entity_chain, ftz_events"
    ),
):
    """
    Get detailed view of a specific risk corridor including:
    - Corridor composition and statistics
    - Active vessels with port call history
    - FTZ dwell events and anomalies
    - Supply chain entity relationships
    - Transshipment risk scoring
    """
    include_params = None
    if include:
        include_params = [param.strip() for param in include.split(",")]

    result = get_corridor_detail(corridor_id, include_params=include_params)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Corridor {corridor_id} not found"
        )

    return RiskCorridorDetailResponse(**result)


@router.get(
    "/api/ports/{port_code}/vessels-of-interest",
    response_model=PortVesselsResponse,
    summary="Vessels of Interest by Port",
    description="Field officers see which vessels are in/approaching their port with suspicious profiles",
)
async def get_port_vessels(
    port_code: str,
    time_window: str = Query("7d", description="Time window: 7d, 14d, 30d"),
    risk_filter: Optional[str] = Query(None, description="Filter by risk level: HIGH, MEDIUM, LOW"),
):
    """
    Get vessels of interest at a specific port with:
    - Cargo risk level assessment
    - Route anomaly detection
    - Recommended examination actions
    - Capacity planning summary
    """
    # Parse time window
    time_days = int(time_window.rstrip("d"))

    result = get_vessels_by_port(port_code, time_window_days=time_days, risk_filter=risk_filter)
    return PortVesselsResponse(**result)


@router.get(
    "/api/risk-corridors/{corridor_id}/timeline",
    response_model=TimelineResponse,
    summary="Corridor Timeline",
    description="Historical corridor evolution for analysts reconstructing network behavior",
)
async def get_corridor_timeline_view(
    corridor_id: str,
    start_date: str = Query(..., description="ISO date: YYYY-MM-DD"),
    end_date: str = Query(..., description="ISO date: YYYY-MM-DD"),
    granularity: str = Query("daily", description="Granularity: daily, weekly, monthly"),
):
    """
    Get historical timeline snapshots of a corridor's evolution including:
    - Daily/weekly/monthly activity snapshots
    - Entity count and active vessel tracking
    - Notable events and anomalies
    - Entity formation timing detection
    """
    # Validate dates
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        if start > end:
            raise ValueError("start_date must be before end_date")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format or range: {str(e)}"
        )

    result = get_corridor_timeline(
        corridor_id,
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
    )
    return TimelineResponse(**result)


@router.post(
    "/api/feedback/override",
    response_model=FeedbackOverrideResponse,
    summary="Log Feedback Override",
    description="Log officer feedback override for model retraining",
    status_code=status.HTTP_201_CREATED,
)
async def submit_feedback_override(feedback: FeedbackOverride):
    """
    Log officer feedback override with justification for future model retraining.

    Actions:
    - MARK_FALSE_POSITIVE: Flagged corridor is benign (e.g., strike-related port delay)
    - MARK_TRUE_POSITIVE: Unflagged shipment detected as high-risk
    - REQUEST_FOLLOW_UP: Escalate for special investigation

    Categories:
    - VERIFIED_LABOR_STRIKE_PORT_DELAY
    - VERIFIED_CAPACITY_EXPANSION
    - VERIFIED_MISCLASSIFIED_VESSEL
    - SUSPECTED_TRANSSHIPMENT
    - SUSPECTED_EVASION_NETWORK
    - OTHER
    """
    override_data = feedback.model_dump()
    result = log_feedback_override(override_data)
    return FeedbackOverrideResponse(**result)
