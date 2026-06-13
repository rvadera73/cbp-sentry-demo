"""
Phase 2: Risk Scoring Endpoint with Feature Flag & Fallback
Routes to either:
  1. Precise Risk Engine API (new model) - if flag enabled
  2. Legacy risk_scoring_engine (old model) - as fallback
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any, Tuple
from flask import Blueprint, request, jsonify, current_app

logger = logging.getLogger(__name__)

# Blueprint for scoring routes
scoring_bp = Blueprint('scoring_phase2', __name__, url_prefix='/api')


@scoring_bp.route('/shipment/<shipment_id>/risk-score', methods=['GET', 'POST'])
def score_shipment(shipment_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Score a shipment for risk

    Uses feature flag to route to either:
    - Precise Risk Engine API (new model)
    - Legacy risk_scoring_engine (fallback)

    Returns:
        JSON with: risk_score, confidence, explanation, model_version, status
    """
    start_time = datetime.utcnow()

    try:
        # Get shipment from request or database
        if request.method == 'POST':
            entity_data = request.get_json()
            if not entity_data:
                return {"error": "Missing request body"}, 400
        else:
            # Would normally fetch from database
            entity_data = {
                "id": shipment_id,
                "origin_country": "CN",
                "destination_country": "US",
                "hs_code": "8517.62",
                "declared_value_usd": 50000,
                "dwell_days": 2.5,
                "element9_is_mismatch": 0
            }

        # Determine which model to use
        use_new_model = current_app.config.get('USE_PRECISE_RISK_MODEL', False)

        logger.info(f"Scoring shipment {shipment_id} - Using {'new' if use_new_model else 'legacy'} model")

        try:
            if use_new_model:
                # Route to Precise Risk Engine
                result = _score_with_precise_risk_engine(shipment_id, entity_data)
                result['model_version'] = 'precise-risk-model-v1'
                result['route'] = 'new'
            else:
                # Use legacy model
                result = _score_with_legacy_model(shipment_id, entity_data)
                result['model_version'] = 'legacy'
                result['route'] = 'legacy'

        except Exception as e:
            logger.error(f"Error with new model, falling back to legacy: {str(e)}")
            # Fallback to legacy
            result = _score_with_legacy_model(shipment_id, entity_data)
            result['model_version'] = 'legacy'
            result['route'] = 'fallback'
            result['fallback_reason'] = str(e)

        # Add metadata
        result['shipment_id'] = shipment_id
        result['scored_at'] = datetime.utcnow().isoformat()
        result['latency_ms'] = (datetime.utcnow() - start_time).total_seconds() * 1000

        logger.info(f"Shipment {shipment_id} scored: {result['risk_score']:.2f} "
                   f"(model={result['route']}, latency={result['latency_ms']:.1f}ms)")

        return result, 200

    except Exception as e:
        logger.error(f"Fatal error in score_shipment: {str(e)}")
        return {
            "error": "Scoring failed",
            "message": str(e),
            "shipment_id": shipment_id
        }, 500


def _score_with_precise_risk_engine(shipment_id: str, entity_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score shipment using Precise Risk Engine API (new model)

    Args:
        shipment_id: Shipment identifier
        entity_data: Entity attributes

    Returns:
        Risk score result from API

    Raises:
        Exception: If API call fails
    """
    try:
        # Get client from app context
        if not hasattr(current_app, 'precise_risk_client'):
            from services.api.clients.precise_risk_client import PreciseRiskClient
            from config_phase2 import PRECISE_RISK_ENGINE_URL, PRECISE_RISK_ENGINE_TIMEOUT

            current_app.precise_risk_client = PreciseRiskClient(
                PRECISE_RISK_ENGINE_URL,
                PRECISE_RISK_ENGINE_TIMEOUT
            )

        client = current_app.precise_risk_client

        # Call Precise Risk Engine
        result = client.score_entity('cbp', shipment_id, entity_data)

        logger.debug(f"Precise Risk Engine response: {json.dumps(result, indent=2)}")

        return result

    except Exception as e:
        logger.error(f"Precise Risk Engine error: {str(e)}")
        raise


def _score_with_legacy_model(shipment_id: str, entity_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score shipment using legacy model (fallback)

    Args:
        shipment_id: Shipment identifier
        entity_data: Entity attributes

    Returns:
        Risk score from legacy model
    """
    try:
        # Simulate legacy model scoring
        # In production, would call actual legacy function
        # from services.risk_scoring_engine_legacy import score_shipment

        # For now, return synthetic result
        risk_score = min(
            100,
            (
                entity_data.get('element9_is_mismatch', 0) * 30 +
                entity_data.get('dwell_days', 0) * 5 +
                (1 - entity_data.get('declared_value_usd', 0) / 100000) * 10
            )
        )

        result = {
            "shipment_id": shipment_id,
            "risk_score": float(risk_score),
            "confidence": 0.75,
            "risk_level": "HIGH" if risk_score > 70 else "MEDIUM" if risk_score > 40 else "LOW",
            "factors": {
                "documentation_risk": 25,
                "routing_risk": 15,
                "commodity_risk": 15,
                "corridor_risk": 20,
                "party_risk": 15,
                "pattern_risk": 10,
                "time_sensitivity": 0
            }
        }

        logger.debug(f"Legacy model result: {json.dumps(result, indent=2)}")

        return result

    except Exception as e:
        logger.error(f"Legacy model error: {str(e)}")
        raise


@scoring_bp.route('/shipment/<shipment_id>/risk-score/compare', methods=['POST'])
def compare_models(shipment_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Score shipment with both models and compare results

    Used during Phase 2 for parallel testing and traffic ramping validation
    """
    try:
        entity_data = request.get_json()

        # Score with both models
        new_result = _score_with_precise_risk_engine(shipment_id, entity_data)
        legacy_result = _score_with_legacy_model(shipment_id, entity_data)

        # Compare results
        score_difference = abs(new_result['risk_score'] - legacy_result['risk_score'])
        agreement = "AGREE" if score_difference < 10 else "DIFFER"

        comparison = {
            "shipment_id": shipment_id,
            "new_model": new_result,
            "legacy_model": legacy_result,
            "comparison": {
                "score_difference": float(score_difference),
                "agreement": agreement,
                "new_score": float(new_result['risk_score']),
                "legacy_score": float(legacy_result['risk_score'])
            }
        }

        logger.info(f"Model comparison for {shipment_id}: {agreement} "
                   f"(diff={score_difference:.1f})")

        return comparison, 200

    except Exception as e:
        logger.error(f"Error in compare_models: {str(e)}")
        return {"error": str(e)}, 500


@scoring_bp.route('/feature-flag', methods=['GET', 'POST'])
def feature_flag() -> Tuple[Dict[str, Any], int]:
    """
    Get or set the USE_PRECISE_RISK_MODEL feature flag

    GET: Returns current flag value
    POST: Sets flag value (requires auth in production)
    """
    if request.method == 'GET':
        return {
            "feature": "USE_PRECISE_RISK_MODEL",
            "enabled": current_app.config.get('USE_PRECISE_RISK_MODEL', False),
            "traffic_percentage": current_app.config.get('TRAFFIC_PERCENTAGE', 0)
        }, 200

    elif request.method == 'POST':
        data = request.get_json()
        new_value = data.get('enabled', False)

        # In production, would validate auth here
        logger.warning(f"Feature flag changed: {new_value}")

        current_app.config['USE_PRECISE_RISK_MODEL'] = new_value
        current_app.config['TRAFFIC_PERCENTAGE'] = data.get('traffic_percentage', 0)

        return {
            "feature": "USE_PRECISE_RISK_MODEL",
            "enabled": new_value,
            "message": "Feature flag updated"
        }, 200

    return {"error": "Method not allowed"}, 405
