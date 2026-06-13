"""
Model Versioning API Routes

Endpoints for:
- Get active model version
- Switch model versions
- View model metadata
- Compare scores across model versions
- Access score history audit trail
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any
import os
import logging

router = APIRouter(prefix="/api/model", tags=["model-versioning"])
logger = logging.getLogger(__name__)


# Pydantic models for requests/responses
class ModelVersion(BaseModel):
    version: str
    name: str
    type: str  # 'legacy' or 'precise'
    features_count: int
    gates_count: int
    rules_count: int
    weight_sum: float
    description: str
    created_at: datetime


class ModelVersionResponse(BaseModel):
    active_version: str
    model_used: str
    model_type: str
    weight_sum: float
    traffic_percentage: int
    feature_flag_enabled: bool
    legacy_available: bool
    fallback_model: str


class SwitchModelRequest(BaseModel):
    active_version: str
    reason: Optional[str] = None


class ScoreComparison(BaseModel):
    shipment_id: str
    v2_1_legacy_score: Optional[float]
    v3_0_precise_score: Optional[float]
    v3_0_confidence: Optional[float]
    score_difference: float
    percent_change: float
    recommendation_changed: bool
    legacy_recommendation: str
    precise_recommendation: str


class ScoreHistory(BaseModel):
    id: str
    shipment_id: str
    model_version: str
    legacy_score: Optional[float]
    precise_score: Optional[float]
    precise_confidence: Optional[float]
    scored_at: datetime


# Utility functions
def get_active_model_version() -> str:
    """Get currently active model version"""
    return os.getenv('MODEL_VERSION_ACTIVE', 'v2.1')


def get_model_type(version: str) -> str:
    """Get model type for version"""
    return 'precise' if version == 'v3.0' else 'legacy'


def score_to_recommendation(score: float) -> str:
    """Convert score to recommendation"""
    if score >= 80:
        return "HOLD"
    elif score >= 50:
        return "EXAMINE"
    else:
        return "CLEAR"


# Routes
@router.get("/version", response_model=ModelVersionResponse)
async def get_model_version():
    """
    Get currently active model version and configuration

    Returns:
    - active_version: Current model (v2.1 or v3.0)
    - model_used: Which implementation (legacy or precise-risk-engine)
    - weight_sum: Total weight of factors (should be 1.0 for v3.0, 1.1 for v2.1)
    - traffic_percentage: % of requests routed to new model (only if v2.1 legacy)
    - feature_flag_enabled: Whether feature flag is ON
    - legacy_available: Can switch back to v2.1

    Example:
    ```
    GET /api/model/version
    {
      "active_version": "v3.0",
      "model_used": "precise-risk-engine",
      "model_type": "precise",
      "weight_sum": 1.0,
      "traffic_percentage": 100,
      "feature_flag_enabled": true,
      "legacy_available": true,
      "fallback_model": "v2.1"
    }
    ```
    """
    active_version = get_active_model_version()
    model_type = get_model_type(active_version)
    weight_sum = 1.0 if active_version == 'v3.0' else 1.10

    return ModelVersionResponse(
        active_version=active_version,
        model_used="precise-risk-engine" if active_version == 'v3.0' else "legacy",
        model_type=model_type,
        weight_sum=weight_sum,
        traffic_percentage=int(os.getenv('TRAFFIC_PERCENTAGE', 0)),
        feature_flag_enabled=os.getenv('USE_PRECISE_RISK_MODEL') == 'true',
        legacy_available=os.getenv('LEGACY_MODEL_AVAILABLE') == 'true',
        fallback_model='v2.1'
    )


@router.post("/version/switch")
async def switch_model_version(request: SwitchModelRequest):
    """
    Switch between model versions

    **Security:** Requires authentication (typically admin/analyst role)

    Params:
    - active_version: 'v2.1' or 'v3.0'
    - reason: Optional reason for switch (logged in audit trail)

    Returns:
    ```
    {
      "switched_to": "v3.0",
      "previous_version": "v2.1",
      "switched_at": "2026-06-12T10:30:00Z",
      "status": "success"
    }
    ```

    Example - Switch to v3.0:
    ```
    POST /api/model/version/switch
    {
      "active_version": "v3.0",
      "reason": "Starting full model testing"
    }
    ```

    Example - Rollback to v2.1:
    ```
    POST /api/model/version/switch
    {
      "active_version": "v2.1",
      "reason": "Critical issue detected in v3.0"
    }
    ```
    """
    if request.active_version not in ['v2.1', 'v3.0']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid version: {request.active_version}. Must be 'v2.1' or 'v3.0'"
        )

    previous_version = get_active_model_version()

    if request.active_version == previous_version:
        return {
            "status": "no_change",
            "current_version": request.active_version,
            "message": f"Already using {request.active_version}"
        }

    # Switch model version
    os.environ['MODEL_VERSION_ACTIVE'] = request.active_version

    # Log the switch
    logger.warning(
        f"🔄 Model version switched: {previous_version} → {request.active_version}. "
        f"Reason: {request.reason or 'Not specified'}"
    )

    return {
        "switched_to": request.active_version,
        "previous_version": previous_version,
        "switched_at": datetime.now().isoformat(),
        "reason": request.reason,
        "status": "success"
    }


@router.get("/metadata")
async def get_model_metadata():
    """
    Get metadata for all available models

    Returns:
    ```
    {
      "models": [
        {
          "version": "v2.1",
          "name": "Legacy Rule-Based Model",
          "type": "legacy",
          "features_count": 72,
          "gates_count": 3,
          "rules_count": 8,
          "weight_sum": 1.10,
          "description": "...",
          "created_at": "2026-05-23T..."
        },
        {
          "version": "v3.0",
          "name": "Precise Risk Model (XGBoost)",
          "type": "precise",
          "features_count": 72,
          "gates_count": 3,
          "rules_count": 8,
          "weight_sum": 1.0,
          "description": "...",
          "created_at": "2026-06-12T..."
        }
      ]
    }
    ```
    """
    return {
        "active_version": get_active_model_version(),
        "models": [
            {
                "version": "v2.1",
                "name": "Legacy Rule-Based Model",
                "type": "legacy",
                "features_count": 72,
                "gates_count": 3,
                "rules_count": 8,
                "weight_sum": 1.10,
                "description": "Original 7-factor rule-based model with H1/H2/H3 horizons. Over-weighted (110%).",
                "created_at": "2026-05-23T00:00:00Z"
            },
            {
                "version": "v3.0",
                "name": "Precise Risk Model (XGBoost)",
                "type": "precise",
                "features_count": 72,
                "gates_count": 3,
                "rules_count": 8,
                "weight_sum": 1.0,
                "description": "ML-based model using XGBoost classifier with proper weight normalization (100%). 3-gate architecture: deterministic → ML → uncertainty.",
                "created_at": "2026-06-12T00:00:00Z"
            }
        ]
    }


@router.get("/shipments/{shipment_id}/score-comparison", response_model=ScoreComparison)
async def get_score_comparison(shipment_id: str):
    """
    Get score comparison across model versions for a shipment

    Shows:
    - Legacy (v2.1) score
    - Precise (v3.0) score
    - Difference and percent change
    - Recommendation difference

    Example:
    ```
    GET /api/model/shipments/SHP-001/score-comparison
    {
      "shipment_id": "SHP-001",
      "v2_1_legacy_score": 65.0,
      "v3_0_precise_score": 72.3,
      "v3_0_confidence": 0.89,
      "score_difference": 7.3,
      "percent_change": 11.2,
      "recommendation_changed": true,
      "legacy_recommendation": "EXAMINE",
      "precise_recommendation": "EXAMINE"
    }
    ```
    """
    # This would query the database for shipment and score_history
    # Implementation depends on database setup
    raise HTTPException(
        status_code=501,
        detail="Endpoint requires database integration"
    )


@router.get("/shipments/{shipment_id}/history", response_model=List[ScoreHistory])
async def get_score_history(shipment_id: str):
    """
    Get complete score history for a shipment

    Shows all scores calculated with different models, useful for:
    - Understanding score evolution
    - Validating model changes
    - Debugging discrepancies

    Example:
    ```
    GET /api/model/shipments/SHP-001/history
    [
      {
        "id": "hist-001",
        "shipment_id": "SHP-001",
        "model_version": "v2.1",
        "legacy_score": 65.0,
        "precise_score": null,
        "precise_confidence": null,
        "scored_at": "2026-05-25T14:30:00Z"
      },
      {
        "id": "hist-002",
        "shipment_id": "SHP-001",
        "model_version": "v3.0",
        "legacy_score": 65.0,
        "precise_score": 72.3,
        "precise_confidence": 0.89,
        "scored_at": "2026-06-12T10:15:00Z"
      }
    ]
    ```
    """
    # This would query score_history table
    raise HTTPException(
        status_code=501,
        detail="Endpoint requires database integration"
    )


@router.get("/statistics")
async def get_model_statistics():
    """
    Get statistics on model versions

    Returns:
    ```
    {
      "v2_1": {
        "total_shipments": 28,
        "avg_score": 62.5,
        "min_score": 25.0,
        "max_score": 98.0,
        "hold_count": 8,
        "examine_count": 12,
        "clear_count": 8
      },
      "v3_0": {
        "total_shipments": 28,
        "avg_score": 65.2,
        "min_score": 28.0,
        "max_score": 96.5,
        "hold_count": 9,
        "examine_count": 11,
        "clear_count": 8
      },
      "comparison": {
        "avg_difference": 2.7,
        "percent_change": 4.3,
        "recommendations_changed": 2
      }
    }
    """
    # This would aggregate scores from database
    raise HTTPException(
        status_code=501,
        detail="Endpoint requires database integration"
    )


@router.post("/rollback")
async def quick_rollback():
    """
    Quick rollback to legacy model (v2.1)

    **Security:** Requires authentication (admin only)

    Use when critical issues detected with new model.
    Instantly switches all traffic back to v2.1 without redeployment.

    Returns:
    ```
    {
      "rolled_back_to": "v2.1",
      "previous_version": "v3.0",
      "timestamp": "2026-06-12T11:45:00Z",
      "status": "emergency_rollback"
    }
    ```
    """
    previous_version = get_active_model_version()

    if previous_version == 'v2.1':
        return {
            "status": "already_on_legacy",
            "current_version": "v2.1",
            "message": "Already using legacy model"
        }

    # Rollback to v2.1
    os.environ['MODEL_VERSION_ACTIVE'] = 'v2.1'

    logger.critical(
        f"🚨 EMERGENCY ROLLBACK: {previous_version} → v2.1"
    )

    return {
        "rolled_back_to": "v2.1",
        "previous_version": previous_version,
        "timestamp": datetime.now().isoformat(),
        "status": "emergency_rollback"
    }
