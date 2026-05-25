"""
Risk Scoring API Routes - 7-Factor Model

Single endpoint for comprehensive risk assessment using the risk_scoring_engine.
Returns full component breakdown, calculation table, and final score.
Calls sentry-data microservice to persist results.
"""
from fastapi import APIRouter, HTTPException, status
from typing import Optional, Dict, Any
from datetime import datetime
import logging
import json
import httpx
import os

# Import the correct engine (single source of truth)
from risk_scoring_engine import RiskScoringEngine
from risk_models import RiskScoreBreakdown, RiskComponentScore

logger = logging.getLogger(__name__)

router = APIRouter(tags=["risk-scoring"])

# Data service URL from environment (sentry-data microservice)
DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://localhost:8005")

# Initialize engine once (loads ML models on startup)
_engine = None

def get_engine():
    """Get or initialize the risk scoring engine"""
    global _engine
    if _engine is None:
        _engine = RiskScoringEngine()
    return _engine

async def save_risk_score_cache(shipment_id: str, score_data: Dict[str, Any]) -> Optional[str]:
    """Call sentry-data to persist risk score cache (clean schema)"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{DATA_SERVICE_URL}/risk-scores/cache/{shipment_id}",
                json=score_data
            )
            if response.status_code in [200, 201]:
                result = response.json()
                return result.get("cache_id")
            else:
                logger.error(f"Data service returned {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Failed to save risk score cache via data service: {e}")
        return None


async def record_transaction(txn_data: Dict[str, Any]) -> Optional[str]:
    """Call sentry-data to record risk score transaction (immutable audit trail)"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{DATA_SERVICE_URL}/risk-scores/transactions",
                json=txn_data
            )
            if response.status_code in [200, 201]:
                result = response.json()
                return result.get("transaction_id")
            else:
                logger.error(f"Data service returned {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Failed to record transaction via data service: {e}")
        return None


async def record_altana_scenario_in_data_service(altana_data: Dict[str, Any]) -> Optional[str]:
    """Call sentry-data to record Altana API scenario"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{DATA_SERVICE_URL}/risk-scores/altana-scenario",
                json=altana_data
            )
            if response.status_code in [200, 201]:
                result = response.json()
                return result.get("scenario_id")
            else:
                logger.error(f"Data service returned {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Failed to record Altana scenario via data service: {e}")
        return None


@router.post(
    "/full-breakdown/{shipment_id}",
    summary="Calculate Full Risk Score Breakdown",
    description="Calculate comprehensive risk score using 7-factor ML model"
)
async def calculate_full_risk_breakdown(
    shipment_id: str,
    shipment_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate risk score using 7-factor model with full transparency.

    **Factors (100 points total):**
    - Documentation Risk (25%) — Element 9 mismatch, ISF amendments, manifest completeness
    - Commodity Sensitivity (15%) — Tariff rate, export control, UFLPA risk
    - Routing Risk (15%) — AIS dwell, port selection, vessel flag
    - Party Profile Risk (15%) — Shipper age, violations, OFAC status
    - Corridor Risk (20%) — Country-pair baseline, tariff evasion incentive
    - Pattern Anomaly (10%) — Pricing anomaly, transshipment ML patterns
    - Time Sensitivity (10%) — Pre-tariff timing, seasonal anomalies

    **Returns:**
    - All component scores with weights and rationale
    - Calculation table showing every component contribution
    - Final score (0-100) with confidence interval
    - Corridor adjustments and additional penalties/bonuses

    Args:
        shipment_id: Unique shipment identifier
        shipment_data: Dict with shipment fields (hs_code, origin_country, etc.)

    Returns:
        Dict with full RiskScoreBreakdown including components, calculation table, final score

    Example:
        ```
        POST /api/score/full-breakdown/shipment-123
        {
            "id": "shipment-123",
            "element9_is_mismatch": true,
            "hs_code": "7604.10.1000",
            "origin_country": "VN",
            "destination_country": "US",
            ...
        }

        Response:
        {
            "shipment_id": "shipment-123",
            "components": [...],
            "subtotal": 44.3,
            "final_score": 87.0,
            "confidence_interval": "±2.5",
            "calculation_table": {...}
        }
        ```
    """
    try:
        # Validate input
        if not shipment_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shipment data is required"
            )

        if "id" not in shipment_data:
            shipment_data["id"] = shipment_id

        logger.info(f"Calculating 7-factor risk score for {shipment_id}")

        # Get engine and calculate
        engine = get_engine()
        breakdown = engine.score_shipment(shipment_data)

        # Convert breakdown to dict for JSON response
        response_data = breakdown.to_dict()

        # Persist risk score cache via sentry-data (non-blocking)
        try:
            breakdown_json = json.dumps(response_data)
            score_data = {
                "final_score": breakdown.final_score,
                "breakdown_json": breakdown_json,
                "current_model_version": "7factor-v1.0"
            }
            cache_id = await save_risk_score_cache(shipment_id, score_data)
            if cache_id:
                logger.info(f"Saved risk score cache for {shipment_id} (cache_id={cache_id})")

                # Record as initial_calculation transaction (non-blocking)
                try:
                    txn_data = {
                        "shipment_id": shipment_id,
                        "new_final_score": breakdown.final_score,
                        "new_breakdown_json": breakdown_json,
                        "transaction_type": "initial_calculation",
                        "transaction_reason": "initial_7factor_calculation",
                        "previous_final_score": None,
                        "previous_breakdown_json": None,
                        "triggered_by": "system",
                        "triggered_by_model_version": "7factor-v1.0"
                    }
                    txn_id = await record_transaction(txn_data)
                    if txn_id:
                        logger.info(f"Recorded transaction for {shipment_id} (txn_id={txn_id})")
                except Exception as txn_error:
                    logger.warning(f"Failed to record transaction for {shipment_id}: {txn_error}")
            else:
                logger.warning(f"Failed to save risk score cache for {shipment_id}")
        except Exception as db_error:
            logger.error(f"Failed to persist risk score to database: {db_error}")
            # Don't fail the request if database save fails, just log it

        logger.info(
            f"Score calculated: {shipment_id} → {breakdown.final_score}/100 "
            f"({breakdown.confidence_interval})"
        )

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating risk score for {shipment_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate risk score: {str(e)}"
        )


@router.get(
    "/full-breakdown/{shipment_id}",
    summary="Get Risk Score (GET method)",
    description="Retrieve previously calculated risk score"
)
async def get_risk_breakdown(
    shipment_id: str,
    recalculate: bool = False
) -> Dict[str, Any]:
    """
    Get risk score for a shipment (GET method for convenience).

    Args:
        shipment_id: Shipment identifier
        recalculate: If True, forces recalculation even if cached

    Returns:
        Risk score with calculation details
    """
    try:
        logger.info(f"Fetching risk score for {shipment_id}")
        # In production, would check cache here
        # For now, requires POST with full data
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail="Use POST /api/score/full-breakdown/{id} with shipment data"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching risk score: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/health-check",
    summary="Health Check - Verify Scoring Engine",
    description="Test that the risk scoring engine is loaded and working"
)
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint to verify the scoring engine is operational.
    Tests ML model loading and basic scoring functionality.

    Returns:
        Status, engine version, and test score result
    """
    try:
        engine = get_engine()

        # Test with minimal data
        test_shipment = {
            "id": "health-check",
            "element9_is_mismatch": False,
            "origin_country": "US",
            "destination_country": "US"
        }

        result = engine.score_shipment(test_shipment)

        return {
            "status": "healthy",
            "engine": "RiskScoringEngine",
            "factors": 7,
            "test_score": result.final_score,
            "timestamp": datetime.utcnow().isoformat(),
            "models_loaded": {
                "isolation_forest": engine.isolation_forest is not None,
                "lgbm_classifier": engine.lgbm_classifier is not None
            }
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get(
    "/staleness-check/{shipment_id}",
    summary="Check Score Staleness",
    description="Check if a cached score is stale due to model versioning"
)
async def check_staleness(shipment_id: str) -> Dict[str, Any]:
    """
    Check if a shipment's cached score is stale.
    A score is stale if it was calculated with an older model version.

    Returns:
        Staleness status and comparison details
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get cached score
            cache_response = await client.get(
                f"{DATA_SERVICE_URL}/risk-scores/cache/{shipment_id}"
            )
            if cache_response.status_code != 200:
                raise HTTPException(
                    status_code=404,
                    detail=f"No score found for shipment {shipment_id}"
                )

            cached = cache_response.json()

            # Get active model
            active_response = await client.get(
                f"{DATA_SERVICE_URL}/model-versions/active"
            )
            if active_response.status_code != 200:
                return {
                    "shipment_id": shipment_id,
                    "status": "error",
                    "message": "No active model version found"
                }

            active_model = active_response.json()

            is_stale = cached.get("is_stale") or (
                cached.get("current_model_version") != active_model.get("id")
            )

            return {
                "shipment_id": shipment_id,
                "is_stale": is_stale,
                "cached_score": cached.get("final_score"),
                "cached_model_version": cached.get("current_model_version"),
                "active_model_version": active_model.get("id"),
                "cached_timestamp": cached.get("calculation_timestamp"),
                "message": "Score is stale - recalculation recommended" if is_stale else "Score is fresh"
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Staleness check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check staleness: {str(e)}"
        )


@router.post(
    "/recalculate-with-comparison/{shipment_id}",
    summary="Recalculate Stale Score with Comparison",
    description="Recalculate a score with current model and show comparison with cached version"
)
async def recalculate_with_comparison(
    shipment_id: str,
    shipment_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Recalculate a shipment's risk score with the current model and show
    side-by-side comparison with the cached (potentially stale) score.

    Returns:
        Cached score, recalculated score, delta, and change analysis
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get cached score
            cache_response = await client.get(
                f"{DATA_SERVICE_URL}/risk-scores/cache/{shipment_id}"
            )
            cached_score = None
            cached_breakdown = None
            if cache_response.status_code == 200:
                cached = cache_response.json()
                cached_score = cached.get("final_score")
                cached_breakdown = json.loads(cached.get("breakdown_json", "{}"))

            # Recalculate with current model
            engine = get_engine()
            if "id" not in shipment_data:
                shipment_data["id"] = shipment_id

            new_breakdown = engine.score_shipment(shipment_data)
            new_score = new_breakdown.final_score
            new_breakdown_json = json.dumps(new_breakdown.to_dict())

            # Calculate delta
            score_delta = None
            if cached_score is not None:
                score_delta = new_score - cached_score

            # Get active model version
            model_response = await client.get(
                f"{DATA_SERVICE_URL}/model-versions/active"
            )
            active_model = model_response.json() if model_response.status_code == 200 else None

            # Record the transaction
            if cached_score is not None and score_delta is not None:
                txn_data = {
                    "shipment_id": shipment_id,
                    "new_final_score": new_score,
                    "new_breakdown_json": new_breakdown_json,
                    "transaction_type": "model_update",
                    "transaction_reason": f"recalculation_on_detail_view",
                    "previous_final_score": cached_score,
                    "previous_breakdown_json": json.dumps(cached_breakdown) if cached_breakdown else None,
                    "triggered_by": "user:analyst",
                    "triggered_by_model_version": active_model.get("id") if active_model else "7factor-v1.0"
                }
                await record_transaction(txn_data)

                # Update cache with new score
                cache_data = {
                    "final_score": new_score,
                    "breakdown_json": new_breakdown_json,
                    "current_model_version": active_model.get("id") if active_model else "7factor-v1.0"
                }
                await save_risk_score_cache(shipment_id, cache_data)

            return {
                "shipment_id": shipment_id,
                "cached_score": {
                    "final_score": cached_score,
                    "model_version": cached_breakdown.get("model_version") if cached_breakdown else None,
                    "breakdown": cached_breakdown
                },
                "recalculated_score": {
                    "final_score": new_score,
                    "model_version": active_model.get("id") if active_model else "7factor-v1.0",
                    "breakdown": new_breakdown.to_dict()
                },
                "comparison": {
                    "score_delta": score_delta,
                    "delta_direction": "increased" if score_delta and score_delta > 0 else ("decreased" if score_delta else None),
                    "percent_change": (score_delta / cached_score * 100) if cached_score and score_delta else None,
                    "recalculation_timestamp": datetime.utcnow().isoformat()
                },
                "message": "Score recalculated and comparison generated. Cache updated."
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recalculation with comparison failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to recalculate score: {str(e)}"
        )
