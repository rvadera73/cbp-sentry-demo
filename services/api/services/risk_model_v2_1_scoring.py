"""
Risk Model v2.1 Scoring Function (Legacy Rule-Based Model)

The v2.1 model is a deterministic rule-based system that scored shipments
using fixed weighted factors without ML components. This implementation
provides backward compatibility for model comparison and analysis.

Framework: Rule-based deterministic scoring
Factors: 3 primary factors (corridor_score, vessel_score, manifest_score)
Weights: Fixed at 110% total (legacy overweighting artifact)
Output: Score 0-100, factor breakdown
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FactorScore:
    """Individual factor score breakdown"""
    factor_name: str
    raw_score: float  # 0-10 scale
    weight: float  # 0-1
    weighted_contribution: float  # raw_score * weight
    evidence: List[str]  # Supporting evidence


@dataclass
class V21ScoringResult:
    """Complete v2.1 scoring result"""
    shipment_id: str
    score: float  # 0-100
    factors: List[FactorScore]
    confidence: Optional[float]  # Always None for rule-based (no ML)
    calculation_details: Dict[str, Any]
    timestamp: str


class RiskModelV21Scorer:
    """Legacy v2.1 rule-based risk scoring model"""

    # ========================================================================
    # FACTOR 1: CORRIDOR RISK (Weight: 0.40)
    # ========================================================================
    # Baseline country-pair risk assessment
    CORRIDOR_SCORES = {
        "CN->US": 8.5,    # China to US: highest risk (origin concealment)
        "VN->US": 7.0,    # Vietnam to US: high risk (tariff evasion)
        "MY->US": 6.5,    # Malaysia to US: medium-high (forced labor)
        "CA->US": 4.5,    # Canada to US: low risk (USMCA)
        "SG->US": 5.0,    # Singapore to US: medium (transshipment hub)
        "MX->US": 3.5,    # Mexico to US: low (USMCA)
        "TH->US": 6.0,    # Thailand to US: medium
        "IN->US": 5.5,    # India to US: medium
        "JP->US": 3.0,    # Japan to US: very low (trusted partner)
        "KR->US": 3.5,    # South Korea to US: low
    }
    CORRIDOR_WEIGHT = 0.40

    # ========================================================================
    # FACTOR 2: VESSEL RISK (Weight: 0.35)
    # ========================================================================
    # Shipping logistics risk factors
    VESSEL_WEIGHT = 0.35

    # High-risk vessel flags
    HIGH_RISK_FLAGS = {"PA", "KH", "MM", "MH", "KP"}  # Panama, Cambodia, Myanmar, Marshall Is, N Korea
    VESSEL_FLAG_PENALTY = 3.0  # +3 points for high-risk flags

    # High-risk ports
    HIGH_RISK_PORTS = {"SG", "HK", "LA", "PA"}  # Known transshipment hubs
    PORT_SELECTION_PENALTY = 2.5  # +2.5 points for hub selection

    # Dwell time anomaly detection
    DWELL_BASELINE_HOURS = 48  # Typical transshipment: ~2 days
    DWELL_ANOMALY_MULTIPLIER = 5.0  # >5x baseline = anomaly

    # ========================================================================
    # FACTOR 3: MANIFEST RISK (Weight: 0.35)
    # ========================================================================
    # Documentation and commodity-level risk
    MANIFEST_WEIGHT = 0.35

    # Commodity sensitivity scores
    COMMODITY_SCORES = {
        "semiconductors": 8.5,
        "aluminum_extrusions": 7.0,
        "solar_equipment": 7.5,
        "machinery": 6.0,
        "chemicals": 6.5,
        "textiles": 5.5,
        "electronics": 7.0,
        "computers": 8.0,
        "medical_devices": 6.0,
        "precision_instruments": 6.5,
    }

    # Documentation quality penalties
    MISSING_ISF = 3.0  # Missing ISF filing
    ELEMENT_9_MISMATCH = 4.0  # Element 9 (origin) mismatch
    MANIFEST_INCOMPLETE = 2.0  # Missing field information

    @staticmethod
    def score_corridor(origin: str, destination: str) -> Tuple[float, List[str]]:
        """Score based on origin-destination corridor risk.

        Args:
            origin: ISO 2-letter country code
            destination: ISO 2-letter country code

        Returns:
            Tuple of (score 0-10, evidence list)
        """
        corridor_key = f"{origin}->{destination}"

        # Try exact match first
        if corridor_key in RiskModelV21Scorer.CORRIDOR_SCORES:
            score = RiskModelV21Scorer.CORRIDOR_SCORES[corridor_key]
            return score, [f"Corridor match: {corridor_key} = {score}"]

        # Try reverse lookup (e.g., "CN->*" for any to China)
        origin_corridors = {
            k: v for k, v in RiskModelV21Scorer.CORRIDOR_SCORES.items()
            if k.startswith(f"{origin}->")
        }
        if origin_corridors:
            avg_score = sum(origin_corridors.values()) / len(origin_corridors)
            return avg_score, [f"Origin baseline: {origin} = {avg_score:.1f}"]

        # Default: medium risk
        return 5.0, ["No specific corridor data, using medium baseline"]

    @staticmethod
    def score_vessel(
        vessel_flag: Optional[str] = None,
        port_of_call: Optional[str] = None,
        dwell_hours: Optional[float] = None
    ) -> Tuple[float, List[str]]:
        """Score vessel and routing risk.

        Args:
            vessel_flag: ISO 2-letter vessel flag
            port_of_call: ISO 2-letter transshipment port
            dwell_hours: Hours spent at transshipment port

        Returns:
            Tuple of (score 0-10, evidence list)
        """
        score = 3.0  # Base score for standard shipping
        evidence = []

        # Penalize high-risk flags
        if vessel_flag and vessel_flag.upper() in RiskModelV21Scorer.HIGH_RISK_FLAGS:
            score += RiskModelV21Scorer.VESSEL_FLAG_PENALTY
            evidence.append(f"High-risk flag {vessel_flag}: +{RiskModelV21Scorer.VESSEL_FLAG_PENALTY}")

        # Penalize transshipment hubs
        if port_of_call and port_of_call.upper() in RiskModelV21Scorer.HIGH_RISK_PORTS:
            score += RiskModelV21Scorer.PORT_SELECTION_PENALTY
            evidence.append(f"Transshipment hub {port_of_call}: +{RiskModelV21Scorer.PORT_SELECTION_PENALTY}")

        # Detect dwell time anomalies
        if dwell_hours:
            if dwell_hours > RiskModelV21Scorer.DWELL_BASELINE_HOURS * RiskModelV21Scorer.DWELL_ANOMALY_MULTIPLIER:
                anomaly_penalty = min(3.0, dwell_hours / RiskModelV21Scorer.DWELL_BASELINE_HOURS / 10)
                score += anomaly_penalty
                evidence.append(f"Dwell time anomaly {dwell_hours}h (baseline {RiskModelV21Scorer.DWELL_BASELINE_HOURS}h): +{anomaly_penalty:.1f}")

        # Clamp to 0-10
        score = min(10.0, score)

        if not evidence:
            evidence.append("Standard vessel and routing profile")

        return score, evidence

    @staticmethod
    def score_manifest(
        commodity_type: Optional[str] = None,
        has_isf: bool = True,
        element_9_match: bool = True,
        manifest_complete: bool = True,
        declared_value: Optional[float] = None,
        unit_price: Optional[float] = None
    ) -> Tuple[float, List[str]]:
        """Score manifest and commodity risk.

        Args:
            commodity_type: Type of commodity being shipped
            has_isf: Whether ISF (Importer Security Filing) is complete
            element_9_match: Whether declared origin matches manifest
            manifest_complete: Whether all required fields are present
            declared_value: Total declared value
            unit_price: Unit price of commodity

        Returns:
            Tuple of (score 0-10, evidence list)
        """
        score = 2.0  # Low base score for good documentation
        evidence = []

        # Commodity sensitivity
        commodity_key = commodity_type.lower().replace(" ", "_") if commodity_type else None
        if commodity_key and commodity_key in RiskModelV21Scorer.COMMODITY_SCORES:
            commodity_score = RiskModelV21Scorer.COMMODITY_SCORES[commodity_key]
            score += commodity_score * 0.5  # Weight commodity at 50% of manifest factor
            evidence.append(f"Commodity {commodity_key}: base score {commodity_score}, contribution +{commodity_score * 0.5:.1f}")

        # Documentation penalties
        if not has_isf:
            score += RiskModelV21Scorer.MISSING_ISF
            evidence.append(f"Missing ISF: +{RiskModelV21Scorer.MISSING_ISF}")

        if not element_9_match:
            score += RiskModelV21Scorer.ELEMENT_9_MISMATCH
            evidence.append(f"Element 9 (origin) mismatch: +{RiskModelV21Scorer.ELEMENT_9_MISMATCH}")

        if not manifest_complete:
            score += RiskModelV21Scorer.MANIFEST_INCOMPLETE
            evidence.append(f"Incomplete manifest: +{RiskModelV21Scorer.MANIFEST_INCOMPLETE}")

        # Price anomaly detection
        if declared_value and unit_price:
            # Check for underpricing (common evasion tactic)
            if unit_price < 10:  # Very low unit price indicator
                score += 2.0
                evidence.append(f"Low unit price indicator: +2.0")

        # Clamp to 0-10
        score = min(10.0, score)

        if not evidence:
            evidence.append("Standard commodity and documentation profile")

        return score, evidence

    @classmethod
    def score_shipment(
        cls,
        shipment_id: str,
        origin: str,
        destination: str,
        commodity_type: Optional[str] = None,
        vessel_flag: Optional[str] = None,
        port_of_call: Optional[str] = None,
        dwell_hours: Optional[float] = None,
        has_isf: bool = True,
        element_9_match: bool = True,
        manifest_complete: bool = True,
        declared_value: Optional[float] = None,
        unit_price: Optional[float] = None,
    ) -> V21ScoringResult:
        """Score a shipment using v2.1 rule-based model.

        This function implements the deterministic rule-based scoring that v2.1
        used before transition to ML-based models.

        Args:
            shipment_id: Unique shipment identifier
            origin: ISO 2-letter country code of origin
            destination: ISO 2-letter country code of destination
            commodity_type: Type of commodity
            vessel_flag: Vessel flag country
            port_of_call: Transshipment port
            dwell_hours: Hours at transshipment port
            has_isf: ISF filing complete
            element_9_match: Origin declaration matches manifest
            manifest_complete: All required fields present
            declared_value: Total declared value
            unit_price: Per-unit price

        Returns:
            V21ScoringResult with score, factors, and evidence
        """

        # Calculate corridor risk
        corridor_score, corridor_evidence = cls.score_corridor(origin, destination)
        corridor_factor = FactorScore(
            factor_name="Corridor Risk",
            raw_score=corridor_score,
            weight=cls.CORRIDOR_WEIGHT,
            weighted_contribution=corridor_score * cls.CORRIDOR_WEIGHT,
            evidence=corridor_evidence
        )

        # Calculate vessel risk
        vessel_score, vessel_evidence = cls.score_vessel(
            vessel_flag=vessel_flag,
            port_of_call=port_of_call,
            dwell_hours=dwell_hours
        )
        vessel_factor = FactorScore(
            factor_name="Vessel Risk",
            raw_score=vessel_score,
            weight=cls.VESSEL_WEIGHT,
            weighted_contribution=vessel_score * cls.VESSEL_WEIGHT,
            evidence=vessel_evidence
        )

        # Calculate manifest risk
        manifest_score, manifest_evidence = cls.score_manifest(
            commodity_type=commodity_type,
            has_isf=has_isf,
            element_9_match=element_9_match,
            manifest_complete=manifest_complete,
            declared_value=declared_value,
            unit_price=unit_price
        )
        manifest_factor = FactorScore(
            factor_name="Manifest Risk",
            raw_score=manifest_score,
            weight=cls.MANIFEST_WEIGHT,
            weighted_contribution=manifest_score * cls.MANIFEST_WEIGHT,
            evidence=manifest_evidence
        )

        # Calculate composite score (0-100)
        # Note: Sum of weights = 1.1 (110% due to legacy overweighting)
        factors = [corridor_factor, vessel_factor, manifest_factor]
        total_weighted = sum(f.weighted_contribution for f in factors)

        # Normalize to 0-100 scale
        # With 110% weight sum, the maximum possible score is 10 * 1.1 = 11
        # So we normalize: (total_weighted / 11) * 100 to get 0-100 scale
        max_possible_score = 10.0 * 1.1
        composite_score = (total_weighted / max_possible_score) * 100
        composite_score = min(100.0, max(0.0, composite_score))  # Clamp to 0-100

        # Build calculation details
        calculation_details = {
            "weights_sum": 1.1,
            "normalization_factor": 1.1,
            "methodology": "Deterministic rule-based scoring with 3 primary factors",
            "factor_contributions": {
                "corridor": {
                    "raw_score": corridor_score,
                    "weight": cls.CORRIDOR_WEIGHT,
                    "contribution": corridor_score * cls.CORRIDOR_WEIGHT,
                },
                "vessel": {
                    "raw_score": vessel_score,
                    "weight": cls.VESSEL_WEIGHT,
                    "contribution": vessel_score * cls.VESSEL_WEIGHT,
                },
                "manifest": {
                    "raw_score": manifest_score,
                    "weight": cls.MANIFEST_WEIGHT,
                    "contribution": manifest_score * cls.MANIFEST_WEIGHT,
                },
            },
            "total_weighted_sum": total_weighted,
            "final_score": composite_score,
        }

        return V21ScoringResult(
            shipment_id=shipment_id,
            score=round(composite_score, 1),
            factors=factors,
            confidence=None,  # Rule-based models have no confidence
            calculation_details=calculation_details,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )


def score_with_v2_1(
    shipment_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Convenience function to score a shipment with v2.1.

    Args:
        shipment_data: Dictionary with shipment details

    Returns:
        Dictionary with v2.1 score, factors, and metadata
    """

    result = RiskModelV21Scorer.score_shipment(
        shipment_id=shipment_data.get("shipment_id", "unknown"),
        origin=shipment_data.get("origin", "unknown"),
        destination=shipment_data.get("destination", "US"),
        commodity_type=shipment_data.get("commodity_type"),
        vessel_flag=shipment_data.get("vessel_flag"),
        port_of_call=shipment_data.get("port_of_call"),
        dwell_hours=shipment_data.get("dwell_hours"),
        has_isf=shipment_data.get("has_isf", True),
        element_9_match=shipment_data.get("element_9_match", True),
        manifest_complete=shipment_data.get("manifest_complete", True),
        declared_value=shipment_data.get("declared_value"),
        unit_price=shipment_data.get("unit_price"),
    )

    # Convert to JSON-serializable format
    return {
        "shipment_id": result.shipment_id,
        "score": result.score,
        "factors": [
            {
                "factor_name": f.factor_name,
                "raw_score": round(f.raw_score, 2),
                "weight": f.weight,
                "weighted_contribution": round(f.weighted_contribution, 2),
                "evidence": f.evidence,
            }
            for f in result.factors
        ],
        "confidence": result.confidence,
        "calculation_details": result.calculation_details,
        "timestamp": result.timestamp,
    }
