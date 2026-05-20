"""
Scoring service router - Three-Level Risk Assessment Engine
Implements: H1 (Corridor) → H2 (Vessel) → H3 (Manifest) → Combined Score
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import sys
from pathlib import Path
import logging
from datetime import datetime

# Add api directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .scoring_engine import ScoringEngine, ScoringWeights

logger = logging.getLogger(__name__)

router = APIRouter()

# Global scoring engine instance with dynamic weights
scoring_engine = ScoringEngine(weights=ScoringWeights())


# ============================================================================
# Pydantic Models
# ============================================================================


class ShipmentDataInput(BaseModel):
    """Input schema for scoring a shipment"""

    shipment_id: str
    shipper_name: str
    consignee_name: str
    origin_country: str
    destination_country: str
    origin_port: str = Field(default="")
    destination_port: str = Field(default="")
    hs_code: str
    declared_value_usd: float
    declared_weight_kg: float
    vessel_name: str = Field(default="")
    dwell_days: float = Field(default=2.1)
    declared_origin: str = Field(default="")
    ais_stuffing_country: str = Field(default="")
    port_calls: list = Field(default_factory=list)
    shipper_age_months: int = Field(default=24)
    importer_age_months: int = Field(default=24)
    importer_ytd_volume: float = Field(default=0)
    senzing_confidence: float = Field(default=0.0)
    entity_type: str = Field(default="")
    ofac_match: bool = Field(default=False)
    watchlist_match: bool = Field(default=False)


class ScoringResponse(BaseModel):
    """Response schema for risk score"""

    shipment_id: str
    h1: Dict[str, Any]
    h2: Dict[str, Any]
    h3: Dict[str, Any]
    total_score: float
    confidence: str
    should_verify_altana: bool
    timestamp: str


class FeedbackInput(BaseModel):
    """Human feedback for score override"""

    shipment_id: str
    system_score: float
    human_label: float  # 0 = false positive, 1 = true positive
    feedback_type: str  # "factory_expansion", "dual_origin", "misclassified_vessel"
    notes: str = Field(default="")


class FeedbackResponse(BaseModel):
    """Response after feedback processing"""

    shipment_id: str
    accepted: bool
    weight_adjustment: Dict[str, float]
    new_weights: Dict[str, float]
    message: str


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/score", response_model=ScoringResponse)
async def calculate_score(shipment: ShipmentDataInput) -> ScoringResponse:
    """
    Calculate comprehensive risk score for a shipment using three-level assessment.

    Flow: H1 (Corridor) → H2 (Vessel) → H3 (Manifest) → Total Score

    Args:
        shipment: Shipment data with all required fields

    Returns:
        ScoringResponse with H1, H2, H3 scores and combined total
    """
    try:
        shipment_data = shipment.dict()
        score_result = scoring_engine.calculate_score(shipment_data)

        return ScoringResponse(
            shipment_id=shipment.shipment_id,
            h1=score_result["h1"],
            h2=score_result["h2"],
            h3=score_result["h3"],
            total_score=score_result["total_score"],
            confidence=score_result["confidence"],
            should_verify_altana=score_result["should_verify_altana"],
            timestamp=score_result["timestamp"],
        )

    except Exception as e:
        logger.error(f"Scoring error for shipment {shipment.shipment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")


@router.get("/score/{shipment_id}", response_model=ScoringResponse)
async def get_score(shipment_id: str) -> ScoringResponse:
    """
    Retrieve pre-calculated score for a shipment from database/cache.

    Args:
        shipment_id: Shipment identifier

    Returns:
        Previously calculated ScoringResponse
    """
    try:
        # TODO: Fetch from database/cache
        logger.info(f"Retrieving score for shipment: {shipment_id}")

        # Mock response for now
        return ScoringResponse(
            shipment_id=shipment_id,
            h1={
                "horizon": "H1",
                "label": "Corridor Risk",
                "score": 40,
                "max_score": 40,
                "weight": 20,
                "factors": [],
                "summary": "Corridor analysis complete",
            },
            h2={
                "horizon": "H2",
                "label": "Vessel Anomaly",
                "score": 35,
                "max_score": 35,
                "weight": 35,
                "factors": [],
                "summary": "Vessel analysis complete",
            },
            h3={
                "horizon": "H3",
                "label": "Intelligence Signals",
                "score": 16,
                "max_score": 25,
                "weight": 45,
                "factors": [],
                "summary": "Intelligence analysis complete",
            },
            total_score=91.0,
            confidence="HIGH",
            should_verify_altana=True,
            timestamp=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        logger.error(f"Error retrieving score: {str(e)}")
        raise HTTPException(status_code=404, detail=f"Score not found: {str(e)}")


@router.post("/feedback", response_model=FeedbackResponse)
async def process_feedback(feedback: FeedbackInput) -> FeedbackResponse:
    """
    Process human analyst feedback and update scoring weights using SGD.

    Implements human-in-the-loop reinforcement learning to reduce false positives
    and adapt model to regional/operational variations.

    Args:
        feedback: Human feedback including override reason

    Returns:
        Updated weights and adjustment details
    """
    try:
        old_weights = {
            "h1": scoring_engine.weights.h1_weight,
            "h2": scoring_engine.weights.h2_weight,
            "h3": scoring_engine.weights.h3_weight,
        }

        # Calculate feature value based on feedback type
        feature_value = 1.0
        if feedback.feedback_type == "factory_expansion":
            feature_value = 0.7
        elif feedback.feedback_type == "dual_origin":
            feature_value = 0.8
        elif feedback.feedback_type == "misclassified_vessel":
            feature_value = 0.9

        # Update weights using SGD
        scoring_engine.update_weights_from_feedback(
            system_score=feedback.system_score,
            human_label=feedback.human_label,
            feature_value=feature_value,
            learning_rate=0.05,
        )

        new_weights = {
            "h1": scoring_engine.weights.h1_weight,
            "h2": scoring_engine.weights.h2_weight,
            "h3": scoring_engine.weights.h3_weight,
        }

        weight_adjustment = {
            "h1": new_weights["h1"] - old_weights["h1"],
            "h2": new_weights["h2"] - old_weights["h2"],
            "h3": new_weights["h3"] - old_weights["h3"],
        }

        return FeedbackResponse(
            shipment_id=feedback.shipment_id,
            accepted=True,
            weight_adjustment=weight_adjustment,
            new_weights=new_weights,
            message=f"Score override processed. Weights adjusted using SGD. "
            f"Feedback type: {feedback.feedback_type}",
        )

    except Exception as e:
        logger.error(f"Error processing feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Feedback processing failed: {str(e)}")


@router.get("/weights")
async def get_current_weights():
    """Get current dynamic weights and recent adjustment history"""
    return {
        "current_weights": {
            "h1": round(scoring_engine.weights.h1_weight, 4),
            "h2": round(scoring_engine.weights.h2_weight, 4),
            "h3": round(scoring_engine.weights.h3_weight, 4),
        },
        "history_length": len(scoring_engine.weight_history),
        "recent_adjustments": scoring_engine.weight_history[-5:] if scoring_engine.weight_history else [],
    }


@router.post("/altana/verify/{shipment_id}")
async def verify_with_altana(shipment_id: str) -> Dict[str, Any]:
    """
    Trigger Altana Atlas API verification for high-risk shipments (score ≥ 90%).
    This is the final validation layer before generating referral package.
    """
    try:
        logger.info(f"Triggering Altana verification for shipment: {shipment_id}")

        # TODO: Integrate actual Altana API call
        # For now, return mock verification response
        return {
            "shipment_id": shipment_id,
            "altana_result": "VERIFIED",
            "supplier_chain": {
                "tier_1": "Greenfield Industrial Trading Co. (VN)",
                "tier_2": "Guangdong Greenfield Aluminum Mfg (CN)",
                "tier_3": "Known aluminum manufacturer with transshipment history",
            },
            "verification_details": [
                "Tier-1 shipper traced to Guangdong parent company",
                "Tier-2 supplier appears in 3 prior EAPA cases",
                "Supply chain linkage confirmed via Altana global knowledge graph",
            ],
            "recommendation": "PROCEED_WITH_REFERRAL",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Altana verification error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Altana verification failed: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check for scoring service"""
    return {
        "status": "healthy",
        "service": "scoring-engine-three-level",
        "version": "1.0.0",
        "current_weights": {
            "h1": round(scoring_engine.weights.h1_weight, 4),
            "h2": round(scoring_engine.weights.h2_weight, 4),
            "h3": round(scoring_engine.weights.h3_weight, 4),
        },
    }
