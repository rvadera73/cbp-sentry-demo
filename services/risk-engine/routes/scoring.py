"""Scoring endpoints for risk calculation."""
import logging
from flask import request, Blueprint, current_app

logger = logging.getLogger(__name__)

scoring_bp = Blueprint("scoring", __name__)

# Global flag to initialize model once
_models_initialized = False


def _ensure_models_loaded():
    """Lazy load models on first use."""
    global _models_initialized
    if _models_initialized:
        return
    if current_app.risk_model is None:
        _models_initialized = False
    else:
        _models_initialized = True


@scoring_bp.route("/score", methods=["POST"])
def score_entity():
    """
    Score an entity for risk.

    Request body:
    {
        "entity_id": "string",
        "entity_data": {
            "entity_risk_score": 25,
            "historical_violation_count": 5,
            "connectivity_score": 40,
            "trade_frequency_anomaly": 35,
            "sanctioned_status": 0,
            "jurisdiction_risk": 20,
            "product_sensitivity": 15
        }
    }

    Returns:
        Risk score result with factors, gates, rules, and final score
    """
    try:
        data = request.get_json()
        if not data:
            return {"error": "Missing request body"}, 400

        entity_id = data.get("entity_id")
        entity_data = data.get("entity_data", {})

        if not entity_id:
            return {"error": "Missing entity_id"}, 400

        if not entity_data:
            return {"error": "Missing entity_data"}, 400

        # Check cache first
        from services.cache_service import cache_risk_score, get_cached_risk_score
        cached_score = get_cached_risk_score(entity_id)
        if cached_score:
            return {"source": "cache", **cached_score}, 200

        # Score the entity
        risk_model = current_app.risk_model
        entity_data["id"] = entity_id
        result = risk_model.score_entity(entity_data)

        if "error" in result:
            return result, 400

        # Cache the result
        cache_risk_score(entity_id, result)

        return {"source": "computed", **result}, 200

    except Exception as e:
        logger.error(f"Error in score_entity: {e}")
        return {"error": str(e)}, 500


@scoring_bp.route("/batch-score", methods=["POST"])
def batch_score():
    """
    Score multiple entities in batch.

    Request body:
    {
        "entities": [
            {
                "entity_id": "string",
                "entity_data": {...}
            }
        ]
    }

    Returns:
        List of scored entities
    """
    try:
        data = request.get_json()
        if not data or "entities" not in data:
            return {"error": "Missing entities list"}, 400

        entities = data.get("entities", [])
        risk_model = current_app.risk_model

        from services.cache_service import cache_risk_score, get_cached_risk_score

        results = []
        for entity in entities:
            entity_id = entity.get("entity_id")
            entity_data = entity.get("entity_data", {})

            if not entity_id or not entity_data:
                continue

            # Check cache
            cached = get_cached_risk_score(entity_id)
            if cached:
                results.append({"source": "cache", **cached})
                continue

            # Score
            entity_data["id"] = entity_id
            result = risk_model.score_entity(entity_data)

            if "error" not in result:
                cache_risk_score(entity_id, result)
                results.append({"source": "computed", **result})

        return {"entities_scored": len(results), "results": results}, 200

    except Exception as e:
        logger.error(f"Error in batch_score: {e}")
        return {"error": str(e)}, 500


@scoring_bp.route("/score/<entity_id>", methods=["GET"])
def get_cached_score(entity_id: str):
    """
    Get cached risk score for an entity.

    Returns:
        Cached score or 404 if not found
    """
    try:
        from services.cache_service import get_cached_risk_score
        cached = get_cached_risk_score(entity_id)
        if cached:
            return {"source": "cache", **cached}, 200
        return {"error": "No cached score found", "entity_id": entity_id}, 404

    except Exception as e:
        logger.error(f"Error in get_cached_score: {e}")
        return {"error": str(e)}, 500


@scoring_bp.route("/score/<entity_id>", methods=["DELETE"])
def invalidate_score_cache(entity_id: str):
    """
    Invalidate cached risk score for an entity.

    Returns:
        Success message
    """
    try:
        from services.cache_service import invalidate_risk_cache
        invalidate_risk_cache(entity_id)
        return {"message": f"Cache invalidated for entity {entity_id}"}, 200

    except Exception as e:
        logger.error(f"Error in invalidate_score_cache: {e}")
        return {"error": str(e)}, 500


@scoring_bp.route("/clear-cache", methods=["POST"])
def clear_all_cache():
    """
    Clear all risk score cache.

    Returns:
        Success message
    """
    try:
        from services.cache_service import invalidate_risk_cache
        invalidate_risk_cache(None)
        return {"message": "All cache cleared"}, 200

    except Exception as e:
        logger.error(f"Error in clear_all_cache: {e}")
        return {"error": str(e)}, 500
