"""Rules management endpoints."""
import logging
from flask import request, Blueprint, current_app

logger = logging.getLogger(__name__)

rules_bp = Blueprint("rules", __name__)


@rules_bp.route("/list", methods=["GET"])
def list_rules():
    """
    List all configured rules.

    Returns:
        List of rules with metadata
    """
    try:
        risk_model = current_app.risk_model
        rules = risk_model.rules

        return {
            "rules_count": len(rules),
            "rules": [
                {
                    "name": r.get("name", "unknown"),
                    "description": r.get("description", ""),
                    "condition": r.get("condition", ""),
                    "action": r.get("action", ""),
                    "severity": r.get("severity", "medium"),
                }
                for r in rules
            ],
        }, 200

    except Exception as e:
        logger.error(f"Error in list_rules: {e}")
        return {"error": str(e)}, 500


@rules_bp.route("/<rule_name>", methods=["GET"])
def get_rule(rule_name: str):
    """
    Get details for a specific rule.

    Args:
        rule_name: Name of the rule

    Returns:
        Rule details or 404 if not found
    """
    try:
        risk_model = current_app.risk_model
        rule = next(
            (r for r in risk_model.rules if r.get("name") == rule_name), None
        )

        if not rule:
            return {"error": f"Rule not found: {rule_name}"}, 404

        return {
            "name": rule.get("name"),
            "description": rule.get("description"),
            "condition": rule.get("condition"),
            "action": rule.get("action"),
            "severity": rule.get("severity"),
        }, 200

    except Exception as e:
        logger.error(f"Error in get_rule: {e}")
        return {"error": str(e)}, 500


@rules_bp.route("/test", methods=["POST"])
def test_rule():
    """
    Test a rule against entity data.

    Request body:
    {
        "rule_name": "string",
        "entity_data": {...}
    }

    Returns:
        Rule evaluation result
    """
    try:
        data = request.get_json()
        if not data:
            return {"error": "Missing request body"}, 400

        rule_name = data.get("rule_name")
        entity_data = data.get("entity_data", {})

        if not rule_name:
            return {"error": "Missing rule_name"}, 400

        risk_model = current_app.risk_model
        rule = next(
            (r for r in risk_model.rules if r.get("name") == rule_name), None
        )

        if not rule:
            return {"error": f"Rule not found: {rule_name}"}, 404

        # Evaluate the rule
        factor_scores = risk_model._calculate_factor_scores(entity_data)
        condition = rule.get("condition", "")
        triggered = risk_model._evaluate_condition(condition, entity_data, factor_scores)

        return {
            "rule_name": rule_name,
            "triggered": triggered,
            "condition": condition,
            "action": rule.get("action"),
            "severity": rule.get("severity"),
        }, 200

    except Exception as e:
        logger.error(f"Error in test_rule: {e}")
        return {"error": str(e)}, 500


@rules_bp.route("/severity/<severity_level>", methods=["GET"])
def get_rules_by_severity(severity_level: str):
    """
    Get rules filtered by severity level.

    Args:
        severity_level: low, medium, high, or critical

    Returns:
        Filtered rules list
    """
    try:
        risk_model = current_app.risk_model
        filtered_rules = [
            r for r in risk_model.rules
            if r.get("severity", "medium").lower() == severity_level.lower()
        ]

        return {
            "severity_level": severity_level,
            "rules_count": len(filtered_rules),
            "rules": filtered_rules,
        }, 200

    except Exception as e:
        logger.error(f"Error in get_rules_by_severity: {e}")
        return {"error": str(e)}, 500
