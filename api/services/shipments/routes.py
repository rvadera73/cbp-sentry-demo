"""
Shipments API endpoints
"""
from fastapi import APIRouter, Query
from core.shipments_db import (
    get_all_shipments,
    get_shipment_by_id,
    search_shipments,
    get_shipments_map_data,
    get_shipments_stats,
)

router = APIRouter()


@router.get("/api/shipments")
async def list_shipments(limit: int = Query(15, ge=1, le=100), offset: int = Query(0, ge=0)):
    """Get all shipments with pagination"""
    return get_all_shipments(limit=limit, offset=offset)


@router.get("/api/shipments/{shipment_id}")
async def get_shipment(shipment_id: int):
    """Get single shipment detail"""
    shipment = get_shipment_by_id(shipment_id)
    if not shipment:
        return {"error": "Shipment not found"}
    return shipment


@router.get("/api/shipments/search")
async def search(
    origin: str = Query(None),
    destination: str = Query(None),
    risk_min: int = Query(None),
    risk_max: int = Query(None),
    status: str = Query(None),
    limit: int = Query(15, ge=1, le=100),
):
    """Search shipments with filters"""
    return search_shipments(
        origin=origin,
        destination=destination,
        risk_min=risk_min,
        risk_max=risk_max,
        status=status,
        limit=limit,
    )


@router.get("/api/shipments/map/data")
async def get_map_data():
    """Get shipment coordinates for map visualization"""
    return get_shipments_map_data()


@router.get("/api/shipments/stats")
async def get_stats():
    """Get dashboard statistics"""
    return get_shipments_stats()
