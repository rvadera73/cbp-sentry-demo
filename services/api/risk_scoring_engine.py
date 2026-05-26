"""
ML-Based Risk Scoring Engine
Calculates comprehensive transshipment risk scores with detailed breakdowns.

Integrates two ML models:
1. Isolation Forest - Detects AIS anomalies (dwell, rerouting, cost spikes)
2. LightGBM - Classifies transshipment patterns
"""

import math
import pickle
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import numpy as np
from risk_models import RiskModelConfig, RiskComponentScore, RiskScoreBreakdown

logger = logging.getLogger(__name__)


class RiskScoringEngine:
    """
    Transshipment Risk Scoring Engine
    Implements multi-factor weighted model with ML model integration
    """

    def __init__(self):
        self.config = RiskModelConfig()
        self.factor_weights = self.config.get_factor_weights()

        # Load pre-trained ML models
        self.isolation_forest = None
        self.scaler = None
        self.lgbm_classifier = None
        self._load_ml_models()

    def _load_ml_models(self):
        """Load pre-trained ML models for AIS anomaly detection and transshipment classification"""
        model_dir = Path(__file__).parent / "models"

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
        # Note: LightGBM models are loaded at prediction time with lgb.Booster()
        lgbm_path = model_dir / "lgbm_classifier.txt"
        if lgbm_path.exists():
            try:
                import lightgbm as lgb

                self.lgbm_classifier = lgb.Booster(model_file=str(lgbm_path))
                logger.info("✓ Loaded LightGBM model for transshipment classification")
            except Exception as e:
                logger.warning(f"Failed to load LightGBM: {e}")

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
        encoding = {"CN": 5, "VN": 6, "MY": 7, "TH": 8, "SG": 3, "US": 1, "CA": 2, "MX": 4, "AE": 9, "HK": 10}
        return encoding.get(country_code, 0)

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

        # Calculate adjustments
        corridor_adjustment = self._calculate_corridor_adjustment(shipment, components)
        additional_adjustments = self._calculate_additional_adjustments(shipment)

        # Final score calculation
        final_score = subtotal
        if corridor_adjustment:
            final_score += corridor_adjustment["adjustment_points"]
        for adj in additional_adjustments or []:
            final_score += adj["adjustment_points"]

        # Cap at 100
        final_score = min(final_score, 100.0)

        # Calculate confidence interval (±uncertainty)
        confidence = self._calculate_confidence_interval(components)

        breakdown = RiskScoreBreakdown(
            shipment_id=shipment.get("id", "UNKNOWN"),
            components=components,
            subtotal=subtotal,
            corridor_risk_adjustment=corridor_adjustment,
            additional_adjustments=additional_adjustments,
            final_score=final_score,
            confidence_interval=confidence,
        )

        # Generate detailed calculation table for transparency
        breakdown.calculation_table = self._generate_calculation_table(
            components, corridor_adjustment, additional_adjustments, subtotal, final_score
        )

        return breakdown

    def _generate_calculation_table(
        self,
        components: List[RiskComponentScore],
        corridor_adj: Dict,
        additional_adj: List[Dict],
        subtotal: float,
        final_score: float,
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
        if corridor_adj:
            adjustments.append(
                {
                    "type": corridor_adj.get("reason", "Corridor Adjustment"),
                    "baseline": round(corridor_adj.get("baseline", 0), 2),
                    "multiplier": round(corridor_adj.get("multiplier", 1.0), 2),
                    "points": round(corridor_adj.get("adjustment_points", 0), 2),
                    "reason": corridor_adj.get("reason", ""),
                }
            )

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
                {"step": 1, "description": "Calculate component scores", "value": round(subtotal, 2)},
                {
                    "step": 2,
                    "description": "Apply adjustments",
                    "value": round(sum(a.get("points", 0) for a in adjustments), 2),
                },
                {"step": 3, "description": "Final score (capped at 100)", "value": round(final_score, 2)},
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

        # Find sensitivity level
        sensitivity = config["sensitivity_matrix"].get(
            (commodity_name or "General").lower(), {"base_risk": 5.0, "export_control": False, "ad_cvd_rate": 0}
        )

        # Tariff Rate Risk (50% of commodity risk)
        tariff_rate = sensitivity.get("ad_cvd_rate", 0)
        tariff_score = min(tariff_rate / 500 * 10, 10.0)
        components.append(
            RiskComponentScore(
                component="Tariff Rate / AD-CVD Exposure",
                factor="Commodity",
                score=tariff_score,
                weight=factor_weight * 0.50,
                weighted_result=(tariff_score * factor_weight * 0.50) / 10,
                rationale=f"HS {commodity_code}: {tariff_rate}% tariff rate = {tariff_rate}% evasion incentive",
                evidence=[f"Commodity: {commodity_name}", f"HS Code: {commodity_code}", f"AD/CVD Rate: {tariff_rate}%"],
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

        # AIS Dwell Anomaly (40% of routing risk) - USE ML MODEL
        is_ais_anomaly, anomaly_score = self._detect_ais_anomaly_ml(shipment)
        # Convert ML anomaly score [-1, 1] to risk score [0, 10]
        dwell_score = 9.0 if is_ais_anomaly else (max(0, (anomaly_score + 1) / 2 * 3))  # Map to 0-3 range for normal
        dwell_days = shipment.get("dwell_days", 0)

        components.append(
            RiskComponentScore(
                component="AIS Dwell Time Anomaly",
                factor="Routing",
                score=dwell_score,
                weight=factor_weight * 0.40,
                weighted_result=(dwell_score * factor_weight * 0.40) / 10,
                rationale="Isolation Forest ML model detects vessel idle time anomalies",
                evidence=[
                    f"Dwell: {dwell_days} days",
                    f"ML anomaly score: {anomaly_score:.3f}",
                    f'Prediction: {"ANOMALY" if is_ais_anomaly else "NORMAL"}',
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
        shipper_age_months = shipment.get("shipper_age_months") or 0
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

        baseline_score = corridor_data["baseline_risk"]
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

    def _score_pattern_risk(self, shipment: Dict) -> List[RiskComponentScore]:
        """Score historical pattern anomalies with ML corroboration"""
        components = []
        config = self.config.PATTERN_RISK
        factor_weight = self.factor_weights["pattern"]

        # Pricing Anomaly (50% of pattern risk)
        price_variance = shipment.get("price_variance_percent") or 0
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
                rationale=f"Price variance: {price_variance:.1f}% ({pricing_cat})",
                evidence=[
                    f"Variance: {price_variance:.1f}%",
                    f'Unit Price: ${shipment.get("unit_price_per_kg", 0):.2f}/kg',
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

    def _calculate_confidence_interval(self, components: List[RiskComponentScore]) -> str:
        """Calculate confidence interval for score"""
        # Simplified: ±2.5 for high confidence, ±5 for lower
        uncertainty = 2.5 if len(components) >= 15 else 5.0
        return f"±{uncertainty:.1f}"
