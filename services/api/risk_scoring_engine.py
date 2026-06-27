"""
ML-Based Risk Scoring Engine
Calculates comprehensive transshipment risk scores with detailed breakdowns.

Integrates three ML models:
1. Isolation Forest - Detects AIS anomalies (dwell, rerouting, cost spikes)
2. LightGBM - Classifies transshipment patterns (legacy 8-feature model)
3. XGBoost - Primary transshipment classifier (36-feature clean model, calibrated)
"""

import json
import os
import math
import pickle
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import numpy as np
from risk_models import COUNTRY_ENCODING, RiskModelConfig, RiskComponentScore, RiskScoreBreakdown

logger = logging.getLogger(__name__)

# Load reference data at module level (cached by lru_cache)
try:
    from reference_loader import (
        get_adcvd_rate, get_corridor_norms, get_entity_age, get_adcvd_order,
        get_adcvd_order_by_country,
    )
    _REF_LOADED = True
    logger.info("Reference data loaded: AD/CVD, Comtrade corridors, VN entities")
except Exception as _ref_err:
    logger.warning(f"Reference data not available: {_ref_err}")
    _REF_LOADED = False
    def get_adcvd_rate(hs_code): return None
    def get_corridor_norms(hs_code): return None
    def get_entity_age(company_name): return None
    def get_adcvd_order(hs_code): return None
    def get_adcvd_order_by_country(origin_country, hs_code): return None


def _calibrate_prob_to_score(prob: float, cal: dict) -> float:
    """
    Map XGBoost probability to risk score [5,95].

    Uses percentile anchors from training distribution:
      prob ≥ p95 of training → score 90-95 (top 5%)
      prob ≥ p90 of training → score 85-90 (top 10%)
      prob ≥ p75 of training → score 70-85 (top 25%, high risk)
      prob ≥ p50 of training → score 50-70 (medium)
      below p50              → score 5-50  (low)
    Falls back to anchored linear if percentile anchors absent.
    """
    pct = cal.get("percentile_anchors", {})
    if pct:
        p50 = pct.get("p50", 0.001)
        p75 = pct.get("p75", 0.004)
        p90 = pct.get("p90", 0.021)
        p95 = pct.get("p95", 0.503)

        if prob >= p95:
            return float(min(95.0, 90.0 + (prob - p95) / max(1.0 - p95, 1e-9) * 5.0))
        if prob >= p90:
            return float(85.0 + (prob - p90) / max(p95 - p90, 1e-9) * 5.0)
        if prob >= p75:
            return float(70.0 + (prob - p75) / max(p90 - p75, 1e-9) * 15.0)
        if prob >= p50:
            return float(50.0 + (prob - p50) / max(p75 - p50, 1e-9) * 20.0)
        return float(max(5.0, 5.0 + prob / max(p50, 1e-9) * 45.0))

    # Legacy fallback: anchored linear
    low_p = cal["anchors"]["neg_95th_pct"]
    high_p = cal["anchors"]["pos_05th_pct"]
    low_s = cal["anchors"]["low_score"]
    high_s = cal["anchors"]["high_score"]
    if prob <= low_p:
        score = 5.0 + (prob / max(low_p, 1e-9)) * (low_s - 5.0)
    elif prob >= high_p:
        score = high_s + ((prob - high_p) / max(1.0 - high_p, 1e-9)) * (95.0 - high_s)
    else:
        score = low_s + ((prob - low_p) / max(high_p - low_p, 1e-9)) * (high_s - low_s)
    return float(min(95.0, max(5.0, score)))


class RiskScoringEngine:
    """
    Transshipment Risk Scoring Engine
    Implements multi-factor weighted model with ML model integration
    """

    def __init__(self):
        self.config = RiskModelConfig()
        # TODO: Switch from static config weights to feedback_engine.get_current_weights()
        # once the 7-factor DB-backed weight configuration is fully rolled out.
        self.feedback_weight_provider = None
        try:
            from feedback_engine import feedback_engine

            self.feedback_weight_provider = feedback_engine.get_current_weights
        except Exception:
            self.feedback_weight_provider = None
        self.factor_weights = self.config.get_factor_weights()

        # Load pre-trained ML models
        self.isolation_forest = None
        self.scaler = None
        self.lgbm_classifier = None
        self.xgboost_model = None
        self.score_calibration = None
        self._load_ml_models()

    def _load_ml_models(self):
        """Load pre-trained ML models for AIS anomaly detection and transshipment classification"""
        model_dir = Path(os.environ.get("MODEL_DIR", "/home/rahulvadera/cbp-sentry/models"))

        # Load Isolation Forest for AIS anomaly detection
        if_path = model_dir / "isolation_forest.pkl"
        scaler_path = model_dir / "scaler.pkl"

        if if_path.exists() and scaler_path.exists():
            try:
                with open(if_path, "rb") as f:
                    self.isolation_forest = pickle.load(f)
                with open(scaler_path, "rb") as f:
                    self.scaler = pickle.load(f)
                logger.info("✓ Loaded Isolation Forest model for AIS anomaly detection")
            except Exception as e:
                logger.warning(f"Failed to load Isolation Forest: {e}")

        # Load LightGBM for transshipment classification
        lgbm_path = model_dir / "lgbm_classifier.txt"
        if lgbm_path.exists():
            try:
                import lightgbm as lgb
                self.lgbm_classifier = lgb.Booster(model_file=str(lgbm_path))
                logger.info("✓ Loaded LightGBM model for transshipment classification")
            except Exception as e:
                logger.warning(f"Failed to load LightGBM: {e}")

        # Load XGBoost primary classifier + calibration (36-feature clean model)
        xgb_path = model_dir / "xgboost_model.json"
        cal_path = model_dir / "score_calibration.json"
        if xgb_path.exists() and cal_path.exists():
            try:
                import xgboost as xgb
                self.xgboost_model = xgb.Booster()
                self.xgboost_model.load_model(str(xgb_path))
                with open(cal_path) as f:
                    self.score_calibration = json.load(f)
                logger.info(
                    "✓ Loaded XGBoost model (%d features) + calibration",
                    self.score_calibration.get("feature_count", 0),
                )
            except Exception as e:
                logger.warning(f"Failed to load XGBoost model: {e}")

    def _score_with_xgboost(self, shipment: Dict) -> Tuple[float, float]:
        """
        Score shipment using XGBoost primary classifier with calibrated output.

        Returns:
            (calibrated_score: float [0,100], raw_probability: float [0,1])
            Returns (0.0, 0.0) if model unavailable — caller falls back to rule engine.
        """
        if self.xgboost_model is None or self.score_calibration is None:
            return 0.0, 0.0

        try:
            import xgboost as xgb
            from inference_features import extract_clean_features

            feature_vector = extract_clean_features(
                shipment, self.score_calibration["clean_features"]
            )
            dmatrix = xgb.DMatrix(
                feature_vector.reshape(1, -1),
                feature_names=self.score_calibration["clean_features"],
            )
            raw_prob = float(self.xgboost_model.predict(dmatrix)[0])
            calibrated = _calibrate_prob_to_score(raw_prob, self.score_calibration)
            return calibrated, raw_prob
        except Exception as e:
            logger.warning(f"XGBoost scoring failed: {e}")
            return 0.0, 0.0

    def _detect_ais_anomaly_ml(self, shipment: Dict) -> Tuple[bool, float]:
        """
        Use Isolation Forest to detect AIS dwell anomalies.

        Features: dwell_days, transit_days, cost_delta, rerouting_count

        Returns:
            (is_anomaly: bool, anomaly_score: float [-1, 1])
        """
        if self.isolation_forest is None or self.scaler is None:
            return False, 0.0

        try:
            dwell_days = float(shipment.get("dwell_days") or 0)
            transit_days = 20  # Typical transit time in days
            cost_delta = 0  # Would need historical price data
            rerouting_count = len(shipment.get("port_calls") or []) - 2  # ports - origin - dest

            # Create feature vector
            features = np.array([[dwell_days, transit_days, cost_delta, rerouting_count]])

            # Scale and predict
            features_scaled = self.scaler.transform(features)
            anomaly_score = self.isolation_forest.score_samples(features_scaled)[0]
            is_anomaly = self.isolation_forest.predict(features_scaled)[0] == -1

            logger.debug(f"AIS anomaly detection: dwell={dwell_days}d, score={anomaly_score:.3f}, anomaly={is_anomaly}")
            return is_anomaly, float(anomaly_score)
        except Exception as e:
            logger.warning(f"AIS anomaly detection failed: {e}")
            return False, 0.0

    def _classify_transshipment_ml(self, shipment: Dict) -> Tuple[float, bool]:
        """
        Use LightGBM to predict transshipment probability.

        Features: hts_6digit, country_origin_encoded, shipper_age_months, ad_duty_rate,
                  er_confidence, ais_anomaly_score, isf_stuffing_country, price_market_ratio

        Returns:
            (probability: float [0, 1], is_transshipment: bool)
        """
        if self.lgbm_classifier is None:
            return 0.0, False

        try:
            # Extract features
            hs_code = int(str(shipment.get("hs_code") or "0").replace(".", "")[:6])
            country_origin = self._encode_country(shipment.get("origin_country") or "US")
            shipper_age = float(shipment.get("shipper_age_months") or 12)
            ad_duty_rate = float(shipment.get("ad_cvd_rate") or 0) * 100
            er_confidence = 0.85  # Would need actual ER data
            ais_anomaly = -1.0 if (shipment.get("dwell_days") or 0) > 8 else 0.3  # From Isolation Forest
            isf_stuffing = 1 if shipment.get("element9_is_mismatch") else 0
            price_market_ratio = 0.95  # Would need actual pricing data

            # Create feature vector
            features = np.array(
                [
                    [
                        hs_code,
                        country_origin,
                        shipper_age,
                        ad_duty_rate,
                        er_confidence,
                        ais_anomaly,
                        isf_stuffing,
                        price_market_ratio,
                    ]
                ]
            )

            # Predict
            prob = self.lgbm_classifier.predict(features)[0]
            is_transshipment = prob > 0.5

            logger.debug(
                f"Transshipment classification: prob={prob:.3f}, predicted={'YES' if is_transshipment else 'NO'}"
            )
            return float(prob), is_transshipment
        except Exception as e:
            logger.warning(f"Transshipment classification failed: {e}")
            return 0.0, False

    @staticmethod
    def _encode_country(country_code: str) -> int:
        """Encode country codes to numeric for model input"""
        return COUNTRY_ENCODING.get((country_code or "").upper(), 0)

    def score_shipment(self, shipment: Dict[str, Any]) -> RiskScoreBreakdown:
        """
        Calculate comprehensive risk score for a shipment

        Args:
            shipment: Shipment data with all fields

        Returns:
            RiskScoreBreakdown with detailed component scores
        """
        components: List[RiskComponentScore] = []

        # 1. DOCUMENTATION RISK
        doc_components = self._score_documentation_risk(shipment)
        components.extend(doc_components)

        # 2. COMMODITY RISK
        commodity_components = self._score_commodity_risk(shipment)
        components.extend(commodity_components)

        # 3. ROUTING RISK
        routing_components = self._score_routing_risk(shipment)
        components.extend(routing_components)

        # 4. PARTY RISK
        party_components = self._score_party_risk(shipment)
        components.extend(party_components)

        # 5. CORRIDOR RISK (baseline)
        corridor_components = self._score_corridor_risk(shipment)
        components.extend(corridor_components)

        # 6. PATTERN ANOMALY RISK
        pattern_components = self._score_pattern_risk(shipment)
        components.extend(pattern_components)

        # 7. TIME SENSITIVITY
        time_components = self._score_time_sensitivity(shipment)
        components.extend(time_components)

        # Calculate subtotal (sum of weighted components)
        subtotal = sum(c.weighted_result for c in components)

        # ── Compound Risk Multiplier ────────────────────────────────────
        # When multiple critical indicators fire simultaneously, the risk
        # is non-additive — apply a compound multiplier to the rule score.
        critical_indicators = self._check_critical_indicators(shipment)
        n = len(critical_indicators)
        if n >= 5:
            compound_multiplier = 1.50
        elif n >= 4:
            compound_multiplier = 1.35
        elif n >= 3:
            compound_multiplier = 1.20
        elif n >= 2:
            compound_multiplier = 1.10
        else:
            compound_multiplier = 1.0
        rule_engine_score = min(subtotal * compound_multiplier, 100.0)

        # ── XGBoost as ADJUSTMENT DELTA (not primary score) ─────────────
        # Model maturity controls how much influence the ML model has.
        # At 15% maturity: small ±delta. At 90%+: larger, more confident delta.
        # This preserves the full 0-100 rule-engine range at all maturities.
        xgb_score, xgb_prob = self._score_with_xgboost(shipment)
        maturity = float(shipment.get("model_maturity") or 15) / 100.0
        if xgb_score > 0:
            xgb_delta = (xgb_score - 50.0) * maturity * 0.30
            blended_score = rule_engine_score + xgb_delta
            scoring_method = "rule_engine_ml_adjusted"
        else:
            blended_score = rule_engine_score
            scoring_method = "rule_engine"

        # Additional AIS dwell adjustments
        additional_adjustments = self._calculate_additional_adjustments(shipment)
        final_score = blended_score
        for adj in additional_adjustments or []:
            final_score += adj["adjustment_points"]

        # Cap at 100
        final_score = min(max(final_score, 0.0), 100.0)

        # ── Maturity-aware Confidence Interval ──────────────────────────
        # At 15% maturity → ±17 pts. At 90% maturity → ±2 pts.
        raw_maturity = float(shipment.get("model_maturity") or 15)
        ci_pts = round(20.0 * (1.0 - raw_maturity / 100.0))
        confidence = f"±{ci_pts}"

        breakdown = RiskScoreBreakdown(
            shipment_id=shipment.get("id", "UNKNOWN"),
            components=components,
            subtotal=subtotal,
            corridor_risk_adjustment=None,
            additional_adjustments=additional_adjustments,
            final_score=final_score,
            confidence_interval=confidence,
        )

        breakdown.calculation_table = self._generate_calculation_table(
            components,
            additional_adjustments,
            subtotal,
            final_score,
            xgb_score=xgb_score,
            xgb_prob=xgb_prob,
            scoring_method=scoring_method,
            compound_multiplier=compound_multiplier,
            critical_indicators=critical_indicators,
            rule_engine_score=rule_engine_score,
        )

        return breakdown

    def _check_critical_indicators(self, shipment: Dict) -> List[str]:
        """Return list of triggered critical risk indicators for compound scoring."""
        indicators = []

        if shipment.get("element9_is_mismatch") or shipment.get("isf_element_mismatch"):
            declared = shipment.get("element9_declared_country", "?")
            actual   = shipment.get("element9_actual_country", "?")
            indicators.append(f"ISF Element 9 origin mismatch ({declared} declared → {actual} actual)")

        ad_cvd = float(shipment.get("ad_cvd_rate") or 0)
        if ad_cvd >= 1.0:
            indicators.append(f"High AD/CVD tariff exposure ({ad_cvd * 100:.0f}%)")

        dwell = float(shipment.get("dwell_days") or 0)
        if dwell >= 10:
            indicators.append(f"Excessive dwell time ({dwell:.0f} days — transshipment window)")

        age = int(shipment.get("shipper_age_months") or 99)
        if age < 6:
            indicators.append(f"Newly established shipper ({age} months — evasion risk)")

        price_var = float(shipment.get("price_variance_percent") or 0)
        if price_var <= -40:
            indicators.append(f"Severely undervalued pricing ({price_var:.0f}% below benchmark)")
        elif price_var <= -20:
            indicators.append(f"Undervalued pricing ({price_var:.0f}% below benchmark)")

        return indicators

    def _generate_calculation_table(
        self,
        components: List[RiskComponentScore],
        additional_adj: List[Dict],
        subtotal: float,
        final_score: float,
        xgb_score: float = 0.0,
        xgb_prob: float = 0.0,
        scoring_method: str = "rule_engine",
        compound_multiplier: float = 1.0,
        critical_indicators: Optional[List[str]] = None,
        rule_engine_score: float = 0.0,
    ) -> Dict[str, Any]:
        """Generate detailed calculation breakdown table for transparency"""

        # Group components by factor
        by_factor = {}
        for comp in components:
            factor = comp.factor
            if factor not in by_factor:
                by_factor[factor] = {"components": [], "factor_total": 0}
            by_factor[factor]["components"].append(
                {
                    "name": comp.component,
                    "score": round(comp.score, 1),
                    "weight": round(comp.weight, 1),
                    "calculation": f"{comp.score:.1f}/10 × {comp.weight:.2f}",
                    "weighted_result": round(comp.weighted_result, 2),
                }
            )
            by_factor[factor]["factor_total"] += comp.weighted_result

        # Build factor summary table
        factor_summary = []
        for factor_name in ["Documentation", "Commodity", "Routing", "Party", "Corridor", "Pattern", "Time"]:
            if factor_name in by_factor:
                factor_data = by_factor[factor_name]
                factor_summary.append(
                    {
                        "factor": factor_name,
                        "components": len(factor_data["components"]),
                        "subtotal": round(factor_data["factor_total"], 2),
                        "percentage": f"{(factor_data['factor_total']/subtotal)*100:.1f}%",
                    }
                )

        # Build adjustment summary
        adjustments = []
        for adj in additional_adj or []:
            adjustments.append(
                {
                    "type": adj.get("adjustment_type", "Additional"),
                    "baseline": "-",
                    "multiplier": "-",
                    "points": adj.get("adjustment_points", 0),
                    "reason": adj.get("reason", ""),
                }
            )

        return {
            "scoring_method": scoring_method,
            "xgb_probability": round(xgb_prob, 4),
            "xgb_calibrated_score": round(xgb_score, 2),
            "rule_engine_subtotal": round(subtotal, 2),
            "compound_multiplier": round(compound_multiplier, 2),
            "rule_engine_score_after_multiplier": round(rule_engine_score, 2),
            "critical_indicators": critical_indicators or [],
            "critical_indicator_count": len(critical_indicators or []),
            "blend_weights": {
                "rules": 1.0,
                "xgb_delta": round(1.0 - 1.0 / compound_multiplier, 2) if compound_multiplier > 1 else 0.0,
            },
            "component_details": [
                {"factor": factor_name, "components": by_factor[factor_name]["components"]}
                for factor_name in ["Documentation", "Commodity", "Routing", "Party", "Corridor", "Pattern", "Time"]
                if factor_name in by_factor
            ],
            "factor_summary": factor_summary,
            "subtotal": round(subtotal, 2),
            "adjustments": adjustments,
            "final_score": round(final_score, 2),
            "calculation_steps": [
                {"step": 1, "description": "Rule engine component scores (18 factors)", "value": round(subtotal, 2)},
                {"step": 2, "description": f"Compound risk multiplier (×{compound_multiplier:.2f}, {len(critical_indicators or [])} critical indicators)", "value": round(rule_engine_score, 2)},
                {"step": 3, "description": "ML adjustment delta (XGBoost, maturity-weighted)", "value": round(xgb_score, 2)},
                {"step": 4, "description": "Final score (capped at 100)", "value": round(final_score, 2)},
            ],
        }

    # ========== FACTOR SCORING METHODS ==========

    def _score_documentation_risk(self, shipment: Dict) -> List[RiskComponentScore]:
        """Score documentation risk factors"""
        components = []
        config = self.config.DOCUMENTATION_RISK
        factor_weight = self.factor_weights["documentation"]

        # Element 9 Mismatch (50% of documentation risk)
        element9_mismatch = shipment.get("element9_is_mismatch", False)
        element9_score = 9.5 if element9_mismatch else 2.0
        components.append(
            RiskComponentScore(
                component="Element 9 Origin Mismatch",
                factor="Documentation",
                score=element9_score,
                weight=factor_weight * 0.50,
                weighted_result=(element9_score * factor_weight * 0.50) / 10,
                rationale="Declared origin differs from actual origin - critical fraud indicator",
                evidence=[
                    "element9_declared: " + str(shipment.get("element9_declared_country")),
                    "element9_actual: " + str(shipment.get("element9_actual_country")),
                ],
            )
        )

        # ISF Amendments (30% of documentation risk)
        isf_amendments = shipment.get("isf_amendments", 0)
        isf_score = min(2.0 + (isf_amendments * 2.5), 10.0)
        components.append(
            RiskComponentScore(
                component="ISF Amendments/Corrections",
                factor="Documentation",
                score=isf_score,
                weight=factor_weight * 0.30,
                weighted_result=(isf_score * factor_weight * 0.30) / 10,
                rationale=f"{isf_amendments} amendments filed post-transmission",
                evidence=[f"Amendments: {isf_amendments}", "Indicates correction of initial errors or concealment"],
            )
        )

        # Manifest Completeness (20% of documentation risk)
        manifest_score = self._assess_manifest_completeness(shipment)
        components.append(
            RiskComponentScore(
                component="Manifest Field Completeness",
                factor="Documentation",
                score=manifest_score,
                weight=factor_weight * 0.20,
                weighted_result=(manifest_score * factor_weight * 0.20) / 10,
                rationale="Manifest descriptions and formatting consistency",
                evidence=["Completeness check: " + str(manifest_score)],
            )
        )

        return components

    def _score_commodity_risk(self, shipment: Dict) -> List[RiskComponentScore]:
        """Score commodity sensitivity factors"""
        components = []
        config = self.config.COMMODITY_RISK
        factor_weight = self.factor_weights["commodity"]

        # Use commodity_code or fall back to hs_code, default to '9999'
        commodity_code_val = shipment.get("commodity_code") or shipment.get("hs_code") or "9999"
        commodity_code = str(commodity_code_val)[:4]
        commodity_name = shipment.get("commodity_name") or "General"

        # Find sensitivity level (config sensitivity_matrix — by commodity name)
        sensitivity = config["sensitivity_matrix"].get(
            (commodity_name or "General").lower(), {"base_risk": 5.0, "export_control": False, "ad_cvd_rate": 0}
        )

        # AD/CVD rate: prefer case data (DB column) → Federal Register → config fallback
        db_adcvd = shipment.get("ad_cvd_rate")
        if db_adcvd is not None and float(db_adcvd) > 0:
            # DB stores as decimal: 1.76 = 176%
            tariff_rate = float(db_adcvd) * 100
            tariff_source = "case data"
        else:
            real_rate = get_adcvd_rate(commodity_code_val)
            if real_rate is not None:
                tariff_rate = real_rate
                adcvd_order = get_adcvd_order(commodity_code_val)
                order_ref = f" (Order {adcvd_order['order_number']})" if adcvd_order else ""
                tariff_source = f"Federal Register{order_ref}"
            else:
                tariff_rate = sensitivity.get("ad_cvd_rate", 0)
                tariff_source = "config (no Federal Register match)"

        # Tariff Rate Risk (50% of commodity risk)
        # Calibrated: 200% AD/CVD → 10/10 (linear, capped)
        tariff_score = min(tariff_rate / 20.0, 10.0)
        tariff_evidence = [f"Commodity: {commodity_name}", f"HS Code: {commodity_code}", f"AD/CVD Rate: {tariff_rate}%"]
        tariff_rationale = f"HS {commodity_code}: {tariff_rate}% AD/CVD rate from {tariff_source}"

        # Real active-order signal: an active AD/CVD order for this (origin
        # country, HS) is a strong commodity-risk signal on its own, even when a
        # precise rate is unavailable. Source: live Federal Register pipeline.
        active_order = get_adcvd_order_by_country(shipment.get("origin_country"), commodity_code_val)
        if active_order:
            order_floor = {"AD/CVD": 8.0, "AD": 6.5, "CVD": 6.5}.get(active_order.get("order_type"), 6.0)
            tariff_score = max(tariff_score, order_floor)
            case_ref = active_order.get("case_number") or active_order.get("source_doc") or "Federal Register"
            tariff_rationale = (
                f"Active {active_order.get('order_type', 'AD/CVD')} order for "
                f"{shipment.get('origin_country')} {active_order.get('commodity') or commodity_name} "
                f"(HS {commodity_code}) — {case_ref}"
            )
            tariff_evidence.append(
                f"Active AD/CVD order ({active_order.get('order_type')}) — {case_ref}, "
                f"published {active_order.get('publication_date', 'n/a')}"
            )
            if active_order.get("source_url"):
                tariff_evidence.append(f"Source: {active_order['source_url']}")

        components.append(
            RiskComponentScore(
                component="Tariff Rate / AD-CVD Exposure",
                factor="Commodity",
                score=tariff_score,
                weight=factor_weight * 0.50,
                weighted_result=(tariff_score * factor_weight * 0.50) / 10,
                rationale=tariff_rationale,
                evidence=tariff_evidence,
            )
        )

        # Export Control (30% of commodity risk)
        export_control_score = 9.0 if sensitivity.get("export_control", False) else 2.0
        components.append(
            RiskComponentScore(
                component="Export Control Classification",
                factor="Commodity",
                score=export_control_score,
                weight=factor_weight * 0.30,
                weighted_result=(export_control_score * factor_weight * 0.30) / 10,
                rationale=(
                    "Commodity subject to EAR/ITAR export controls"
                    if sensitivity.get("export_control")
                    else "No export control classification"
                ),
                evidence=["Export Controlled" if sensitivity.get("export_control") else "Not Controlled"],
            )
        )

        # UFLPA Risk (20% of commodity risk)
        uflpa_score = 8.0 if sensitivity.get("uflpa_exposure", False) else 3.0
        components.append(
            RiskComponentScore(
                component="UFLPA Forced Labor Risk",
                factor="Commodity",
                score=uflpa_score,
                weight=factor_weight * 0.20,
                weighted_result=(uflpa_score * factor_weight * 0.20) / 10,
                rationale="Goods subject to forced labor presumption or enforcement risk",
                evidence=["UFLPA Exposure" if sensitivity.get("uflpa_exposure") else "No UFLPA Exposure"],
            )
        )

        return components

    def _score_routing_risk(self, shipment: Dict) -> List[RiskComponentScore]:
        """Score routing and logistics risk factors"""
        components = []
        config = self.config.ROUTING_RISK
        factor_weight = self.factor_weights["routing"]

        # AIS Dwell Anomaly (40% of routing risk)
        # Primary: threshold-based direct scoring from dwell_days DB column
        # Secondary: Isolation Forest adds signal if it detects anomaly
        dwell_days = float(shipment.get("dwell_days") or 0)
        if dwell_days >= 18:
            dwell_score = 9.5
            dwell_category = "CRITICAL"
        elif dwell_days >= 12:
            dwell_score = 7.5
            dwell_category = "SEVERE"
        elif dwell_days >= 8:
            dwell_score = 5.5
            dwell_category = "ELEVATED"
        elif dwell_days >= 4:
            dwell_score = 2.5
            dwell_category = "MODERATE"
        else:
            dwell_score = 1.0
            dwell_category = "NORMAL"

        # Isolation Forest provides corroborating signal
        is_ais_anomaly, anomaly_score = self._detect_ais_anomaly_ml(shipment)
        if is_ais_anomaly and dwell_score < 9.5:
            dwell_score = min(dwell_score * 1.20, 10.0)
            dwell_category += "+ML"

        components.append(
            RiskComponentScore(
                component="AIS Dwell Time Anomaly",
                factor="Routing",
                score=dwell_score,
                weight=factor_weight * 0.40,
                weighted_result=(dwell_score * factor_weight * 0.40) / 10,
                rationale=f"Vessel idle time: {dwell_days:.0f} days ({dwell_category})",
                evidence=[
                    f"Dwell: {dwell_days:.0f} days",
                    f"Category: {dwell_category}",
                    f'ML corroboration: {"ANOMALY" if is_ais_anomaly else "NORMAL"}',
                ],
            )
        )

        # Port Selection (30% of routing risk)
        port_calls = shipment.get("port_calls", []) or []
        hub_risk = any(hub in str(port_calls) for hub in ["SG", "HK", "LA", "PA"])
        port_score = 6.5 if hub_risk else 3.0
        components.append(
            RiskComponentScore(
                component="Transshipment Hub Selection",
                factor="Routing",
                score=port_score,
                weight=factor_weight * 0.30,
                weighted_result=(port_score * factor_weight * 0.30) / 10,
                rationale="Route includes known transshipment centers (Singapore, Hong Kong, LA, Panama)",
                evidence=["Port Calls: " + str(port_calls)],
            )
        )

        # Vessel Flag Risk (20% of routing risk)
        vessel_imo = shipment.get("vessel_imo", "")
        # Flag derived from IMO (simplified - in production would query IMO registry)
        flag_score = 6.0  # Default medium risk
        components.append(
            RiskComponentScore(
                component="Vessel Flag of Convenience",
                factor="Routing",
                score=flag_score,
                weight=factor_weight * 0.20,
                weighted_result=(flag_score * factor_weight * 0.20) / 10,
                rationale="Vessel flag state risk classification",
                evidence=["Vessel: " + str(shipment.get("vessel_name", "Unknown"))],
            )
        )

        # Routing Consistency (10% of routing risk) - covered by above
        return components

    def _score_party_risk(self, shipment: Dict) -> List[RiskComponentScore]:
        """Score party (shipper/importer) risk factors"""
        components = []
        config = self.config.PARTY_RISK
        factor_weight = self.factor_weights["party"]

        # Shipper Age (35% of party risk)
        # Use real VN entity age if available, fall back to DB field
        shipper_age_months = shipment.get("shipper_age_months") or 0
        shipper_name = shipment.get("shipper_name", "")
        origin_country = (shipment.get("origin_country") or "").upper()

        if not shipper_age_months and shipper_name and origin_country in ("VN", "VIETNAM"):
            ref_age = get_entity_age(shipper_name)
            if ref_age is not None:
                shipper_age_months = ref_age
                logger.debug(f"Party: used reference entity age {ref_age}mo for '{shipper_name}'")

        if shipper_age_months < 12:
            age_score = 9.0
            age_category = "NEW"
        elif shipper_age_months < 36:
            age_score = 6.5
            age_category = "EMERGING"
        else:
            age_score = 3.0
            age_category = "ESTABLISHED"

        components.append(
            RiskComponentScore(
                component="Shipper Age & Establishment",
                factor="Party",
                score=age_score,
                weight=factor_weight * 0.35,
                weighted_result=(age_score * factor_weight * 0.35) / 10,
                rationale=f"Shipper age: {shipper_age_months} months ({age_category})",
                evidence=[f"Age: {shipper_age_months} months"],
            )
        )

        # Prior Violations (30% of party risk)
        prior_violations = shipment.get("prior_violations", 0)
        violation_score = min(prior_violations * 2.5, 10.0)
        components.append(
            RiskComponentScore(
                component="Compliance History",
                factor="Party",
                score=violation_score,
                weight=factor_weight * 0.30,
                weighted_result=(violation_score * factor_weight * 0.30) / 10,
                rationale=f"{prior_violations} prior CBP violations or detentions",
                evidence=[f"Violations: {prior_violations}"],
            )
        )

        # OFAC/Sanctions (20% of party risk)
        ofac_status = shipment.get("ofac_status", "CLEAR")
        if ofac_status == "BLOCKED":
            ofac_score = 9.5
        elif ofac_status == "WATCH":
            ofac_score = 7.0
        else:
            ofac_score = 1.5
        components.append(
            RiskComponentScore(
                component="OFAC/Sanctions Exposure",
                factor="Party",
                score=ofac_score,
                weight=factor_weight * 0.20,
                weighted_result=(ofac_score * factor_weight * 0.20) / 10,
                rationale=f"OFAC Status: {ofac_status}",
                evidence=[f"Status: {ofac_status}"],
            )
        )

        # Beneficial Ownership (15% of party risk)
        ownership_opacity = shipment.get("ownership_opacity", False)
        ownership_score = 8.0 if ownership_opacity else 2.0
        components.append(
            RiskComponentScore(
                component="Corporate Structure Opacity",
                factor="Party",
                score=ownership_score,
                weight=factor_weight * 0.15,
                weighted_result=(ownership_score * factor_weight * 0.15) / 10,
                rationale="Difficulty verifying beneficial owner",
                evidence=["Hidden ownership" if ownership_opacity else "Clear ownership"],
            )
        )

        return components

    def _score_corridor_risk(self, shipment: Dict) -> List[RiskComponentScore]:
        """Score corridor and origin risk factors"""
        components = []
        config = self.config.CORRIDOR_RISK
        factor_weight = self.factor_weights["corridor"]

        origin = shipment.get("origin_country", "XX")[:2].upper()
        dest = shipment.get("destination_country", "XX")[:2].upper()
        corridor_key = f"{origin}→{dest}"

        corridor_data = config["corridors"].get(
            corridor_key, {"baseline_risk": 5.0, "tariff_rate": 0, "export_control": False, "multiplier": 1.0}
        )

        raw_baseline_score = corridor_data["baseline_risk"] * corridor_data.get("multiplier", 1.0)
        baseline_score = min(raw_baseline_score, 10.0)
        tariff_points = min(corridor_data["tariff_rate"] / 25 * 5, 5.0)

        components.append(
            RiskComponentScore(
                component="Country-of-Origin Risk",
                factor="Corridor",
                score=baseline_score,
                weight=factor_weight * 0.60,
                weighted_result=(baseline_score * factor_weight * 0.60) / 10,
                rationale=f'Corridor {corridor_key}: {corridor_data.get("primary_concern", "Unknown")}',
                evidence=[
                    f"Route: {corridor_key}",
                    f'Risk Profile: {corridor_data.get("risk_profile", "Unknown")}',
                    f"Baseline × multiplier: {corridor_data['baseline_risk']:.2f} × {corridor_data.get('multiplier', 1.0):.2f} = {raw_baseline_score:.2f}",
                    f'Multiplier Applied: {corridor_data.get("multiplier", 1.0):.2f}',
                    f'Tariff Rate: {corridor_data["tariff_rate"]}%',
                ],
            )
        )

        components.append(
            RiskComponentScore(
                component="Tariff Evasion Incentive",
                factor="Corridor",
                score=tariff_points,
                weight=factor_weight * 0.40,
                weighted_result=(tariff_points * factor_weight * 0.40) / 10,
                rationale=f"Tariff differential = {tariff_points:.1f} incentive points",
                evidence=[f'Tariff Rate: {corridor_data["tariff_rate"]}%'],
            )
        )

        return components

    # HS-family price benchmarks ($/kg) — fallback when Comtrade data unavailable
    _HS_PRICE_BASELINES = {
        "7604": 4.50,   # Aluminum extrusions
        "7610": 5.20,   # Aluminum structures
        "7611": 4.80,   # Aluminum reservoirs
        "7210": 0.85,   # Flat-rolled steel (coated)
        "7225": 0.90,   # Other flat-rolled steel
        "8541": 0.45,   # Solar panels / photovoltaic
        "8471": 8.00,   # Computers / ADP
        "8517": 12.00,  # Phones / telecom
        "6203": 15.00,  # Men's garments
        "6204": 13.00,  # Women's garments
        "3004": 50.00,  # Pharmaceuticals
        "2709": 0.40,   # Petroleum oils
    }

    def _score_pattern_risk(self, shipment: Dict) -> List[RiskComponentScore]:
        """Score historical pattern anomalies with ML corroboration"""
        components = []
        config = self.config.PATTERN_RISK
        factor_weight = self.factor_weights["pattern"]

        # Pricing Anomaly (50% of pattern risk)
        price_variance = shipment.get("price_variance_percent") or 0
        hs_code = shipment.get("hs_code") or shipment.get("commodity_code") or ""
        unit_price = shipment.get("unit_price_per_kg") or 0
        price_source = "manifest"

        if not price_variance and hs_code and unit_price:
            # Try Comtrade first
            corridor_norms = get_corridor_norms(hs_code)
            if corridor_norms and corridor_norms.get("avg_usd_per_kg"):
                baseline = corridor_norms["avg_usd_per_kg"]
                if baseline > 0:
                    price_variance = ((unit_price - baseline) / baseline) * 100
                    price_source = f"Comtrade VN→US baseline ${baseline:.2f}/kg"
            # Fallback: HS-family internal benchmark table
            if not price_variance:
                hs4 = str(hs_code)[:4]
                baseline = self._HS_PRICE_BASELINES.get(hs4)
                if baseline and baseline > 0:
                    price_variance = ((unit_price - baseline) / baseline) * 100
                    price_source = f"HS-{hs4} benchmark ${baseline:.2f}/kg"

        if price_variance < -50:
            pricing_score = 9.0
            pricing_cat = "SEVERE"
        elif price_variance < -20:
            pricing_score = 6.5
            pricing_cat = "HIGH"
        elif price_variance > 20:
            pricing_score = 4.0
            pricing_cat = "PREMIUM"
        else:
            pricing_score = 2.0
            pricing_cat = "NORMAL"

        components.append(
            RiskComponentScore(
                component="Unit Price vs Benchmark",
                factor="Pattern",
                score=pricing_score,
                weight=factor_weight * 0.50,
                weighted_result=(pricing_score * factor_weight * 0.50) / 10,
                rationale=f"Price variance: {price_variance:.1f}% ({pricing_cat}) vs {price_source}",
                evidence=[
                    f"Variance: {price_variance:.1f}%",
                    f'Unit Price: ${unit_price:.2f}/kg',
                ],
            )
        )

        # ML-Based Transshipment Pattern Detection (50% of pattern risk)
        transshipment_prob, is_transshipment = self._classify_transshipment_ml(shipment)
        # Convert probability [0, 1] to risk score [0, 10]
        ml_pattern_score = transshipment_prob * 10

        components.append(
            RiskComponentScore(
                component="Transshipment Pattern (ML)",
                factor="Pattern",
                score=ml_pattern_score,
                weight=factor_weight * 0.50,
                weighted_result=(ml_pattern_score * factor_weight * 0.50) / 10,
                rationale="LightGBM model predicts transshipment concealment based on historical patterns",
                evidence=[
                    f"Transshipment probability: {transshipment_prob:.1%}",
                    f'Prediction: {"TRANSSHIPMENT" if is_transshipment else "DIRECT"}',
                    f"Features: HS code, shipper age, AD/CVD rate, ISF mismatch",
                ],
            )
        )

        return components

    def _score_time_sensitivity(self, shipment: Dict) -> List[RiskComponentScore]:
        """Score time sensitivity factors"""
        components = []
        config = self.config.TIME_SENSITIVITY
        factor_weight = self.factor_weights["time"]

        # Simplified time sensitivity (would integrate with actual tariff calendars in production)
        time_score = 3.0  # Default low risk
        components.append(
            RiskComponentScore(
                component="Time Sensitivity Indicators",
                factor="Time",
                score=time_score,
                weight=factor_weight,
                weighted_result=(time_score * factor_weight) / 10,
                rationale="Timing relative to tariff changes and enforcement actions",
                evidence=["Filing Date: " + str(shipment.get("created_at", "Unknown"))],
            )
        )

        return components

    # ========== HELPER METHODS ==========

    def _assess_manifest_completeness(self, shipment: Dict) -> float:
        """Assess manifest field completeness (0-10 scale)"""
        required_fields = [
            "shipper_name",
            "consignee_name",
            "commodity_name",
            "commodity_code",
            "declared_weight_kg",
            "declared_value",
        ]
        completeness = sum(1 for field in required_fields if shipment.get(field)) / len(required_fields)
        # Score: 10 = complete, 2 = incomplete
        return 2.0 + (completeness * 8.0)

    def _calculate_corridor_adjustment(self, shipment: Dict, components: List[RiskComponentScore]) -> Dict:
        """Calculate Country-of-Origin Risk adjustment"""
        origin = shipment.get("origin_country", "XX")[:2].upper()
        dest = shipment.get("destination_country", "XX")[:2].upper()
        corridor_key = f"{origin}→{dest}"

        corridor_data = self.config.CORRIDOR_RISK["corridors"].get(corridor_key)
        if not corridor_data:
            return None

        baseline = corridor_data["baseline_risk"]
        multiplier = corridor_data.get("multiplier", 1.0)

        # Find corridor risk component
        corridor_component = next((c for c in components if c.component == "Country-of-Origin Risk"), None)
        if not corridor_component:
            return None

        adjustment_points = corridor_component.score * (multiplier - 1.0)

        return {
            "corridor": corridor_key,
            "baseline_risk": baseline,
            "multiplier": multiplier,
            "adjustment_points": adjustment_points,
            "reason": f"Country pair risk adjustment for {corridor_key}",
        }

    def _calculate_additional_adjustments(self, shipment: Dict) -> List[Dict]:
        """Calculate additional adjustments (AIS dwell, etc)"""
        adjustments = []

        # AIS dwell anomaly adjustment
        if "DWELL_ANOMALY" in (shipment.get("h2_signals", []) or []):
            dwell_points = min(shipment.get("dwell_anomaly_multiplier", 3) * 4, 16)
            adjustments.append(
                {
                    "type": "AIS Dwell Time Corroboration",
                    "adjustment_points": dwell_points,
                    "reason": f'AIS idle time {shipment.get("dwell_anomaly_multiplier", 3):.1f}x baseline',
                }
            )

        return adjustments if adjustments else None

    def _calculate_confidence_interval(self, components: List[RiskComponentScore], maturity: float = 15.0) -> str:
        """Confidence interval widens at lower model maturity. At 15% → ±17 pts, at 90% → ±2 pts."""
        ci_pts = round(20.0 * (1.0 - maturity / 100.0))
        return f"±{ci_pts}"
