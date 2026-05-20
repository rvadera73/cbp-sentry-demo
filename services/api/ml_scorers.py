"""
ML Models for H1 & H2 Scoring
"""
import logging
import numpy as np
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class H1CorridorRiskScorer:
    """Machine Learning model for Horizon 1 corridor risk scoring

    Factors:
    - Trade route (shipper country, consignee country)
    - Commodity (HS code, duty rate, AD/CVD)
    - Historical patterns (shipper age, prior filings)
    - Market pricing (declared value vs. benchmarks)
    """

    def __init__(self):
        self.name = "H1 Corridor Risk Scorer"
        self.max_score = 40  # H1 contributes max 40/100 points

    async def score(
        self,
        shipper_country: str,
        consignee_country: str,
        hs_code: str,
        declared_value: float,
        declared_weight_kg: float,
        shipper_info: Dict[str, Any],
        tariff_info: Dict[str, Any],
        benchmark_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Score corridor risk based on trade route and commodity"""

        score = 0
        factors = []

        # 1. COUNTRY PAIR RISK (0-12 points)
        # High-risk routes: CN→US, VN→US (transshipment concerns)
        country_pair = f"{shipper_country}-{consignee_country}"
        high_risk_pairs = ["CN-US", "VN-US", "TH-US", "MY-US"]
        if country_pair in high_risk_pairs:
            country_score = 12
            score += country_score
            factors.append({"name": "HIGH_RISK_CORRIDOR", "points": country_score, "route": country_pair})
        else:
            country_score = 4
            score += country_score
            factors.append({"name": "NORMAL_CORRIDOR", "points": country_score})

        # 2. DUTY RATE RISK (0-10 points)
        # High AD/CVD rates = higher evasion incentive
        ad_cv_rate = tariff_info.get("ad_cv_rate", 0)
        if ad_cv_rate > 2.0:  # 200%+ duty
            duty_score = 10
            factors.append({"name": "EXTREME_DUTY_RATE", "points": duty_score, "rate": ad_cv_rate})
        elif ad_cv_rate > 1.0:  # 100%+ duty
            duty_score = 7
            factors.append({"name": "HIGH_DUTY_RATE", "points": duty_score, "rate": ad_cv_rate})
        elif ad_cv_rate > 0.2:  # 20%+ duty
            duty_score = 3
            factors.append({"name": "MODERATE_DUTY_RATE", "points": duty_score})
        else:
            duty_score = 0
            factors.append({"name": "LOW_DUTY_RATE", "points": 0})

        score += duty_score

        # 3. SHIPPER RISK (0-8 points)
        # New or suspicious companies
        incorporation_date = shipper_info.get("incorporation_date")
        if incorporation_date:
            company_age_years = (datetime.now() - datetime.fromisoformat(incorporation_date.split("T")[0])).days / 365
            if company_age_years < 2:
                shipper_score = 8
                factors.append({"name": "SHIPPER_AGE_CONCERN", "points": shipper_score, "age_years": company_age_years})
            elif company_age_years < 5:
                shipper_score = 4
                factors.append({"name": "SHIPPER_YOUNG", "points": shipper_score, "age_years": company_age_years})
            else:
                shipper_score = 0
        else:
            shipper_score = 3  # Unknown shipper
            factors.append({"name": "SHIPPER_UNKNOWN", "points": shipper_score})

        score += shipper_score

        # 4. PRICING RISK (0-10 points)
        # Declared value significantly below market
        benchmark_price = benchmark_data.get("benchmark_unit_price_usd_per_kg", 0)
        declared_unit_price = declared_value / declared_weight_kg if declared_weight_kg > 0 else 0
        pricing_score = 0

        if benchmark_price > 0:
            price_ratio = declared_unit_price / benchmark_price
            if price_ratio < 0.6:  # 40% below market = extreme
                pricing_score = 10
                factors.append({"name": "EXTREME_UNDERVALUATION", "points": pricing_score, "ratio": round(price_ratio, 2)})
            elif price_ratio < 0.75:  # 25% below market = suspicious
                pricing_score = 6
                factors.append({"name": "SUSPICIOUS_UNDERVALUATION", "points": pricing_score, "ratio": round(price_ratio, 2)})
            elif price_ratio < 0.9:  # 10% below market = notable
                pricing_score = 2
                factors.append({"name": "SLIGHT_UNDERVALUATION", "points": pricing_score})
            else:
                pricing_score = 0
                factors.append({"name": "NORMAL_PRICING", "points": 0})

            score += pricing_score

        # Normalize to 0-40 range
        final_score = min(score, self.max_score)

        return {
            "horizon": "H1",
            "score": final_score,
            "max_score": self.max_score,
            "factors": factors,
            "breakdown": {
                "corridor_risk": country_score,
                "duty_risk": duty_score,
                "shipper_risk": shipper_score,
                "pricing_risk": pricing_score,
            },
        }


class H2AnomalyScorer:
    """Machine Learning model for Horizon 2 anomaly detection

    Detects shipping pattern anomalies:
    - AIS dwell anomalies
    - ISF Element 9 contradictions
    - Unusual routing
    - AIS signal gaps
    """

    def __init__(self):
        self.name = "H2 Anomaly Scorer"
        self.max_score = 35  # H2 contributes max 35/100 points

    async def score(
        self,
        vessel_data: Dict[str, Any],
        isf_data: Dict[str, Any],
        port_calls: list,
    ) -> Dict[str, Any]:
        """Score shipping pattern anomalies"""

        score = 0
        anomalies = []

        # 1. AIS DWELL ANOMALY (0-12 points)
        dwell_anomaly_percentile = vessel_data.get("dwell_anomaly_percentile", 50)
        dwell_days = vessel_data.get("port_dwell_days", 0)
        baseline_days = vessel_data.get("baseline_dwell_days", 2)
        anomaly_ratio = dwell_days / baseline_days if baseline_days > 0 else 1

        if anomaly_ratio > 5:
            dwell_score = 12
            anomalies.append({"name": "EXTREME_DWELL_ANOMALY", "points": dwell_score, "ratio": round(anomaly_ratio, 1), "percentile": dwell_anomaly_percentile})
        elif anomaly_ratio > 3:
            dwell_score = 8
            anomalies.append({"name": "HIGH_DWELL_ANOMALY", "points": dwell_score, "ratio": round(anomaly_ratio, 1)})
        elif anomaly_ratio > 1.8:
            dwell_score = 4
            anomalies.append({"name": "MODERATE_DWELL_ANOMALY", "points": dwell_score})
        else:
            dwell_score = 0

        score += dwell_score

        # 2. ISF ELEMENT 9 MISMATCH (0-12 points)
        declared_origin = isf_data.get("declared_origin", "")
        actual_stuffing = isf_data.get("actual_stuffing_location", "")
        isf_confidence = isf_data.get("confidence", 0)

        if declared_origin and actual_stuffing and declared_origin != actual_stuffing:
            if isf_confidence > 0.95:
                isf_score = 12
                anomalies.append({"name": "ISF_ELEMENT_9_MISMATCH", "points": isf_score, "declared": declared_origin, "actual": actual_stuffing, "confidence": isf_confidence})
            elif isf_confidence > 0.80:
                isf_score = 8
                anomalies.append({"name": "ISF_ELEMENT_9_DISCREPANCY", "points": isf_score, "confidence": isf_confidence})
            else:
                isf_score = 3
                anomalies.append({"name": "ISF_ELEMENT_9_POSSIBLE_MISMATCH", "points": isf_score})
        else:
            isf_score = 0

        score += isf_score

        # 3. AIS SIGNAL GAPS (0-6 points)
        ais_gaps = vessel_data.get("ais_gaps", 0)
        if ais_gaps > 3:
            gap_score = 6
            anomalies.append({"name": "EXTREME_AIS_GAPS", "points": gap_score, "gaps": ais_gaps})
        elif ais_gaps > 1:
            gap_score = 3
            anomalies.append({"name": "NOTABLE_AIS_GAPS", "points": gap_score})
        else:
            gap_score = 0

        score += gap_score

        # 4. UNUSUAL ROUTING (0-5 points)
        # Check for unexpected port sequences
        routing_flag = vessel_data.get("routing_flag")
        if routing_flag:
            routing_score = 5
            anomalies.append({"name": routing_flag, "points": routing_score})
        else:
            routing_score = 0

        score += routing_score

        final_score = min(score, self.max_score)

        return {
            "horizon": "H2",
            "score": final_score,
            "max_score": self.max_score,
            "anomalies": anomalies,
            "breakdown": {
                "dwell_anomaly": dwell_score,
                "isf_mismatch": isf_score,
                "ais_gaps": gap_score,
                "routing_anomaly": routing_score,
            },
        }
