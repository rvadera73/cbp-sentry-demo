"""Generic, config-driven PreciseRiskModel implementation with ML integration."""
import logging
import yaml
import os
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class PreciseRiskModel:
    """
    Config-driven risk scoring model with ML integration.

    Loaded from YAML configuration (cbp.yaml) with:
    - 7 factors (entity characteristics)
    - 3 gates (threshold-based decision points)
    - 8 rules (conditional logic)
    - ML models (XGBoost, Isolation Forest, SHAP)
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize PreciseRiskModel.

        Args:
            config_path: Path to cbp.yaml configuration
        """
        # Try to find config file relative to this file first
        default_config = os.path.join(os.path.dirname(__file__), '..', 'config', 'cbp.yaml')

        self.config_path = config_path or os.getenv(
            "MODEL_CONFIG_PATH",
            default_config
        )
        self.config = {}
        self.factors = []
        self.gates = []
        self.rules = []
        self.factor_weights = {}
        self.model_loader = None
        self.ml_models_available = False
        logger.info(f"PreciseRiskModel initialized with config: {self.config_path}")

    def load_config(self) -> bool:
        """
        Load configuration from YAML file.

        Returns:
            Success flag
        """
        try:
            if not os.path.exists(self.config_path):
                logger.error(f"Config file not found: {self.config_path}")
                return False

            with open(self.config_path, "r") as f:
                self.config = yaml.safe_load(f)

            # Extract factors
            self.factors = self.config.get("factors", [])
            logger.info(f"Loaded {len(self.factors)} factors")

            # Extract gates
            self.gates = self.config.get("gates", [])
            logger.info(f"Loaded {len(self.gates)} gates")

            # Extract rules
            self.rules = self.config.get("rules", [])
            logger.info(f"Loaded {len(self.rules)} rules")

            # Extract factor weights
            self.factor_weights = self.config.get("factor_weights", {})
            logger.info(f"Loaded factor weights: {self.factor_weights}")

            return True
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return False

    def load_ml_models(self) -> bool:
        """
        Load trained ML models (XGBoost, Isolation Forest, SHAP).

        Returns:
            Success flag
        """
        try:
            from .model_loader import ModelLoader

            models_dir = os.getenv("ML_MODELS_DIR", "/home/rahulvadera/cbp-sentry/models")
            self.model_loader = ModelLoader(models_dir)

            if self.model_loader.load_all_models():
                self.ml_models_available = True
                logger.info("ML models loaded successfully")
                return True
            else:
                logger.warning("Some ML models failed to load")
                return False

        except Exception as e:
            logger.warning(f"Failed to load ML models: {e}")
            self.ml_models_available = False
            return False

    def score_entity(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score an entity based on configured factors, rules, and ML models.

        Args:
            entity_data: Entity attributes to score

        Returns:
            Risk score result with factors, gates, ML scores, final score
        """
        if not self.factors or not self.rules or not self.gates:
            logger.error("Model not properly configured")
            return {"error": "Model not configured", "score": None}

        try:
            # Calculate factor scores
            factor_scores = self._calculate_factor_scores(entity_data)

            # Apply rules
            rule_results = self._apply_rules(entity_data, factor_scores)

            # Apply gates
            gate_results = self._apply_gates(entity_data, factor_scores, rule_results)

            # Calculate final score (rule-based)
            final_score = self._calculate_final_score(factor_scores, rule_results)

            # Apply ML models if available
            ml_scores = {}
            if self.ml_models_available and self.model_loader:
                try:
                    # Try to build feature vector and get ML scores
                    features = self._extract_features(entity_data)
                    if features is not None:
                        ml_scores = self._apply_ml_model(features)
                        # Blend ML score with rule-based score
                        final_score = 0.6 * final_score + 0.4 * ml_scores.get("xgboost_probability", final_score)
                except Exception as e:
                    logger.warning(f"ML scoring failed: {e}, using rule-based score only")

            result = {
                "entity_id": entity_data.get("id", "unknown"),
                "score": round(final_score, 2),
                "factors": factor_scores,
                "rules": rule_results,
                "gates": gate_results,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Add ML scores if available
            if ml_scores:
                result["ml_scores"] = ml_scores

            return result

        except Exception as e:
            logger.error(f"Error scoring entity: {e}")
            return {"error": str(e), "score": None}

    def _calculate_factor_scores(self, entity_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate scores for each factor.

        Args:
            entity_data: Entity data

        Returns:
            Factor scores dictionary
        """
        factor_scores = {}
        for factor in self.factors:
            name = factor.get("name", "unknown")
            value = entity_data.get(name, 0)
            weight = self.factor_weights.get(name, 1.0)

            # Simple scoring: normalize value and apply weight
            score = float(value) * weight if isinstance(value, (int, float)) else 0.0
            factor_scores[name] = min(100.0, max(0.0, score))

        return factor_scores

    def _apply_rules(
        self, entity_data: Dict[str, Any], factor_scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Apply conditional rules.

        Args:
            entity_data: Entity data
            factor_scores: Calculated factor scores

        Returns:
            Rule evaluation results
        """
        rule_results = {}
        for rule in self.rules:
            rule_name = rule.get("name", "unknown")
            condition = rule.get("condition", "")
            action = rule.get("action", "")

            # Simple rule evaluation: check if condition is met
            triggered = self._evaluate_condition(condition, entity_data, factor_scores)
            rule_results[rule_name] = {
                "triggered": triggered,
                "condition": condition,
                "action": action,
            }

        return rule_results

    def _apply_gates(
        self,
        entity_data: Dict[str, Any],
        factor_scores: Dict[str, float],
        rule_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Apply threshold-based gates.

        Args:
            entity_data: Entity data
            factor_scores: Calculated factor scores
            rule_results: Rule results

        Returns:
            Gate evaluation results
        """
        gate_results = {}
        for gate in self.gates:
            gate_name = gate.get("name", "unknown")
            threshold = gate.get("threshold", 50.0)
            factor = gate.get("factor", "score")

            # Get the value to compare
            if factor in factor_scores:
                value = factor_scores[factor]
            else:
                value = entity_data.get(factor, 0)

            passed = float(value) >= threshold
            gate_results[gate_name] = {
                "passed": passed,
                "threshold": threshold,
                "value": value,
            }

        return gate_results

    def _evaluate_condition(
        self,
        condition: str,
        entity_data: Dict[str, Any],
        factor_scores: Dict[str, float],
    ) -> bool:
        """
        Evaluate a condition string (placeholder for rule engine).

        Args:
            condition: Condition description
            entity_data: Entity data
            factor_scores: Factor scores

        Returns:
            Condition evaluation result
        """
        # Placeholder: simple string matching
        # In production, use a proper rule engine
        if not condition:
            return False
        return True  # Default: all conditions pass for now

    def _calculate_final_score(
        self, factor_scores: Dict[str, float], rule_results: Dict[str, Any]
    ) -> float:
        """
        Calculate final risk score.

        Args:
            factor_scores: Calculated factor scores
            rule_results: Rule results

        Returns:
            Final risk score (0-100)
        """
        if not factor_scores:
            return 0.0

        # Simple averaging with rule modifiers
        base_score = sum(factor_scores.values()) / len(factor_scores)

        # Adjust based on triggered rules
        rule_modifier = sum(
            10 if result["triggered"] else 0 for result in rule_results.values()
        )

        final_score = min(100.0, max(0.0, base_score + rule_modifier))
        return round(final_score, 2)

    def _extract_features(self, entity_data: Dict[str, Any]) -> Optional[np.ndarray]:
        """
        Extract feature vector from entity data.

        Args:
            entity_data: Entity attributes

        Returns:
            Feature vector or None if extraction fails
        """
        try:
            # For now, return None since we don't have full 72-feature dataset
            # In production, this would extract/engineer all 72 features
            logger.debug("Feature extraction not yet implemented for entity_data dict")
            return None
        except Exception as e:
            logger.warning(f"Error extracting features: {e}")
            return None

    def _apply_ml_model(self, features: np.ndarray) -> Dict[str, Any]:
        """
        Apply ML models to get risk scores.

        Args:
            features: Feature vector (72 features)

        Returns:
            ML scoring results
        """
        try:
            if not self.model_loader:
                return {}

            results = {}

            # XGBoost prediction
            try:
                predictions, probabilities = self.model_loader.predict_xgboost(features)
                # Convert to 0-100 scale
                xgb_score = float(probabilities[0] * 100) if len(probabilities) > 0 else 0.0
                results["xgboost_prediction"] = int(predictions[0]) if len(predictions) > 0 else 0
                results["xgboost_probability"] = xgb_score
            except Exception as e:
                logger.warning(f"XGBoost prediction failed: {e}")

            # Isolation Forest anomaly detection
            try:
                if_predictions = self.model_loader.predict_isolation_forest(features)
                if_scores = self.model_loader.get_anomaly_scores(features)
                # Convert anomaly scores to 0-100 scale (more negative = more anomalous)
                anomaly_score = max(0, min(100, 50 + float(if_scores[0]) * 5))
                results["anomaly_prediction"] = int(if_predictions[0])
                results["anomaly_score"] = anomaly_score
            except Exception as e:
                logger.warning(f"Isolation Forest prediction failed: {e}")

            # SHAP explanation
            try:
                explanation = self.model_loader.explain_prediction(features, 0)
                if explanation:
                    results["shap_explanation"] = explanation
            except Exception as e:
                logger.debug(f"SHAP explanation failed: {e}")

            return results

        except Exception as e:
            logger.error(f"Error applying ML model: {e}")
            return {}

    def explain(self, entity_data: Dict[str, Any], entity_id: str = "") -> Dict[str, Any]:
        """
        Generate explanation for entity risk score.

        Args:
            entity_data: Entity attributes
            entity_id: Entity identifier

        Returns:
            Explanation with factors, rules, gates
        """
        try:
            factor_scores = self._calculate_factor_scores(entity_data)
            rule_results = self._apply_rules(entity_data, factor_scores)
            gate_results = self._apply_gates(entity_data, factor_scores, rule_results)

            # Build explanation
            explanation = {
                "entity_id": entity_id,
                "timestamp": datetime.utcnow().isoformat(),
                "factors": {
                    name: {
                        "value": score,
                        "weight": self.factor_weights.get(name, 1.0),
                        "weighted_contribution": score * self.factor_weights.get(name, 1.0)
                    }
                    for name, score in factor_scores.items()
                },
                "rules": {
                    name: {
                        "triggered": result["triggered"],
                        "description": next(
                            (r.get("description", "") for r in self.rules if r.get("name") == name),
                            ""
                        ),
                        "severity": next(
                            (r.get("severity", "") for r in self.rules if r.get("name") == name),
                            ""
                        )
                    }
                    for name, result in rule_results.items()
                },
                "gates": {
                    name: {
                        "passed": result["passed"],
                        "threshold": result["threshold"],
                        "value": result["value"],
                        "description": next(
                            (g.get("description", "") for g in self.gates if g.get("name") == name),
                            ""
                        )
                    }
                    for name, result in gate_results.items()
                }
            }

            return explanation

        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            return {"error": str(e)}

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information and configuration."""
        info = {
            "config_path": self.config_path,
            "factors_count": len(self.factors),
            "gates_count": len(self.gates),
            "rules_count": len(self.rules),
            "factors": [f.get("name") for f in self.factors],
            "gates": [g.get("name") for g in self.gates],
            "rules": [r.get("name") for r in self.rules],
            "factor_weights": self.factor_weights,
            "ml_models_available": self.ml_models_available,
        }

        if self.model_loader:
            info["ml_model_info"] = self.model_loader.get_model_info()

        return info
