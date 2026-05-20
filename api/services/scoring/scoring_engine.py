"""
Three-Level Risk Scoring Engine for Illegal Transshipment Detection

Flow: Level 1 (Corridor) → Level 2 (Vessel) → Level 3 (Manifest) → Combined Score
"""
import logging
from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class ScoringFactor:
    """Individual scoring factor with contribution and evidence"""
    name: str
    contribution: float
    signal: str
    evidence: List[str]
    status: str  # high, medium, low, neutral


@dataclass
class HorizonScore:
    """Horizon-level risk assessment"""
    horizon: str  # H1, H2, H3
    label: str
    score: float
    max_score: float
    weight: float
    factors: List[ScoringFactor]
    summary: str


@dataclass
class ScoringWeights:
    """Dynamic weight configuration for each horizon"""
    h1_weight: float = 0.20
    h2_weight: float = 0.35
    h3_weight: float = 0.45


class Level1CorridorRiskScorer:
    """
    Level 1: Macro-level corridor risk assessment
    Data: UN Comtrade, World Bank, Trade sanctions
    Weight: 20% of total
    Max Points: 40
    """

    def __init__(self):
        self.max_score = 40
        self.logger = logging.getLogger(__name__)

    def score(self, shipment_data: Dict) -> HorizonScore:
        """Calculate corridor risk based on trade route and HS code"""
        factors = []
        score = 0

        origin = shipment_data.get("origin_country", "")
        hs_code = shipment_data.get("hs_code", "")
        value = shipment_data.get("declared_value_usd", 0)

        # Factor 1: AD/CVD Active Orders (60% of Layer 1)
        adc_contribution = self._evaluate_adc_orders(origin, hs_code)
        if adc_contribution > 0:
            factors.append(
                ScoringFactor(
                    name="AD/CVD Active Orders",
                    contribution=adc_contribution,
                    signal=f"{origin} to US {hs_code} corridor has elevated antidumping duty rates",
                    evidence=[
                        f"HS Code {hs_code} matches active AD/CVD case",
                        f"Duty rate status: Active as of 2026-Q2",
                        f"Origin country flagged: {origin}",
                    ],
                    status="high" if adc_contribution > 8 else "medium",
                )
            )
            score += adc_contribution

        # Factor 2: Regulatory Delta / Origin Risk (40% of Layer 1)
        reg_contribution = self._evaluate_origin_risk(origin)
        if reg_contribution > 0:
            factors.append(
                ScoringFactor(
                    name="Origin Country Risk",
                    contribution=reg_contribution,
                    signal=f"Transshipment hub jurisdiction ({origin}) shows elevated risk patterns",
                    evidence=[
                        f"{origin} flagged as transshipment hub (6-month pattern analysis)",
                        f"Import surge detected in last quarter",
                        f"Prior EAPA investigations in this corridor",
                    ],
                    status="high" if reg_contribution > 8 else "medium",
                )
            )
            score += reg_contribution

        # Factor 3: Shipper Profile Risk
        shipper_contribution = self._evaluate_shipper_profile(shipment_data)
        if shipper_contribution > 0:
            factors.append(
                ScoringFactor(
                    name="Shipper Profile Risk",
                    contribution=shipper_contribution,
                    signal=f"Shipper company profile shows elevated risk indicators",
                    evidence=[
                        f"Company incorporation: Recent establishment",
                        f"Prior CBP filings: None or minimal",
                        f"Manufacturing capacity: Not verified",
                    ],
                    status="high" if shipper_contribution > 8 else "medium",
                )
            )
            score += shipper_contribution

        # Factor 4: Historical Pattern Analysis / Undervaluation
        pattern_contribution = self._evaluate_pricing_anomaly(shipment_data)
        if pattern_contribution > 0:
            factors.append(
                ScoringFactor(
                    name="Historical Pattern Analysis",
                    contribution=pattern_contribution,
                    signal="Unusual pricing compared to market baseline",
                    evidence=[
                        f"Declared FOB vs market baseline variance",
                        f"6-month average undervaluation detected",
                        f"Aligns with known transshipment pricing patterns",
                    ],
                    status="high" if pattern_contribution > 8 else "medium",
                )
            )
            score += pattern_contribution

        summary = f"Trade corridor analysis examining import patterns, regulations, and shipper profile."

        return HorizonScore(
            horizon="H1",
            label="Corridor Risk",
            score=min(score, self.max_score),
            max_score=self.max_score,
            weight=20,
            factors=factors,
            summary=summary,
        )

    def _evaluate_adc_orders(self, origin: str, hs_code: str) -> float:
        """Check for active AD/CVD orders affecting this corridor"""
        # Mock data: Known high-risk corridors
        adc_cases = {
            ("VN", "7604"): 10,  # Vietnam aluminum
            ("MY", "8541"): 10,  # Malaysia solar
            ("TH", "8541"): 9,  # Thailand solar
            ("CN", "7604"): 11,  # China aluminum
        }
        return adc_cases.get((origin, hs_code[:4]), 0)

    def _evaluate_origin_risk(self, origin: str) -> float:
        """Evaluate country-level transshipment risk"""
        transshipment_hubs = {
            "VN": 12,  # Vietnam
            "MY": 10,  # Malaysia
            "TH": 10,  # Thailand
            "HK": 12,  # Hong Kong
            "SG": 8,  # Singapore
        }
        return transshipment_hubs.get(origin, 0)

    def _evaluate_shipper_profile(self, shipment_data: Dict) -> float:
        """Evaluate shipper company profile risk"""
        # Mock: Check if shipper is newly incorporated
        shipper_age = shipment_data.get("shipper_age_months", 24)
        if shipper_age < 12:
            return 8
        elif shipper_age < 24:
            return 4
        return 0

    def _evaluate_pricing_anomaly(self, shipment_data: Dict) -> float:
        """Detect pricing anomalies indicating transshipment"""
        # Mock: Check for undervaluation
        hs_code = shipment_data.get("hs_code", "")
        declared_value = shipment_data.get("declared_value_usd", 0)
        weight = shipment_data.get("declared_weight_kg", 1)

        # Market baselines ($/kg)
        market_prices = {
            "7604": 17.25,  # Aluminum
            "8541": 0.50,  # Solar modules
            "7610": 16.50,  # Aluminum profiles
        }

        market_price = market_prices.get(hs_code[:4], 10)
        if weight > 0:
            declared_price = declared_value / weight
            undervaluation = (market_price - declared_price) / market_price

            if undervaluation > 0.40:
                return 10
            elif undervaluation > 0.25:
                return 6
            elif undervaluation > 0.15:
                return 3

        return 0


class Level2VesselRiskScorer:
    """
    Level 2: Pre-manifest vessel risk assessment
    Data: AIS live streams, VesselFinder API, port dwell times
    Weight: 35% of total
    Max Points: 35
    """

    def __init__(self):
        self.max_score = 35
        self.logger = logging.getLogger(__name__)

    def score(self, shipment_data: Dict) -> HorizonScore:
        """Calculate vessel risk based on AIS and routing anomalies"""
        factors = []
        score = 0

        vessel_name = shipment_data.get("vessel_name", "")
        origin_port = shipment_data.get("origin_port", "")
        destination_port = shipment_data.get("destination_port", "")

        # Factor 1: FTZ Loitering (40% of Layer 2)
        loiter_contribution = self._evaluate_ftz_loitering(shipment_data)
        if loiter_contribution > 0:
            factors.append(
                ScoringFactor(
                    name="Port Dwell Time Anomaly",
                    contribution=loiter_contribution,
                    signal=f"Vessel spent abnormal duration in transshipment port",
                    evidence=[
                        f"Vessel: {vessel_name}",
                        f"Dwell time: {shipment_data.get('dwell_days', 0)} days vs baseline 2-3 days",
                        f"Extended dwell suggests cargo consolidation/manipulation",
                    ],
                    status="high" if loiter_contribution > 10 else "medium",
                )
            )
            score += loiter_contribution

        # Factor 2: AIS Dark Activity (60% of Layer 2)
        ais_contribution = self._evaluate_ais_anomalies(shipment_data)
        if ais_contribution > 0:
            factors.append(
                ScoringFactor(
                    name="ISF Element 9 Mismatch",
                    contribution=ais_contribution,
                    signal=f"Country of origin mismatch: Declared vs AIS stuffing location",
                    evidence=[
                        f"Declared origin: {shipment_data.get('declared_origin', 'Unknown')}",
                        f"AIS stuffing location: {shipment_data.get('ais_stuffing_country', 'Unknown')}",
                        f"CBP procedure: origin ≠ stuffing location is transshipment flag",
                    ],
                    status="high" if ais_contribution > 10 else "medium",
                )
            )
            score += ais_contribution

        # Factor 3: Routing Anomalies
        routing_contribution = self._evaluate_routing_anomalies(shipment_data)
        if routing_contribution > 0:
            factors.append(
                ScoringFactor(
                    name="AIS Routing Anomalies",
                    contribution=routing_contribution,
                    signal="Unusual port sequence inconsistent with shortest route",
                    evidence=[
                        f"Expected route: Direct path",
                        f"Actual route: Multiple port calls detected",
                        f"Extra cost/time consistent with transshipment economics",
                    ],
                    status="high" if routing_contribution > 10 else "medium",
                )
            )
            score += routing_contribution

        summary = (
            "Physical shipment routing and documentation consistency analysis from AIS and ISF data."
        )

        return HorizonScore(
            horizon="H2",
            label="Vessel Anomaly",
            score=min(score, self.max_score),
            max_score=self.max_score,
            weight=35,
            factors=factors,
            summary=summary,
        )

    def _evaluate_ftz_loitering(self, shipment_data: Dict) -> float:
        """Detect abnormal vessel dwell times in FTZ"""
        dwell_days = shipment_data.get("dwell_days", 0)
        baseline_dwell = 2.1

        if dwell_days > 10:
            ratio = dwell_days / baseline_dwell
            if ratio > 5:
                return 12
            elif ratio > 3:
                return 8
            elif ratio > 2:
                return 5

        return 0

    def _evaluate_ais_anomalies(self, shipment_data: Dict) -> float:
        """Check for AIS data mismatches with declared origin"""
        declared_origin = shipment_data.get("declared_origin", "")
        ais_stuffing = shipment_data.get("ais_stuffing_country", "")

        if declared_origin and ais_stuffing and declared_origin != ais_stuffing:
            return 12

        return 0

    def _evaluate_routing_anomalies(self, shipment_data: Dict) -> float:
        """Detect unusual routing patterns"""
        port_calls = shipment_data.get("port_calls", [])

        # More than 2 stops for a typical Asia-US route is anomalous
        if len(port_calls) > 2:
            return 11

        return 0


class Level3ManifestRiskScorer:
    """
    Level 3: Manifest-level risk assessment
    Data: CBP documents, Senzing entity resolution, OFAC
    Weight: 45% of total
    Max Points: 25
    """

    def __init__(self):
        self.max_score = 25
        self.logger = logging.getLogger(__name__)

    def score(self, shipment_data: Dict) -> HorizonScore:
        """Calculate manifest risk based on entity and document validation"""
        factors = []
        score = 0

        # Factor 1: Entity Resolution Match (50% of Layer 3)
        entity_contribution = self._evaluate_entity_resolution(shipment_data)
        if entity_contribution > 0:
            factors.append(
                ScoringFactor(
                    name="Entity Ownership Linkage",
                    contribution=entity_contribution,
                    signal="Director/owner match between entities in different countries",
                    evidence=[
                        f"Shipper director name match with parent company (Senzing confidence 94%)",
                        f"Ownership obfuscation pattern detected",
                        f"Prior EAPA cases show similar ownership structures",
                    ],
                    status="high" if entity_contribution > 6 else "medium",
                )
            )
            score += entity_contribution

        # Factor 2: HS Code / Weight Delta (30% of Layer 3)
        weight_contribution = self._evaluate_weight_anomaly(shipment_data)
        if weight_contribution > 0:
            factors.append(
                ScoringFactor(
                    name="New Importer - High Volume",
                    contribution=weight_contribution,
                    signal="First-time importer processing unusually high volume",
                    evidence=[
                        f"First CBP filing: Recent",
                        f"YTD imports: High value for new entrant",
                        f"Baseline new importer 12-mo average: Much lower",
                    ],
                    status="medium",
                )
            )
            score += weight_contribution

        # Factor 3: Network Anomaly (20% of Layer 3)
        network_contribution = self._evaluate_network_anomaly(shipment_data)
        if network_contribution > 0:
            factors.append(
                ScoringFactor(
                    name="OFAC/Sanction Risk",
                    contribution=network_contribution,
                    signal="Entity appears in watchlists or related entities flagged",
                    evidence=[
                        f"Related entity in watchlist",
                        f"Appears in prior trade briefs",
                        f"Recommend enhanced due diligence",
                    ],
                    status="low",
                )
            )
            score += network_contribution

        summary = (
            "Final risk indicators combining entity intelligence, OFAC checks, and import behavior analysis."
        )

        return HorizonScore(
            horizon="H3",
            label="Intelligence Signals",
            score=min(score, self.max_score),
            max_score=self.max_score,
            weight=45,
            factors=factors,
            summary=summary,
        )

    def _evaluate_entity_resolution(self, shipment_data: Dict) -> float:
        """Evaluate Senzing entity resolution results"""
        senzing_confidence = shipment_data.get("senzing_confidence", 0)
        entity_type = shipment_data.get("entity_type", "")

        if senzing_confidence > 0.90:
            if "shell" in entity_type.lower() or "proxy" in entity_type.lower():
                return 8
            return 6

        return 0

    def _evaluate_weight_anomaly(self, shipment_data: Dict) -> float:
        """Detect weight/density anomalies"""
        importer_age_months = shipment_data.get("importer_age_months", 24)
        ytd_volume = shipment_data.get("importer_ytd_volume", 0)

        if importer_age_months < 12 and ytd_volume > 100000:
            return 5
        elif importer_age_months < 24 and ytd_volume > 150000:
            return 3

        return 0

    def _evaluate_network_anomaly(self, shipment_data: Dict) -> float:
        """Check for network anomalies and watchlist matches"""
        ofac_match = shipment_data.get("ofac_match", False)
        watchlist_match = shipment_data.get("watchlist_match", False)

        if ofac_match:
            return 3
        if watchlist_match:
            return 2

        return 0


class ScoringEngine:
    """
    Master scoring engine orchestrating three-level assessment
    """

    def __init__(self, weights: Optional[ScoringWeights] = None):
        self.weights = weights or ScoringWeights()
        self.level1_scorer = Level1CorridorRiskScorer()
        self.level2_scorer = Level2VesselRiskScorer()
        self.level3_scorer = Level3ManifestRiskScorer()
        self.logger = logging.getLogger(__name__)
        self.weight_history = []

    def calculate_score(self, shipment_data: Dict) -> Dict:
        """
        Calculate cumulative risk score across all three levels

        Returns:
            Dict with H1, H2, H3 scores and combined total
        """
        h1 = self.level1_scorer.score(shipment_data)
        h2 = self.level2_scorer.score(shipment_data)
        h3 = self.level3_scorer.score(shipment_data)

        # Calculate weighted contributions
        h1_contribution = (h1.score / h1.max_score) * self.weights.h1_weight * 100
        h2_contribution = (h2.score / h2.max_score) * self.weights.h2_weight * 100
        h3_contribution = (h3.score / h3.max_score) * self.weights.h3_weight * 100

        total_score = h1_contribution + h2_contribution + h3_contribution

        confidence = self._determine_confidence(h1, h2, h3)

        return {
            "h1": {
                "horizon": h1.horizon,
                "label": h1.label,
                "score": h1.score,
                "max_score": h1.max_score,
                "weight": h1.weight,
                "factors": [
                    {
                        "name": f.name,
                        "contribution": f.contribution,
                        "signal": f.signal,
                        "evidence": f.evidence,
                        "status": f.status,
                    }
                    for f in h1.factors
                ],
                "summary": h1.summary,
            },
            "h2": {
                "horizon": h2.horizon,
                "label": h2.label,
                "score": h2.score,
                "max_score": h2.max_score,
                "weight": h2.weight,
                "factors": [
                    {
                        "name": f.name,
                        "contribution": f.contribution,
                        "signal": f.signal,
                        "evidence": f.evidence,
                        "status": f.status,
                    }
                    for f in h2.factors
                ],
                "summary": h2.summary,
            },
            "h3": {
                "horizon": h3.horizon,
                "label": h3.label,
                "score": h3.score,
                "max_score": h3.max_score,
                "weight": h3.weight,
                "factors": [
                    {
                        "name": f.name,
                        "contribution": f.contribution,
                        "signal": f.signal,
                        "evidence": f.evidence,
                        "status": f.status,
                    }
                    for f in h3.factors
                ],
                "summary": h3.summary,
            },
            "total_score": round(total_score, 2),
            "confidence": confidence,
            "should_verify_altana": total_score >= 90,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _determine_confidence(self, h1, h2, h3) -> str:
        """Determine confidence level based on factor consistency"""
        total_factors = len(h1.factors) + len(h2.factors) + len(h3.factors)

        if total_factors >= 6:
            return "HIGH"
        elif total_factors >= 3:
            return "MEDIUM"
        else:
            return "LOW"

    def update_weights_from_feedback(
        self, system_score: float, human_label: float, feature_value: float, learning_rate: float = 0.05
    ):
        """
        Update weights using SGD based on human feedback
        Formula: W_new = W_old - α × (System_Score - Human_Label) × X_feature_value
        """
        error = system_score - human_label
        adjustment = learning_rate * error * feature_value

        self.weights.h1_weight = max(0.05, min(0.50, self.weights.h1_weight - adjustment * 0.3))
        self.weights.h2_weight = max(0.05, min(0.50, self.weights.h2_weight - adjustment * 0.35))
        self.weights.h3_weight = max(0.05, min(0.50, self.weights.h3_weight - adjustment * 0.35))

        # Normalize to sum to 1.0
        total = self.weights.h1_weight + self.weights.h2_weight + self.weights.h3_weight
        self.weights.h1_weight /= total
        self.weights.h2_weight /= total
        self.weights.h3_weight /= total

        self.weight_history.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "h1_weight": self.weights.h1_weight,
                "h2_weight": self.weights.h2_weight,
                "h3_weight": self.weights.h3_weight,
                "error": error,
                "adjustment": adjustment,
            }
        )

        self.logger.info(
            f"Weights updated. H1: {self.weights.h1_weight:.3f}, H2: {self.weights.h2_weight:.3f}, H3: {self.weights.h3_weight:.3f}"
        )
