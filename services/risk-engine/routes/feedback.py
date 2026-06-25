"""Feedback and model improvement endpoints."""
import logging
from flask import request, Blueprint
from datetime import datetime

logger = logging.getLogger(__name__)

feedback_bp = Blueprint("feedback", __name__)

# In-memory feedback storage (would use database in production)
FEEDBACK_STORE = []


@feedback_bp.route("/submit", methods=["POST"])
def submit_feedback():
    """
    Submit feedback on a risk score.

    Request body:
    {
        "entity_id": "string",
        "predicted_score": 45.5,
        "actual_outcome": "low_risk" | "high_risk",
        "correction_score": 35.0,
        "notes": "string"
    }

    Returns:
        Feedback acknowledgment
    """
    try:
        data = request.get_json()
        if not data:
            return {"error": "Missing request body"}, 400

        entity_id = data.get("entity_id")
        if not entity_id:
            return {"error": "Missing entity_id"}, 400

        feedback_record = {
            "id": len(FEEDBACK_STORE) + 1,
            "entity_id": entity_id,
            "predicted_score": data.get("predicted_score"),
            "actual_outcome": data.get("actual_outcome"),
            "correction_score": data.get("correction_score"),
            "notes": data.get("notes", ""),
            "timestamp": datetime.utcnow().isoformat(),
            "status": "recorded",
        }

        FEEDBACK_STORE.append(feedback_record)
        logger.info(f"Feedback recorded for entity {entity_id}")

        return {
            "id": feedback_record["id"],
            "message": "Feedback recorded successfully",
            "entity_id": entity_id,
        }, 201

    except Exception as e:
        logger.error(f"Error in submit_feedback: {e}")
        return {"error": str(e)}, 500


@feedback_bp.route("/list", methods=["GET"])
def list_feedback():
    """
    List all feedback records.

    Query parameters:
    - entity_id: Filter by entity
    - limit: Maximum number of records (default 100)
    - offset: Pagination offset (default 0)

    Returns:
        List of feedback records
    """
    try:
        entity_id = request.args.get("entity_id")
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))

        feedback_list = FEEDBACK_STORE
        if entity_id:
            feedback_list = [f for f in feedback_list if f["entity_id"] == entity_id]

        total = len(feedback_list)
        paginated = feedback_list[offset : offset + limit]

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "count": len(paginated),
            "feedback": paginated,
        }, 200

    except Exception as e:
        logger.error(f"Error in list_feedback: {e}")
        return {"error": str(e)}, 500


@feedback_bp.route("/<int:feedback_id>", methods=["GET"])
def get_feedback(feedback_id: int):
    """
    Get a specific feedback record.

    Returns:
        Feedback record or 404 if not found
    """
    try:
        feedback = next(
            (f for f in FEEDBACK_STORE if f["id"] == feedback_id), None
        )

        if not feedback:
            return {"error": f"Feedback not found: {feedback_id}"}, 404

        return feedback, 200

    except Exception as e:
        logger.error(f"Error in get_feedback: {e}")
        return {"error": str(e)}, 500


@feedback_bp.route("/analyze", methods=["POST"])
def analyze_feedback():
    """
    Analyze feedback patterns to identify model drift.

    Request body:
    {
        "window_days": 7
    }

    Returns:
        Analysis of feedback patterns
    """
    try:
        if not FEEDBACK_STORE:
            return {
                "message": "No feedback records available",
                "total_feedback": 0,
                "analysis": None,
            }, 200

        total = len(FEEDBACK_STORE)
        high_risk_feedback = [
            f for f in FEEDBACK_STORE
            if f.get("actual_outcome") == "high_risk"
        ]
        low_risk_feedback = [
            f for f in FEEDBACK_STORE
            if f.get("actual_outcome") == "low_risk"
        ]

        # Calculate average correction
        corrections = [
            abs(f.get("predicted_score", 0) - f.get("correction_score", 0))
            for f in FEEDBACK_STORE
            if f.get("correction_score") is not None
        ]
        avg_correction = sum(corrections) / len(corrections) if corrections else 0

        return {
            "total_feedback": total,
            "high_risk_feedback": len(high_risk_feedback),
            "low_risk_feedback": len(low_risk_feedback),
            "average_correction_magnitude": round(avg_correction, 2),
            "drift_detected": avg_correction > 10,
            "recommendation": (
                "Model recalibration recommended" if avg_correction > 10
                else "Model performing within tolerance"
            ),
        }, 200

    except Exception as e:
        logger.error(f"Error in analyze_feedback: {e}")
        return {"error": str(e)}, 500


@feedback_bp.route("/<int:feedback_id>/update", methods=["PATCH"])
def update_feedback(feedback_id: int):
    """
    Update a feedback record status.

    Request body:
    {
        "status": "recorded" | "processed" | "incorporated"
    }

    Returns:
        Updated feedback record
    """
    try:
        data = request.get_json()
        if not data:
            return {"error": "Missing request body"}, 400

        feedback = next(
            (f for f in FEEDBACK_STORE if f["id"] == feedback_id), None
        )

        if not feedback:
            return {"error": f"Feedback not found: {feedback_id}"}, 404

        new_status = data.get("status")
        if new_status:
            feedback["status"] = new_status
            feedback["updated_at"] = datetime.utcnow().isoformat()

        logger.info(f"Feedback {feedback_id} updated to status: {new_status}")
        return feedback, 200

    except Exception as e:
        logger.error(f"Error in update_feedback: {e}")
        return {"error": str(e)}, 500
