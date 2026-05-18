"""
Referral package API routes.

Endpoints:
- GET /api/referral/{shipment_id}
- GET /api/referral/{shipment_id}/summary
- POST /api/referral/{shipment_id}/pdf
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from .service import get_service

router = APIRouter(prefix="/api/referral", tags=["referral"])


# TODO: Implement actual endpoints
# For now, routes are placeholders pending integration with database layer
