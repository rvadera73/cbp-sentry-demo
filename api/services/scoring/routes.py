"""
Scoring service router
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import sys
from pathlib import Path

# Add api directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models.schemas import ScoreResponse, XAIAssertion
from .service import ScoringService

router = APIRouter()

# Initialize scoring service
_scoring_service = None


def get_scoring_service() -> ScoringService:
    """Get or create scoring service singleton"""
    global _scoring_service
    if _scoring_service is None:
        _scoring_service = ScoringService()
    return _scoring_service


@router.post("/api/score", response_model=ScoreResponse)
async def score_shipment(
    manifest: Dict[str, Any],
    entities: Dict[str, Any]
) -> ScoreResponse:
    """
    Score a shipment using 4-tier ML pipeline.

    Args:
        manifest: Manifest data (HTS, COO, AIS, pricing, etc.)
        entities: Entity resolution results

    Returns:
        ScoreResponse with total_score, components, XAI assertions
    """
    try:
        service = get_scoring_service()
        response = service.score_shipment(manifest, entities)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/score/{shipment_id}/xai", response_model=list[XAIAssertion])
async def get_xai_explanations(shipment_id: str) -> list[XAIAssertion]:
    """
    Get XAI explanations for a scored shipment.

    Args:
        shipment_id: Shipment identifier

    Returns:
        List of XAI assertions with citations
    """
    # TODO: Load shipment from DB and return XAI assertions
    raise HTTPException(status_code=501, detail="XAI endpoint not yet implemented")
