"""Metrics and monitoring endpoints."""
import logging
from flask import request, Blueprint, current_app
from datetime import datetime

logger = logging.getLogger(__name__)

metrics_bp = Blueprint("metrics", __name__)

# Metrics storage
METRICS_STORE = {
    "scores_computed": 0,
    "cache_hits": 0,
    "cache_misses": 0,
    "errors": 0,
    "total_requests": 0,
}


@metrics_bp.route("/summary", methods=["GET"])
def get_metrics_summary():
    """
    Get metrics summary for the risk engine.

    Returns:
        Current metrics state
    """
    try:
        total_requests = METRICS_STORE["total_requests"]
        cache_hit_rate = (
            METRICS_STORE["cache_hits"] / total_requests
            if total_requests > 0
            else 0
        )
        error_rate = (
            METRICS_STORE["errors"] / total_requests * 100
            if total_requests > 0
            else 0
        )

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "scores_computed": METRICS_STORE["scores_computed"],
            "cache_hits": METRICS_STORE["cache_hits"],
            "cache_misses": METRICS_STORE["cache_misses"],
            "cache_hit_rate": round(cache_hit_rate * 100, 2),
            "total_requests": total_requests,
            "errors": METRICS_STORE["errors"],
            "error_rate": round(error_rate, 2),
        }, 200

    except Exception as e:
        logger.error(f"Error in get_metrics_summary: {e}")
        return {"error": str(e)}, 500


@metrics_bp.route("/model-info", methods=["GET"])
def get_model_info():
    """
    Get model configuration and metadata.

    Returns:
        Model information
    """
    try:
        risk_model = current_app.risk_model
        model_info = risk_model.get_model_info()

        return {
            "model_info": model_info,
            "timestamp": datetime.utcnow().isoformat(),
        }, 200

    except Exception as e:
        logger.error(f"Error in get_model_info: {e}")
        return {"error": str(e)}, 500


@metrics_bp.route("/factors", methods=["GET"])
def get_factors():
    """
    Get factor definitions and weights.

    Returns:
        Factor configuration
    """
    try:
        risk_model = current_app.risk_model
        factors = risk_model.factors
        weights = risk_model.factor_weights

        return {
            "factors_count": len(factors),
            "factors": factors,
            "weights": weights,
            "timestamp": datetime.utcnow().isoformat(),
        }, 200

    except Exception as e:
        logger.error(f"Error in get_factors: {e}")
        return {"error": str(e)}, 500


@metrics_bp.route("/gates", methods=["GET"])
def get_gates():
    """
    Get gate definitions.

    Returns:
        Gate configuration
    """
    try:
        risk_model = current_app.risk_model
        gates = risk_model.gates

        return {
            "gates_count": len(gates),
            "gates": gates,
            "timestamp": datetime.utcnow().isoformat(),
        }, 200

    except Exception as e:
        logger.error(f"Error in get_gates: {e}")
        return {"error": str(e)}, 500


@metrics_bp.route("/drift-report", methods=["GET"])
def get_drift_report():
    """
    Get model drift detection report.

    Returns:
        Drift analysis
    """
    try:
        from services.drift_detection import DriftDetector
        drift_detector = DriftDetector()
        report = drift_detector.get_health_report()

        return {
            "drift_report": report,
            "timestamp": datetime.utcnow().isoformat(),
        }, 200

    except Exception as e:
        logger.error(f"Error in get_drift_report: {e}")
        return {"error": str(e)}, 500


@metrics_bp.route("/performance", methods=["POST"])
def record_performance():
    """
    Record performance metrics for a scoring operation.

    Request body:
    {
        "operation": "score" | "batch_score" | "cache_hit",
        "duration_ms": 45.5,
        "entity_count": 1,
        "success": true
    }

    Returns:
        Performance acknowledgment
    """
    try:
        data = request.get_json()
        if not data:
            return {"error": "Missing request body"}, 400

        operation = data.get("operation", "unknown")
        success = data.get("success", True)

        METRICS_STORE["total_requests"] += 1

        if operation == "score" and success:
            METRICS_STORE["scores_computed"] += 1
        elif operation == "cache_hit":
            METRICS_STORE["cache_hits"] += 1
        elif operation == "cache_miss":
            METRICS_STORE["cache_misses"] += 1

        if not success:
            METRICS_STORE["errors"] += 1

        logger.debug(f"Performance recorded: {operation}, success={success}")

        return {
            "message": "Performance metrics recorded",
            "operation": operation,
            "timestamp": datetime.utcnow().isoformat(),
        }, 200

    except Exception as e:
        logger.error(f"Error in record_performance: {e}")
        return {"error": str(e)}, 500


@metrics_bp.route("/reset", methods=["POST"])
def reset_metrics():
    """
    Reset metrics counters (admin only).

    Returns:
        Confirmation message
    """
    try:
        global METRICS_STORE
        METRICS_STORE = {
            "scores_computed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0,
            "total_requests": 0,
        }

        logger.warning("Metrics reset by admin")
        return {"message": "Metrics reset successfully"}, 200

    except Exception as e:
        logger.error(f"Error in reset_metrics: {e}")
        return {"error": str(e)}, 500
